"""
Determines whether a position is instructive for a given Silman concept.

A position is instructive when ALL THREE conditions hold:
  1. The player didn't play the best move
  2. The best move involves the piece type relevant to the concept
     (e.g. open_file errors require a rook/queen best move)
  3. The best move produces a concept score at least THRESHOLD better
     than the move played — not just marginally better

This establishes a genuine causal link between the mistake and the concept,
filtering out positions where the concept happened to be present but was
unrelated to why the move was bad.
"""
import chess
from modules.position_analyzer import detect_concepts


# ── Move-type constraints ─────────────────────────────────────────────────────
# If a concept is listed here, the best move must involve moving one of these
# piece types. If Stockfish's recommendation was e.g. a bishop capture, the
# error wasn't about the open file — skip it.

CONCEPT_REQUIRED_PIECE: dict[str, set] = {
    "open_file":      {chess.ROOK, chess.QUEEN},
    "rook_on_7th":    {chess.ROOK},
    "knight_outpost": {chess.KNIGHT},
    "passed_pawn":    {chess.PAWN},
    "bad_bishop":     {chess.BISHOP},
    "bishop_pair":    {chess.BISHOP},
}

# ── Minimum score delta per concept ──────────────────────────────────────────
# score_best must be >= score_played + threshold to count as instructive.
# Higher values = stricter filter for noisy concepts.

CONCEPT_SCORE_THRESHOLD: dict[str, float] = {
    "open_file":      2.0,   # rook must land on file AND make a meaningful difference
    "piece_activity": 2.0,   # mobility gap must be real, not one square
    "space_advantage": 3.0,  # space is coarse — require a bigger delta
    "passed_pawn":    1.0,
    "pawn_majority":  1.0,
    "weak_square":    1.0,
    "king_safety":    1.0,
    "isolated_pawn":  1.0,
    "doubled_pawn":   1.0,
    "overloaded_piece": 1.0,
    "backward_pawn":    1.0,
    "center_control":   1.5,
}
_DEFAULT_THRESHOLD = 1.0


# ── Concept scoring ───────────────────────────────────────────────────────────

def _concept_score(concepts: dict, concept_key: str) -> float:
    """
    Returns a numeric score representing how well the concept is being handled
    after a move. Higher = better for the player regarding this concept.
    """
    c = concepts.get(concept_key, {})

    if concept_key == "weak_square":
        return -c.get("count", 0)

    if concept_key == "open_file":
        open_count = len(c.get("open_files", [])) + len(c.get("semi_open_files", []))
        rook_bonus = 2 if c.get("player_has_rook_on_open") else 0
        return open_count + rook_bonus

    if concept_key == "isolated_pawn":
        return -c.get("count", 0)

    if concept_key == "bishop_pair":
        return 1.0 if c.get("detected") else 0.0

    if concept_key == "knight_outpost":
        return len(c.get("squares", []))

    if concept_key == "king_safety":
        shield = c.get("shield_pawns", 0)
        exposed_penalty = -2 if c.get("exposed") else 0
        return shield + exposed_penalty

    if concept_key == "space_advantage":
        return c.get("advantage", 0)

    if concept_key == "passed_pawn":
        return c.get("count", 0)

    if concept_key == "doubled_pawn":
        return -c.get("count", 0)

    if concept_key == "rook_on_7th":
        return len(c.get("squares", []))

    if concept_key == "bad_bishop":
        return -c.get("count", 0)

    if concept_key == "pawn_majority":
        score = 0.0
        if c.get("queenside_majority"):
            score += c.get("player_queenside", 0) - c.get("opponent_queenside", 0)
        if c.get("kingside_majority"):
            score += c.get("player_kingside", 0) - c.get("opponent_kingside", 0)
        return score

    if concept_key == "piece_activity":
        return c.get("advantage", 0)

    if concept_key == "overloaded_piece":
        return len(c.get("overloaded_squares", []))

    if concept_key == "hanging_piece":
        return -c.get("count", 0)

    if concept_key == "backward_pawn":
        return -c.get("count", 0)

    if concept_key == "center_control":
        return c.get("advantage", 0)

    return 0.0


# ── Tactical-first gate ───────────────────────────────────────────────────────
# Material value of each piece type, used to decide whether a capture wins material.

_PIECE_VALUES: dict[int, int] = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 100,
}


def is_missed_tactic(
    board_before: chess.Board,
    move_played_uci: str,
    best_move_uci: str,
    player_color: bool,
) -> bool:
    """
    Returns True when the best move was a material-winning capture the player declined.

    Signals a *tactical* oversight — most often an enemy piece left hanging that the
    player failed to grab — rather than a strategic misunderstanding. Such errors don't
    belong to any Silman strategic concept; they map to the `missed_tactic` concept.

    A capture wins material when the captured piece is either:
      - undefended by the opponent (free material), or
      - defended, but worth more than the capturing piece (favourable exchange).
    """
    if not best_move_uci or not move_played_uci:
        return False
    if move_played_uci == best_move_uci:
        return False  # player found the tactic

    try:
        best_move = chess.Move.from_uci(best_move_uci)
        if not board_before.is_capture(best_move):
            return False

        victim = board_before.piece_at(best_move.to_square)
        attacker = board_before.piece_at(best_move.from_square)
        if victim is None or attacker is None:
            return False  # en passant / malformed — skip conservatively

        opponent_color = not player_color
        if board_before.is_attacked_by(opponent_color, best_move.to_square):
            # Defended target — only a missed tactic if the exchange wins material.
            return _PIECE_VALUES[victim.piece_type] > _PIECE_VALUES[attacker.piece_type]
        return True  # undefended enemy piece — free material

    except Exception:
        return False  # on any parse error, don't claim a missed tactic


# ── Public API ────────────────────────────────────────────────────────────────

def is_instructive(
    board_before: chess.Board,
    move_played_uci: str,
    best_move_uci: str,
    concept_key: str,
    player_color: bool,
) -> bool:
    """
    Returns True if this position is genuinely instructive for the given concept.

    Three gates, in order (cheapest first):
      1. Player didn't play the best move
      2. Best move involves the piece type relevant to the concept
      3. Best move improves the concept score by at least the threshold
    """
    if not best_move_uci or not move_played_uci:
        return True  # no data — keep it

    if move_played_uci == best_move_uci:
        return False  # no mistake

    try:
        best_move = chess.Move.from_uci(best_move_uci)

        # Gate 2: move-type awareness
        required_pieces = CONCEPT_REQUIRED_PIECE.get(concept_key)
        if required_pieces:
            piece = board_before.piece_at(best_move.from_square)
            if piece is None or piece.piece_type not in required_pieces:
                return False

        # Gate 3: score delta threshold
        board_after_played = board_before.copy()
        board_after_played.push(chess.Move.from_uci(move_played_uci))
        concepts_after_played = detect_concepts(board_after_played, player_color)

        board_after_best = board_before.copy()
        board_after_best.push(best_move)
        concepts_after_best = detect_concepts(board_after_best, player_color)

        score_played = _concept_score(concepts_after_played, concept_key)
        score_best   = _concept_score(concepts_after_best,   concept_key)
        threshold    = CONCEPT_SCORE_THRESHOLD.get(concept_key, _DEFAULT_THRESHOLD)

        return score_best >= score_played + threshold

    except Exception:
        return True  # on any error, don't filter out
