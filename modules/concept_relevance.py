"""
Determines whether a position is instructive for a given Silman concept.

A position is considered instructive if the best move (according to Stockfish)
handles the concept measurably better than the move actually played.
This filters out positions where the error was incidental to the concept
(e.g., a tactical blunder while a weak square happened to exist).
"""
import chess
from modules.position_analyzer import detect_concepts


def _concept_score(concepts: dict, concept_key: str) -> float:
    """
    Returns a numeric score representing how well the concept is being handled.
    Higher score = better position for the player regarding this concept.
    """
    c = concepts.get(concept_key, {})

    if concept_key == "weak_square":
        # Fewer weak squares in your own camp is better
        return -c.get("count", 0)

    if concept_key == "open_file":
        # Having a rook on an open/semi-open file is better
        open_count = len(c.get("open_files", [])) + len(c.get("semi_open_files", []))
        rook_bonus = 2 if c.get("player_has_rook_on_open") else 0
        return open_count + rook_bonus

    if concept_key == "isolated_pawn":
        # Fewer isolated pawns is better
        return -c.get("count", 0)

    if concept_key == "bishop_pair":
        # Having the bishop pair advantage is better
        return 1 if c.get("detected") else 0

    if concept_key == "knight_outpost":
        # More outpost squares occupied is better
        return len(c.get("squares", []))

    if concept_key == "king_safety":
        # More shield pawns and not exposed is better
        shield = c.get("shield_pawns", 0)
        exposed_penalty = -2 if c.get("exposed") else 0
        return shield + exposed_penalty

    if concept_key == "space_advantage":
        # More space advantage is better
        return c.get("advantage", 0)

    return 0


def is_instructive(
    board_before: chess.Board,
    move_played_uci: str,
    best_move_uci: str,
    concept_key: str,
    player_color: bool,
) -> bool:
    """
    Returns True if this position is genuinely instructive for the given concept.

    A position is instructive when the best move results in a measurably better
    concept score than the move the player actually played. This establishes a
    causal link between the mistake and the Silman concept.

    If move_played == best_move, always returns False (no mistake was made).
    If best_move is unknown, falls back to True (keep the position).
    """
    if not best_move_uci or not move_played_uci:
        return True  # no data to filter on — keep it

    if move_played_uci == best_move_uci:
        return False  # player played the best move, not a concept error

    try:
        board_after_played = board_before.copy()
        board_after_played.push(chess.Move.from_uci(move_played_uci))
        concepts_after_played = detect_concepts(board_after_played, player_color)

        board_after_best = board_before.copy()
        board_after_best.push(chess.Move.from_uci(best_move_uci))
        concepts_after_best = detect_concepts(board_after_best, player_color)

        score_played = _concept_score(concepts_after_played, concept_key)
        score_best = _concept_score(concepts_after_best, concept_key)

        # Instructive if the best move produces a strictly better concept outcome
        return score_best > score_played

    except Exception:
        return True  # on any error, don't filter out the position
