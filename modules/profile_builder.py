import json
import chess
from config import MIN_OCCURRENCES, MAX_STAT_CP
from modules.concept_relevance import is_instructive, is_missed_tactic


def _player_eval(validation: dict, key: str, player_color_bool: bool) -> float:
    """Returns the eval at a given key (eval_before/eval_after) from the player's perspective."""
    raw = validation.get(key, 0)
    return raw if player_color_bool else -raw


def _is_missed_checkmate(validation: dict, player_color_bool: bool) -> bool:
    """True when the player had a forced mate available (eval >= 9000 cp) but didn't take it."""
    if not validation.get("is_error"):
        return False
    return _player_eval(validation, "eval_before", player_color_bool) >= 9000


def _is_allowed_checkmate(validation: dict, player_color_bool: bool) -> bool:
    """True when the opponent has or gets a forced mate in the position (eval <= -9000 cp for player).

    Covers two cases:
      - Player was already in a forced mate before their move (position was tactically lost).
      - Player's move handed the opponent a forced mate (the blunder that loses by mate).
    """
    if not validation.get("is_error"):
        return False
    before = _player_eval(validation, "eval_before", player_color_bool)
    after  = _player_eval(validation, "eval_after",  player_color_bool)
    return before <= -9000 or after <= -9000


def _record_error(concept_stats: dict, concept_key: str, validation: dict,
                  game: dict, fen, move_played, best_move):
    """Credita uma ocorrência de erro a um conceito e guarda a posição de exemplo."""
    stats = concept_stats.setdefault(concept_key, {
        "total_occurrences": 0,
        "error_occurrences": 0,
        "total_error_magnitude": 0,
        "positions": [],
    })
    stats["error_occurrences"] += 1
    # Cap at MAX_STAT_CP so mate scores (≈10000 cp) don't skew the average
    stats["total_error_magnitude"] += min(validation["error_magnitude"], MAX_STAT_CP)
    stats["positions"].append({
        "game_id": game["game_id"],
        "white": game.get("white", "White"),
        "black": game.get("black", "Black"),
        "player_color": game.get("player_color", "white"),
        "fen": fen,
        "move_played": move_played,
        "best_move": best_move,
        "error_magnitude": validation["error_magnitude"],
    })


def build_profile(games_data: list) -> dict:
    """
    Constrói o perfil de fraquezas do jogador a partir dos dados de todas as partidas.

    games_data: lista de dicts com:
        - game_id
        - positions: lista de dicts com concepts_detected + stockfish_validation

    Retorna perfil com contagens, aproveitamento e padrões.
    """
    concept_stats = {}
    total_positions = 0
    total_errors = 0
    total_missed_checkmates = 0
    total_allowed_checkmates = 0

    for game in games_data:
        for position in game["positions"]:
            total_positions += 1
            validation = position["stockfish_validation"]
            concepts = position["concepts_detected"]
            player_color_bool = game.get("player_color", "white") == "white"

            if validation["is_error"]:
                total_errors += 1

                if _is_missed_checkmate(validation, player_color_bool):
                    total_missed_checkmates += 1
                    continue  # tactical oversight, not a strategic pattern

                if _is_allowed_checkmate(validation, player_color_bool):
                    total_allowed_checkmates += 1
                    continue  # opponent delivering mate — not a strategic pattern

                fen = position.get("fen")
                move_played = position.get("move_played")
                best_move = validation.get("best_move")
                board = chess.Board(fen) if fen else None

                # Tactical-first precedence: if the best move was a material-winning
                # capture the player declined (e.g. an enemy piece left hanging), this
                # is a tactical oversight, not a strategic one. Attribute it to the
                # `missed_tactic` concept ONLY, so it doesn't leak into co-occurring
                # strategic concepts (weak_square, king_safety, ...).
                if board and is_missed_tactic(board, move_played, best_move, player_color_bool):
                    _record_error(concept_stats, "missed_tactic", validation,
                                  game, fen, move_played, best_move)
                    continue

                for concept_key, concept_data in concepts.items():
                    if not concept_data.get("detected", False):
                        continue

                    # Gate the counter behind is_instructive — only count errors
                    # that are causally linked to the concept (move type + score delta)
                    if board and not is_instructive(board, move_played, best_move,
                                                    concept_key, player_color_bool):
                        continue

                    # Store every instructive error position; the Game Explorer shows
                    # one per game by default and "loads more" up to all of them.
                    _record_error(concept_stats, concept_key, validation,
                                  game, fen, move_played, best_move)
            else:
                for concept_key, concept_data in concepts.items():
                    if concept_data.get("detected", False):
                        if concept_key not in concept_stats:
                            concept_stats[concept_key] = {
                                "total_occurrences": 0,
                                "error_occurrences": 0,
                                "total_error_magnitude": 0,
                                "positions": []
                            }
                        concept_stats[concept_key]["total_occurrences"] += 1

    weaknesses = []
    for concept_key, stats in concept_stats.items():
        total_occ = stats["total_occurrences"] + stats["error_occurrences"]
        error_rate = stats["error_occurrences"] / total_occ if total_occ > 0 else 0
        avg_error = stats["total_error_magnitude"] / stats["error_occurrences"] if stats["error_occurrences"] > 0 else 0

        if stats["error_occurrences"] >= MIN_OCCURRENCES:
            weaknesses.append({
                "concept": concept_key,
                "total_occurrences": total_occ,
                "error_occurrences": stats["error_occurrences"],
                "error_rate": round(error_rate, 3),
                "avg_error_magnitude_cp": round(avg_error, 1),
                # Store every error position so the Game Explorer can show one per game
                # by default and "load more" up to all of them.
                "sample_positions": stats["positions"]
            })

    weaknesses.sort(key=lambda x: x["error_occurrences"], reverse=True)

    return {
        "total_games": len(games_data),
        "total_positions_analyzed": total_positions,
        "total_errors_detected": total_errors,
        "total_missed_checkmates": total_missed_checkmates,
        "total_allowed_checkmates": total_allowed_checkmates,
        "overall_error_rate": round(total_errors / total_positions, 3) if total_positions > 0 else 0,
        "weaknesses": weaknesses
    }


def save_profile(profile: dict, path: str):
    """Salva o perfil como JSON no caminho especificado."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    print(f"[profile_builder] Perfil salvo em {path}")


def load_profile(path: str) -> dict:
    """Carrega um perfil JSON do caminho especificado."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
