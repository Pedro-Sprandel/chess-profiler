"""Shared fixtures: every test talks to throwaway storage, never data/profiler.db.

- modules/db.py (Stockfish cache, positions) → a per-test SQLite file.
- modules/app_store.py (accounts, sessions, analyses) → the same per-test SQLite
  file, or a real PostgreSQL database when TEST_DATABASE_URL is set, e.g.:

      TEST_DATABASE_URL=postgresql://localhost/chess_test pytest

  In that mode the AppStore tables are dropped before every test.
"""
import os

import pytest

import config
import modules.app_store
import modules.db
import modules.stockfish_validator

_APP_TABLES = ("sessions", "analyses", "explanations", "legacy_imports", "users")


def _reset_postgres(url: str):
    import psycopg

    with psycopg.connect(url, autocommit=True) as conn:
        for table in _APP_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    modules.app_store.reset_schema_cache()


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(modules.db, "DEFAULT_DB_PATH", tmp_path / "profiler_test.db")
    # The validator memoizes a Database for the eval cache; drop it so it reopens
    # against this test's file.
    monkeypatch.setattr(modules.stockfish_validator, "_db", None)

    # Accounts: fast hashing in tests, open sign-up, no invite code.
    monkeypatch.setattr(modules.app_store, "PBKDF2_ITERATIONS", 1_000)
    monkeypatch.setattr(config, "ALLOW_SIGNUP", True)
    monkeypatch.setattr(config, "SIGNUP_CODE", None)

    pg_url = os.getenv("TEST_DATABASE_URL")
    monkeypatch.setattr(config, "DATABASE_URL", pg_url or None)
    if pg_url:
        _reset_postgres(pg_url)

    # Never import real output/*.json files from the working copy.
    import ui.store
    monkeypatch.setattr(ui.store, "OUTPUT_DIR", str(tmp_path / "output"))

    yield tmp_path / "profiler_test.db"


@pytest.fixture
def store():
    with modules.app_store.AppStore() as s:
        yield s
