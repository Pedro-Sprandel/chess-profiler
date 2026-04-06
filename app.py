import streamlit as st

st.set_page_config(
    page_title="Chess Strategic Profiler",
    page_icon="♟",
    layout="wide",
)

st.title("♟ Chess Strategic Profiler")
st.markdown(
    """
    Welcome to the **Chess Strategic Profiler** — a personalized strategic diagnostic system
    for chess players based on Jeremy Silman's *The Amateur's Mind*.

    Use the sidebar to navigate between sections:

    | Page | Description |
    |------|-------------|
    | **Analyze** | Run a fresh analysis or load a saved profile |
    | **Profile Dashboard** | View weakness charts and error statistics |
    | **Game Explorer** | Inspect individual error positions on a chessboard |
    | **Diagnosis Report** | Read the AI-generated root cause diagnosis |
    """
)
