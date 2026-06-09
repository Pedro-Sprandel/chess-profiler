"""Tests for the CLI entry point (_main) in main.py."""
import chess
import pytest
from unittest.mock import patch, MagicMock


MOCK_DIAGNOSIS = {
    "en": {
        "root_cause": {"id": "test", "name": "Test", "description": "Test"},
        "weakness_classification": [],
        "study_priority": [],
        "cognitive_pattern": "test",
        "confidence": "LOW",
    },
    "pt": {
        "root_cause": {"id": "test", "name": "Teste", "description": "Teste"},
        "weakness_classification": [],
        "study_priority": [],
        "cognitive_pattern": "teste",
        "confidence": "LOW",
    },
}

MOCK_PROFILE = {
    "total_games": 1,
    "total_positions_analyzed": 5,
    "total_errors_detected": 1,
    "overall_error_rate": 0.2,
    "weaknesses": [],
}


class TestMainPgnMode:
    def test_pgn_flag_calls_analyze_player(self, tmp_path):
        pgn = tmp_path / "game.pgn"
        pgn.write_text("[Event \"?\"]\n1. e4 *\n")
        with patch("main.analyze_player", return_value=(MOCK_PROFILE, MOCK_DIAGNOSIS)) as mock_ap, \
             patch("main.analyze_player_from_username") as mock_un:
            from main import _main
            _main(["--user", "alice", "--pgn", str(pgn)])
        mock_ap.assert_called_once()
        mock_un.assert_not_called()

    def test_pgn_passes_player_name(self, tmp_path):
        pgn = tmp_path / "game.pgn"
        pgn.write_text("[Event \"?\"]\n1. e4 *\n")
        with patch("main.analyze_player", return_value=(MOCK_PROFILE, MOCK_DIAGNOSIS)) as mock_ap:
            from main import _main
            _main(["--user", "alice", "--pgn", str(pgn)])
        call_kwargs = mock_ap.call_args
        assert call_kwargs.kwargs.get("player_name") == "alice" or \
               call_kwargs.args[1] == "alice"

    def test_pgn_default_color_is_white(self, tmp_path):
        pgn = tmp_path / "game.pgn"
        pgn.write_text("[Event \"?\"]\n1. e4 *\n")
        with patch("main.analyze_player", return_value=(MOCK_PROFILE, MOCK_DIAGNOSIS)) as mock_ap:
            from main import _main
            _main(["--user", "alice", "--pgn", str(pgn)])
        ca = mock_ap.call_args
        color = ca.kwargs.get("player_color", ca.args[2] if len(ca.args) > 2 else chess.WHITE)
        assert color == chess.WHITE

    def test_pgn_color_black_passes_black(self, tmp_path):
        pgn = tmp_path / "game.pgn"
        pgn.write_text("[Event \"?\"]\n1. e4 *\n")
        with patch("main.analyze_player", return_value=(MOCK_PROFILE, MOCK_DIAGNOSIS)) as mock_ap:
            from main import _main
            _main(["--user", "alice", "--pgn", str(pgn), "--color", "black"])
        ca = mock_ap.call_args
        color = ca.kwargs.get("player_color", ca.args[2] if len(ca.args) > 2 else None)
        assert color == chess.BLACK

    def test_pgn_color_white_passes_white(self, tmp_path):
        pgn = tmp_path / "game.pgn"
        pgn.write_text("[Event \"?\"]\n1. e4 *\n")
        with patch("main.analyze_player", return_value=(MOCK_PROFILE, MOCK_DIAGNOSIS)) as mock_ap:
            from main import _main
            _main(["--user", "alice", "--pgn", str(pgn), "--color", "white"])
        ca = mock_ap.call_args
        color = ca.kwargs.get("player_color", ca.args[2] if len(ca.args) > 2 else None)
        assert color == chess.WHITE


class TestMainUsernameMode:
    def test_no_pgn_calls_analyze_player_from_username(self):
        with patch("main.analyze_player_from_username", return_value=(MOCK_PROFILE, MOCK_DIAGNOSIS)) as mock_un, \
             patch("main.analyze_player") as mock_ap:
            from main import _main
            _main(["--user", "bob"])
        mock_un.assert_called_once()
        mock_ap.assert_not_called()

    def test_username_is_passed_correctly(self):
        with patch("main.analyze_player_from_username", return_value=(MOCK_PROFILE, MOCK_DIAGNOSIS)) as mock_un:
            from main import _main
            _main(["--user", "sprandel"])
        call_kwargs = mock_un.call_args
        username = call_kwargs.kwargs.get("username") or call_kwargs.args[0]
        assert username == "sprandel"

    def test_default_games_is_50(self):
        with patch("main.analyze_player_from_username", return_value=(MOCK_PROFILE, MOCK_DIAGNOSIS)) as mock_un:
            from main import _main
            _main(["--user", "bob"])
        call_kwargs = mock_un.call_args
        n_games = call_kwargs.kwargs.get("n_games") or call_kwargs.args[1]
        assert n_games == 50

    def test_custom_games_count(self):
        with patch("main.analyze_player_from_username", return_value=(MOCK_PROFILE, MOCK_DIAGNOSIS)) as mock_un:
            from main import _main
            _main(["--user", "bob", "--games", "30"])
        call_kwargs = mock_un.call_args
        n_games = call_kwargs.kwargs.get("n_games") or call_kwargs.args[1]
        assert n_games == 30

    def test_invalid_games_raises_system_exit(self):
        with pytest.raises(SystemExit):
            from main import _main
            _main(["--user", "bob", "--games", "notanumber"])

    def test_missing_user_raises_system_exit(self):
        with pytest.raises(SystemExit):
            from main import _main
            _main([])
