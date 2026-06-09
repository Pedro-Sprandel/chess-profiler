import streamlit as st
from ui.i18n import t


def render():
    st.markdown('<a name="home"></a>', unsafe_allow_html=True)
    st.title(t("home.title"))
    st.markdown(t("home.welcome"))
