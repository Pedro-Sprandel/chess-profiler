import os
import json
import pandas as pd
import streamlit as st
from ui.components.weakness_chart import build_error_count_chart, build_error_magnitude_chart

OUTPUT_DIR = "output"

st.title("📊 Profile Dashboard")

# ── Profile selector ──────────────────────────────────────────────────────────
profile_files = sorted(
    f for f in os.listdir(OUTPUT_DIR) if f.endswith("_profile.json")
) if os.path.isdir(OUTPUT_DIR) else []

if not profile_files:
    st.info("No saved profiles found in `output/`. Run an analysis from the **Analyze** page first.")
    st.stop()

selected = st.selectbox("Select a profile", profile_files)
profile_path = os.path.join(OUTPUT_DIR, selected)

with open(profile_path, "r", encoding="utf-8") as f:
    profile = json.load(f)

# ── Metrics row ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Games Analyzed", profile["total_games"])
col2.metric("Positions Analyzed", profile["total_positions_analyzed"])
col3.metric("Errors Detected", profile["total_errors_detected"])
col4.metric("Overall Error Rate", f"{profile['overall_error_rate'] * 100:.1f}%")

st.divider()

weaknesses = profile.get("weaknesses", [])

if not weaknesses:
    st.warning("No recurring weaknesses detected in this profile (minimum 3 occurrences required).")
    st.stop()

# ── Charts ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.plotly_chart(build_error_count_chart(weaknesses), use_container_width=True)

with col_right:
    st.plotly_chart(build_error_magnitude_chart(weaknesses), use_container_width=True)

# ── Error rate table ──────────────────────────────────────────────────────────
st.subheader("Weakness Detail")

rows = [
    {
        "Concept": w["concept"].replace("_", " ").title(),
        "Error Occurrences": w["error_occurrences"],
        "Total Occurrences": w["total_occurrences"],
        "Error Rate (%)": round(w["error_rate"] * 100, 1),
        "Avg Error (cp)": w["avg_error_magnitude_cp"],
    }
    for w in weaknesses
]

df = pd.DataFrame(rows)
st.dataframe(
    df.style.background_gradient(subset=["Error Rate (%)"], cmap="Reds"),
    use_container_width=True,
    hide_index=True,
)
