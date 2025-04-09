import streamlit as st
import gspread
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
import plotly.graph_objects as go

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

    # --- Worksheet setup ---
    worksheet = sh.worksheet("Weights")

    try:
        metadata_ws = sh.worksheet("Metadata")
    except gspread.exceptions.WorksheetNotFound:
        metadata_ws = sh.add_worksheet(title="Metadata", rows="10", cols="2")
        metadata_ws.append_row(["Key", "Value"])
        metadata_ws.append_row(["target_weight", "85.0"])

    # --- Target weight logic ---
    metadata = metadata_ws.get_all_records()
    metadata_df = pd.DataFrame(metadata)

    # Default target or previously saved one
    target_row = metadata_df[metadata_df["Key"] == "target_weight"]
    if not target_row.empty:
        default_target = float(target_row.iloc[0]["Value"])
    else:
        default_target = 85.0
        metadata_ws.append_row(["target_weight", str(default_target)])

    # UI to adjust target
    target_weight = st.number_input("🎯 Set your target weight (kg):", min_value=30.0, max_value=200.0, step=0.1, value=default_target)

    if target_weight != default_target:
        # Update or insert target_weight row
        cell = metadata_ws.find("target_weight")
        metadata_ws.update_cell(cell.row, cell.col + 1, str(target_weight))

    st.markdown("### Log Your Weight")

    weight = st.number_input("Enter today’s weight (kg):", min_value=30.0, max_value=200.0, step=0.1, key="weight_input")

    if st.button("Log Weight"):
        today = datetime.today().strftime("%Y-%m-%d")
        worksheet.append_row([today, weight])
        st.success(f"Weight logged for {today}")

    # --- Load and plot weights ---
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["Weight"],
            mode="lines+markers",
            name="Actual Weight"
        ))

        fig.add_hline(
            y=target_weight,
            line_dash="dash",
            line_color="green",
            annotation_text=f"Target: {target_weight} kg",
            annotation_position="top left"
        )

        fig.update_layout(
            title="📉 Weight Over Time",
            xaxis_title="Date",
            yaxis_title="Weight (kg)",
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)
