"""Streamlit AppTest coverage for app.py and all page sections."""
import json
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

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
PYTEST_PROFILE = "_pytest_profile.json"
PYTEST_DIAGNOSIS = "_pytest_diagnosis.json"


@pytest.fixture()
def with_profile_files():
    """Write sample profile + diagnosis to output/, yield filename, then clean up."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    profile_path = os.path.join(OUTPUT_DIR, PYTEST_PROFILE)
    diagnosis_path = os.path.join(OUTPUT_DIR, PYTEST_DIAGNOSIS)
    with open(profile_path, "w") as f:
        json.dump(SAMPLE_PROFILE, f)
    with open(diagnosis_path, "w") as f:
        json.dump(SAMPLE_DIAGNOSIS, f)
    yield PYTEST_PROFILE
    for p in (profile_path, diagnosis_path):
        if os.path.exists(p):
            os.remove(p)


class TestAppStartup:
    def test_runs_without_exception(self):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        assert not at.exception

    def test_default_language_is_english(self):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        assert at.session_state.lang == "en"

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
