import os
import tempfile

import chess
import streamlit as st
from main import analyze_profile, analyze_profile_from_username
from ui.i18n import t
from ui.profiles import make_profile_name
from config import OUTPUT_DIR, STOCKFISH_DEPTH


def _run_with_progress(fn, **kwargs):
    """
    Runs a pipeline function that accepts on_progress callback.
    Renders a progress bar + live log inside a st.status container.
    Returns (profile, diagnosis) or raises.
    """
    bar = st.progress(0, text=t("analyze.progress.starting"))
    log = st.empty()
    messages = []

    def on_progress(stage, current, total, message):
        # Compute overall progress fraction
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
            "<div style='font-size:0.8rem;color:#888;max-height:120px;overflow-y:auto'>"
            + "<br>".join(messages[-6:])
            + "</div>",
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
        if req["kind"] == "chesscom":
            profile = _run_with_progress(
                analyze_profile_from_username,
                username=req["username"],
                n_games=req["n_games"],
                profile_name=name,
                depth=depth,
            )
        else:
            profile = _run_with_progress(
                analyze_profile,
                pgn_path=req["pgn_path"],
                player_name=name,
                player_color=req["player_color"],
                depth=depth,
            )

        st.session_state.active_profile = f"{name}_profile.json"
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
        st.success(t("analyze.success"))
        st.info(t("analyze.info.scroll"))
    else:
        st.error(t("analyze.error.failed", e=outcome["error"]))


def _queue(request):
    st.session_state.analysis_request = request
    st.session_state.analysis_running = True
    st.rerun()


def render():
    st.markdown('<a name="analyze"></a>', unsafe_allow_html=True)
    st.title(t("analyze.title"))

    tab_fresh, tab_load = st.tabs([t("analyze.tab.fresh"), t("analyze.tab.load")])

    # ── Fresh Analysis ────────────────────────────────────────────────────────
    with tab_fresh:
        st.subheader(t("analyze.fresh.subheader"))

        # An analysis was queued on the previous run — execute it now (sidebar locked).
        if st.session_state.get("analysis_running"):
            _execute_pending()
            return

        _render_outcome()

        # While the AI diagnosis (phase 2) runs below, disable the Run button so the
        # user can't trigger a rerun that would interrupt the in-flight diagnosis.
        busy = st.session_state.get("diagnosis_running", False)

        source_options = [t("analyze.source.chesscom"), t("analyze.source.pgn")]
        source = st.radio(t("analyze.source.label"), source_options, horizontal=True, key="analyze_source")

        # Stockfish search depth — shared by both sources. Higher = more accurate
        # (fewer shallow-search false positives) but slower.
        depth = st.slider(t("analyze.depth.label"), min_value=8, max_value=12,
                          value=STOCKFISH_DEPTH, step=1, key="analyze_depth",
                          help=t("analyze.depth.help"))

        if source == t("analyze.source.chesscom"):
            username = st.text_input(t("analyze.username.label"), key="analyze_username")
            n_games = st.slider(t("analyze.ngames.label"), min_value=10, max_value=200, value=50, step=10, key="analyze_n_games")

            if st.button(t("analyze.btn.run"), key="run_chesscom", disabled=busy):
                if not username.strip():
                    st.error(t("analyze.error.no_user"))
                else:
                    name = make_profile_name(username.strip(), depth, n_games)
                    _queue({"kind": "chesscom", "username": username.strip(), "n_games": n_games,
                            "depth": depth, "profile_name": name})

        else:
            pgn_file = st.file_uploader(t("analyze.pgn.label"), type=["pgn"], key="analyze_pgn_upload")
            color_options = [t("analyze.color.white"), t("analyze.color.black")]
            color = st.radio(t("analyze.color.label"), color_options, horizontal=True, key="analyze_color")
            player_name = st.text_input(t("analyze.playername.label"), value="player", key="analyze_player_name")

            if st.button(t("analyze.btn.run"), key="run_pgn", disabled=busy):
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
                    _queue({"kind": "pgn", "pgn_path": pgn_path,
                            "player_color": player_color, "depth": depth, "profile_name": name})

    # ── Load Saved Profile ────────────────────────────────────────────────────
    with tab_load:
        st.subheader(t("analyze.load.subheader"))

        profile_files = sorted(
            f for f in os.listdir(OUTPUT_DIR) if f.endswith("_profile.json")
        ) if os.path.isdir(OUTPUT_DIR) else []

        if not profile_files:
            st.info(t("analyze.load.no_profiles"))
        else:
            active = st.session_state.get("active_profile")
            if active and active in profile_files:
                st.success(t("analyze.load.selected", f=active))
            st.info(t("analyze.load.info"))
