import streamlit as st
st.set_page_config(page_title="Strava Dashboard", layout="wide")
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone as dt_timezone
import pytz
import math
import plotly.express as px
from weight_tracker import run_weight_tracker
import operator
import gspread
from google.oauth2 import service_account
import plotly.graph_objects as go

st.title("\U0001F3C3 Live Strava Mileage Dashboard")

# --- WEIGHT TRACKING ---
st.markdown("---")
run_weight_tracker()

# --- STRAVA CREDENTIALS ---
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REFRESH_TOKEN = st.secrets["REFRESH_TOKEN"]

# --- REFRESH ACCESS TOKEN ---
def get_access_token():
    response = requests.post("https://www.strava.com/api/v3/oauth/token", data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': REFRESH_TOKEN
    })

    data = response.json()

    if "access_token" in data:
        return data["access_token"]
    else:
        st.error("\u274C Failed to get access token from Strava:")
        st.json(data)
        print("STRAVA ERROR RESPONSE:", data)
        st.stop()

access_token = get_access_token()
if not access_token:
    st.stop()

# --- FETCH ACTIVITIES ---
def fetch_strava_data(access_token, max_activities=200):
    url = "https://www.strava.com/api/v3/athlete/activities"
    response = requests.get(url, headers={
        "Authorization": f"Bearer {access_token}"
    }, params={"per_page": max_activities})

    activities = response.json()
    if isinstance(activities, list):
        df = pd.DataFrame(activities)
        df = df[df["type"].isin(["Run", "VirtualRun"])]
        return df
    else:
        st.error("\u274C Failed to fetch activities:")
        st.json(activities)
        print("FETCH ERROR RESPONSE:", activities)
        st.stop()

df = fetch_strava_data(access_token)

# --- CLEAN + FORMAT ---
df["start_date_local"] = pd.to_datetime(df["start_date_local"], errors='coerce').dt.tz_localize(None)
df["formatted_date"] = df["start_date_local"].dt.strftime("%A %d %Y, %H:%M:%S")
df["week_start"] = df["start_date_local"].dt.to_period("W").apply(lambda r: r.start_time)
df["distance_miles"] = (df["distance"] / 1609.34).round(2)

# Ensure clean datetime for merge later
df["start_date_local"] = pd.to_datetime(df["start_date_local"], errors='coerce')


