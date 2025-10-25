# app.py
# Run:
#   pip install streamlit pandas numpy plotly matplotlib
#   streamlit run app.py

import os, hmac, streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path

# --------------------------- Page Config ---------------------------
st.set_page_config(page_title="PowerPlay", layout="wide")

# --------------------------- Security: Access Gate ---------------------------
def access_gate():
    """Simple shared-password gate (reads from Streamlit Secrets or APP_PASSWORD env)."""
    app_pw = st.secrets.get("APP_PASSWORD") or os.environ.get("APP_PASSWORD")
    if not app_pw:
        st.warning("APP password not configured. Set APP_PASSWORD in .streamlit/secrets.toml (local) or Secrets (Cloud).")
        return
    if not st.session_state.get("authed", False):
        with st.form("auth_form", clear_on_submit=False):
            st.markdown("### 🔒 Enter Access Password")
            pw = st.text_input("Password", type="password")
            ok = st.form_submit_button("Enter")
        if ok:
            if hmac.compare_digest(str(pw), str(app_pw)):
                st.session_state.authed = True
                try: st.rerun()
                except AttributeError: st.experimental_rerun()
            else:
                st.error("Access denied.")
        st.stop()  # halt until authenticated

# --------------------------- Chart builders ---------------------------
from ichart_from_history_csv import build_ichart_from_history
from ichart_from_current_csv import build_ichart_from_current
from ichart_from_ai_csv import build_ichart_from_ai

# --------------------------- Theme & Colors ---------------------------
DARK_BLUE      = "#003366"
LIGHT_GRAY     = "#F5F5F5"
DARK_GRAY      = "#333333"
SKY_BLUE       = "#87CEEB"
EMERALD        = "#28a745"  # Go
CORAL          = "#FF7F50"  # Back
LOGOUT_YELLOW  = "#B8860B"  # Dark Yellow (DarkGoldenRod) for Logout

HISTORY_CSV = Path("history_export.csv")
CURRENT_CSV = Path("current_export.csv")
AI_CSV      = Path("AI_export.csv")

