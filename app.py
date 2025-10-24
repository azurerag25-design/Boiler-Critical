# app.py
# Run:
#   streamlit run app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
from ichart_from_history_csv import build_ichart_from_history  # Import Option A

# --------------------------- Theme ---------------------------
st.set_page_config(page_title="PowerPlay", layout="wide")

DARK_BLUE   = "#003366"
LIGHT_GRAY  = "#F5F5F5"
DARK_GRAY   = "#333333"
SKY_BLUE    = "#87CEEB"
EMERALD     = "#28a745"
CORAL       = "#FF7F50"

CSV_PATH = Path("history_export.csv")

def inject_css(for_back_button=False):
    btn_color = CORAL if for_back_button else EMERALD
    st.markdown(f"""
        <style>
        .stApp {{ background-color: {LIGHT_GRAY}; }}
        .pp-center {{ text-align: center; }}
        .powerplay-header {{
            color: {DARK_BLUE}; font-weight: 800; margin-bottom: 0.2rem;
        }}
        .powerplay-sub {{
            color: {DARK_GRAY}; font-size: 0.95rem; margin-bottom: 1.0rem;
        }}
        .pp-card {{
            background: white; border: 1.5px solid {DARK_BLUE};
            border-radius: 8px; padding: 1rem 1rem 0.75rem 1rem;
        }}
        .pp-title {{ color: {DARK_BLUE}; font-weight: 700; margin-bottom: 0.5rem; }}
        .stButton button {{
            background-color: {btn_color}; color: white; border: none;
            border-radius: 6px; padding: 0.5rem 1.0rem; font-weight: 600;
        }}
        .stButton button:hover {{ filter: brightness(0.95); }}
        .pp-plot {{
            background: white; border: 2px solid {DARK_BLUE};
            border-radius: 8px; padding: 0.5rem;
        }}
        </style>
    """, unsafe_allow_html=True)

# --------------------------- State ---------------------------
PARAM_MAP = {
    "Bed Temperature": "BED TEMPERATURE",
    "Bed Hight": "BED HEIGHT",
    "Screen Inlet Temperature": "SCREEN INLET TEMPERATURE",
    "APH Outlet Temperature": "APH OUTLET TEMPERATURE",
    "SH3 Outlet Temperature": "SH3 OUTLET TEMPERATURE",
}
SNAPSHOT_OPTIONS   = ["History Snapshot", "Current Snapshot", "AI Predictions"]
WINDOW_OPTIONS_MIN = [20, 30, 60]

if "show_chart" not in st.session_state:
    st.session_state.show_chart = False
if "selection" not in st.session_state:
    st.session_state.selection = {}

def do_rerun():
    try: st.rerun()
    except AttributeError: st.experimental_rerun()

# --------------------------- Header ---------------------------
inject_css(for_back_button=st.session_state.show_chart)
st.markdown("<div class='pp-center'><h1 class='powerplay-header'>Welcome to PowerPlay</h1></div>", unsafe_allow_html=True)
st.markdown("<div class='pp-center powerplay-sub'>Your intelligent assistant to thermal plant boiler performance analysis.</div>", unsafe_allow_html=True)

# --------------------------- Controls / Chart ---------------------------
if not st.session_state.show_chart:
    st.markdown("<div class='pp-card'>", unsafe_allow_html=True)
    st.markdown("<div class='pp-title'>Critical Parameters</div>", unsafe_allow_html=True)

    param_name = st.selectbox("Select a critical parameter", list(PARAM_MAP.keys()), key="param_select")
    tag = PARAM_MAP[param_name]
    st.caption(f"Tag: **{tag}**")

    snapshot = st.radio("Select snapshot", SNAPSHOT_OPTIONS, index=0, horizontal=True, key="snapshot_select")

    if snapshot == "History Snapshot":
        st.selectbox("Time Window (predefined)", ["Predefined"], index=0, disabled=True, label_visibility="collapsed", key="window_disabled")
        window = None
    else:
        window = st.selectbox("Time Window (minutes)", WINDOW_OPTIONS_MIN, index=0, key="window_select")

    if st.button("Go", key="go_button"):
        st.session_state.selection = {"param": param_name, "tag": tag, "snapshot": snapshot, "window": window}
        st.session_state.show_chart = True
        do_rerun()
    st.markdown("</div>", unsafe_allow_html=True)

else:
    sel = st.session_state.selection
    st.markdown("<div class='pp-plot'>", unsafe_allow_html=True)

    if sel["snapshot"] == "History Snapshot":
        try:
            fig = build_ichart_from_history(str(CSV_PATH), sel["tag"])
            # Streamlit 2025+ : replace use_container_width with width='stretch'
            st.pyplot(fig, width='stretch', clear_figure=True)
        except Exception as e:
            st.error(f"History Snapshot error: {e}")
    else:
        # Placeholder for demo snapshots
        now = datetime.now()
        times = pd.date_range(end=now, periods=(sel["window"] or 20), freq="1min")
        vals = np.cumsum(np.random.normal(0, 0.3, size=len(times))) + 100.0
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=times, y=vals, mode="lines", name="Value", line=dict(width=2)))
        fig.update_layout(
            height=340, margin=dict(l=8, r=8, t=40, b=6), plot_bgcolor="white",
            xaxis=dict(title="Time", showgrid=True, gridcolor="#eee"),
            yaxis=dict(title="Value", showgrid=True, gridcolor="#eee"),
            autosize=True,
        )
        st.plotly_chart(fig, width='stretch', theme=None)

    # Bottom-centered parameter name (already inside Matplotlib fig, so just for placeholders)
    if sel["snapshot"] != "History Snapshot":
        st.markdown(f"<p style='text-align:center; font-weight:600;'>{sel['param']}</p>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    inject_css(for_back_button=True)
    st.write("")
    back_col = st.columns([0.4, 0.2, 0.4])[1]
    with back_col:
        if st.button("Back", key="back_btn", use_container_width=False):
            st.session_state.show_chart = False
            st.session_state.selection = {}
            do_rerun()