def seconds_to_hhmmss(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"

def speed_to_pace_mile(speed_mps):
    if speed_mps == 0:
        return "00:00"
    pace_seconds = 1609.34 / speed_mps
    return f"{int(pace_seconds // 60):02}:{int(pace_seconds % 60):02}"

df["moving_time"] = df["moving_time"].apply(seconds_to_hhmmss)
df["pace"] = df["average_speed"].apply(speed_to_pace_mile)

# --- WEEKLY MILEAGE SUMMARY ---
weekly_mileage = df.groupby("week_start")["distance_miles"].sum().reset_index()
weekly_mileage.columns = ["Week Starting", "Total Miles"]
weekly_mileage["Number of Runs"] = df.groupby("week_start").size().values

# --- DATETIME SETUP ---
today = datetime.now(dt_timezone.utc).replace(tzinfo=None)
start_of_this_week = (today - timedelta(days=today.weekday())).replace(tzinfo=None)
start_of_last_week = (start_of_this_week - timedelta(days=7)).replace(tzinfo=None)
end_of_last_week = (start_of_this_week - timedelta(seconds=1)).replace(tzinfo=None)

# --- SMART WEEKLY MILEAGE RECOMMENDATION ---
weekly_mileage["Week Starting"] = pd.to_datetime(weekly_mileage["Week Starting"])
start_of_this_week_naive = pd.Timestamp(start_of_this_week).tz_localize(None)
completed_weeks = weekly_mileage[weekly_mileage["Week Starting"] < start_of_this_week_naive]
last_4_weeks = completed_weeks.sort_values("Week Starting").tail(4)

if not last_4_weeks.empty:
    avg_mileage = last_4_weeks["Total Miles"].mean()
    suggested_mileage = math.ceil(avg_mileage * 1.15)
else:
    avg_mileage = 0
    suggested_mileage = 0

# --- THIS WEEK vs LAST WEEK DAYS ---
last_week_runs = df[(df["start_date_local"] >= start_of_last_week) & (df["start_date_local"] <= end_of_last_week)]
this_week_runs = df[(df["start_date_local"] >= start_of_this_week) & (df["start_date_local"] <= today)]

days_this_week = this_week_runs["start_date_local"].dt.date.nunique()
days_last_week = last_week_runs["start_date_local"].dt.date.nunique()

# --- DISPLAY SECTIONS ---
st.subheader("\U0001F4C5 Weekly Consistency Tracker")
col1, col2 = st.columns(2)

with col1:
    st.metric(label="\U0001F3C3‍♂️ Days Run This Week", value=f"{days_this_week} / 7")
with col2:
    st.metric(label="\U0001F4C9 Days Run Last Week", value=f"{days_last_week} / 7")

# --- SMART RECOMMENDATION METRICS ---
this_week_total_miles = this_week_runs["distance_miles"].sum()
remaining_miles = max(suggested_mileage - this_week_total_miles, 0)
percent_complete = min((this_week_total_miles / suggested_mileage) * 100 if suggested_mileage else 0, 100)
above_avg_pct = ((this_week_total_miles - avg_mileage) / avg_mileage) * 100 if avg_mileage else 0

if above_avg_pct > 30:
    card_color = "#ffcccc"
    emoji = "🔴"
elif above_avg_pct > 20:
    card_color = "#d4edda"
    emoji = "🟢"
else:
    card_color = "#f8f9fa"
    emoji = "⚪"

st.markdown(
    f"""
    <div style="background-color: {card_color}; padding: 20px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 20px;">
        <h4 style="margin-top: 0;">{emoji} Weekly Progress Summary</h4>
        <ul style="list-style: none; padding-left: 0; font-size: 16px;">
            <li><strong>4-Week Avg:</strong> {avg_mileage:.2f} mi</li>
            <li><strong>Target Mileage:</strong> {suggested_mileage:.2f} mi</li>
            <li><strong>Total This Week:</strong> {this_week_total_miles:.2f} mi</li>
            <li><strong>Remaining:</strong> {remaining_miles:.2f} mi</li>
            <li><strong>Progress:</strong> {percent_complete:.0f}%</li>
        </ul>
        <div style="margin-top: 10px;">
            <progress value="{percent_complete}" max="100" style="width: 100%; height: 20px;"></progress>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- GOALS SECTION ---
st.subheader("🎯 My Long Term Goal: Place Top Ten in a Centurion 50 mile Ultra within the next 5 years.")

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["google_sheets"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
try:
    sheet = gc.open("WeightTracker").worksheet("Goals")
    current_goals = sheet.col_values(1)
except:
    sheet = gc.open("WeightTracker").add_worksheet(title="Goals", rows="100", cols="1")
    current_goals = []

st.markdown("📌 Short-Term Goals to achieve long term goal")
for goal in current_goals:
    st.markdown(f"- {goal}")

with st.expander("✍️ Update My Goals"):
    new_goals_input = st.text_area("Update your goals (one per line):", value="\n".join(current_goals), height=150)
    if st.button("Save Goals"):
        sheet.clear()
        sheet.update("A1", [[goal] for goal in new_goals_input.split("\n") if goal.strip()])
        st.success("Goals updated!")

# --- DAILY MILEAGE TABLE CALENDAR ---
daily_mileage = df.groupby(df["start_date_local"].dt.normalize())["distance_miles"].sum().reset_index()
daily_mileage.columns = ["Date", "Miles"]

end_date = df["start_date_local"].max().date()
start_date = end_date - timedelta(weeks=5)

calendar_df = pd.DataFrame({"Date": pd.date_range(start=start_date, end=end_date, freq="D")})
calendar_df = calendar_df.merge(daily_mileage, on="Date", how="left").fillna(0)
calendar_df["Day"] = calendar_df["Date"].dt.day_name()
calendar_df["Week"] = calendar_df["Date"].apply(lambda d: f"{(d - timedelta(days=d.weekday())).strftime('%d %b')} - {(d + timedelta(days=6 - d.weekday())).strftime('%d %b')}")
calendar_df["Week Start"] = calendar_df["Date"] - pd.to_timedelta(calendar_df["Date"].dt.weekday, unit="D")
calendar_df["Week Label"] = calendar_df["Week Start"].dt.strftime("%-d %b") + " - " + (calendar_df["Week Start"] + pd.Timedelta(days=6)).dt.strftime("%-d %b")

pivot = calendar_df.pivot(index="Week", columns="Day", values="Miles").fillna(0).sort_index(ascending=False)
days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
pivot = pivot[days_order]
weeks = pivot.index.tolist()
days = pivot.columns.tolist()

fig = go.Figure()
cell_width, cell_height = 1, 1

for i, week in enumerate(weeks):
    for j, day in enumerate(days):
        miles = pivot.loc[week, day]
        x0, x1 = j, j + cell_width
        y0, y1 = -i, -i + cell_height

        if miles > 0:
            fig.add_shape(
                type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                fillcolor="#3F9C35", line=dict(width=1, color="white")
            )
            fig.add_annotation(
                x=x0 + 0.5, y=y0 + 0.5,
                text=f"<b>{miles:.2f}</b>",
                showarrow=False, font=dict(color="white", size=14),
                xanchor="center", yanchor="middle"
            )
        else:
            fig.add_shape(
                type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                fillcolor="white", line=dict(width=1, color="#ccc")
            )
            fig.add_annotation(
                x=x0 + 0.5, y=y0 + 0.5,
                text="REST", showarrow=False,
                font=dict(color="#888", size=12),
                xanchor="center", yanchor="middle"
            )

# Create weekly summary to use in row labels
weekly_stats = calendar_df.groupby("Week Label").agg(
    Total_Miles=("Miles", "sum"),
    Total_Runs=("Miles", lambda x: (x > 0).sum())
).reset_index()


stats = weekly_stats[weekly_stats["Week Label"] == week].iloc[0]
label = f"<b>{week}</b><br>Total Miles: {int(stats.Total_Miles)}<br>Total Runs: {int(stats.Total_Runs)}"
fig.add_annotation(
    x=-0.5, y=y0 + 0.5, text=label, showarrow=False,
    font=dict(size=13, color="black"), align="right",
    xanchor="right", yanchor="middle"
)

fig.update_xaxes(
    tickvals=[i + 0.5 for i in range(len(days))],
    ticktext=days,
    showgrid=False, zeroline=False,
    tickfont=dict(size=14, color="black")
)
fig.update_yaxes(visible=False)

fig.update_layout(
    title="\U0001F4C5 Last 5 Weeks – Daily Mileage Calendar",
    xaxis=dict(showline=False),
    yaxis=dict(showticklabels=False),
    width=1600,
    height=len(weeks) * 70 + 100,
    margin=dict(t=60, l=220, r=30, b=30),
    plot_bgcolor="white",
    paper_bgcolor="white"
)

st.plotly_chart(fig, use_container_width=True)


# --- RAW DATA ---
st.subheader("\U0001F4DD Recent Runs")
df["start_date_local"] = df["start_date_local"].dt.strftime("%A %d %Y, %H:%M:%S")
df_display = df[["name", "start_date_local", "distance_miles", "moving_time", "pace"]].copy()
df_display.index = df_display.index + 1

df_display.index.name = "#"
st.dataframe(df_display)
