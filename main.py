import requests
import pandas as pd

# 🔐 Credentials
CLIENT_ID = "56595"
CLIENT_SECRET = "6b58f9d44228dda57cbf36420169c9991a78ab8e"
REFRESH_TOKEN = "297141bdcf01ef90e9ecb13439fae12e0eff773a"

# 🔁 Step 1: Refresh the access token
token_url = "https://www.strava.com/api/v3/oauth/token"
refresh_response = requests.post(token_url, data={
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'grant_type': 'refresh_token',
    'refresh_token': REFRESH_TOKEN
})

refresh_data = refresh_response.json()

if 'access_token' in refresh_data:
    ACCESS_TOKEN = refresh_data['access_token']
    print("✅ Access token refreshed!")
else:
    print("❌ Failed to refresh token:")
    print(refresh_data)
    exit()

# 🔗 Step 2: Fetch recent activities
activities_url = "https://www.strava.com/api/v3/athlete/activities"
response = requests.get(activities_url, headers={
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}, params={
    "per_page": 200
})

activities = response.json()

# 🔍 Step 3: Validate response and convert to DataFrame
print("Raw response:")
print(activities)

if isinstance(activities, list):
    df = pd.DataFrame(activities)

    # Only keep Runs and VirtualRuns
    df = df[df['type'].isin(['Run', 'VirtualRun'])]
else:
    print("⚠️ API returned an error or unexpected format:")
    print(activities)
    exit()

# 🧹 Step 4: Clean and convert data
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

df['start_date_local'] = pd.to_datetime(df['start_date_local'])
df['week_start'] = df['start_date_local'].dt.to_period('W').apply(lambda r: r.start_time)
df['distance_miles'] = (df['distance'] / 1609.34).round(2)
df['moving_time_formatted'] = df['moving_time'].apply(seconds_to_hhmmss)
df['elapsed_time_formatted'] = df['elapsed_time'].apply(seconds_to_hhmmss)
df['pace_per_mile'] = df['average_speed'].apply(speed_to_pace_mile)
df['start_date_local'] = df['start_date_local'].dt.strftime('%d:%m:%y %H:%M:%S')

# 🧾 Step 5: Final output
df_final = df[[
    'start_date_local',
    'name',
    'type',
    'distance_miles',
    'moving_time_formatted',
    'elapsed_time_formatted',
    'pace_per_mile',
    'total_elevation_gain'
]]

print("\n🏃 Recent Runs:")
print(df_final)

# 💾 Save to CSV
df_final.to_csv("recent_strava_activities_clean.csv", index=False)
