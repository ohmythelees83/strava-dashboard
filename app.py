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
gspread
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
df["distance_miles"] = (df["distance"] / 1609.34).round(2)

# --- DAILY MILEAGE TABLE CALENDAR ---
end_date = df["start_date_local"].max().normalize()
start_date = end_date - timedelta(weeks=5)
date_range = pd.date_range(start=start_date, end=end_date)

# Group by exact date only
daily_mileage = df.groupby(df["start_date_local"].dt.normalize())["distance_miles"].sum().reset_index()
daily_mileage.columns = ["Date", "Miles"]
daily_mileage["Date"] = pd.to_datetime(daily_mileage["Date"])

calendar_df = pd.DataFrame({"Date": date_range})
calendar_df["Date"] = pd.to_datetime(calendar_df["Date"])
calendar_df = calendar_df.merge(daily_mileage, on="Date", how="left")
calendar_df["Miles"] = calendar_df["Miles"].fillna(0).round(2)
calendar_df["Day"] = calendar_df["Date"].dt.day_name()
calendar_df["Week Start"] = calendar_df["Date"] - pd.to_timedelta(calendar_df["Date"].dt.weekday, unit="D")
calendar_df["Week Label"] = calendar_df["Week Start"].dt.strftime("%-d %b") + " - " + (calendar_df["Week Start"] + pd.Timedelta(days=6)).dt.strftime("%-d %b")

weekly_stats = calendar_df.groupby("Week Label").agg(
    Total_Miles=("Miles", "sum"),
    Total_Runs=("Miles", lambda x: (x > 0).sum())
).reset_index()

pivot = calendar_df.pivot(index="Week Label", columns="Day", values="Miles").fillna(0)
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
                font=dict(color="gray", size=12),
                xanchor="center", yanchor="middle"
            )

    stats = weekly_stats[weekly_stats["Week Label"] == week]
    if not stats.empty:
        s = stats.iloc[0]
        label = f"<b>{week}</b><br>Total Miles: {int(s.Total_Miles)}<br>Total Runs: {int(s.Total_Runs)}"
        fig.add_annotation(
            x=-0.6, y=y0 + 0.5, text=label, showarrow=False,
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
    title="\U0001F4C5 <b>Last 5 Weeks – Daily Mileage Calendar</b>",
    title_font=dict(size=20, color="black"),
    xaxis=dict(showline=False),
    yaxis=dict(showticklabels=False),
    width=1600,
    height=len(weeks) * 80 + 100,
    margin=dict(t=80, l=240, r=30, b=30),
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
