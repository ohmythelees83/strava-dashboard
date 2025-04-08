import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

def run_weight_tracker():
    st.header("⚖️ Weight Tracker")

    # Initialize the weight log
    if "weight_log" not in st.session_state:
        st.session_state.weight_log = []

    # Unique key added here
    weight = st.number_input("Enter today’s weight (kg):", min_value=30.0, max_value=200.0, step=0.1, key="weight_input")

    if st.button("Log Weight"):
        st.session_state.weight_log.append({
            "date": datetime.date.today(),
            "weight": weight
        })

    # Display weight chart if there is data
    if st.session_state.weight_log:
        df_weight = pd.DataFrame(st.session_state.weight_log)
        df_weight = df_weight.sort_values("date")

        fig = px.line(
            df_weight,
            x="date",
            y="weight",
            markers=True,
            title="Weight Over Time",
            labels={"date": "Date", "weight": "Weight (kg)"}
        )

        fig.update_traces(mode="lines+markers")
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Weight (kg)",
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)
