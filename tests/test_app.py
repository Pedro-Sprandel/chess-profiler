"""Streamlit AppTest coverage for app.py and all page sections."""
import os
import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "app.py")

SAMPLE_PROFILE = {
    "total_games": 2,
    "total_positions_analyzed": 40,
    "total_errors_detected": 6,
    "overall_error_rate": 0.15,
    "weaknesses": [
        {
            "concept": "weak_square",
            "error_occurrences": 4,
            "total_occurrences": 8,
            "error_rate": 0.5,
            "avg_error_magnitude_cp": 85.0,
            "sample_positions": [
                {
                    "game_id": "https://chess.com/game/123",
                    "white": "Player1",
                    "black": "Player2",
                    "player_color": "white",
                    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                    "move_played": "e2e4",
                    "best_move": "d2d4",
                    "error_magnitude": 80.0,
                }
            ],
        }
    ],
}

SAMPLE_DIAGNOSIS = {
    "en": {
        "root_cause": {
            "id": "static_thinking",
            "name": "Static Thinking",
            "description": "Player fails to evaluate dynamic imbalances.",
        },
        "weakness_classification": [
            {
                "concept": "weak_square",
                "classification": "PRIMARY",
                "reasoning": "Root of the problem.",
            }
        ],
        "study_priority": [
            {
                "concept": "weak_square",
                "silman_chapter": 3,
                "priority_rank": 1,
                "reason": "Root cause concept.",
                "silman_name": "Weak Square",
                "silman_page": 67,
                "silman_description": "A square that cannot be defended by a pawn.",
            }
        ],
        "cognitive_pattern": "Ignores weak squares in opponent's field.",
        "confidence": "HIGH",
    },
    "pt": {
        "root_cause": {
            "id": "static_thinking",
            "name": "Pensamento Estático",
            "description": "O jogador não avalia desequilíbrios dinâmicos.",
        },
        "weakness_classification": [
            {
                "concept": "weak_square",
                "classification": "PRIMARY",
                "reasoning": "Raiz do problema.",
            }
        ],
        "study_priority": [
            {
                "concept": "weak_square",
                "silman_chapter": 3,
                "priority_rank": 1,
                "reason": "Conceito da causa raiz.",
                "silman_name": "Casa Fraca",
                "silman_page": 67,
                "silman_description": "Uma casa que não pode ser defendida por um peão.",
            }
        ],
        "cognitive_pattern": "Ignora casas fracas no campo adversário.",
        "confidence": "HIGH",
    },
}

PYTEST_PROFILE = "_pytest"


@pytest.fixture()
def with_profile_files():
    """Store a sample analysis (profile + diagnosis) in the test DB and yield its name.

    conftest.py points every Database() at a per-test temp file, so nothing leaks
    into data/profiler.db.
    """
    from modules.db import Database
    with Database() as db:
        db.save_analysis(PYTEST_PROFILE, SAMPLE_PROFILE, subject="pytest_player",
                         source="pgn", depth=10, n_games=2)
        db.save_diagnosis(PYTEST_PROFILE, SAMPLE_DIAGNOSIS)
    yield PYTEST_PROFILE


class TestAppStartup:
    def test_runs_without_exception(self):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        assert not at.exception

    def test_default_language_is_portuguese(self):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        assert at.session_state.lang == "pt"

    def test_sidebar_language_radio_present(self):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        assert not at.exception
        radios = at.radio
        assert any(r.key == "lang" for r in radios)

    def test_active_profile_initialised_in_session_state(self):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        assert "active_profile" in at.session_state


class TestLanguageSwitching:
    def test_switch_to_portuguese(self):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        lang_radio = next(r for r in at.radio if r.key == "lang")
        lang_radio.set_value("pt").run()
        assert not at.exception
        assert at.session_state.lang == "pt"

    def test_switch_back_to_english(self):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        next(r for r in at.radio if r.key == "lang").set_value("pt").run()
        # Re-fetch the widget after the previous run
        next(r for r in at.radio if r.key == "lang").set_value("en").run()
        assert not at.exception
        assert at.session_state.lang == "en"

    def test_page_renders_after_language_switch(self):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        lang_radio = next(r for r in at.radio if r.key == "lang")
        lang_radio.set_value("pt").run()
        assert not at.exception


