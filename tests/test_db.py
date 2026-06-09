"""Unit tests for the SQLite persistence layer (modules/db.py)."""
import pytest
from modules.db import Database


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


class TestFenCache:
    def test_get_returns_none_when_uncached(self, db):
        assert db.get_cached_eval("fen-unknown", 10) is None

    def test_cache_roundtrip(self, db):
        db.cache_eval("8/8/8/8/8/8/8/8 w - - 0 1", 10, 55, "e2e4")
        cached = db.get_cached_eval("8/8/8/8/8/8/8/8 w - - 0 1", 10)
        assert cached == {"score_cp": 55, "best_move": "e2e4"}

    def test_cache_is_depth_specific(self, db):
        db.cache_eval("fen-x", 10, 10, "a1a2")
        assert db.get_cached_eval("fen-x", 12) is None

    def test_cache_upsert_overwrites(self, db):
        db.cache_eval("fen-y", 10, 10, "a1a2")
        db.cache_eval("fen-y", 10, 99, "b1b2")
        assert db.get_cached_eval("fen-y", 10) == {"score_cp": 99, "best_move": "b1b2"}

    def test_cache_stats_counts_entries(self, db):
        assert db.cache_stats()["cached_evals"] == 0
        db.cache_eval("a", 10, 1, None)
        db.cache_eval("b", 10, 2, None)
        assert db.cache_stats()["cached_evals"] == 2


class TestPositions:
    def _sample(self, **overrides):
        pos = {
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "move_played": "e2e4",
            "player_color": "white",
            "white": "alice", "black": "bob",
            "white_rating": 1500, "black_rating": 1400,
            "eco": "B20", "source": "chess_com",
        }
        pos.update(overrides)
        return pos

    def test_insert_returns_id_and_increments_count(self, db):
        assert db.count_positions() == 0
        pid = db.insert_position(self._sample())
        assert isinstance(pid, int)
        assert db.count_positions() == 1

    def test_query_filter_by_source(self, db):
        db.insert_position(self._sample(source="pgn"))
        db.insert_position(self._sample(source="chess_com"))
        rows = db.query_positions(source="pgn")
        assert len(rows) == 1
        assert rows[0]["source"] == "pgn"

    def test_query_filter_by_eco_prefix(self, db):
        db.insert_position(self._sample(eco="B20"))
        db.insert_position(self._sample(eco="C50"))
        rows = db.query_positions(eco="B")
        assert len(rows) == 1
        assert rows[0]["eco"] == "B20"

    def test_query_rating_filter_targets_opponent(self, db):
        # player is white -> rating filter applies to black_rating
        db.insert_position(self._sample(player_color="white", black_rating=900))
        db.insert_position(self._sample(player_color="white", black_rating=1800))
        rows = db.query_positions(min_rating=1500)
        assert len(rows) == 1
        assert rows[0]["black_rating"] == 1800


class TestAnalysisResults:
    def _insert_position(self, db):
        return db.insert_position({"fen": "x", "source": "pgn"})

    def test_bulk_insert_and_get(self, db):
        pid = self._insert_position(db)
        db.insert_analysis_results_bulk([
            (pid, "weak_square", True, {"squares": ["e5"]}, True, 120.0),
            (pid, "open_file", True, {"files": ["d"]}, False, 0.0),
        ])
        rows = db.get_analysis_results(pid)
        assert len(rows) == 2
        by_key = {r["concept_key"]: r for r in rows}
        assert by_key["weak_square"]["details"] == {"squares": ["e5"]}
        assert by_key["weak_square"]["is_error"] == 1

    def test_concept_error_summary_aggregates(self, db):
        pid = self._insert_position(db)
        db.insert_analysis_results_bulk([
            (pid, "weak_square", True, {}, True, 100.0),
            (pid, "weak_square", True, {}, True, 200.0),
            (pid, "weak_square", True, {}, False, 0.0),
        ])
        summary = db.concept_error_summary()
        ws = next(r for r in summary if r["concept_key"] == "weak_square")
        assert ws["total_occurrences"] == 3
        assert ws["error_occurrences"] == 2
        assert ws["avg_error_magnitude"] == 150.0


class TestContextManager:
    def test_usable_as_context_manager(self, tmp_path):
        with Database(tmp_path / "ctx.db") as database:
            database.cache_eval("fen", 10, 5, None)
            assert database.cache_stats()["cached_evals"] == 1
