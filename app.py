import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Streamlit page config
st.set_page_config(page_title="Strava Dashboard", layout="wide")
st.title("🏃 Live Strava Mileage Dashboard")

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
        st.error("❌ Failed to get access token from Strava:")
        st.json(data)
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
        st.error("❌ Failed to fetch activities:")
        st.json(activities)  # 🔍 this will show the exact response from Strava
        st.stop()


df = fetch_strava_data(access_token)

# --- CLEAN + FORMAT ---
df["start_date_local"] = pd.to_datetime(df["start_date_local"])
df["week_start"] = df["start_date_local"].dt.to_period("W").apply(lambda r: r.start_time)
df["distance_miles"] = (df["distance"] / 1609.34).round(2)
df["start_date_local"] = pd.to_datetime(df["start_date_local"])

def seconds_to_hhmmss(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"

def speed_to_pace_mile(speed_mps):
    if speed_mps == 0:
        return "00:00"
    pace_seconds = 1609.34 / speed_mps
    minutes = int(pace_seconds // 60)
    seconds = int(pace_seconds % 60)
    return f"{minutes:02}:{seconds:02}"


today = datetime.today()
start_of_this_week = today - timedelta(days=today.weekday())  # Monday
start_of_last_week = start_of_this_week - timedelta(days=7)
end_of_last_week = start_of_this_week - timedelta(seconds=1)

# Filter for runs this week and last week
this_week_runs = df[
    (df["start_date_local"] >= start_of_this_week) &
    (df["start_date_local"] <= today)
]

last_week_runs = df[
    (df["start_date_local"] >= start_of_last_week) &
    (df["start_date_local"] <= end_of_last_week)
]

# Count unique days with a run
days_this_week = this_week_runs["start_date_local"].dt.date.nunique()
days_last_week = last_week_runs["start_date_local"].dt.date.nunique()

# Display
st.subheader("📆 Weekly Consistency Tracker")
col1, col2 = st.columns(2)

with col1:
    st.metric(label="🏃‍♂️ Days Run This Week", value=f"{days_this_week} / 7")

with col2:
    st.metric(label="📉 Days Run Last Week", value=f"{days_last_week} / 7")

run_dates = sorted(df["start_date_local"].dt.date.unique(), reverse=True)

streak = 0
for i, date in enumerate(run_dates):
    if i == 0:
        if date != today.date():
            break  # no run today = streak is 0
    if i > 0 and (run_dates[i - 1] - date).days != 1:
        break
    streak += 1

st.markdown(f"🔥 **Current Streak:** {streak} day(s)")

print[run_dates]
