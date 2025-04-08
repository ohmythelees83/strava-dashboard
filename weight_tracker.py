import streamlit as st
import pandas as pd
import datetime
import os

DATA_FILE = "weight_log.csv"

def load_weight_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE, parse_dates=["date"])
    else:
        return pd.DataFrame(columns=["date", "weight"])

def save_weight_data(df):
    df.to_csv(DATA_FILE, index=False)

def run_weight_tracker():
    st.header("⚖️ Weight Tracker")

    # Load existing data
    df_weight = load_weight_data()

    # Input
    weight = st.number_input("Enter today’s weight (kg):", min_value=30.0, max_value=200.0, step=0.1, key="weight_input")

    if st.button("Log Weight"):
        today = pd.to_datetime(datetime.date.today())

        if today in df_weight["date"].values:
            st.warning("You've already logged weight for today.")
        else:
            new_entry = pd.DataFrame({"date": [today], "weight": [weight]})
            df_weight = pd.concat([df_weight, new_entry], ignore_index=True)
            save_weight_data(df_weight)
            st.success("✅ Weight logged!")

    # Display chart
    if not df_weight.empty:
        df_weight = df_weight.sort_values("date")
        st.line_chart(df_weight.set_index("date")["weight"])
