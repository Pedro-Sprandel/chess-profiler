import os
import tempfile

import chess
import pandas as pd
import streamlit as st

from config import STOCKFISH_DEPTH
from main import analyze_profile, analyze_profile_from_username
from ui.auth import current_user_id
from ui.i18n import t
from ui.profiles import format_date, make_profile_name
from ui.store import list_analyses
from ui.style import MUTED, anchor, section_header


def _run_with_progress(fn, **kwargs):
    """
    Runs a pipeline function that accepts on_progress callback.
    Renders a progress bar + a short live log. Returns the function's result.
    """
    bar = st.progress(0, text=t("analyze.progress.starting"))
    log = st.empty()
    messages = []

    def on_progress(stage, current, total, message):
        if stage in ("fetch", "load"):
            frac = 0.05
        elif stage == "game":
            frac = 0.05 + 0.80 * ((current + 1) / max(total, 1))
        elif stage == "profile":
            frac = 0.87
        elif stage == "ai":
            frac = 0.93
        else:  # done
            frac = 1.0

        label = message.replace("[main] ", "")
        bar.progress(frac, text=label)
        messages.append(label)
        log.markdown(
            f"<div style='font-size:0.8rem;color:{MUTED};font-family:monospace;"
            "max-height:120px;overflow-y:auto'>" + "<br>".join(messages[-6:]) + "</div>",
            unsafe_allow_html=True,
        )

    result = fn(**kwargs, on_progress=on_progress)
    bar.progress(1.0, text=t("analyze.progress.done"))
    log.empty()
    return result


def _execute_pending():
    """Build the weakness profile for the queued request (set when Run was clicked).

    This is phase 1 — the fast, local part (games → Stockfish → profile). The slow AI
    diagnosis runs afterwards as a separate phase so the Profile Dashboard can render
    immediately while the diagnosis loads below. Runs on a dedicated rerun where the
    sidebar widgets are disabled so the user can't interrupt the in-flight pipeline.
    """
    req = st.session_state.analysis_request
    try:
        depth = req.get("depth", STOCKFISH_DEPTH)
        name = req["profile_name"]
        owner_id = current_user_id()
        if req["kind"] == "chesscom":
            profile = _run_with_progress(
                analyze_profile_from_username,
                username=req["username"],
                n_games=req["n_games"],
                profile_name=name,
                depth=depth,
                export_json=False,
                owner_id=owner_id,
            )
        else:
            try:
                profile = _run_with_progress(
                    analyze_profile,
                    pgn_path=req["pgn_path"],
                    player_name=name,
                    player_color=req["player_color"],
                    depth=depth,
                    subject=req["subject"],
                    export_json=False,
                    owner_id=owner_id,
                )
            finally:
                if os.path.exists(req["pgn_path"]):
                    os.remove(req["pgn_path"])

        st.session_state.active_profile = name
        st.session_state.analysis_outcome = {
            "ok": True,
            "weaknesses_found": len(profile["weaknesses"]),
        }
        # Hand off to phase 2: the diagnosis section runs the AI call on the next rerun.
        st.session_state.diagnosis_running = True
        st.session_state.diagnosis_target = name
    except Exception as e:
        st.session_state.analysis_outcome = {"ok": False, "error": str(e)}
    finally:
        st.session_state.analysis_running = False
        st.session_state.pop("analysis_request", None)
        st.rerun()


def _render_outcome():
    outcome = st.session_state.pop("analysis_outcome", None)
    if not outcome:
        return
    if outcome["ok"]:
        st.success(t("analyze.success", n=outcome.get("weaknesses_found", 0)))
    else:
        st.error(t("analyze.error.failed", e=outcome["error"]))


def _queue(request):
    st.session_state.analysis_request = request
    st.session_state.analysis_running = True
    st.rerun()