def inject_button_css(primary_color: str, secondary_color: str):
    """
    Strong, DOM-targeted CSS so colors are not overridden by Streamlit theme.
    - Primary buttons (Go/Back) use data-testid=baseButton-primary
    - Secondary buttons (Logout) use data-testid=baseButton-secondary
    Forces secondary text & border to dark yellow; background stays transparent if theme forces white.
    """
    st.markdown(
        f"""
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
            border-radius: 8px; padding: 1rem 1rem 0.6rem 1rem;
          }}
          .pp-title {{ color: {DARK_BLUE}; font-weight: 700; margin-bottom: 0.5rem; }}
          div[data-baseweb="select"] > div {{ background-color: {SKY_BLUE}10; border-radius: 6px; }}

          .pp-plot {{
            background: white; border: 2px solid {DARK_BLUE};
            border-radius: 8px; padding: 0.5rem;
          }}

          .go-logout-row {{ margin-top: 0.40rem; }}

          /* --- Primary buttons (Go / Back) --- */
          button[data-testid="baseButton-primary"] {{
            background-color: {primary_color} !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 0.5rem 1.0rem !important;
            font-weight: 600 !important;
          }}
          button[data-testid="baseButton-primary"]:hover {{
            filter: brightness(0.95);
          }}

          /* --- Secondary buttons (Logout) --- 
             Some Streamlit themes force white bg; ensure icon/text and border are dark yellow. */
          button[data-testid="baseButton-secondary"] {{
            color: {secondary_color} !important;                /* icon/text color */
            border: 2px solid {secondary_color} !important;     /* border color */
            border-radius: 8px !important;
            padding: 0.50rem 0.85rem !important;
            font-size: 1.05rem !important;  /* icon size */
            background: transparent !important;                 /* leave bg as white/transparent */
          }}
          button[data-testid="baseButton-secondary"]:hover {{
            filter: brightness(0.95);
          }}

          /* --- Fallbacks for older Streamlit builds --- */
          div.stButton > button[kind="primary"] {{
            background-color: {primary_color} !important; color: #fff !important; border: none !important;
          }}
          div.stButton > button[kind="secondary"] {{
            color: {secondary_color} !important; border: 2px solid {secondary_color} !important;
            background: transparent !important; border-radius: 8px !important;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# --------------------------- App State ---------------------------
if "show_chart" not in st.session_state:
    st.session_state.show_chart = False
if "selection" not in st.session_state:
    st.session_state.selection = {}

def do_rerun():
    try: st.rerun()
    except AttributeError: st.experimental_rerun()

# --------------------------- Security Gate ---------------------------
access_gate()

# Inject CSS for CONTROLS screen: Go=emerald (primary), Logout=dark yellow (secondary)
inject_button_css(primary_color=EMERALD, secondary_color=LOGOUT_YELLOW)

# --------------------------- Header ---------------------------
st.markdown("<div class='pp-center'><h1 class='powerplay-header'>Welcome to PowerPlay</h1></div>", unsafe_allow_html=True)
st.markdown("<div class='pp-center powerplay-sub'>Your intelligent assistant to thermal plant boiler performance analysis.</div>", unsafe_allow_html=True)

# --------------------------- Controls / Chart ---------------------------
PARAM_MAP = {
    "Bed Temperature": "BED TEMPERATURE",
    "Bed Height": "BED HEIGHT",
    "Screen Inlet Temperature": "SCREEN INLET TEMPERATURE",
    "APH Outlet Temperature": "APH OUTLET TEMPERATURE",
    "SH3 Outlet Temperature": "SH3 OUTLET TEMPERATURE",
}
SNAPSHOT_OPTIONS = ["History Snapshot", "Current Snapshot", "AI Snapshot"]
WINDOW_OPTIONS_CURRENT = [20, 40, 60]
WINDOW_OPTIONS_AI = [20, 40, 60]

if not st.session_state.show_chart:
    st.markdown("<div class='pp-card'>", unsafe_allow_html=True)
    st.markdown("<div class='pp-title'>Critical Parameters</div>", unsafe_allow_html=True)

    param_name = st.selectbox("Select a critical parameter", list(PARAM_MAP.keys()), index=0, key="param_select")
    tag = PARAM_MAP[param_name]

    snapshot = st.radio("Select snapshot", SNAPSHOT_OPTIONS, index=0, horizontal=True, key="snapshot_select")

    if snapshot == "History Snapshot":
        st.selectbox("Time Window (predefined)", ["Predefined"], index=0, disabled=True,
                     label_visibility="collapsed", key="window_disabled")
        window = None
    elif snapshot == "Current Snapshot":
        window = st.selectbox("Time Window (minutes)", WINDOW_OPTIONS_CURRENT, index=0, key="window_current")
    else:  # AI Snapshot
        window = st.selectbox("Time Window (minutes)", WINDOW_OPTIONS_AI, index=0, key="window_ai")

    # ---------- Bottom row of the controls card ----------
    st.markdown("<div class='go-logout-row'>", unsafe_allow_html=True)
    col_go, col_spacer, col_logout = st.columns([0.18, 0.67, 0.15])
    with col_go:
        # Go button as PRIMARY
        go_clicked = st.button("Go", key="go_button", type="primary")
    with col_logout:
        # Logout icon as SECONDARY (dark yellow text/border; bg transparent)
        logout_clicked = st.button("🟨⎋", key="logout_btn", help="Logout", type="secondary")
    st.markdown("</div>", unsafe_allow_html=True)
    # -----------------------------------------------------

    # Actions
    if go_clicked:
        st.session_state.selection = {"param": param_name, "tag": tag, "snapshot": snapshot, "window": window}
        st.session_state.show_chart = True
        do_rerun()

    if logout_clicked:
        st.session_state.pop("authed", None)
        do_rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # end card

else:
    sel = st.session_state.selection
    st.markdown("<div class='pp-plot'>", unsafe_allow_html=True)

    if sel["snapshot"] == "History Snapshot":
        try:
            fig = build_ichart_from_history(str(HISTORY_CSV), sel["tag"])
            st.pyplot(fig, width='stretch', clear_figure=True)
        except Exception as e:
            st.error(f"History Snapshot error: {e}")

    elif sel["snapshot"] == "Current Snapshot":
        try:
            minutes = int(sel["window"] or 20)
            fig = build_ichart_from_current(str(CURRENT_CSV), sel["tag"], minutes)
            st.pyplot(fig, width='stretch', clear_figure=True)
        except Exception as e:
            st.error(f"Current Snapshot error: {e}")

    else:  # AI Snapshot
        try:
            minutes = int(sel["window"] or 20)
            fig = build_ichart_from_ai(str(AI_CSV), sel["tag"], minutes)
            st.pyplot(fig, width='stretch', clear_figure=True)
        except Exception as e:
            st.error(f"AI Snapshot error: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

    # --------- Bottom row on the chart screen: Back (center) + Logout (right) ---------
    # Re-inject CSS so PRIMARY=coral for Back; Logout remains dark yellow secondary.
    inject_button_css(primary_color=CORAL, secondary_color=LOGOUT_YELLOW)

    row_left, row_center, row_right = st.columns([0.4, 0.2, 0.4])
    with row_center:
        back_clicked = st.button("Back", key="back_btn", type="primary")
    with row_right:
        logout_clicked_chart = st.button("🟨⎋", key="logout_btn_chart", help="Logout", type="secondary")

    # Actions (chart screen)
    if logout_clicked_chart:
        st.session_state.pop("authed", None)
        do_rerun()
    if back_clicked:
        st.session_state.show_chart = False
        st.session_state.selection = {}
        do_rerun()

