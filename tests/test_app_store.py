"""AppStore: accounts, login sessions and per-user analyses.

Runs on SQLite by default; set TEST_DATABASE_URL to run the same tests on PostgreSQL.
"""
import sqlite3

import pytest

import modules.app_store as app_store
from modules.app_store import AppStore, AuthError, hash_password, verify_password

PROFILE = {"total_games": 3, "total_positions_analyzed": 50, "overall_error_rate": 0.2,
           "weaknesses": [{"concept": "weak_square"}]}
PW = "correct-horse"


def _err(fn, *args, **kwargs) -> str:
    with pytest.raises(AuthError) as exc:
        fn(*args, **kwargs)
    return exc.value.code


# ── Passwords ─────────────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_salted_and_verifies(self):
        a, b = hash_password(PW), hash_password(PW)
        assert a != b
        assert a.startswith("pbkdf2_sha256$")
        assert PW not in a
        assert verify_password(PW, a) and verify_password(PW, b)

    def test_wrong_password_and_garbage_hash(self):
        assert not verify_password("nope", hash_password(PW))
        assert not verify_password(PW, "not-a-hash")
        assert not verify_password(PW, "md5$1$00$00")


# ── Accounts ──────────────────────────────────────────────────────────────────

class TestUsers:
    def test_first_user_is_admin_next_are_not(self, store):
        first = store.create_user("ana", PW)
        second = store.create_user("bia", PW)
        assert first["is_admin"] is True
        assert second["is_admin"] is False
        assert store.user_count() == 2

    def test_username_is_unique_case_insensitive(self, store):
        store.create_user("Ana", PW)
        assert _err(store.create_user, "ana", PW) == "username_taken"
        assert store.get_user_by_username("ANA")["username"] == "Ana"

    @pytest.mark.parametrize("name", ["ab", "a" * 33, "has space", "acentuação", "", "x;drop"])
    def test_invalid_usernames(self, store, name):
        assert _err(store.create_user, name, PW) == "username_invalid"

    def test_password_length_rules(self, store):
        assert _err(store.create_user, "ana", "short") == "password_short"
        assert _err(store.create_user, "ana", "x" * 300) == "password_long"

    def test_password_is_not_stored_in_clear(self, store):
        store.create_user("ana", PW)
        row = store._one("SELECT password_hash FROM users WHERE username_key = 'ana'")
        assert PW not in row["password_hash"]


class TestAuthenticate:
    def test_success_records_last_login(self, store):
        store.create_user("ana", PW)
        user = store.authenticate(" ANA ", PW)
        assert user["username"] == "ana"
        assert user["last_login_at"]

    def test_wrong_password_and_unknown_user_look_the_same(self, store):
        store.create_user("ana", PW)
        assert _err(store.authenticate, "ana", "wrong-pass") == "invalid_credentials"
        assert _err(store.authenticate, "ghost", PW) == "invalid_credentials"

    def test_lockout_after_repeated_failures(self, store):
        store.create_user("ana", PW)
        for _ in range(app_store.MAX_FAILED_LOGINS - 1):
            assert _err(store.authenticate, "ana", "wrong-pass") == "invalid_credentials"
        assert _err(store.authenticate, "ana", "wrong-pass") == "locked"
        # Even the right password is refused while locked.
        assert _err(store.authenticate, "ana", PW) == "locked"

    def test_lock_expires(self, store):
        store.create_user("ana", PW)
        store._x("UPDATE users SET locked_until = ? WHERE username_key = 'ana'",
                 ("2000-01-01 00:00:00.000000",))
        assert store.authenticate("ana", PW)["username"] == "ana"

    def test_success_resets_failure_counter(self, store):
        store.create_user("ana", PW)
        for _ in range(app_store.MAX_FAILED_LOGINS - 1):
            _err(store.authenticate, "ana", "wrong-pass")
        store.authenticate("ana", PW)
        assert _err(store.authenticate, "ana", "wrong-pass") == "invalid_credentials"

    def test_old_hash_is_upgraded_on_login(self, store, monkeypatch):
        store.create_user("ana", PW)
        monkeypatch.setattr(app_store, "PBKDF2_ITERATIONS", 2_000)
        store.authenticate("ana", PW)
        stored = store._one("SELECT password_hash FROM users WHERE username_key = 'ana'")
        assert stored["password_hash"].split("$")[1] == "2000"
        assert store.authenticate("ana", PW)


