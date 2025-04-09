import streamlit as st
import gspread
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account

def run_weight_tracker():
    st.header("⚖️ Weight Tracker")

    # Auth with service account
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_sheets"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"]
    )

    gc = gspread.authorize(credentials)
    sh = gc.open("WeightTracker")
    worksheet = sh.worksheet("Weights")

    weight = st.number_input("Enter today’s weight (kg):", min_value=30.0, max_value=200.0, step=0.1, key="weight_input")

    if st.button("Log Weight"):
        today = datetime.today().strftime("%Y-%m-%d")
        worksheet.append_row([today, weight])
        st.success(f"Weight logged for {today}")

    # Load and plot weights
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")
        st.line_chart(df.set_index)

        # --- WEIGHT TRACKING ---
st.markdown("---")
try:
    run_weight_tracker()
except Exception as e:
    st.error(f"⚠️ Weight Tracker failed to load: {e}")

