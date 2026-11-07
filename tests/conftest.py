"""Shared fixtures: every test talks to a throwaway SQLite file, never data/profiler.db."""
import pytest

import modules.db
import modules.stockfish_validator


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(modules.db, "DEFAULT_DB_PATH", tmp_path / "profiler_test.db")
    # The validator memoizes a Database for the eval cache; drop it so it reopens
    # against this test's file.
    monkeypatch.setattr(modules.stockfish_validator, "_db", None)
    yield tmp_path / "profiler_test.db"