class TestNoDataState:
    def test_profile_section_shows_no_data_info(self):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.session_state["active_profile"] = None
        at.run()
        assert not at.exception

    def test_diagnosis_section_shows_no_data_info(self):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.session_state["active_profile"] = None
        at.run()
        assert not at.exception

    def test_analyze_tab_fresh_renders(self):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        assert not at.exception
        assert any(r.key == "analyze_source" for r in at.radio)


class TestWithProfileData:
    def test_profile_metrics_visible(self, with_profile_files):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.session_state["active_profile"] = with_profile_files
        at.run()
        assert not at.exception
        metric_values = [m.value for m in at.metric]
        assert "2" in metric_values or 2 in metric_values

    def test_diagnosis_renders_without_exception(self, with_profile_files):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.session_state["active_profile"] = with_profile_files
        at.run()
        assert not at.exception

    def test_diagnosis_renders_in_portuguese(self, with_profile_files):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.session_state["active_profile"] = with_profile_files
        at.session_state["lang"] = "pt"
        at.run()
        assert not at.exception

    def test_profile_selector_picks_up_fixture_file(self, with_profile_files):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.session_state["active_profile"] = with_profile_files
        at.run()
        assert not at.exception
        assert at.session_state.active_profile == with_profile_files

    def test_defaults_to_most_recent_analysis(self, with_profile_files):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        assert not at.exception
        assert at.session_state.active_profile == with_profile_files

    def test_legacy_filename_in_session_is_normalized(self, with_profile_files):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.session_state["active_profile"] = with_profile_files + "_profile.json"
        at.run()
        assert not at.exception
        assert at.session_state.active_profile == with_profile_files

    def test_deleted_selection_falls_back(self, with_profile_files):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.session_state["active_profile"] = "does_not_exist"
        at.run()
        assert not at.exception
        assert at.session_state.active_profile == with_profile_files

    def test_diagnosis_cards_render(self, with_profile_files):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.session_state["active_profile"] = with_profile_files
        at.session_state["lang"] = "en"
        at.run()
        assert not at.exception
        html = " ".join(m.value for m in at.markdown)
        assert "Static Thinking" in html


class TestMissingDiagnosis:
    def test_generate_button_shown_when_no_diagnosis(self):
        from modules.db import Database
        with Database() as db:
            db.save_analysis("_nodiag", SAMPLE_PROFILE, subject="x")
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.session_state["active_profile"] = "_nodiag"
        at.run()
        assert not at.exception
        assert any(b.key == "diagnosis_generate" for b in at.button)


class TestAnalyzePageInputs:
    def test_no_username_shows_error(self):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        source_radio = next(r for r in at.radio if r.key == "analyze_source")
        source_radio.set_value(source_radio.options[0]).run()
        run_btn = next(b for b in at.button if b.key == "run_chesscom")
        run_btn.click().run()
        assert not at.exception
        assert any("username" in (e.value or "").lower() or "usuário" in (e.value or "").lower()
                   for e in at.error)


class TestDeleteAnalysis:
    def test_delete_removes_from_db_and_falls_back(self, with_profile_files):
        from modules.db import Database
        with Database() as db:
            db.save_analysis("_older", SAMPLE_PROFILE, subject="older",
                             created_at="2020-01-01 00:00:00")
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.session_state["active_profile"] = with_profile_files
        at.run()
        next(b for b in at.button if b.key == "delete_confirm").click().run()
        assert not at.exception
        with Database() as db:
            assert db.get_analysis(with_profile_files) is None
        assert at.session_state.active_profile == "_older"
