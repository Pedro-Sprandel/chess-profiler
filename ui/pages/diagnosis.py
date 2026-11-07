from html import escape

import streamlit as st

from main import run_diagnosis
from ui.components.diagnosis_card import format_root_cause, format_study_priority, format_weakness_table
from ui.concepts import concept_label
from ui.i18n import t
from ui.store import get_analysis
from ui.style import CLASSIFICATION_COLORS, CONFIDENCE_COLORS, SUBTLE, anchor, badge, section_header

_CLASS_ORDER = {"PRIMARY": 0, "SECONDARY": 1, "NOISE": 2}


def _run_pending_diagnosis():
    """Phase 2: run the AI diagnosis after the profile has already been rendered above.

    Renders a spinner here (the last section), so the user can read/scroll the Profile
    Dashboard and Game Explorer while the API call is in flight. On completion the
    diagnosis is stored in SQLite and we rerun to display it.
    """
    name = st.session_state.get("diagnosis_target")
    with st.spinner(t("diagnosis.running")):
        try:
            run_diagnosis(name)
        except Exception as e:
            st.session_state.diagnosis_error = str(e)
        finally:
            st.session_state.diagnosis_running = False
            st.session_state.pop("diagnosis_target", None)
            st.rerun()


def _localized(diagnosis_raw: dict) -> dict:
    """Bilingual format {"en": {...}, "pt": {...}}; legacy files are flat dicts."""
    lang = st.session_state.get("lang", "pt")
    if "en" in diagnosis_raw or "pt" in diagnosis_raw:
        return diagnosis_raw.get(lang) or diagnosis_raw.get("en") or diagnosis_raw.get("pt") or {}
    return diagnosis_raw


def _render_root_cause(diagnosis: dict):
    rc = format_root_cause(diagnosis)
    conf = rc["confidence"] if rc["confidence"] in CONFIDENCE_COLORS else "LOW"
    conf_badge = badge(
        f'{t("diagnosis.confidence_label")}: {t("diagnosis.confidence." + conf)}',
        CONFIDENCE_COLORS[conf],
    )
    st.markdown(
        f"""<div class="cp-card" style="padding:1.25rem 1.4rem">
              <div class="cp-eyebrow">{t("diagnosis.root_cause")}</div>
              <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:.2rem 0 .6rem">
                <span style="font-size:1.35rem;font-weight:650">{escape(rc["name"])}</span>{conf_badge}
              </div>
            </div>""",
        unsafe_allow_html=True,
    )
    # Description as Markdown (the model may use emphasis/lists).
    if rc["description"]:
        st.markdown(rc["description"])

    st.write("")
    st.markdown(f"### {t('diagnosis.cognitive')}")
    pattern = diagnosis.get("cognitive_pattern")
    if pattern:
        st.markdown(f'<div class="cp-quote">{escape(pattern)}</div>', unsafe_allow_html=True)
    else:
        st.caption(t("diagnosis.no_cognitive"))


def _render_classification(diagnosis: dict):
    st.markdown(f"### {t('diagnosis.weakness_class')}")
    rows = format_weakness_table(diagnosis)
    if not rows:
        st.caption(t("diagnosis.no_weakness"))
        return
    rows.sort(key=lambda r: _CLASS_ORDER.get(r["Classification"], 9))
    for r in rows:
        cls = r["Classification"]
        color = CLASSIFICATION_COLORS.get(cls, SUBTLE)
        cls_label = t(f"diagnosis.class.{cls}") if cls in CLASSIFICATION_COLORS else cls
        st.markdown(
            f"""<div class="cp-card" style="border-left:3px solid {color}">
                  <h4>{escape(concept_label(r["key"]) if r.get("key") else r["Concept"])}
                    &nbsp;{badge(cls_label, color)}</h4>
                  <p>{escape(r["Reasoning"])}</p>
                </div>""",
            unsafe_allow_html=True,
        )


def _render_study_plan(diagnosis: dict):
    st.markdown(f"### {t('diagnosis.study_plan')}")
    items = format_study_priority(diagnosis)
    if not items:
        st.caption(t("diagnosis.no_study"))
        return
    for item in items:
        rank = item["rank"] if item["rank"] is not None else "–"
        name = concept_label(item["key"]) if item.get("key") else item["concept"]
        ref = t("diagnosis.study_ref", chapter=item["chapter"], page=item["page"])
        st.markdown(
            f"""<div class="cp-card" style="display:flex;gap:1rem">
                  <div style="font-size:1.4rem;font-weight:650;color:{SUBTLE};min-width:2rem">{rank:0>2}</div>
                  <div>
                    <h4>{escape(name)}</h4>
                    <div class="cp-eyebrow" style="margin-bottom:.4rem">{escape(ref)}</div>
                    <p>{escape(item["reason"])}</p>
                  </div>
                </div>""",
            unsafe_allow_html=True,
        )


def render():
    anchor("diagnosis-report")
    section_header(t("diagnosis.eyebrow"), t("diagnosis.title"))

    record = get_analysis(st.session_state.get("active_profile"))
    if record is None:
        st.info(t("diagnosis.no_files"))
        return

    # Phase 2: an analysis just built the profile; run the AI diagnosis now (with a
    # spinner) so everything above is already visible while we wait on the API.
    if st.session_state.get("diagnosis_running"):
        _run_pending_diagnosis()
        return

    error = st.session_state.pop("diagnosis_error", None)
    if error:
        st.error(t("diagnosis.failed", e=error))

    if not record["diagnosis"]:
        st.info(t("diagnosis.missing"))
        busy = st.session_state.get("analysis_running", False)
        if st.button(t("diagnosis.generate"), type="primary", disabled=busy, key="diagnosis_generate"):
            st.session_state.diagnosis_running = True
            st.session_state.diagnosis_target = record["name"]
            st.rerun()
        return

    diagnosis = _localized(record["diagnosis"])

    col_main, col_side = st.columns([3, 2], gap="large")
    with col_main:
        _render_root_cause(diagnosis)
        st.write("")
        _render_classification(diagnosis)
    with col_side:
        _render_study_plan(diagnosis)