class TestSessions:
    def test_token_roundtrip_and_revoke(self, store):
        user = store.create_user("ana", PW)
        token = store.create_session(user["id"])
        assert store.user_for_token(token)["id"] == user["id"]
        store.revoke_session(token)
        assert store.user_for_token(token) is None

    def test_only_token_hash_is_stored(self, store):
        user = store.create_user("ana", PW)
        token = store.create_session(user["id"])
        rows = store._all("SELECT token_hash FROM sessions")
        assert token not in [r["token_hash"] for r in rows]

    def test_unknown_or_empty_token(self, store):
        assert store.user_for_token("nope") is None
        assert store.user_for_token(None) is None

    def test_expired_session_is_rejected_and_purged(self, store):
        user = store.create_user("ana", PW)
        token = store.create_session(user["id"], ttl_days=-1)
        assert store.user_for_token(token) is None
        assert store.purge_expired_sessions() == 1

    def test_change_password_keeps_current_session_only(self, store):
        user = store.create_user("ana", PW)
        here, elsewhere = store.create_session(user["id"]), store.create_session(user["id"])
        assert _err(store.change_password, user["id"], "wrong-pass", "new-password") == "wrong_password"
        store.change_password(user["id"], PW, "new-password", keep_token=here)
        assert store.user_for_token(here) is not None
        assert store.user_for_token(elsewhere) is None
        assert store.authenticate("ana", "new-password")

    def test_admin_password_reset_revokes_all_sessions(self, store):
        user = store.create_user("ana", PW)
        token = store.create_session(user["id"])
        store.set_password("ana", "brand-new-pass")
        assert store.user_for_token(token) is None
        assert store.authenticate("ana", "brand-new-pass")
        assert _err(store.set_password, "ghost", "whatever-123") == "unknown_user"


# ── Analyses ──────────────────────────────────────────────────────────────────

class TestAnalyses:
    def test_save_and_get_roundtrip(self, store):
        store.save_analysis("a1", PROFILE, subject="alice", source="pgn", depth=10, n_games=3)
        rec = store.get_analysis("a1")
        assert rec["subject"] == "alice"
        assert rec["profile"] == PROFILE
        assert rec["diagnosis"] is None
        assert rec["n_weaknesses"] == 1
        assert rec["overall_error_rate"] == pytest.approx(0.2)
        assert not rec["has_diagnosis"]

    def test_get_unknown_returns_none(self, store):
        assert store.get_analysis("nope") is None

    def test_save_diagnosis_attaches_and_keeps_on_profile_update(self, store):
        store.save_analysis("a1", PROFILE, subject="alice")
        assert store.save_diagnosis("a1", {"en": {"confidence": "HIGH"}})
        store.save_analysis("a1", {**PROFILE, "total_games": 4}, subject="alice")
        rec = store.get_analysis("a1")
        assert rec["diagnosis"] == {"en": {"confidence": "HIGH"}}
        assert rec["has_diagnosis"]
        assert rec["profile"]["total_games"] == 4

    def test_save_diagnosis_unknown_returns_false(self, store):
        assert store.save_diagnosis("ghost", {}) is False

    def test_list_most_recent_first(self, store):
        store.save_analysis("old", PROFILE, subject="x", created_at="2026-01-01 10:00:00")
        store.save_analysis("new", PROFILE, subject="x", created_at="2026-06-01 10:00:00")
        store.save_analysis("now", PROFILE, subject="x")
        assert [a["name"] for a in store.list_analyses()] == ["now", "new", "old"]

    def test_delete(self, store):
        store.save_analysis("a1", PROFILE, subject="alice")
        assert store.delete_analysis("a1")
        assert store.get_analysis("a1") is None


