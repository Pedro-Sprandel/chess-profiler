import os
import json
import pandas as pd
import streamlit as st
from ui.components.weakness_chart import (
    build_error_count_chart,
    build_error_magnitude_chart,
    build_category_radar,
    build_comparison_chart,
)
from ui.i18n import t
from ui.concepts import concept_label
from ui.profiles import display_label
from config import OUTPUT_DIR


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

    # ── Metadata caption ──────────────────────────────────────────────────────
    meta = profile.get("metadata", {})
    if profile.get("generated_at") or meta:
        st.caption(t(
            "profile.meta",
            when=profile.get("generated_at", "?"),
            source=meta.get("source", "?"),
            depth=meta.get("depth", "?"),
        ))

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

    st.plotly_chart(build_category_radar(weaknesses), use_container_width=True)

    # ── Error rate table ──────────────────────────────────────────────────────
    st.subheader(t("profile.table.subheader"))

    rows = [
        {
            t("profile.col.concept"):    concept_label(w["concept"]),
            t("profile.col.error_occ"):  w["error_occurrences"],
            t("profile.col.total_occ"):  w["total_occurrences"],
            t("profile.col.error_rate"): round(w["error_rate"] * 100, 1),
            t("profile.col.avg_error"):  w["avg_error_magnitude_cp"],
        }
        for w in weaknesses
    ]

    df = pd.DataFrame(rows)

    # Red heat-map on the error-rate column without pulling in matplotlib
    # (Styler.background_gradient requires it). Normalize across the column and
    # shade from light to dark red.
    rate_col = t("profile.col.error_rate")
    rates = df[rate_col].astype(float)
    lo, hi = rates.min(), rates.max()
    span = (hi - lo) or 1.0

    def _heat(v):
        norm = (float(v) - lo) / span
        text = "#ffffff" if norm > 0.6 else "#000000"
        return f"background-color: rgba(204, 0, 0, {0.12 + 0.6 * norm:.3f}); color: {text}"

    st.dataframe(
        df.style.map(_heat, subset=[rate_col]),
        use_container_width=True,
        hide_index=True,
    )

    # ── Profile comparison ────────────────────────────────────────────────────
    all_profiles = sorted(
        f for f in os.listdir(OUTPUT_DIR) if f.endswith("_profile.json")
    ) if os.path.isdir(OUTPUT_DIR) else []

    if len(all_profiles) >= 2:
        st.divider()
        st.subheader(t("profile.compare.subheader"))
        chosen = st.multiselect(
            t("profile.compare.label"),
            all_profiles,
            default=[selected] if selected in all_profiles else [],
            format_func=display_label,
            key="profile_compare_select",
        )
        if len(chosen) >= 2:
            series = []
            for fname in chosen:
                try:
                    with open(os.path.join(OUTPUT_DIR, fname), "r", encoding="utf-8") as f:
                        p = json.load(f)
                    series.append((display_label(fname), p.get("weaknesses", [])))
                except (OSError, json.JSONDecodeError):
                    continue
            if len(series) >= 2:
                st.plotly_chart(build_comparison_chart(series), use_container_width=True)
        else:
            st.caption(t("profile.compare.hint"))
