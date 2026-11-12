import chess
import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Longo o suficiente para sobrar posições após o skip de abertura
# (OPENING_MOVES_TO_SKIP=6): lances 7-9 das brancas são analisados.
MINIMAL_PGN = """[Event "Test"]
[Site "?"]
[Date "????.??.??"]
[Round "?"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7
6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 1-0
"""

MOCK_VALIDATION = {
    "is_error": False,
    "eval_before": 20,
    "eval_after": 20,
    "error_magnitude": 0,
    "best_move": "e2e4"
}

MOCK_DIAGNOSIS = {
    "root_cause": {"id": "test", "name": "Test", "description": "Test"},
    "weakness_classification": [],
    "study_priority": [],
    "cognitive_pattern": "test",
    "confidence": "LOW"
}


def make_mock_game():
    """Return a real chess.pgn.Game parsed from MINIMAL_PGN."""
    import chess.pgn
    import io
    return chess.pgn.read_game(io.StringIO(MINIMAL_PGN))


class TestAnalyzePlayer:
    def _run_analyze(self, tmp_pgn_path, player_name, output_dir):
        """Run analyze_player with all external deps mocked."""
        mock_game = make_mock_game()

        with patch("main.load_games_from_file", return_value=[mock_game]) as mock_load, \
             patch("main.batch_validate", return_value=[MOCK_VALIDATION] * 3) as mock_validate, \
             patch("main.diagnose", return_value=MOCK_DIAGNOSIS) as mock_diagnose, \
             patch("main.OUTPUT_DIR", output_dir):
            from main import analyze_player
            return analyze_player(tmp_pgn_path, player_name, chess.WHITE)

    def test_returns_profile_and_diagnosis_tuple(self, tmp_path):
        pgn = tmp_path / "test.pgn"
        pgn.write_text(MINIMAL_PGN)
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir, exist_ok=True)

        profile, diagnosis = self._run_analyze(str(pgn), "testplayer", output_dir)

        assert isinstance(profile, dict)
        assert isinstance(diagnosis, dict)

    def test_writes_profile_json_to_output(self, tmp_path):
        pgn = tmp_path / "test.pgn"
        pgn.write_text(MINIMAL_PGN)
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir, exist_ok=True)

        self._run_analyze(str(pgn), "testplayer", output_dir)

        profile_path = os.path.join(output_dir, "testplayer_profile.json")
        assert os.path.exists(profile_path)
        with open(profile_path) as f:
            data = json.load(f)
        assert "total_games" in data

    def test_writes_diagnosis_json_to_output(self, tmp_path):
        pgn = tmp_path / "test.pgn"
        pgn.write_text(MINIMAL_PGN)
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir, exist_ok=True)

        self._run_analyze(str(pgn), "testplayer", output_dir)

        diagnosis_path = os.path.join(output_dir, "testplayer_diagnosis.json")
        assert os.path.exists(diagnosis_path)
        with open(diagnosis_path) as f:
            data = json.load(f)
        assert "root_cause" in data

    def test_calls_load_games_from_file(self, tmp_path):
        pgn = tmp_path / "test.pgn"
        pgn.write_text(MINIMAL_PGN)
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir, exist_ok=True)

        mock_game = make_mock_game()
        with patch("main.load_games_from_file", return_value=[mock_game]) as mock_load, \
             patch("main.batch_validate", return_value=[MOCK_VALIDATION] * 3), \
             patch("main.diagnose", return_value=MOCK_DIAGNOSIS), \
             patch("main.OUTPUT_DIR", output_dir):
            from main import analyze_player
            analyze_player(str(pgn), "testplayer", chess.WHITE)

        mock_load.assert_called_once_with(str(pgn))

    def test_calls_batch_validate_once_per_game(self, tmp_path):
        pgn = tmp_path / "test.pgn"
        pgn.write_text(MINIMAL_PGN)
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir, exist_ok=True)

        # Force at least one concept detected per position so batch_validate is reached
        mock_concepts = {"weak_square": {"detected": True, "squares": ["e5"], "count": 1}}
        mock_game = make_mock_game()
        with patch("main.load_games_from_file", return_value=[mock_game, mock_game]), \
             patch("main.detect_concepts", return_value=mock_concepts), \
             patch("main.batch_validate", return_value=[MOCK_VALIDATION] * 3) as mock_validate, \
             patch("main.diagnose", return_value=MOCK_DIAGNOSIS), \
             patch("main.OUTPUT_DIR", output_dir):
            from main import analyze_player
            analyze_player(str(pgn), "testplayer", chess.WHITE)

        assert mock_validate.call_count == 2

    def test_calls_diagnose_once(self, tmp_path):
        pgn = tmp_path / "test.pgn"
        pgn.write_text(MINIMAL_PGN)
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir, exist_ok=True)

        mock_game = make_mock_game()
        with patch("main.load_games_from_file", return_value=[mock_game]), \
             patch("main.batch_validate", return_value=[MOCK_VALIDATION] * 3), \
             patch("main.diagnose", return_value=MOCK_DIAGNOSIS) as mock_diag, \
             patch("main.OUTPUT_DIR", output_dir):
            from main import analyze_player
            analyze_player(str(pgn), "testplayer", chess.WHITE)

        mock_diag.assert_called_once()


