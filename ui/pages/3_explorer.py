import os
import json
import chess
import chess.svg
import streamlit as st
import streamlit.components.v1 as components

OUTPUT_DIR = "output"

st.title("♟ Game Explorer")

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

weaknesses = [w for w in profile.get("weaknesses", []) if w.get("sample_positions")]

if not weaknesses:
    st.warning("No sample positions available in this profile.")
    st.stop()

# ── Concept selector ──────────────────────────────────────────────────────────
concept_options = {
    w["concept"].replace("_", " ").title(): w for w in weaknesses
}
selected_concept = st.selectbox("Select a weakness concept", list(concept_options.keys()))
weakness = concept_options[selected_concept]

st.markdown(
    f"**{selected_concept}** — {weakness['error_occurrences']} errors "
    f"({weakness['error_rate'] * 100:.0f}% error rate, "
    f"avg {weakness['avg_error_magnitude_cp']} cp loss)"
)

st.divider()

# ── Position viewer ───────────────────────────────────────────────────────────
positions = weakness["sample_positions"]
st.subheader(f"Sample Positions ({len(positions)} shown)")

for i, pos in enumerate(positions):
    with st.expander(f"Position {i + 1} — Game {pos.get('game_id', '?')} · Error: {pos.get('error_magnitude', '?')} cp", expanded=(i == 0)):
        fen = pos.get("fen")
        if not fen:
            st.write("No FEN available for this position.")
            continue

        board = chess.Board(fen)
        svg = chess.svg.board(board, size=350)

        col_board, col_info = st.columns([1, 1])
        with col_board:
            components.html(
                f'<div style="display:flex;justify-content:center">{svg}</div>',
                height=380,
            )
        with col_info:
            st.markdown(f"**FEN:** `{fen}`")
            st.markdown(f"**Error magnitude:** {pos.get('error_magnitude', '?')} centipawns")
            st.markdown(f"**Game:** {pos.get('game_id', '?')}")
