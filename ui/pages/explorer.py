from html import escape

import chess
import chess.svg
import streamlit as st
import streamlit.components.v1 as components

from modules.ai_diagnostician import explain_position
from ui.concepts import concept_label
from ui.i18n import t
from ui.store import get_analysis, get_explanation, save_explanation
from ui.style import ERROR, GOOD, INK, MUTED, WARN, anchor, badge, section_header, swatch

BOARD_COLORS = {
    "square light": "#C9D2D9",
    "square dark": "#6F8797",
    "square light lastmove": "#B3C1CB",
    "square dark lastmove": "#5F7787",
    "margin": "#00000000",
    "coord": "#9AA4B2",
}


def _san(fen: str, uci: str | None) -> str | None:
    """Converte um lance UCI para SAN no contexto da posição (g1f3 → Nf3)."""
    if not uci:
        return None
    try:
        return chess.Board(fen).san(chess.Move.from_uci(uci))
    except Exception:
        return uci


def _fmt_eval(cp) -> str:
    """Formata centipawns (POV brancas) como avaliação legível (+1.2 / -0.5 / #)."""
    if cp is None:
        return "?"
    if abs(cp) >= 9000:
        return "#" if cp > 0 else "-#"
    return f"{cp / 100:+.1f}"


def _fmt_cp(v) -> str:
    try:
        return f"{float(v):.0f}"
    except (TypeError, ValueError):
        return "?"


def _ordered_positions(all_positions: list) -> tuple[list, int]:
    """One representative position per game (largest error) first, then the rest.

    Consecutive flagged positions in a game are usually the same mistake a few
    moves apart, so the default view shows the worst one per game.
    """
    def _mag(p):
        return p.get("error_magnitude") or 0

    best_idx_by_game = {}
    for idx, p in enumerate(all_positions):
        gid = p.get("game_id", "?")
        if gid not in best_idx_by_game or _mag(p) > _mag(all_positions[best_idx_by_game[gid]]):
            best_idx_by_game[gid] = idx
    primary_idxs = set(best_idx_by_game.values())
    primary = sorted((all_positions[i] for i in primary_idxs), key=_mag, reverse=True)
    secondary = sorted((p for i, p in enumerate(all_positions) if i not in primary_idxs),
                       key=_mag, reverse=True)
    return primary + secondary, len(primary)


def _board_html(fen, move_played, best_move, player_color, white_name, black_name) -> str:
    board = chess.Board(fen)
    orientation = chess.WHITE if player_color == "white" else chess.BLACK

    arrows = []
    if move_played:
        m = chess.Move.from_uci(move_played)
        arrows.append(chess.svg.Arrow(m.from_square, m.to_square, color=ERROR + "cc"))
    if best_move and best_move != move_played:
        m = chess.Move.from_uci(best_move)
        arrows.append(chess.svg.Arrow(m.from_square, m.to_square, color=GOOD + "cc"))

    svg = chess.svg.board(board, arrows=arrows, size=380, orientation=orientation,
                          colors=BOARD_COLORS)
    if orientation == chess.WHITE:
        top, bottom = black_name, white_name
    else:
        top, bottom = white_name, black_name

    font = "font-family:Inter,-apple-system,Segoe UI,Roboto,sans-serif;font-size:13px"
    return f"""
        <div style="{font};width:380px">
          <div style="color:{MUTED};margin-bottom:6px">{escape(top)}</div>
          {svg}
          <div style="color:{INK};font-weight:600;margin-top:6px">{escape(bottom)}
            <span style="color:{MUTED};font-weight:400">{t("explorer.you")}</span></div>
        </div>
    """


def _details_html(pos: dict, fen: str, move_played, best_move) -> str:
    rows = []
    if pos.get("date"):
        rows.append((t("explorer.date"), escape(str(pos["date"]))))
    if pos.get("move_number"):
        rows.append((t("explorer.move_number"), str(pos["move_number"])))
    if move_played:
        rows.append((swatch(ERROR) + t("explorer.move_played"), f"<code>{escape(_san(fen, move_played))}</code>"))
    if best_move:
        key = "explorer.best_same" if best_move == move_played else "explorer.best_move"
        rows.append((swatch(GOOD) + t(key), f"<code>{escape(_san(fen, best_move))}</code>"))
    if pos.get("eval_before") is not None and pos.get("eval_after") is not None:
        rows.append((t("explorer.eval_swing"),
                     f"{_fmt_eval(pos['eval_before'])} → {_fmt_eval(pos['eval_after'])}"))
    rows.append((t("explorer.error_cp"), f"−{_fmt_cp(pos.get('error_magnitude'))} cp"))
    # Origem da atribuição deste erro ao conceito: regra determinística ou IA.
    if pos.get("attribution") == "llm":
        reason = pos.get("reason") or {}
        lang = st.session_state.get("lang", "pt")
        text = reason.get(lang) or reason.get("en") or reason.get("pt") or ""
        value = badge(t("explorer.attr.llm"), WARN)
        if text:
            value += f'<div style="margin-top:.3rem">{escape(text)}</div>'
        rows.append((t("explorer.attr"), value))
    elif pos.get("motif"):
        rows.append((t("explorer.attr"), escape(t(f"explorer.motif.{pos['motif']}"))))
    body = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
    return f'<table class="cp-kv">{body}</table>'


