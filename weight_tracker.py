import streamlit as st
import pandas as pd
import os
import datetime

WEIGHT_FILE = "weight_log.csv"

def run_weight_tracker():
    st.subheader("⚖️ Weight Tracker")

    # Input
    weight = st.number_input("Enter today’s weight (kg):", min_value=0.0, step=0.1)

    if st.button("Save weight"):
        today = pd.Timestamp.today().strftime("%Y-%m-%d")
        new_data = pd.DataFrame({"Date": [today], "Weight (kg)": [weight]})

        if os.path.exists(WEIGHT_FILE):
            df = pd.read_csv(WEIGHT_FILE)
            df = pd.concat([df, new_data], ignore_index=True)
        else:
            df = new_data

        df.to_csv(WEIGHT_FILE, index=False)
        st.success("✅ Weight saved!")

    # Show log
    if os.path.exists(WEIGHT_FILE):
        df = pd.read_csv(WEIGHT_FILE)
        df["Date"] = pd.to_datetime(df["Date"])
        st.line_chart(df.set_index("Date")["Weight (kg)"])
        st.dataframe(df)
