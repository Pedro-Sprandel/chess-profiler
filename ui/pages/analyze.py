import os
import chess
import streamlit as st
from main import analyze_player, analyze_player_from_username
from ui.i18n import t

OUTPUT_DIR = "output"


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


def render():
    st.markdown('<a name="analyze"></a>', unsafe_allow_html=True)
    st.title(t("analyze.title"))

    tab_fresh, tab_load = st.tabs([t("analyze.tab.fresh"), t("analyze.tab.load")])

    # ── Fresh Analysis ────────────────────────────────────────────────────────
    with tab_fresh:
        st.subheader(t("analyze.fresh.subheader"))
        source_options = [t("analyze.source.chesscom"), t("analyze.source.pgn")]
        source = st.radio(t("analyze.source.label"), source_options, horizontal=True, key="analyze_source")

        if source == t("analyze.source.chesscom"):
            username = st.text_input(t("analyze.username.label"), key="analyze_username")
            n_games = st.slider(t("analyze.ngames.label"), min_value=10, max_value=200, value=50, step=10, key="analyze_n_games")

            if st.button(t("analyze.btn.run"), key="run_chesscom"):
                if not username.strip():
                    st.error(t("analyze.error.no_user"))
                else:
                    try:
                        profile, diagnosis = _run_with_progress(
                            analyze_player_from_username,
                            username=username.strip(),
                            n_games=n_games,
                        )
                        st.session_state.active_profile = f"{username.strip()}_profile.json"
                        st.success(t("analyze.success"))
                        st.json({"weaknesses_found": len(profile["weaknesses"]),
                                 "root_cause": diagnosis["root_cause"]["name"]})
                        st.info(t("analyze.info.scroll"))
                    except Exception as e:
                        st.error(t("analyze.error.failed", e=e))

        else:
            pgn_file = st.file_uploader(t("analyze.pgn.label"), type=["pgn"], key="analyze_pgn_upload")
            color_options = [t("analyze.color.white"), t("analyze.color.black")]
            color = st.radio(t("analyze.color.label"), color_options, horizontal=True, key="analyze_color")
            player_name = st.text_input(t("analyze.playername.label"), value="player", key="analyze_player_name")

            if st.button(t("analyze.btn.run"), key="run_pgn"):
                if pgn_file is None:
                    st.error(t("analyze.error.no_pgn"))
                elif not player_name.strip():
                    st.error(t("analyze.error.no_name"))
                else:
                    pgn_path = f"/tmp/{pgn_file.name}"
                    with open(pgn_path, "wb") as f:
                        f.write(pgn_file.read())

                    try:
                        player_color = chess.WHITE if color == t("analyze.color.white") else chess.BLACK
                        profile, diagnosis = _run_with_progress(
                            analyze_player,
                            pgn_path=pgn_path,
                            player_name=player_name.strip(),
                            player_color=player_color,
                        )
                        st.session_state.active_profile = f"{player_name.strip()}_profile.json"
                        st.success(t("analyze.success"))
                        st.json({"weaknesses_found": len(profile["weaknesses"]),
                                 "root_cause": diagnosis["root_cause"]["name"]})
                        st.info(t("analyze.info.scroll"))
                    except Exception as e:
                        st.error(t("analyze.error.failed", e=e))

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
