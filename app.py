import streamlit as st

st.set_page_config(
    page_title="Chess Strategic Profiler",
    page_icon="♟",
    layout="wide",
)

pg = st.navigation([
    st.Page("ui/pages/0_home.py", title="Home", icon="🏠"),
    st.Page("ui/pages/1_analyze.py", title="Analyze", icon="🔍"),
    st.Page("ui/pages/2_profile.py", title="Profile Dashboard", icon="📊"),
    st.Page("ui/pages/3_explorer.py", title="Game Explorer", icon="♟"),
    st.Page("ui/pages/4_diagnosis.py", title="Diagnosis Report", icon="🧠"),
])
pg.run()
