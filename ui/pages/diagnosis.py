import os
import json
import pandas as pd
import streamlit as st
from ui.components.diagnosis_card import format_root_cause, format_weakness_table, format_study_priority
from ui.i18n import t

OUTPUT_DIR = "output"


def render():
    st.markdown('<a name="diagnosis-report"></a>', unsafe_allow_html=True)
    st.title(t("diagnosis.title"))

    active_profile = st.session_state.get("active_profile")
    if not active_profile:
        st.info(t("diagnosis.no_files"))
        return

    diagnosis_file = active_profile.replace("_profile.json", "_diagnosis.json")
    diagnosis_path = os.path.join(OUTPUT_DIR, diagnosis_file)
    if not os.path.exists(diagnosis_path):
        st.info(t("diagnosis.no_files"))
        return

    with open(diagnosis_path, "r", encoding="utf-8") as f:
        diagnosis_raw = json.load(f)

    # Bilingual format: {"en": {...}, "pt": {...}}; old files are flat dicts
    lang = st.session_state.get("lang", "en")
    if "en" in diagnosis_raw or "pt" in diagnosis_raw:
        diagnosis = diagnosis_raw.get(lang, diagnosis_raw.get("en", {}))
    else:
        diagnosis = diagnosis_raw

    # ── Root cause ────────────────────────────────────────────────────────────
    st.divider()
    st.subheader(t("diagnosis.root_cause"))

    rc = format_root_cause(diagnosis)
    confidence = rc["confidence"]
    label = t("diagnosis.confidence", name=rc["name"], conf=confidence)
    if confidence == "HIGH":
        st.success(label)
    elif confidence == "MEDIUM":
        st.warning(label)
    else:
        st.info(label)

    st.markdown(rc["description"])

    # ── Cognitive pattern ─────────────────────────────────────────────────────
    st.divider()
    st.subheader(t("diagnosis.cognitive"))

    cognitive_pattern = diagnosis.get("cognitive_pattern")
    if cognitive_pattern:
        st.markdown(f"> {cognitive_pattern}")
    else:
        st.info(t("diagnosis.no_cognitive"))

    # ── Weakness classification ───────────────────────────────────────────────
    st.divider()
    st.subheader(t("diagnosis.weakness_class"))

    rows = format_weakness_table(diagnosis)
    if rows:
        df = pd.DataFrame(rows).rename(columns={
            "Concept": t("diagnosis.col.concept"),
            "Classification": t("diagnosis.col.classification"),
            "Reasoning": t("diagnosis.col.reasoning"),
        })
        class_col = t("diagnosis.col.classification")

        def color_classification(val):
            colors = {
                "PRIMARY":   "background-color:#c0392b;color:#ffffff;font-weight:700",
                "SECONDARY": "background-color:#e67e22;color:#ffffff;font-weight:700",
                "NOISE":     "background-color:#7f8c8d;color:#ffffff;font-weight:700",
            }
            return colors.get(val, "")

        st.dataframe(
            df.style.map(color_classification, subset=[class_col]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(t("diagnosis.no_weakness"))

    # ── Study priority ────────────────────────────────────────────────────────
    st.divider()
    st.subheader(t("diagnosis.study_plan"))

    items = format_study_priority(diagnosis)
    if items:
        for item in items:
            st.markdown(t(
                "diagnosis.study_item",
                rank=item["rank"],
                concept=item["concept"],
                chapter=item["chapter"],
                page=item["page"],
            ))
            st.markdown(f"*{item['reason']}*")
            st.divider()
    else:
        st.info(t("diagnosis.no_study"))
