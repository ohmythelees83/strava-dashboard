import streamlit as st
import pandas as pd
import os
from datetime import datetime

def run_weight_tracker():
    st.subheader("⚖️ Weight Tracker")

    # File path
    csv_file = "weight_log.csv"

    # Load existing data
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file, parse_dates=["date"])
    else:
        df = pd.DataFrame(columns=["date", "weight"])

    # Input
    weight = st.number_input("Enter your weight today (kg)", min_value=0.0, step=0.1)

    if st.button("Log weight"):
        today = pd.to_datetime(datetime.today().date())

        if (df["date"] == today).any():
            st.warning("You've already logged weight today.")
        else:
            new_entry = pd.DataFrame([{"date": today, "weight": weight}])
            df = pd.concat([df, new_entry], ignore_index=True)
            df.to_csv(csv_file, index=False)
            st.success(f"Weight {weight} kg logged for {today.strftime('%Y-%m-%d')}!")

    # Show chart if data exists
    if not df.empty:
        df = df.sort_values("date")
        st.line_chart(df.set_index("date")["weight"])
        st.dataframe(df)
    