def _render_form(busy: bool):
    source_options = [t("analyze.source.chesscom"), t("analyze.source.pgn")]
    source = st.radio(t("analyze.source.label"), source_options, horizontal=True, key="analyze_source")
    is_chesscom = source == t("analyze.source.chesscom")

    col_input, col_params = st.columns([3, 2], gap="large")

    with col_params:
        # Stockfish search depth — shared by both sources. Higher = more accurate
        # (fewer shallow-search false positives) but slower.
        depth = st.slider(t("analyze.depth.label"), min_value=8, max_value=12,
                          value=STOCKFISH_DEPTH, step=1, key="analyze_depth",
                          help=t("analyze.depth.help"))
        if is_chesscom:
            n_games = st.slider(t("analyze.ngames.label"), min_value=10, max_value=200,
                                value=50, step=10, key="analyze_n_games")

    with col_input:
        if is_chesscom:
            username = st.text_input(t("analyze.username.label"), key="analyze_username",
                                     placeholder="hikaru")
            if st.button(t("analyze.btn.run"), key="run_chesscom", type="primary", disabled=busy):
                if not username.strip():
                    st.error(t("analyze.error.no_user"))
                else:
                    name = make_profile_name(username.strip(), depth, n_games)
                    _queue({"kind": "chesscom", "username": username.strip(), "n_games": n_games,
                            "depth": depth, "profile_name": name})
        else:
            pgn_file = st.file_uploader(t("analyze.pgn.label"), type=["pgn"], key="analyze_pgn_upload")
            c1, c2 = st.columns(2)
            with c1:
                player_name = st.text_input(t("analyze.playername.label"), key="analyze_player_name")
            with c2:
                color_options = [t("analyze.color.white"), t("analyze.color.black")]
                color = st.radio(t("analyze.color.label"), color_options, horizontal=True,
                                 key="analyze_color")

            if st.button(t("analyze.btn.run"), key="run_pgn", type="primary", disabled=busy):
                if pgn_file is None:
                    st.error(t("analyze.error.no_pgn"))
                elif not player_name.strip():
                    st.error(t("analyze.error.no_name"))
                else:
                    # tempfile evita colisão de nomes entre usuários simultâneos
                    with tempfile.NamedTemporaryFile(suffix=".pgn", delete=False) as f:
                        f.write(pgn_file.read())
                        pgn_path = f.name
                    player_color = chess.WHITE if color == t("analyze.color.white") else chess.BLACK
                    name = make_profile_name(player_name.strip(), depth)
                    _queue({"kind": "pgn", "pgn_path": pgn_path, "subject": player_name.strip(),
                            "player_color": player_color, "depth": depth, "profile_name": name})


def _render_history(busy: bool):
    analyses = list_analyses()
    if not analyses:
        return

    st.write("")
    st.markdown(f"### {t('analyze.history')}")
    st.caption(t("analyze.history.hint"))

    names = [a["name"] for a in analyses]
    df = pd.DataFrame([
        {
            t("analyze.history.col.player"): a["subject"],
            t("analyze.history.col.date"): format_date(a["created_at"]),
            t("analyze.history.col.games"): a["total_games"],
            t("analyze.history.col.depth"): a["depth"],
            t("analyze.history.col.rate"): round((a["overall_error_rate"] or 0) * 100, 1),
            t("analyze.history.col.weak"): a["n_weaknesses"],
            t("analyze.history.col.diag"): t("analyze.history.yes") if a["has_diagnosis"]
                                            else t("analyze.history.no"),
        }
        for a in analyses
    ])

    active = st.session_state.get("active_profile")
    table_key = f"history_table::{active}"

    def _on_select():
        rows = st.session_state[table_key].selection.rows
        if rows and not busy:
            st.session_state.active_profile = names[rows[0]]

    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        on_select=_on_select,
        selection_mode="single-row",
        key=table_key,
        column_config={
            t("analyze.history.col.rate"): st.column_config.NumberColumn(format="%.1f%%"),
        },
    )


def render():
    anchor("analyze")
    section_header(t("analyze.eyebrow"), t("analyze.title"), t("analyze.subtitle"))

    # An analysis was queued on the previous run — execute it now (sidebar locked).
    if st.session_state.get("analysis_running"):
        _execute_pending()
        return

    _render_outcome()

    # While the AI diagnosis (phase 2) runs below, disable the Run button so the
    # user can't trigger a rerun that would interrupt the in-flight diagnosis.
    busy = st.session_state.get("diagnosis_running", False)

    _render_form(busy)
    _render_history(busy)