class TestAnalyzePlayerFromUsername:
    def _run(self, username, output_dir):
        mock_game = make_mock_game()
        with patch("main.fetch_recent_games",
                   return_value=[(mock_game, chess.WHITE)]) as mock_fetch, \
             patch("main.batch_validate", return_value=[MOCK_VALIDATION] * 3), \
             patch("main.diagnose", return_value=MOCK_DIAGNOSIS), \
             patch("main.OUTPUT_DIR", output_dir):
            from main import analyze_player_from_username
            return analyze_player_from_username(username, n_games=2)

    def test_returns_profile_and_diagnosis_tuple(self, tmp_path):
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir, exist_ok=True)
        profile, diagnosis = self._run("sprandel", output_dir)
        assert isinstance(profile, dict)
        assert isinstance(diagnosis, dict)

    def test_writes_profile_json_to_output(self, tmp_path):
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir, exist_ok=True)
        self._run("sprandel", output_dir)
        assert os.path.exists(os.path.join(output_dir, "sprandel_profile.json"))

    def test_writes_diagnosis_json_to_output(self, tmp_path):
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir, exist_ok=True)
        self._run("sprandel", output_dir)
        assert os.path.exists(os.path.join(output_dir, "sprandel_diagnosis.json"))

    def test_calls_fetch_recent_games_with_correct_args(self, tmp_path):
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir, exist_ok=True)
        mock_game = make_mock_game()
        with patch("main.fetch_recent_games",
                   return_value=[(mock_game, chess.WHITE)]) as mock_fetch, \
             patch("main.batch_validate", return_value=[MOCK_VALIDATION] * 3), \
             patch("main.diagnose", return_value=MOCK_DIAGNOSIS), \
             patch("main.OUTPUT_DIR", output_dir):
            from main import analyze_player_from_username
            analyze_player_from_username("sprandel", n_games=2)
        mock_fetch.assert_called_once_with("sprandel", n_games=2)


class TestDatabasePersistence:
    """The analysis (profile + diagnosis) is stored in SQLite — the UI's source of truth."""

    def _run_username(self, output_dir, **kwargs):
        mock_game = make_mock_game()
        with patch("main.fetch_recent_games", return_value=[(mock_game, chess.WHITE)]), \
             patch("main.batch_validate", return_value=[MOCK_VALIDATION] * 3), \
             patch("main.diagnose", return_value=MOCK_DIAGNOSIS), \
             patch("main.OUTPUT_DIR", output_dir):
            from main import analyze_profile_from_username, run_diagnosis
            analyze_profile_from_username("sprandel", n_games=2, profile_name="sprandel__d10_x",
                                          depth=10, **kwargs)
            run_diagnosis("sprandel__d10_x")

    def test_profile_and_diagnosis_saved_to_db(self, tmp_path):
        from modules.app_store import AppStore
        self._run_username(str(tmp_path))
        with AppStore() as store:
            rec = store.get_analysis("sprandel__d10_x")
        assert rec["subject"] == "sprandel"
        assert rec["source"] == "chess_com"
        assert rec["depth"] == 10
        assert rec["total_games"] == 1
        assert rec["diagnosis"] == MOCK_DIAGNOSIS

    def test_export_json_false_writes_no_files(self, tmp_path):
        self._run_username(str(tmp_path), export_json=False)
        assert not any(f.endswith(".json") for f in os.listdir(tmp_path))

    def test_owner_id_is_recorded(self, tmp_path):
        from modules.app_store import AppStore
        with AppStore() as store:
            owner = store.create_user("ana", "correct-horse")
        self._run_username(str(tmp_path), export_json=False, owner_id=owner["id"])
        with AppStore() as store:
            assert store.get_analysis("sprandel__d10_x", owner_id=owner["id"]) is not None
            assert store.get_analysis("sprandel__d10_x", owner_id=owner["id"] + 1) is None

    def test_unattributed_mistakes_go_to_classifier_and_stats_are_recorded(self, tmp_path):
        from modules.app_store import AppStore
        stats = {"candidates": 1, "cached": 0, "sent": 1, "accepted": 1, "skipped": 0}
        with patch("main.classify_unattributed", return_value=stats) as mock_cls:
            self._run_username(str(tmp_path), export_json=False)
        mock_cls.assert_called_once()
        with AppStore() as store:
            profile = store.get_analysis("sprandel__d10_x")["profile"]
        assert profile["metadata"]["llm_classification"] == stats
        assert set(profile["attribution_summary"]) == {"rule", "llm", "unattributed"}
