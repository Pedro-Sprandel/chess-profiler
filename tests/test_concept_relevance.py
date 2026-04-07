"""Tests for concept_relevance instructive position filtering."""
import chess
import pytest
from modules.concept_relevance import is_instructive, _concept_score


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
