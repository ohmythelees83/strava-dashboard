import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
import math

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
df["start_date_local"] = pd.to_datetime(df["start_date_local"], errors='coerce')
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
# Use only the most recent 4 complete weeks (excluding this week)
completed_weeks = weekly_mileage[weekly_mileage["Week Starting"] < start_of_this_week.replace(tzinfo=None)]
last_4_weeks = completed_weeks.tail(4)

if not last_4_weeks.empty:
    avg_mileage = last_4_weeks["Total Miles"].mean()
    suggested_mileage = math.ceil(avg_mileage * 1.15)
else:
    avg_mileage = 0
    suggested_mileage = 0

# --- THIS WEEK vs LAST WEEK DAYS ---
df["start_date_local"] = pd.to_datetime(df["start_date_local"], errors='coerce')

this_week_runs = df[
    (df["start_date_local"] >= start_of_this_week) &
    (df["start_date_local"] <= today)
]

last_week_runs = df[
    (df["start_date_local"] >= start_of_last_week) &
    (df["start_date_local"] <= end_of_last_week)
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

# --- WEEKLY MILEAGE CHART ---
st.subheader("\U0001F4C8 Weekly Mileage Chart")
fig, ax = plt.subplots()
ax.plot(weekly_mileage["Week Starting"], weekly_mileage["Total Miles"], marker='o', label='Total Miles')
ax.bar(weekly_mileage["Week Starting"], weekly_mileage["Number of Runs"], alpha=0.3, label='Runs per Week')
ax.axhline(y=20, color='red', linestyle='--', label='20mi Goal')
ax.set_title("Weekly Running Mileage")
ax.set_xlabel("Week Starting")
ax.set_ylabel("Miles")
ax.grid(True)
plt.xticks(rotation=45)
ax.legend()
st.pyplot(fig)

# --- RAW DATA ---
st.subheader("\U0001F4DD Recent Runs")
st.dataframe(df[["name", "start_date_local", "distance_miles", "moving_time", "pace"]])