def _render_position(i: int, pos: dict, concept_key: str):
    player_color = pos.get("player_color", "white")
    white_name = pos.get("white", "White")
    black_name = pos.get("black", "Black")
    opponent = black_name if player_color == "white" else white_name
    cp = _fmt_cp(pos.get("error_magnitude"))
    if pos.get("move_number"):
        label = t("explorer.expander", i=i + 1, opp=opponent, move=pos["move_number"], cp=cp)
    else:
        label = t("explorer.expander_nomove", i=i + 1, opp=opponent, cp=cp)

    with st.expander(label, expanded=(i == 0)):
        fen = pos.get("fen")
        if not fen:
            st.write(t("explorer.no_fen"))
            return

        move_played = pos.get("move_played")
        best_move = pos.get("best_move")

        col_board, col_info = st.columns([1, 1], gap="large")
        with col_board:
            components.html(
                _board_html(fen, move_played, best_move, player_color, white_name, black_name),
                height=450,
            )
        with col_info:
            st.markdown(_details_html(pos, fen, move_played, best_move), unsafe_allow_html=True)
            st.write("")
            st.caption(t("explorer.fen"))
            st.code(fen, language=None, wrap_lines=True)
            game_link = pos.get("game_url") or (
                pos["game_id"] if str(pos.get("game_id", "")).startswith("http") else None)
            if game_link:
                st.link_button(t("explorer.view_game"), game_link)

            # ── Ask AI why this move is a mistake (cached in SQLite) ─────────
            lang = st.session_state.get("lang", "pt")
            explanation = get_explanation(fen, move_played, concept_key, lang)
            err_key = f"explain_err::{fen}::{move_played}::{lang}"

            if explanation is None and st.button(t("explorer.ask_ai"), key=f"btn_explain::{i}::{fen}::{move_played}::{lang}"):
                with st.spinner(t("explorer.ai_thinking")):
                    try:
                        explanation = explain_position(
                            fen=fen,
                            move_played=move_played,
                            best_move=best_move,
                            concept_key=concept_key,
                            error_magnitude=pos.get("error_magnitude"),
                            player_color=player_color,
                            lang=lang,
                        )
                        save_explanation(fen, move_played, concept_key, lang, explanation)
                        st.session_state.pop(err_key, None)
                    except Exception as e:
                        st.session_state[err_key] = str(e)

            if st.session_state.get(err_key):
                st.error(t("analyze.error.failed", e=st.session_state[err_key]))

        if explanation:
            st.markdown(f"**{t('explorer.ai_title')}**")
            st.markdown(explanation)


def render():
    anchor("game-explorer")
    section_header(t("explorer.eyebrow"), t("explorer.title"), t("explorer.subtitle"))

    record = get_analysis(st.session_state.get("active_profile"))
    if record is None:
        st.info(t("explorer.no_profiles"))
        return

    weaknesses = [w for w in record["profile"].get("weaknesses", []) if w.get("sample_positions")]
    if not weaknesses:
        st.info(t("explorer.no_positions"))
        return

    # ── Concept selector ──────────────────────────────────────────────────────
    concept_options = {concept_label(w["concept"]): w for w in weaknesses}
    col_sel, col_sum = st.columns([2, 3], gap="large", vertical_alignment="bottom")
    with col_sel:
        selected_concept = st.selectbox(t("explorer.select_concept"), list(concept_options.keys()),
                                        key="explorer_concept_select")
    weakness = concept_options[selected_concept]
    with col_sum:
        st.markdown(
            f'<div style="color:{MUTED};padding-bottom:0.6rem">' + t(
                "explorer.summary",
                errors=weakness["error_occurrences"],
                rate=weakness["error_rate"] * 100,
                avg=_fmt_cp(weakness["avg_error_magnitude_cp"]),
            ) + "</div>",
            unsafe_allow_html=True,
        )

    # ── Position viewer ───────────────────────────────────────────────────────
    ordered, n_primary = _ordered_positions(weakness["sample_positions"])
    total = len(ordered)

    # Show at least 3 (or all if fewer); default to the deduped per-game count.
    show_key = f"explorer_show::{record['name']}::{weakness['concept']}"
    default_n = min(total, max(3, n_primary))
    show_n = min(st.session_state.get(show_key, default_n), total)

    st.caption(t("explorer.sample_positions", n=show_n, total=total))
    for i, pos in enumerate(ordered[:show_n]):
        _render_position(i, pos, weakness["concept"])

    if show_n < total:
        if st.button(t("explorer.load_more", shown=show_n, total=total), key=f"more_{show_key}"):
            st.session_state[show_key] = min(show_n + 3, total)
            st.rerun()
