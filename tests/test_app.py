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
PASSWORD = "correct-horse"

# Session of the account every test is logged in as (set by the autouse fixture).
_AUTH: dict = {}


@pytest.fixture(autouse=True)
def logged_in():
    """Create an account + login session; _app() injects it into the AppTest.

    conftest.py points the AppStore at a per-test temp file (or a scratch Postgres
    database with TEST_DATABASE_URL), so nothing leaks into data/profiler.db.
    """
    from modules.app_store import AppStore
    with AppStore() as store:
        user = store.create_user("pytest_user", PASSWORD)
        token = store.create_session(user["id"])
    _AUTH.clear()
    _AUTH.update({"user": user, "token": token})
    yield _AUTH


def _app(logged: bool = True) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    if logged:
        at.session_state["auth"] = {"user": dict(_AUTH["user"]), "token": _AUTH["token"]}
    return at


def _save(name, profile=SAMPLE_PROFILE, diagnosis=None, owner_id="me", **kwargs):
    from modules.app_store import AppStore
    if owner_id == "me":
        owner_id = _AUTH["user"]["id"]
    with AppStore() as store:
        store.save_analysis(name, profile, owner_id=owner_id, **kwargs)
        if diagnosis is not None:
            store.save_diagnosis(name, diagnosis)


@pytest.fixture()
def with_profile_files():
    """Store a sample analysis (profile + diagnosis) owned by the logged-in user."""
    _save(PYTEST_PROFILE, diagnosis=SAMPLE_DIAGNOSIS, subject="pytest_player",
          source="pgn", depth=10, n_games=2)
    yield PYTEST_PROFILE


class TestAppStartup:
    def test_runs_without_exception(self):
        at = _app()
        at.run()
        assert not at.exception

    def test_default_language_is_portuguese(self):
        at = _app()
        at.run()
        assert at.session_state.lang == "pt"

    def test_sidebar_language_radio_present(self):
        at = _app()
        at.run()
        assert not at.exception
        radios = at.radio
        assert any(r.key == "lang" for r in radios)

    def test_active_profile_initialised_in_session_state(self):
        at = _app()
        at.run()
        assert "active_profile" in at.session_state


class TestLanguageSwitching:
    def test_switch_to_portuguese(self):
        at = _app()
        at.run()
        lang_radio = next(r for r in at.radio if r.key == "lang")
        lang_radio.set_value("pt").run()
        assert not at.exception
        assert at.session_state.lang == "pt"

    def test_switch_back_to_english(self):
        at = _app()
        at.run()
        next(r for r in at.radio if r.key == "lang").set_value("pt").run()
        # Re-fetch the widget after the previous run
        next(r for r in at.radio if r.key == "lang").set_value("en").run()
        assert not at.exception
        assert at.session_state.lang == "en"

    def test_page_renders_after_language_switch(self):
        at = _app()
        at.run()
        lang_radio = next(r for r in at.radio if r.key == "lang")
        lang_radio.set_value("pt").run()
        assert not at.exception


class TestNoDataState:
    def test_profile_section_shows_no_data_info(self):
        at = _app()
        at.session_state["active_profile"] = None
        at.run()
        assert not at.exception

    def test_diagnosis_section_shows_no_data_info(self):
        at = _app()
        at.session_state["active_profile"] = None
        at.run()
        assert not at.exception

    def test_analyze_tab_fresh_renders(self):
        at = _app()
        at.run()
        assert not at.exception
        assert any(r.key == "analyze_source" for r in at.radio)


