import chess
import pytest
from unittest.mock import MagicMock, patch, call


def make_mock_engine(score_before_cp: int, score_after_cp: int, best_move_uci: str = "e2e4"):
    """Helper to build a mock Stockfish engine with preset scores."""
    engine = MagicMock()

    best_move = chess.Move.from_uci(best_move_uci)

    info_before = {
        "score": MagicMock(),
        "pv": [best_move],
    }
    info_before["score"].white.return_value.score.return_value = score_before_cp

    info_after = {
        "score": MagicMock(),
        "pv": [best_move],
    }
    info_after["score"].white.return_value.score.return_value = score_after_cp

    engine.analyse.side_effect = [info_before, info_after]
    return engine


# --- validate_move ---

class TestValidateMove:
    def test_returns_required_keys(self):
        from modules.stockfish_validator import validate_move
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        with patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
            mock_popen.return_value = make_mock_engine(50, 30)
            result = validate_move(board, move)

        assert "is_error" in result
        assert "eval_before" in result
        assert "eval_after" in result
        assert "error_magnitude" in result
        assert "best_move" in result

    def test_is_error_true_when_magnitude_exceeds_threshold(self):
        from modules.stockfish_validator import validate_move
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        # score drops 100cp for white → magnitude = 100 > 50 threshold
        with patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
            mock_popen.return_value = make_mock_engine(200, 100)
            result = validate_move(board, move)

        assert result["is_error"] is True
        assert result["error_magnitude"] > 50

    def test_is_error_false_when_magnitude_within_threshold(self):
        from modules.stockfish_validator import validate_move
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        # score drops only 20cp → not an error
        with patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
            mock_popen.return_value = make_mock_engine(100, 80)
            result = validate_move(board, move)

        assert result["is_error"] is False

    def test_engine_quit_called_on_success(self):
        from modules.stockfish_validator import validate_move
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        with patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
            mock_engine = make_mock_engine(100, 80)
            mock_popen.return_value = mock_engine
            validate_move(board, move)

        mock_engine.quit.assert_called_once()

    def test_engine_quit_called_on_exception(self):
        from modules.stockfish_validator import validate_move
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        with patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
            mock_engine = MagicMock()
            mock_engine.analyse.side_effect = RuntimeError("engine crash")
            mock_popen.return_value = mock_engine

            with pytest.raises(RuntimeError):
                validate_move(board, move)

        mock_engine.quit.assert_called_once()

    def test_best_move_returned_as_uci(self):
        from modules.stockfish_validator import validate_move
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        with patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
            mock_popen.return_value = make_mock_engine(100, 80, best_move_uci="e2e4")
            result = validate_move(board, move)

        assert result["best_move"] == "e2e4"

    def test_eval_before_and_after_are_ints(self):
        from modules.stockfish_validator import validate_move
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        with patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
            mock_popen.return_value = make_mock_engine(100, 80)
            result = validate_move(board, move)

        assert isinstance(result["eval_before"], int)
        assert isinstance(result["eval_after"], int)


# --- batch_validate ---

class TestBatchValidate:
    def _make_batch_engine(self, pairs):
        """Build mock engine for batch: pairs is list of (score_before, score_after)."""
        engine = MagicMock()
        side_effects = []
        best_move = chess.Move.from_uci("e2e4")
        for score_before, score_after in pairs:
            info_b = {"score": MagicMock(), "pv": [best_move]}
            info_b["score"].white.return_value.score.return_value = score_before
            info_a = {"score": MagicMock(), "pv": [best_move]}
            info_a["score"].white.return_value.score.return_value = score_after
            side_effects.extend([info_b, info_a])
        engine.analyse.side_effect = side_effects
        return engine

    def test_returns_list_same_length_as_input(self):
        from modules.stockfish_validator import batch_validate
        board = chess.Board()
        positions = [(board.copy(), chess.Move.from_uci("e2e4"))] * 3

        with patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
            mock_popen.return_value = self._make_batch_engine([(100, 80)] * 3)
            results = batch_validate(positions)

        assert len(results) == 3

    def test_engine_quit_called_exactly_once(self):
        from modules.stockfish_validator import batch_validate
        board = chess.Board()
        positions = [(board.copy(), chess.Move.from_uci("e2e4"))] * 3

        with patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
            mock_engine = self._make_batch_engine([(100, 80)] * 3)
            mock_popen.return_value = mock_engine
            batch_validate(positions)

        mock_engine.quit.assert_called_once()

    def test_empty_input_returns_empty_list(self):
        from modules.stockfish_validator import batch_validate

        with patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
            mock_engine = MagicMock()
            mock_engine.analyse.side_effect = []
            mock_popen.return_value = mock_engine
            results = batch_validate([])

        assert results == []

    def test_each_result_has_required_keys(self):
        from modules.stockfish_validator import batch_validate
        board = chess.Board()
        positions = [(board.copy(), chess.Move.from_uci("e2e4"))]

        with patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
            mock_popen.return_value = self._make_batch_engine([(100, 80)])
            results = batch_validate(positions)

        assert "is_error" in results[0]
        assert "error_magnitude" in results[0]
