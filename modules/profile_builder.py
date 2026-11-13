import json
from datetime import datetime, timezone

import chess
from config import MIN_OCCURRENCES, MAX_STAT_CP
from modules.attribution import attribute_error, is_tactical_opportunity


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


def _empty_stats() -> dict:
    return {
        "total_occurrences": 0,
        "error_occurrences": 0,
        "total_error_magnitude": 0,
        "positions": [],
    }


def is_mate_error(validation: dict, player_color_bool: bool) -> bool:
    """Erro de mate perdido ou permitido — contado à parte, nunca atribuído a conceito."""
    return (_is_missed_checkmate(validation, player_color_bool)
            or _is_allowed_checkmate(validation, player_color_bool))


def _attribution_for(position: dict, player_color_bool: bool) -> dict:
    """A atribuição já calculada (main / classificador LLM) ou calculada agora."""
    if position.get("attribution") is not None:
        return position["attribution"]
    fen = position.get("fen")
    if not fen:
        return {"concept": None, "source": None, "motif": None}
    return attribute_error(chess.Board(fen), position.get("move_played"),
                           position["stockfish_validation"],
                           position.get("concepts_detected") or {}, player_color_bool)


def annotate_attributions(games_data: list) -> list[tuple[dict, dict]]:
    """Calcula e grava position["attribution"] em cada erro (exceto mates).

    Retorna os pares (game, position) dos erros que ficaram sem conceito — os
    candidatos ao classificador LLM (modules/error_classifier.py).
    """
    unattributed = []
    for game in games_data:
        color = game.get("player_color", "white") == "white"
        for position in game["positions"]:
            validation = position["stockfish_validation"]
            if not validation.get("is_error") or is_mate_error(validation, color):
                continue
            position["attribution"] = _attribution_for(position, color)
            if not position["attribution"].get("concept"):
                unattributed.append((game, position))
    return unattributed


def _record_error(concept_stats: dict, concept_key: str, validation: dict,
                  game: dict, position: dict, attribution: dict | None = None):
    """Credita uma ocorrência de erro a um conceito e guarda a posição de exemplo."""
    attribution = attribution or {}
    stats = concept_stats.setdefault(concept_key, _empty_stats())
    stats["error_occurrences"] += 1
    source = attribution.get("source") or "rule"
    stats[f"{source}_errors"] = stats.get(f"{source}_errors", 0) + 1
    # Cap at MAX_STAT_CP so mate scores (≈10000 cp) don't skew the average
    stats["total_error_magnitude"] += min(validation["error_magnitude"], MAX_STAT_CP)
    stats["positions"].append({
        "game_id": game["game_id"],
        "white": game.get("white", "White"),
        "black": game.get("black", "Black"),
        "player_color": game.get("player_color", "white"),
        "game_url": game.get("game_url", ""),
        "date": game.get("date", ""),
        "fen": position.get("fen"),
        "move_number": position.get("move_number"),
        "move_played": position.get("move_played"),
        "best_move": validation.get("best_move"),
        "eval_before": validation.get("eval_before"),
        "eval_after": validation.get("eval_after"),
        "error_magnitude": validation["error_magnitude"],
        # Origem da atribuição: "rule" (regras determinísticas) ou "llm" (inferida pelo
        # classificador para erros que as regras não explicam). motif: o caminho da
        # regra (capture/line/check/refutation/hanging/structural); reason: a
        # justificativa curta do LLM.
        "attribution": source,
        "motif": attribution.get("motif"),
        "confidence": attribution.get("confidence"),
        "reason": attribution.get("reason"),
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
    attribution_counts = {"rule": 0, "llm": 0, "unattributed": 0}

    for game in games_data:
        player_color_bool = game.get("player_color", "white") == "white"
        for position in game["positions"]:
            total_positions += 1
            validation = position["stockfish_validation"]
            concepts = position.get("concepts_detected") or {}
            validated = validation.get("eval_before") is not None

            if validation["is_error"]:
                total_errors += 1

                if _is_missed_checkmate(validation, player_color_bool):
                    total_missed_checkmates += 1
                    continue  # tactical oversight, not a strategic pattern

                if _is_allowed_checkmate(validation, player_color_bool):
                    total_allowed_checkmates += 1
                    continue  # opponent delivering mate — not a strategic pattern

                # Cada erro vai para no máximo UM conceito (modules/attribution.py):
                # táticas primeiro (perdida / peça pendurada / permitida / xeque),
                # depois o conceito estratégico com vínculo causal mais forte.
                attribution = _attribution_for(position, player_color_bool)
                concept = attribution.get("concept")
                if not concept:
                    attribution_counts["unattributed"] += 1
                    continue
                attribution_counts[attribution.get("source") or "rule"] += 1
                _record_error(concept_stats, concept, validation, game, position, attribution)
            else:
                # Oportunidade tática convertida: o melhor lance era tático (ganhava
                # material ou dava xeque) e o jogador o jogou. Alimenta o denominador do
                # missed_tactic para a taxa de erro dele significar algo (perdidas /
                # oportunidades), em vez de ficar ~100% por construção.
                fen = position.get("fen")
                best_move = validation.get("best_move")
                if (fen and best_move and position.get("move_played") == best_move
                        and is_tactical_opportunity(chess.Board(fen), best_move,
                                                    validation.get("best_line"),
                                                    player_color_bool)):
                    stats = concept_stats.setdefault("missed_tactic", _empty_stats())
                    stats["total_occurrences"] += 1

                # Tática permitida: toda posição avaliada sem erro é uma oportunidade
                # de não entregar material — a taxa vira "lances que entregam material".
                if validated:
                    stats = concept_stats.setdefault("allowed_tactic", _empty_stats())
                    stats["total_occurrences"] += 1

                # Nota metodológica: o denominador (total_occurrences) conta toda
                # posição correta com o conceito presente, sem o gate causal — que só é
                # definível quando houve erro. A taxa de erro é portanto conservadora
                # (denominador amplo, numerador com vínculo causal).
                for concept_key, concept_data in concepts.items():
                    if concept_data.get("detected", False):
                        stats = concept_stats.setdefault(concept_key, _empty_stats())
                        stats["total_occurrences"] += 1

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
                "rule_errors": stats.get("rule_errors", 0),
                "llm_errors": stats.get("llm_errors", 0),
                # Store every error position so the Game Explorer can show one per game
                # by default and "load more" up to all of them.
                "sample_positions": stats["positions"]
            })

    weaknesses.sort(key=lambda x: x["error_occurrences"], reverse=True)

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "total_games": len(games_data),
        "total_positions_analyzed": total_positions,
        "total_errors_detected": total_errors,
        "total_missed_checkmates": total_missed_checkmates,
        "total_allowed_checkmates": total_allowed_checkmates,
        # Erros por origem da atribuição; "unattributed" = nenhum conceito os explica.
        "attribution_summary": attribution_counts,
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
