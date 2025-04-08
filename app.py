import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
import math
import plotly.express as px

# Streamlit page config
st.set_page_config(page_title="Strava Dashboard", layout="wide")
st.title("\U0001F3C3 Live Strava Mileage Dashboard")

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
df["week_start"] = df["start_date_local"].dt.tz_localize(None).dt.to_period("W").apply(lambda r: r.start_time)
df["distance_miles"] = (df["distance"] / 1609.34).round(2)

# Time and pace formatting
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
utc = pytz.UTC
today = utc.localize(datetime.today())
start_of_this_week = today - timedelta(days=today.weekday())
start_of_last_week = start_of_this_week - timedelta(days=7)
end_of_last_week = start_of_this_week - timedelta(seconds=1)

# --- SMART WEEKLY MILEAGE RECOMMENDATION ---
# Make sure 'Week Starting' column is in datetime (naive)
weekly_mileage["Week Starting"] = pd.to_datetime(weekly_mileage["Week Starting"])

# Set start of this week as naive datetime
start_of_this_week_naive = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=datetime.utcnow().weekday())

# Exclude current week
completed_weeks = weekly_mileage[weekly_mileage["Week Starting"] < start_of_this_week_naive]

# Get the latest 4 complete weeks
last_4_weeks = completed_weeks.sort_values("Week Starting").tail(4)

# Calculate average + suggested target
if not last_4_weeks.empty:
    avg_mileage = last_4_weeks["Total Miles"].mean()
    suggested_mileage = math.ceil(avg_mileage * 1.15)
else:
    avg_mileage = 0
    suggested_mileage = 0


# --- THIS WEEK vs LAST WEEK DAYS ---
df["start_date_local"] = pd.to_datetime(df["start_date_local"], errors='coerce').dt.tz_localize(None)

today = datetime.utcnow()
start_of_this_week = today - timedelta(days=today.weekday())
start_of_last_week = start_of_this_week - timedelta(days=7)
end_of_last_week = start_of_this_week - timedelta(seconds=1)

last_week_runs = df[
    (df["start_date_local"] >= start_of_last_week) &
    (df["start_date_local"] <= end_of_last_week)
]

this_week_runs = df[
    (df["start_date_local"] >= start_of_this_week) &
    (df["start_date_local"] <= today)
]

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
st.subheader("\U0001F4A1 Suggested Mileage")
col5, col6 = st.columns(2)

with col5:
    st.metric(label="\U0001F4CA 4-Week Average", value=f"{avg_mileage:.2f} miles")

with col6:
    st.metric(label="\U0001F680 This Week Target Mileage (+15%)", value=f"{suggested_mileage:.2f} miles")

# Keep only the last year  of weekly mileage
weekly_mileage_trimmed = weekly_mileage.tail(52)


# --- WEEKLY MILEAGE CHART (Plotly) ---
st.subheader("📈 Weekly Mileage Chart (Interactive)")

fig = px.line(
    weekly_mileage_trimmed,
    x="Week Starting",
    y="Total Miles",
    markers=True,
    title="Weekly Running Mileage",
    labels={"Total Miles": "Miles"},
    hover_data={"Total Miles": True, "Week Starting": True}
)

# Add suggested mileage as a horizontal line
fig.add_hline(
    y=suggested_mileage,
    line_dash="dash",
    line_color="green",
    annotation_text=f"Next Week Target: {suggested_mileage}mi",
    annotation_position="top left"
)

# Optional: static 20mi line
fig.add_hline(
    y=20,
    line_dash="dot",
    line_color="red",
    annotation_text="Static 20mi Goal",
    annotation_position="top right"
)

fig.update_layout(
    xaxis_title="Week Starting",
    yaxis_title="Total Miles",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

# --- RAW DATA ---
st.subheader("\U0001F4DD Recent Runs")
st.dataframe(df[["name", "start_date_local", "distance_miles", "moving_time", "pace"]])