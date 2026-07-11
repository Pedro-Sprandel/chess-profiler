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

        # best_move differs from played move so played_best=False;
        # score drops from +100 to -80 → magnitude 180 > 50 AND the win
        # probability drops ~16 percentage points (> WINP_ERROR_THRESHOLD)
        with patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
            mock_popen.return_value = make_mock_engine(100, -80, best_move_uci="d2d4")
            result = validate_move(board, move)

        assert result["is_error"] is True
        assert result["error_magnitude"] > 50

    def test_small_winp_drop_in_winning_position_not_error(self):
        from modules.stockfish_validator import validate_move
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        # Dropping 100cp while still clearly better (+200 → +100) barely moves
        # the win probability — not an instructive error under ΔWinP.
        with patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
            mock_popen.return_value = make_mock_engine(200, 100, best_move_uci="d2d4")
            result = validate_move(board, move)

        assert result["is_error"] is False

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

        # Bypass cache so the engine path is always exercised
        with patch("modules.stockfish_validator._get_db", return_value=None), \
             patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci") as mock_popen:
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


class TestConfirmationPass:
    """Second-pass deep validation of screened errors in batch_validate."""

    @staticmethod
    def _info(score_cp, best_uci):
        info = {"score": MagicMock(), "pv": [chess.Move.from_uci(best_uci)]}
        info["score"].white.return_value.score.return_value = score_cp
        return info

    def test_confirm_pass_clears_horizon_false_positive(self):
        """Screening flags an error, but the deeper pass shows a small swing → cleared."""
        from modules.stockfish_validator import batch_validate
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        engine = MagicMock()
        engine.analyse.side_effect = [
            self._info(100, "d2d4"),    # screening: before (+100, best d2d4)
            self._info(-100, "d2d4"),   # screening: after (-100) → flagged as error
            [self._info(100, "d2d4"),   # confirm (multipv): best line
             self._info(80, "g1f3")],   # confirm (multipv): 2nd best
            self._info(70, "d2d4"),     # confirm: after (+70) → magnitude 30 < 50
        ]

        with patch("modules.stockfish_validator._get_db", return_value=None), \
             patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci",
                   return_value=engine):
            results = batch_validate([(board, move)], depth=10, confirm_depth=16)

        assert results[0]["is_error"] is False
        assert engine.analyse.call_count == 4

    def test_confirm_pass_keeps_real_error(self):
        """A real blunder survives the deeper pass."""
        from modules.stockfish_validator import batch_validate
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        engine = MagicMock()
        engine.analyse.side_effect = [
            self._info(100, "d2d4"),     # screening: before
            self._info(-200, "d2d4"),    # screening: after → error
            [self._info(100, "d2d4"),    # confirm: best
             self._info(-150, "g1f3")],  # confirm: distant 2nd best
            self._info(-180, "d2d4"),    # confirm: after → still a big drop
        ]

        with patch("modules.stockfish_validator._get_db", return_value=None), \
             patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci",
                   return_value=engine):
            results = batch_validate([(board, move)], depth=10, confirm_depth=16)

        assert results[0]["is_error"] is True

    def test_second_best_with_small_gap_not_an_error(self):
        """Played move was the engine's close 2nd choice → hard position, not error."""
        from modules.stockfish_validator import batch_validate
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        engine = MagicMock()
        engine.analyse.side_effect = [
            self._info(100, "d2d4"),    # screening: before
            self._info(-100, "d2d4"),   # screening: after → flagged
            [self._info(100, "d2d4"),   # confirm: best
             self._info(70, "e2e4")],   # confirm: played move is 2nd best, gap 30 ≤ 50
            self._info(-100, "d2d4"),   # confirm: after (would still classify as error)
        ]

        with patch("modules.stockfish_validator._get_db", return_value=None), \
             patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci",
                   return_value=engine):
            results = batch_validate([(board, move)], depth=10, confirm_depth=16)

        assert results[0]["is_error"] is False

    def test_no_confirm_pass_when_depths_equal(self):
        from modules.stockfish_validator import batch_validate
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        engine = MagicMock()
        engine.analyse.side_effect = [
            self._info(100, "d2d4"),
            self._info(-100, "d2d4"),
        ]

        with patch("modules.stockfish_validator._get_db", return_value=None), \
             patch("modules.stockfish_validator.chess.engine.SimpleEngine.popen_uci",
                   return_value=engine):
            results = batch_validate([(board, move)], depth=10, confirm_depth=10)

        assert results[0]["is_error"] is True
        assert engine.analyse.call_count == 2


class TestErrorGuards:
    """Guards in _classify that suppress non-instructive 'errors'."""

    def test_winning_capture_detected(self):
        from modules.stockfish_validator import _is_winning_capture
        # Pawn takes bishop (1 -> 3): clearly winning capture.
        b = chess.Board("rnbk2nr/pp4pp/2p2p2/4p3/4P3/2P1b3/PP3PPP/R3KBNR w KQ - 0 12")
        assert _is_winning_capture(b, chess.Move.from_uci("f2e3")) is True

    def test_equal_capture_not_winning(self):
        from modules.stockfish_validator import _is_winning_capture
        # Knight takes knight (equal) is not a "winning" capture.
        b = chess.Board("rnbqkb1r/pppppppp/5n2/8/4N3/8/PPPPPPPP/R1BQKBNR w KQkq - 0 1")
        assert _is_winning_capture(b, chess.Move.from_uci("e4f6")) is False

    def test_non_capture_not_winning(self):
        from modules.stockfish_validator import _is_winning_capture
        b = chess.Board()
        assert _is_winning_capture(b, chess.Move.from_uci("e2e4")) is False

    def test_winning_capture_suppresses_error(self):
        from modules.stockfish_validator import _classify
        b = chess.Board("rnbk2nr/pp4pp/2p2p2/4p3/4P3/2P1b3/PP3PPP/R3KBNR w KQ - 0 12")
        # white to move; eval drops 100cp but the move recovers a piece -> not an error
        r = _classify(b, chess.Move.from_uci("f2e3"), 100, 0, chess.Move.from_uci("f1c4"))
        assert r["is_error"] is False

    def test_already_decided_suppresses_error(self):
        from modules.stockfish_validator import _classify
        b = chess.Board()  # white to move, non-capture move
        # White already losing badly before AND after: the cp swing barely moves
        # the win probability (ΔWinP ≈ 0.03 < threshold) -> noise, not an error
        r = _classify(b, chess.Move.from_uci("e2e4"), -700, -820, chess.Move.from_uci("d2d4"))
        assert r["is_error"] is False

    def test_normal_error_still_flagged(self):
        from modules.stockfish_validator import _classify
        b = chess.Board()  # white to move, non-capture, position not decided
        r = _classify(b, chess.Move.from_uci("e2e4"), 50, -120, chess.Move.from_uci("d2d4"))
        assert r["is_error"] is True
        assert r["error_magnitude"] == 170

    def test_best_move_never_error(self):
        from modules.stockfish_validator import _classify
        b = chess.Board()
        # Even a big swing: if the played move IS the best move, it's not an error.
        r = _classify(b, chess.Move.from_uci("e2e4"), 500, -500, chess.Move.from_uci("e2e4"))
        assert r["is_error"] is False
