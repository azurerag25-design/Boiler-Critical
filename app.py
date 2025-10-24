import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

# ---------- Styles ----------
st.markdown("""
<style>
body { background-color: #F5F5F5; }
.header-title { color: #003366; font-size: 32px; font-weight: 700; margin-bottom: 4px; }
.header-desc { color: #333333; font-size: 16px; margin-bottom: 16px; }
.section-box {
  border: 2px solid #003366; border-radius: 8px; padding: 16px; background-color: #ffffff20;
}
.section-title { color: #003366; font-weight: 700; margin-bottom: 8px; }
.skyblue .stSelectbox [data-baseweb="select"] { background-color: #87CEEB22; }
.go-btn div.stButton>button { background-color: #28a745; color: white; border: 0; }
.back-btn div.stButton>button { background-color: #1e7e34; color: white; border: 0; } /* complementary tone */
.graph-panel {
  background: #ffffff; border: 2px solid #003366; border-radius: 8px; padding: 12px;
}
.center { display: flex; justify-content: center; }
.greyed { color: grey; }
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
st.markdown('<div class="header-title">Welcome to PowerPlay</div>', unsafe_allow_html=True)
st.markdown('<div class="header-desc">Your intelligent assistant to thermal plant boiler performance analysis.</div>', unsafe_allow_html=True)

# ---------- Session State ----------
if "show_graph" not in st.session_state:
    st.session_state.show_graph = False
if "selection" not in st.session_state:
    st.session_state.selection = {
        "param": "Bed Temperature",
        "snapshot": "History Snapshot",
        "window": 1
    }

# ---------- UI / Graph Toggle ----------
if not st.session_state.show_graph:
    # Inputs Panel
    with st.container():
        # Critical Parameters
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Critical Parameters</div>', unsafe_allow_html=True)
        with st.container():
            param = st.selectbox(
                "Select Critical Parameter",
                ["Bed Temperature", "Bed Height", "Screen Inlet Temperature", "APH Outlet Temperature"],
                index=0,
                key="param_select"
            )
        st.markdown('</div>', unsafe_allow_html=True)

        # Snapshot Selection
        snapshot = st.radio(
            "Select Snapshot",
            ["History Snapshot", "Current Snapshot", "AI Predictions"],
            index=0,
            horizontal=True
        )

        # Time Window
        if snapshot == "History Snapshot":
            st.markdown('<div class="greyed"><b>Time Window (fixed for History Snapshot)</b></div>', unsafe_allow_html=True)
            time_window = 1  # internally fixed; not shown
        else:
            time_window = st.selectbox("Select Time Window (hours)", [1, 2, 3], index=0)

        # Go Button
        col_go, _, _ = st.columns([1,2,2])
        with col_go:
            go_clicked = st.button("Go", key="go_btn")
        if go_clicked:
            st.session_state.selection = {"param": param, "snapshot": snapshot, "window": time_window}
            st.session_state.show_graph = True
            st.experimental_rerun()

else:
    # Graph Panel
    sel = st.session_state.selection
    title = f"{sel['param']} {sel['snapshot']} {sel['window']} hour(s)"
    st.markdown(f'<div class="graph-panel"><b>{title}</b></div>', unsafe_allow_html=True)

    # Sample time-series (placeholder)
    t = np.arange(0, 3600 * sel["window"], 60)  # 1-minute resolution
    y = np.sin(2 * np.pi * t / (600))  # synthetic signal
    plt.figure(figsize=(10, 4))
    plt.plot(t/3600, y, color="#003366")
    plt.xlabel("Time (hours)")
    plt.ylabel(sel["param"])
    plt.title(title)
    plt.grid(True, alpha=0.3)
    st.pyplot(plt, clear_figure=True)

    # Back Button (centered)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if st.button("Back", key="back_btn"):
            st.session_state.show_graph = False
            st.experimental_rerun()
