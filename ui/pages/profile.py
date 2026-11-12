import json

import pandas as pd
import streamlit as st

from ui.components.weakness_chart import (
    build_category_radar,
    build_comparison_chart,
    build_error_count_chart,
    build_error_magnitude_chart,
)
from ui.concepts import category_label, concept_category, concept_label
from ui.i18n import t
from ui.profiles import analysis_label, format_date
from ui.store import get_analysis, list_analyses
from ui.style import anchor, section_header

_CHART_CONFIG = {"displayModeBar": False}


def _meta_line(record: dict) -> str:
    profile = record["profile"]
    meta = profile.get("metadata", {})
    source = meta.get("source") or record.get("source")
    source_label = t(f"profile.source.{source}") if source in ("chess_com", "pgn") else (source or "—")
    return t(
        "profile.meta",
        subject=record.get("subject", "—"),
        when=format_date(record.get("created_at")),
        source=source_label,
        depth=meta.get("depth") or record.get("depth") or "—",
    )


def render():
    anchor("profile-dashboard")
    record = get_analysis(st.session_state.get("active_profile"))
    if record is None:
        section_header(t("profile.eyebrow"), t("profile.title"))
        st.info(t("profile.no_profiles"))
        return

    profile = record["profile"]
    section_header(t("profile.eyebrow"), t("profile.title"), _meta_line(record))

    # ── Metrics row ───────────────────────────────────────────────────────────
    cols = st.columns(6)
    cols[0].metric(t("profile.metric.games"), profile["total_games"], border=True)
    cols[1].metric(t("profile.metric.positions"), profile["total_positions_analyzed"], border=True)
    cols[2].metric(t("profile.metric.errors"), profile["total_errors_detected"], border=True)
    cols[3].metric(t("profile.metric.error_rate"), f"{profile['overall_error_rate'] * 100:.1f}%", border=True)
    cols[4].metric(t("profile.metric.missed_mates"), profile.get("total_missed_checkmates", 0), border=True)
    cols[5].metric(t("profile.metric.allowed_mates"), profile.get("total_allowed_checkmates", 0), border=True)

    # Cobertura: quantos erros as regras explicam, quantos a IA inferiu, quantos não
    # têm conceito (perfis antigos não têm o resumo).
    summary = profile.get("attribution_summary")
    if summary:
        st.caption(t("profile.attribution", rule=summary.get("rule", 0),
                     llm=summary.get("llm", 0), none=summary.get("unattributed", 0)))

    weaknesses = profile.get("weaknesses", [])
    if not weaknesses:
        st.write("")
        st.info(t("profile.no_weaknesses"))
        return

    # ── Charts ────────────────────────────────────────────────────────────────
    st.write("")
    col_left, col_right = st.columns(2, gap="large")
    with col_left:
        st.plotly_chart(build_error_count_chart(weaknesses), use_container_width=True, config=_CHART_CONFIG)
    with col_right:
        st.plotly_chart(build_error_magnitude_chart(weaknesses), use_container_width=True, config=_CHART_CONFIG)

    # ── Detail table ──────────────────────────────────────────────────────────
    st.markdown(f"### {t('profile.table.subheader')}")
    rate_col = t("profile.col.error_rate")
    df = pd.DataFrame([
        {
            t("profile.col.concept"):    concept_label(w["concept"]),
            t("profile.col.category"):   category_label(concept_category(w["concept"]) or "—"),
            t("profile.col.error_occ"):  w["error_occurrences"],
            t("profile.col.total_occ"):  w["total_occurrences"],
            rate_col:                    round(w["error_rate"] * 100, 1),
            t("profile.col.avg_error"):  w["avg_error_magnitude_cp"],
            t("profile.col.llm"):        w.get("llm_errors", 0),
        }
        for w in sorted(weaknesses, key=lambda x: x["error_occurrences"], reverse=True)
    ])
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            rate_col: st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
            t("profile.col.avg_error"): st.column_config.NumberColumn(format="%.0f"),
        },
    )
    st.download_button(
        t("profile.export"),
        data=json.dumps(profile, indent=2, ensure_ascii=False),
        file_name=f"{record.get('subject', 'profile')}_profile.json",
        mime="application/json",
        key="profile_export",
    )

    # ── Silman categories ─────────────────────────────────────────────────────
    st.write("")
    col_radar, col_cat = st.columns(2, gap="large", vertical_alignment="center")
    with col_radar:
        st.plotly_chart(build_category_radar(weaknesses), use_container_width=True, config=_CHART_CONFIG)
    with col_cat:
        totals: dict[str, int] = {}
        for w in weaknesses:
            cat = category_label(concept_category(w["concept"]) or "—")
            totals[cat] = totals.get(cat, 0) + w["error_occurrences"]
        grand = sum(totals.values()) or 1
        share_col = t("profile.col.share")
        st.dataframe(
            pd.DataFrame([
                {t("profile.col.category"): cat, t("profile.col.error_occ"): n,
                 share_col: round(100 * n / grand, 1)}
                for cat, n in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
            ]),
            use_container_width=True,
            hide_index=True,
            column_config={
                share_col: st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100),
            },
        )

    # ── Comparison ────────────────────────────────────────────────────────────
    summaries = {a["name"]: a for a in list_analyses()}
    if len(summaries) >= 2:
        st.write("")
        st.markdown(f"### {t('profile.compare.subheader')}")
        selected = record["name"]
        chosen = st.multiselect(
            t("profile.compare.label"),
            list(summaries),
            default=[selected] if selected in summaries else [],
            format_func=lambda n: analysis_label(summaries[n]),
            key="profile_compare_select",
        )
        if len(chosen) >= 2:
            series = []
            for name in chosen:
                other = get_analysis(name)
                if other:
                    series.append((analysis_label(summaries[name]), other["profile"].get("weaknesses", [])))
            if len(series) >= 2:
                st.plotly_chart(build_comparison_chart(series), use_container_width=True, config=_CHART_CONFIG)
        else:
            st.caption(t("profile.compare.hint"))
