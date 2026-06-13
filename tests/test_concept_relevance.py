"""Tests for concept_relevance instructive position filtering."""
import chess
import pytest
from modules.concept_relevance import is_instructive, is_missed_tactic, _concept_score


# ── _concept_score ────────────────────────────────────────────────────────────

def test_weak_square_score_fewer_is_better():
    assert _concept_score({"weak_square": {"count": 2}}, "weak_square") == -2
    assert _concept_score({"weak_square": {"count": 0}}, "weak_square") == 0
    assert _concept_score({"weak_square": {"count": 2}}, "weak_square") < \
           _concept_score({"weak_square": {"count": 1}}, "weak_square")


def test_isolated_pawn_score_fewer_is_better():
    assert _concept_score({"isolated_pawn": {"count": 3}}, "isolated_pawn") == -3
    assert _concept_score({"isolated_pawn": {"count": 1}}, "isolated_pawn") > \
           _concept_score({"isolated_pawn": {"count": 3}}, "isolated_pawn")


def test_bishop_pair_score():
    assert _concept_score({"bishop_pair": {"detected": True}}, "bishop_pair") == 1
    assert _concept_score({"bishop_pair": {"detected": False}}, "bishop_pair") == 0


def test_knight_outpost_score():
    assert _concept_score({"knight_outpost": {"squares": ["e5", "d6"]}}, "knight_outpost") == 2
    assert _concept_score({"knight_outpost": {"squares": []}}, "knight_outpost") == 0


def test_king_safety_score_exposed_penalized():
    safe = _concept_score({"king_safety": {"shield_pawns": 3, "exposed": False}}, "king_safety")
    exposed = _concept_score({"king_safety": {"shield_pawns": 3, "exposed": True}}, "king_safety")
    assert safe > exposed


def test_space_advantage_score():
    assert _concept_score({"space_advantage": {"advantage": 10}}, "space_advantage") == 10
    assert _concept_score({"space_advantage": {"advantage": -5}}, "space_advantage") == -5


# ── is_instructive ────────────────────────────────────────────────────────────

def test_same_move_is_never_instructive():
    board = chess.Board()
    assert is_instructive(board, "e2e4", "e2e4", "weak_square", chess.WHITE) is False


def test_missing_best_move_keeps_position():
    board = chess.Board()
    assert is_instructive(board, "e2e4", None, "weak_square", chess.WHITE) is True


def test_missing_move_played_keeps_position():
    board = chess.Board()
    assert is_instructive(board, None, "e2e4", "weak_square", chess.WHITE) is True


def test_invalid_uci_does_not_crash():
    board = chess.Board()
    # Should not raise, should return True (keep on error)
    result = is_instructive(board, "invalid", "e2e4", "weak_square", chess.WHITE)
    assert isinstance(result, bool)


# ── is_missed_tactic ──────────────────────────────────────────────────────────

# Real position the profiler misclassified as weak_square: white to move, the black
# bishop on f3 is hanging and the best move (Nxf3, g5f3) grabs it for free.
_HANGING_BISHOP_FEN = "r3k3/pp2r1pp/2pR4/2n1p1N1/2P1P3/nP3b2/P6P/2K3R1 w - - 5 25"


def test_declined_free_capture_is_missed_tactic():
    board = chess.Board(_HANGING_BISHOP_FEN)
    assert is_missed_tactic(board, "g1e1", "g5f3", chess.WHITE) is True


def test_playing_the_capture_is_not_a_miss():
    board = chess.Board(_HANGING_BISHOP_FEN)
    assert is_missed_tactic(board, "g5f3", "g5f3", chess.WHITE) is False


def test_best_move_not_a_capture_is_not_a_miss():
    board = chess.Board(_HANGING_BISHOP_FEN)
    assert is_missed_tactic(board, "d6d7", "g1e1", chess.WHITE) is False


def test_missing_best_move_is_not_a_miss():
    board = chess.Board()
    assert is_missed_tactic(board, "e2e4", None, chess.WHITE) is False


def test_equal_trade_of_defended_piece_is_not_a_miss():
    # Knight takes a defended knight (equal value, defended) — not a winning tactic.
    board = chess.Board("4k3/8/3n4/8/4N3/8/3K4/8 w - - 0 1")
    # Nxd6 is a capture but d6 knight... set up a defended equal capture instead:
    board = chess.Board("4k3/2p5/3n4/8/4N3/8/3K4/8 w - - 0 1")  # d6 knight defended by c7 pawn
    assert is_missed_tactic(board, "d2d3", "e4d6", chess.WHITE) is False


def test_invalid_uci_does_not_crash_missed_tactic():
    board = chess.Board()
    assert is_missed_tactic(board, "invalid", "e2e4", chess.WHITE) is False