class TestWithProfileData:
    def test_profile_metrics_visible(self, with_profile_files):
        at = _app()
        at.session_state["active_profile"] = with_profile_files
        at.run()
        assert not at.exception
        metric_values = [m.value for m in at.metric]
        assert "2" in metric_values or 2 in metric_values

    def test_diagnosis_renders_without_exception(self, with_profile_files):
        at = _app()
        at.session_state["active_profile"] = with_profile_files
        at.run()
        assert not at.exception

    def test_diagnosis_renders_in_portuguese(self, with_profile_files):
        at = _app()
        at.session_state["active_profile"] = with_profile_files
        at.session_state["lang"] = "pt"
        at.run()
        assert not at.exception

    def test_profile_selector_picks_up_fixture_file(self, with_profile_files):
        at = _app()
        at.session_state["active_profile"] = with_profile_files
        at.run()
        assert not at.exception
        assert at.session_state.active_profile == with_profile_files

    def test_defaults_to_most_recent_analysis(self, with_profile_files):
        at = _app()
        at.run()
        assert not at.exception
        assert at.session_state.active_profile == with_profile_files

    def test_legacy_filename_in_session_is_normalized(self, with_profile_files):
        at = _app()
        at.session_state["active_profile"] = with_profile_files + "_profile.json"
        at.run()
        assert not at.exception
        assert at.session_state.active_profile == with_profile_files

    def test_deleted_selection_falls_back(self, with_profile_files):
        at = _app()
        at.session_state["active_profile"] = "does_not_exist"
        at.run()
        assert not at.exception
        assert at.session_state.active_profile == with_profile_files

    def test_diagnosis_cards_render(self, with_profile_files):
        at = _app()
        at.session_state["active_profile"] = with_profile_files
        at.session_state["lang"] = "en"
        at.run()
        assert not at.exception
        html = " ".join(m.value for m in at.markdown)
        assert "Static Thinking" in html


class TestMissingDiagnosis:
    def test_generate_button_shown_when_no_diagnosis(self):
        _save("_nodiag", subject="x")
        at = _app()
        at.session_state["active_profile"] = "_nodiag"
        at.run()
        assert not at.exception
        assert any(b.key == "diagnosis_generate" for b in at.button)


class TestAnalyzePageInputs:
    def test_no_username_shows_error(self):
        at = _app()
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
        _save("_older", subject="older", created_at="2020-01-01 00:00:00")
        at = _app()
        at.session_state["active_profile"] = with_profile_files
        at.run()
        next(b for b in at.button if b.key == "delete_confirm").click().run()
        assert not at.exception
        from modules.app_store import AppStore
        with AppStore() as store:
            assert store.get_analysis(with_profile_files) is None
        assert at.session_state.active_profile == "_older"


# ── Login ─────────────────────────────────────────────────────────────────────

def _fill(at, **values):
    for key, value in values.items():
        next(w for w in at.text_input if w.key == key).input(value)


def _submit(at, key):
    next(b for b in at.button if b.key == key).click().run()


class TestLoginGate:
    def test_anonymous_sees_login_and_no_app(self, with_profile_files):
        at = _app(logged=False)
        at.run()
        assert not at.exception
        keys = {w.key for w in at.text_input}
        assert {"login_username", "login_password", "signup_username"} <= keys
        assert not any(r.key == "analyze_source" for r in at.radio)
        assert "active_profile" not in at.session_state
        assert any(r.key == "lang" for r in at.radio)

    def test_login_with_valid_credentials(self, with_profile_files):
        at = _app(logged=False)
        at.run()
        _fill(at, login_username="pytest_user", login_password=PASSWORD)
        _submit(at, "login_submit")
        assert not at.exception
        assert at.session_state.auth["user"]["username"] == "pytest_user"
        assert at.session_state.active_profile == with_profile_files
        assert any(r.key == "analyze_source" for r in at.radio)
        # The password typed in the form is not kept in session state.
        assert "login_password" not in at.session_state

    def test_wrong_password_shows_error(self):
        at = _app(logged=False)
        at.run()
        _fill(at, login_username="pytest_user", login_password="wrong-password")
        _submit(at, "login_submit")
        assert not at.exception
        assert "auth" not in at.session_state
        assert len(at.error) == 1

    def test_signup_creates_account_and_logs_in(self):
        at = _app(logged=False)
        at.run()
        _fill(at, signup_username="newbie", signup_password="new-password",
              signup_confirm="new-password")
        _submit(at, "signup_submit")
        assert not at.exception
        user = at.session_state.auth["user"]
        assert user["username"] == "newbie"
        assert user["is_admin"] is False  # pytest_user was the first account
        assert at.session_state.active_profile is None  # new account starts empty

    def test_signup_password_mismatch(self):
        at = _app(logged=False)
        at.run()
        _fill(at, signup_username="newbie", signup_password="new-password",
              signup_confirm="other-password")
        _submit(at, "signup_submit")
        assert "auth" not in at.session_state
        assert len(at.error) == 1

    def test_signup_requires_invite_code_when_configured(self, monkeypatch):
        import config
        monkeypatch.setattr(config, "SIGNUP_CODE", "s3cret")
        at = _app(logged=False)
        at.run()
        _fill(at, signup_username="newbie", signup_password="new-password",
              signup_confirm="new-password", signup_code="guess")
        _submit(at, "signup_submit")
        assert "auth" not in at.session_state
        _fill(at, signup_code="s3cret")
        _submit(at, "signup_submit")
        assert at.session_state.auth["user"]["username"] == "newbie"

    def test_signup_closed(self, monkeypatch):
        import config
        monkeypatch.setattr(config, "ALLOW_SIGNUP", False)
        at = _app(logged=False)
        at.run()
        assert not at.exception
        assert not any(w.key == "signup_username" for w in at.text_input)

    def test_session_resumed_from_cookie(self, monkeypatch, with_profile_files):
        """A page reload has a fresh session_state; the cookie token restores the login."""
        monkeypatch.setattr("ui.auth._cookie_token", lambda: _AUTH["token"])
        at = _app(logged=False)
        at.run()
        assert not at.exception
        assert at.session_state.auth["user"]["username"] == "pytest_user"
        assert at.session_state.active_profile == with_profile_files

    def test_revoked_session_goes_back_to_login(self):
        from modules.app_store import AppStore
        at = _app()
        at.run()
        with AppStore() as store:
            store.revoke_session(_AUTH["token"])
        at.run()
        assert not at.exception
        assert "auth" not in at.session_state
        assert any(w.key == "login_username" for w in at.text_input)

    def test_logout(self, with_profile_files):
        from modules.app_store import AppStore
        at = _app()
        at.run()
        next(b for b in at.button if b.key == "logout_btn").click().run()
        assert not at.exception
        assert "auth" not in at.session_state
        assert "active_profile" not in at.session_state
        with AppStore() as store:
            assert store.user_for_token(_AUTH["token"]) is None


