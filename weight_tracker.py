import streamlit as st
import pandas as pd
from datetime import datetime

def run_weight_tracker():
    st.header("⚖️ Weight Tracker")

    st.info(
        "The weight tracker is currently disabled while we reconnect Google Sheets. "
        "We'll bring it back soon!"
    )

    # Placeholder inputs so the layout remains
    st.number_input("Enter today’s weight (kg):", min_value=30.0, max_value=200.0, step=0.1, key="weight_input")
    st.button("Log Weight")
