import os
import json
import chess
import chess.svg
import streamlit as st
import streamlit.components.v1 as components
from modules.ai_diagnostician import explain_position
from ui.i18n import t

OUTPUT_DIR = "output"


def render():
    st.markdown('<a name="game-explorer"></a>', unsafe_allow_html=True)
    st.title(t("explorer.title"))

    selected = st.session_state.get("active_profile")
    if not selected:
        st.info(t("explorer.no_profiles"))
        return

    profile_path = os.path.join(OUTPUT_DIR, selected)
    if not os.path.exists(profile_path):
        st.info(t("explorer.no_profiles"))
        return

    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    weaknesses = [w for w in profile.get("weaknesses", []) if w.get("sample_positions")]

    if not weaknesses:
        st.warning(t("explorer.no_positions"))
        return

    # ── Concept selector ──────────────────────────────────────────────────────
    concept_options = {
        w["concept"].replace("_", " ").title(): w for w in weaknesses
    }
    selected_concept = st.selectbox(t("explorer.select_concept"), list(concept_options.keys()), key="explorer_concept_select")
    weakness = concept_options[selected_concept]

    st.markdown(t(
        "explorer.summary",
        concept=selected_concept,
        errors=weakness["error_occurrences"],
        rate=weakness["error_rate"] * 100,
        avg=weakness["avg_error_magnitude_cp"],
    ))

    st.divider()

    # ── Position viewer ───────────────────────────────────────────────────────
    # Collapse multiple same-concept errors from the same game into a single
    # representative position (the largest error). Consecutive flagged positions in
    # one game are usually the same mistake a few moves apart.
    by_game = {}
    for p in weakness["sample_positions"]:
        gid = p.get("game_id", "?")
        if gid not in by_game or (p.get("error_magnitude") or 0) > (by_game[gid].get("error_magnitude") or 0):
            by_game[gid] = p
    positions = list(by_game.values())
    st.subheader(t("explorer.sample_positions", n=len(positions)))

    for i, pos in enumerate(positions):
        label = t("explorer.expander", i=i + 1, game=pos.get("game_id", "?"), cp=pos.get("error_magnitude", "?"))
        with st.expander(label, expanded=(i == 0)):
            fen = pos.get("fen")
            if not fen:
                st.write(t("explorer.no_fen"))
                continue

            board = chess.Board(fen)
            move_played = pos.get("move_played")
            best_move = pos.get("best_move")
            player_color = pos.get("player_color", "white")
            orientation = chess.WHITE if player_color == "white" else chess.BLACK
            white_name = pos.get("white", "White")
            black_name = pos.get("black", "Black")

            arrows = []
            if move_played:
                m = chess.Move.from_uci(move_played)
                arrows.append(chess.svg.Arrow(m.from_square, m.to_square, color="#cc0000"))
            if best_move and best_move != move_played:
                m = chess.Move.from_uci(best_move)
                arrows.append(chess.svg.Arrow(m.from_square, m.to_square, color="#00aa00"))

            svg = chess.svg.board(board, arrows=arrows, size=360, orientation=orientation)

            if orientation == chess.WHITE:
                top_name, bottom_name = black_name, white_name
            else:
                top_name, bottom_name = white_name, black_name

            col_board, col_info = st.columns([1, 1])
            with col_board:
                components.html(
                    f"""
                    <div style="font-family:sans-serif;text-align:center">
                      <div style="margin-bottom:4px;font-weight:600;color:#555">{top_name}</div>
                      {svg}
                      <div style="margin-top:4px;font-weight:700;color:#000">{bottom_name} {t("explorer.you")}</div>
                    </div>
                    """,
                    height=430,
                )
            with col_info:
                st.markdown(t("explorer.game", v=pos.get("game_id", "?")))
                st.markdown(t("explorer.error_cp", v=pos.get("error_magnitude", "?")))
                if move_played:
                    st.markdown(t("explorer.move_played", v=move_played))
                if best_move:
                    key = "explorer.best_same" if best_move == move_played else "explorer.best_move"
                    st.markdown(t(key, v=best_move))
                st.markdown(t("explorer.fen", v=fen))

            # ── Ask AI why this move is a mistake ─────────────────────────────
            lang = st.session_state.get("lang", "en")
            # Cache the explanation per position+language so it persists across reruns.
            cache_key = f"explain::{selected}::{selected_concept}::{i}::{lang}"

            if st.button(t("explorer.ask_ai"), key=f"btn_{cache_key}"):
                with st.spinner(t("explorer.ai_thinking")):
                    try:
                        st.session_state[cache_key] = {
                            "text": explain_position(
                                fen=fen,
                                move_played=move_played,
                                best_move=best_move,
                                concept_key=weakness["concept"],
                                error_magnitude=pos.get("error_magnitude"),
                                player_color=player_color,
                                lang=lang,
                            )
                        }
                    except Exception as e:
                        st.session_state[cache_key] = {"error": str(e)}

            cached = st.session_state.get(cache_key)
            if cached:
                if "error" in cached:
                    st.error(t("analyze.error.failed", e=cached["error"]))
                else:
                    st.info(cached["text"])