class TestOwnership:
    @pytest.fixture
    def two_users(self, store):
        ana, bia = store.create_user("ana", PW), store.create_user("bia", PW)
        store.save_analysis("ana_1", PROFILE, subject="x", owner_id=ana["id"])
        store.save_analysis("bia_1", PROFILE, subject="y", owner_id=bia["id"])
        return ana, bia

    def test_list_is_scoped_to_owner(self, store, two_users):
        ana, bia = two_users
        assert [a["name"] for a in store.list_analyses(owner_id=ana["id"])] == ["ana_1"]
        assert [a["name"] for a in store.list_analyses(owner_id=bia["id"])] == ["bia_1"]
        assert len(store.list_analyses()) == 2  # no filter: CLI / admin tools

    def test_cannot_read_or_delete_someone_elses_analysis(self, store, two_users):
        ana, bia = two_users
        assert store.get_analysis("bia_1", owner_id=ana["id"]) is None
        assert store.delete_analysis("bia_1", owner_id=ana["id"]) is False
        assert store.get_analysis("bia_1", owner_id=bia["id"]) is not None

    def test_upsert_never_steals_ownership(self, store, two_users):
        ana, bia = two_users
        store.save_analysis("ana_1", PROFILE, subject="x", owner_id=bia["id"])
        assert store.get_analysis("ana_1")["owner_id"] == ana["id"]

    def test_claim_orphans(self, store, two_users):
        ana, _ = two_users
        store.save_analysis("legacy", PROFILE, subject="z")  # no owner (pre-login / CLI)
        assert store.claim_orphan_analyses(ana["id"]) == 1
        assert {a["name"] for a in store.list_analyses(owner_id=ana["id"])} == {"ana_1", "legacy"}
        assert store.claim_orphan_analyses(ana["id"]) == 0

    def test_delete_user_removes_their_data_only(self, store, two_users):
        ana, bia = two_users
        token = store.create_session(ana["id"])
        store.delete_user(ana["id"])
        assert store.get_user(ana["id"]) is None
        assert store.user_for_token(token) is None
        assert store.get_analysis("ana_1") is None
        assert store.get_analysis("bia_1") is not None


class TestExplanations:
    def test_roundtrip_is_keyed_by_language(self, store):
        store.save_explanation("fen", "e2e4", "weak_square", "pt", "texto")
        assert store.get_explanation("fen", "e2e4", "weak_square", "pt") == "texto"
        assert store.get_explanation("fen", "e2e4", "weak_square", "en") is None

    def test_missing_move_is_supported_and_upserts(self, store):
        store.save_explanation("fen", None, "weak_square", "en", "text")
        store.save_explanation("fen", None, "weak_square", "en", "text v2")
        assert store.get_explanation("fen", None, "weak_square", "en") == "text v2"


# ── Backend selection / migration ─────────────────────────────────────────────

class TestBackend:
    def test_rejects_unknown_url_scheme(self):
        with pytest.raises(ValueError):
            AppStore(url="mysql://x")

    def test_sqlite_url(self, tmp_path):
        with AppStore(url=f"sqlite:///{tmp_path / 'u.db'}") as s:
            assert not s.is_pg
            s.create_user("ana", PW)
        assert (tmp_path / "u.db").exists()

    def test_pre_login_sqlite_database_gets_owner_column(self, tmp_path):
        """A data/profiler.db created before accounts existed keeps its analyses."""
        path = tmp_path / "old.db"
        conn = sqlite3.connect(path)
        conn.executescript("""
            CREATE TABLE analyses (
                name TEXT PRIMARY KEY, subject TEXT NOT NULL, source TEXT, n_games INTEGER,
                depth INTEGER, total_games INTEGER, total_positions INTEGER,
                overall_error_rate REAL, n_weaknesses INTEGER, profile_json TEXT NOT NULL,
                diagnosis_json TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')),
                diagnosed_at TEXT);
            INSERT INTO analyses (name, subject, profile_json) VALUES ('old_run', 'bob', '{}');
        """)
        conn.close()
        with AppStore(path=path) as s:
            assert s.get_analysis("old_run")["owner_id"] is None
            admin = s.create_user("ana", PW)
            assert s.claim_orphan_analyses(admin["id"]) == 1
            assert [a["name"] for a in s.list_analyses(owner_id=admin["id"])] == ["old_run"]
