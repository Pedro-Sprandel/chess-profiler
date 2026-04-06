import os
import json
import pandas as pd
import streamlit as st
from ui.components.diagnosis_card import format_root_cause, format_weakness_table, format_study_priority

OUTPUT_DIR = "output"

st.title("🧠 Diagnosis Report")

# ── Diagnosis selector ────────────────────────────────────────────────────────
diagnosis_files = sorted(
    f for f in os.listdir(OUTPUT_DIR) if f.endswith("_diagnosis.json")
) if os.path.isdir(OUTPUT_DIR) else []

if not diagnosis_files:
    st.info("No saved diagnoses found in `output/`. Run an analysis from the **Analyze** page first.")
    st.stop()

selected = st.selectbox("Select a diagnosis", diagnosis_files)
diagnosis_path = os.path.join(OUTPUT_DIR, selected)

with open(diagnosis_path, "r", encoding="utf-8") as f:
    diagnosis = json.load(f)

# ── Root cause card ───────────────────────────────────────────────────────────
st.subheader("Root Cause")
rc = format_root_cause(diagnosis)

confidence = rc["confidence"]
if confidence == "HIGH":
    st.success(f"**{rc['name']}** · Confidence: {confidence}")
elif confidence == "MEDIUM":
    st.warning(f"**{rc['name']}** · Confidence: {confidence}")
else:
    st.info(f"**{rc['name']}** · Confidence: {confidence}")

st.markdown(rc["description"])

cognitive_pattern = diagnosis.get("cognitive_pattern")
if cognitive_pattern:
    st.divider()
    st.subheader("Cognitive Pattern to Change")
    st.markdown(f"> {cognitive_pattern}")

st.divider()

# ── Weakness classification table ─────────────────────────────────────────────
st.subheader("Weakness Classification")

rows = format_weakness_table(diagnosis)
if rows:
    df = pd.DataFrame(rows)

    def color_classification(val):
        colors = {"PRIMARY": "background-color:#ffd6d6", "SECONDARY": "background-color:#fff3cd", "NOISE": "background-color:#e8e8e8"}
        return colors.get(val, "")

    st.dataframe(
        df.style.applymap(color_classification, subset=["Classification"]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No weakness classification data available.")

st.divider()

# ── Study priority ────────────────────────────────────────────────────────────
st.subheader("Silman Study Plan")

items = format_study_priority(diagnosis)
if items:
    for item in items:
        with st.container():
            st.markdown(
                f"**#{item['rank']} — {item['concept']}** "
                f"· Chapter {item['chapter']}, p. {item['page']}"
            )
            st.markdown(f"*{item['reason']}*")
            st.divider()
else:
    st.info("No study priority data available.")
