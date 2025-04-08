import streamlit as st
import pandas as pd
import datetime

def run_weight_tracker():
    st.header("⚖️ Weight Tracker")

    # Initialize the weight log
    if "weight_log" not in st.session_state:
        st.session_state.weight_log = []

    # Unique key added here 👇
    weight = st.number_input("Enter today’s weight (kg):", min_value=30.0, max_value=200.0, step=0.1, key="weight_input")

    if st.button("Log Weight"):
        st.session_state.weight_log.append({
            "date": datetime.date.today(),
            "weight": weight
        })

    # Display weight chart if there is data
    if st.session_state.weight_log:
        df_weight = pd.DataFrame(st.session_state.weight_log)
        st.line_chart(df_weight.set_index("date"))