class TestPerUserAnalyses:
    def test_other_users_analyses_are_invisible(self, with_profile_files):
        from modules.app_store import AppStore
        with AppStore() as store:
            other = store.create_user("someone_else", PASSWORD)
        _save("_theirs", subject="theirs", owner_id=other["id"],
              created_at="2099-01-01 00:00:00")  # newest overall, but not ours
        at = _app()
        at.session_state["active_profile"] = "_theirs"  # even if forced into the session
        at.run()
        assert not at.exception
        assert at.session_state.active_profile == with_profile_files
        assert "_theirs" not in next(s for s in at.selectbox if s.key == "profile_widget").options

    def test_admin_adopts_orphan_analyses(self):
        _save("_orphan", subject="legacy", owner_id=None)  # e.g. created before login existed
        at = _app()  # pytest_user is the first account → admin
        at.run()
        assert not at.exception
        assert at.session_state.active_profile == "_orphan"

    def test_non_admin_does_not_adopt_orphans(self):
        from modules.app_store import AppStore
        with AppStore() as store:
            user = store.create_user("regular", PASSWORD)
            token = store.create_session(user["id"])
        _save("_orphan", subject="legacy", owner_id=None)
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.session_state["auth"] = {"user": user, "token": token}
        at.run()
        assert not at.exception
        assert at.session_state.active_profile is None


class TestAttributionDisplay:
    def test_llm_attribution_badge_and_coverage_caption(self):
        import copy
        profile = copy.deepcopy(SAMPLE_PROFILE)
        profile["attribution_summary"] = {"rule": 5, "llm": 1, "unattributed": 2}
        profile["weaknesses"][0]["llm_errors"] = 1
        profile["weaknesses"][0]["sample_positions"][0].update({
            "attribution": "llm", "motif": "llm", "confidence": "high",
            "reason": {"en": "The knight takes over d5.", "pt": "O cavalo ocupa d5."},
        })
        _save("_llm", profile=profile, subject="x")
        at = _app()
        at.session_state["active_profile"] = "_llm"
        at.session_state["lang"] = "pt"
        at.run()
        assert not at.exception
        text = " ".join(m.value for m in at.markdown) + " ".join(c.value for c in at.caption)
        assert "inferido pela IA" in text
        assert "O cavalo ocupa d5." in text
        assert "sem conceito: 2" in text
