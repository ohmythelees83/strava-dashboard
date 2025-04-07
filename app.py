import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("🏃 Strava Weekly Mileage Tracker")

# Load your data (replace with your actual DataFrame or file)
df = pd.read_csv("recent_strava_activities_clean.csv")

# Convert week column if needed
df['start_date_local'] = pd.to_datetime(df['start_date_local'], format='%d:%m:%y %H:%M:%S')
df['week_start'] = df['start_date_local'].dt.to_period('W').apply(lambda r: r.start_time)

weekly_mileage = df.groupby('week_start')['distance_miles'].sum().reset_index()
weekly_mileage.columns = ['Week Starting', 'Total Miles']

st.subheader("📅 Weekly Mileage Table")
st.dataframe(weekly_mileage)

st.subheader("📈 Weekly Mileage Chart")
fig, ax = plt.subplots()
ax.plot(weekly_mileage['Week Starting'], weekly_mileage['Total Miles'], marker='o')
ax.set_xlabel("Week Starting")
ax.set_ylabel("Miles")
ax.set_title("Weekly Running Mileage")
ax.grid(True)
st.pyplot(fig)
