import chess
import os
import tempfile
import pytest

MINIMAL_PGN = """[Event "Test"]
[Site "?"]
[Date "????.??.??"]
[Round "?"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""

TWO_GAMES_PGN = MINIMAL_PGN + "\n" + """[Event "Test2"]
[Site "?"]
[Date "????.??.??"]
[Round "?"]
[White "Player3"]
[Black "Player4"]
[Result "0-1"]

1. d4 d5 2. c4 e6 0-1
"""


class TestLoadGamesFromString:
    def test_single_game_returns_one_game(self):
        from modules.pgn_loader import load_games_from_string
        games = load_games_from_string(MINIMAL_PGN)
        assert len(games) == 1

    def test_two_games_returns_two_games(self):
        from modules.pgn_loader import load_games_from_string
        games = load_games_from_string(TWO_GAMES_PGN)
        assert len(games) == 2

    def test_empty_string_returns_empty_list(self):
        from modules.pgn_loader import load_games_from_string
        games = load_games_from_string("")
        assert games == []

    def test_returns_list_of_game_objects(self):
        from modules.pgn_loader import load_games_from_string
        import chess.pgn
        games = load_games_from_string(MINIMAL_PGN)
        assert isinstance(games[0], chess.pgn.Game)


class TestLoadGamesFromFile:
    def test_loads_games_from_file(self):
        from modules.pgn_loader import load_games_from_file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False, encoding="utf-8") as f:
            f.write(MINIMAL_PGN)
            tmp_path = f.name
        try:
            games = load_games_from_file(tmp_path)
            assert len(games) == 1
        finally:
            os.unlink(tmp_path)

    def test_loads_multiple_games_from_file(self):
        from modules.pgn_loader import load_games_from_file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False, encoding="utf-8") as f:
            f.write(TWO_GAMES_PGN)
            tmp_path = f.name
        try:
            games = load_games_from_file(tmp_path)
            assert len(games) == 2
        finally:
            os.unlink(tmp_path)


class TestIteratePositions:
    def test_yields_tuples_of_three(self):
        from modules.pgn_loader import load_games_from_string, iterate_positions
        games = load_games_from_string(MINIMAL_PGN)
        positions = list(iterate_positions(games[0], chess.WHITE))
        assert len(positions) > 0
        for item in positions:
            assert len(item) == 3

    def test_board_before_is_chess_board(self):
        from modules.pgn_loader import load_games_from_string, iterate_positions
        games = load_games_from_string(MINIMAL_PGN)
        positions = list(iterate_positions(games[0], chess.WHITE))
        board_before, move, board_after = positions[0]
        assert isinstance(board_before, chess.Board)
        assert isinstance(board_after, chess.Board)
        assert isinstance(move, chess.Move)

    def test_only_yields_positions_for_white(self):
        from modules.pgn_loader import load_games_from_string, iterate_positions
        games = load_games_from_string(MINIMAL_PGN)
        positions = list(iterate_positions(games[0], chess.WHITE))
        for board_before, move, board_after in positions:
            assert board_before.turn == chess.WHITE

    def test_only_yields_positions_for_black(self):
        from modules.pgn_loader import load_games_from_string, iterate_positions
        games = load_games_from_string(MINIMAL_PGN)
        positions = list(iterate_positions(games[0], chess.BLACK))
        for board_before, move, board_after in positions:
            assert board_before.turn == chess.BLACK

    def test_board_after_has_move_applied(self):
        from modules.pgn_loader import load_games_from_string, iterate_positions
        games = load_games_from_string(MINIMAL_PGN)
        positions = list(iterate_positions(games[0], chess.WHITE))
        board_before, move, board_after = positions[0]
        expected = board_before.copy()
        expected.push(move)
        assert board_after.fen() == expected.fen()
