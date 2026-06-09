import os
import json
import pandas as pd
import streamlit as st
from ui.components.weakness_chart import build_error_count_chart, build_error_magnitude_chart
from ui.i18n import t

OUTPUT_DIR = "output"


def render():
    st.markdown('<a name="profile-dashboard"></a>', unsafe_allow_html=True)
    st.title(t("profile.title"))

    selected = st.session_state.get("active_profile")
    if not selected:
        st.info(t("profile.no_profiles"))
        return

    profile_path = os.path.join(OUTPUT_DIR, selected)
    if not os.path.exists(profile_path):
        st.info(t("profile.no_profiles"))
        return

    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    # ── Metrics row ───────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric(t("profile.metric.games"), profile["total_games"])
    col2.metric(t("profile.metric.positions"), profile["total_positions_analyzed"])
    col3.metric(t("profile.metric.errors"), profile["total_errors_detected"])
    col4.metric(t("profile.metric.missed_mates"), profile.get("total_missed_checkmates", 0))
    col5.metric(t("profile.metric.allowed_mates"), profile.get("total_allowed_checkmates", 0))
    col6.metric(t("profile.metric.error_rate"), f"{profile['overall_error_rate'] * 100:.1f}%")

    st.divider()

    weaknesses = profile.get("weaknesses", [])

    if not weaknesses:
        st.warning(t("profile.no_weaknesses"))
        return

    # ── Charts ────────────────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.plotly_chart(build_error_count_chart(weaknesses), use_container_width=True)

    with col_right:
        st.plotly_chart(build_error_magnitude_chart(weaknesses), use_container_width=True)

    # ── Error rate table ──────────────────────────────────────────────────────
    st.subheader(t("profile.table.subheader"))

    rows = [
        {
            t("profile.col.concept"):    w["concept"].replace("_", " ").title(),
            t("profile.col.error_occ"):  w["error_occurrences"],
            t("profile.col.total_occ"):  w["total_occurrences"],
            t("profile.col.error_rate"): round(w["error_rate"] * 100, 1),
            t("profile.col.avg_error"):  w["avg_error_magnitude_cp"],
        }
        for w in weaknesses
    ]

    df = pd.DataFrame(rows)
    st.dataframe(
        df.style.background_gradient(subset=[t("profile.col.error_rate")], cmap="Reds"),
        use_container_width=True,
        hide_index=True,
    )
