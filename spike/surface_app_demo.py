"""
SPIKE: how the interactive surface drops into the streamlit app.

This is the production shape for app.py's Surface tab:
  - streamlit owns the controls (ticker + smoothing/clip sliders) and the server-side RBF fit
  - on any change, build() recomputes the payload and render_html() emits the self-contained figure
  - components.html() renders it — the mouse-driven slice hover stays 100% client-side (smooth)

Run:
    .venv/Scripts/python.exe -m streamlit run spike/surface_app_demo.py
"""
import streamlit as st
import streamlit.components.v1 as components

from build_surface_beast import build, render_html

st.set_page_config(page_title="Vol Surface (spike)", layout="wide")
st.markdown("### Vol Surface — interactive (spike)")

c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
ticker = c1.selectbox("Ticker", ["SPY", "QQQ", "IWM"])
smoothing = c2.slider("Smoothing", 0.0, 2.0, 0.4, 0.1,
                      help="RBF regularisation. Lower = hugs raw quotes; higher = creamier/flatter. CV favours low.")
clip = c3.slider("Wing clip (±ln K/S)", 0.10, 0.24, 0.20, 0.01,
                 help="How far into the wings to show. Raw data reaches ~±0.24.")
unpin = c4.checkbox("Natural footprint", value=True,
                    help="Off = pin DTE axis to the floor (old fixed look).")

# Server-side fit on control change; cached so unchanged inputs don't refit.
@st.cache_data(show_spinner=False)
def _payload(t, s, c, pin):
    return build(t, smoothing=s, clip=c, fit_floor=5.0, pin_floor=pin, near_max=5.0)

try:
    payload = _payload(ticker, smoothing, clip, not unpin)
except SystemExit as e:
    st.error(str(e))
    st.stop()

st.caption(f"{ticker} {payload['date']} · spot {payload['spot']} · "
           f"coverage {payload['coverage']}% · fit RMSE {payload['rmse']}pp")

# The buttery part: client-side hover lives entirely inside this embedded HTML.
components.html(render_html(payload), height=620, scrolling=False)
