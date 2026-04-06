import os
import sys
import chess
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from main import analyze_player, analyze_player_from_username

OUTPUT_DIR = "output"

st.title("🔍 Analyze")

tab_fresh, tab_load = st.tabs(["Fresh Analysis", "Load Saved Profile"])

# ── Fresh Analysis ────────────────────────────────────────────────────────────
with tab_fresh:
    st.subheader("Run a new analysis")
    source = st.radio("Source", ["Chess.com username", "Local PGN file"], horizontal=True)

    if source == "Chess.com username":
        username = st.text_input("Chess.com username")
        months = st.slider("Months to fetch", min_value=1, max_value=12, value=3)

        if st.button("Run Analysis", key="run_chesscom"):
            if not username.strip():
                st.error("Please enter a username.")
            else:
                with st.spinner(f"Fetching and analyzing games for **{username}**… this may take a few minutes."):
                    try:
                        profile, diagnosis = analyze_player_from_username(
                            username=username.strip(), n_months=months
                        )
                        st.success("Analysis complete!")
                        st.json({"weaknesses_found": len(profile["weaknesses"]),
                                 "root_cause": diagnosis["root_cause"]["name"]})
                        st.info("Navigate to **Profile Dashboard** or **Diagnosis Report** to explore results.")
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")

    else:
        pgn_file = st.file_uploader("Upload a PGN file", type=["pgn"])
        color = st.radio("Your color in the games", ["White", "Black"], horizontal=True)
        player_name = st.text_input("Player name (used for output filenames)", value="player")

        if st.button("Run Analysis", key="run_pgn"):
            if pgn_file is None:
                st.error("Please upload a PGN file.")
            elif not player_name.strip():
                st.error("Please enter a player name.")
            else:
                pgn_path = f"/tmp/{pgn_file.name}"
                with open(pgn_path, "wb") as f:
                    f.write(pgn_file.read())

                with st.spinner("Analyzing games… this may take a few minutes."):
                    try:
                        player_color = chess.WHITE if color == "White" else chess.BLACK
                        profile, diagnosis = analyze_player(
                            pgn_path=pgn_path,
                            player_name=player_name.strip(),
                            player_color=player_color,
                        )
                        st.success("Analysis complete!")
                        st.json({"weaknesses_found": len(profile["weaknesses"]),
                                 "root_cause": diagnosis["root_cause"]["name"]})
                        st.info("Navigate to **Profile Dashboard** or **Diagnosis Report** to explore results.")
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")

# ── Load Saved Profile ────────────────────────────────────────────────────────
with tab_load:
    st.subheader("Load a saved profile")

    profile_files = sorted(
        f for f in os.listdir(OUTPUT_DIR) if f.endswith("_profile.json")
    ) if os.path.isdir(OUTPUT_DIR) else []

    if not profile_files:
        st.info("No saved profiles found in `output/`. Run a fresh analysis first.")
    else:
        selected = st.selectbox("Select a profile", profile_files)
        st.success(f"Selected: **{selected}**")
        st.info("Navigate to **Profile Dashboard** or **Game Explorer** to explore this profile.")
