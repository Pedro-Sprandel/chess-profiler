import json
from config import MIN_OCCURRENCES


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

    for game in games_data:
        for position in game["positions"]:
            total_positions += 1
            validation = position["stockfish_validation"]
            concepts = position["concepts_detected"]

            if validation["is_error"]:
                total_errors += 1

                for concept_key, concept_data in concepts.items():
                    if concept_data.get("detected", False):
                        if concept_key not in concept_stats:
                            concept_stats[concept_key] = {
                                "total_occurrences": 0,
                                "error_occurrences": 0,
                                "total_error_magnitude": 0,
                                "positions": []
                            }
                        concept_stats[concept_key]["error_occurrences"] += 1
                        concept_stats[concept_key]["total_error_magnitude"] += validation["error_magnitude"]
                        concept_stats[concept_key]["positions"].append({
                            "game_id": game["game_id"],
                            "fen": position.get("fen"),
                            "move_played": position.get("move_played"),
                            "best_move": validation.get("best_move"),
                            "error_magnitude": validation["error_magnitude"]
                        })
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
                "sample_positions": stats["positions"][:3]
            })

    weaknesses.sort(key=lambda x: x["error_occurrences"], reverse=True)

    return {
        "total_games": len(games_data),
        "total_positions_analyzed": total_positions,
        "total_errors_detected": total_errors,
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
