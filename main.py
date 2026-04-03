import chess
import json
import os
from modules.pgn_loader import load_games_from_file, iterate_positions
from modules.chess_com_loader import fetch_recent_games
from modules.position_analyzer import detect_concepts
from modules.stockfish_validator import batch_validate
from modules.profile_builder import build_profile, save_profile
from modules.ai_diagnostician import diagnose, load_silman_concepts

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def analyze_player(pgn_path: str, player_name: str, player_color: bool = chess.WHITE):
    """
    Pipeline completo de análise de um jogador.

    pgn_path: caminho para o arquivo PGN com as partidas
    player_name: nome do jogador (para identificação)
    player_color: chess.WHITE ou chess.BLACK
    """
    print(f"\n=== Iniciando análise de {player_name} ===\n")

    # 1. Carrega partidas
    games = load_games_from_file(pgn_path)

    # 2. Para cada partida, coleta posições e dados
    games_data = []
    for i, game in enumerate(games):
        print(f"[main] Processando partida {i + 1}/{len(games)}...")
        game_positions = []
        positions_to_validate = []

        for board_before, move_played, board_after in iterate_positions(game, player_color):
            concepts = detect_concepts(board_before, player_color)
            positions_to_validate.append((board_before.copy(), move_played))
            game_positions.append({
                "fen": board_before.fen(),
                "move_played": move_played.uci(),
                "concepts_detected": concepts,
                "stockfish_validation": None
            })

        validations = batch_validate(positions_to_validate)
        for j, validation in enumerate(validations):
            game_positions[j]["stockfish_validation"] = validation

        games_data.append({
            "game_id": f"game_{i + 1}",
            "positions": game_positions
        })

    # 3. Constrói perfil de fraquezas
    print("\n[main] Construindo perfil de fraquezas...")
    profile = build_profile(games_data)
    save_profile(profile, f"{OUTPUT_DIR}/{player_name}_profile.json")

    print(f"\n[main] Resumo do perfil:")
    print(f"  Partidas analisadas: {profile['total_games']}")
    print(f"  Posições analisadas: {profile['total_positions_analyzed']}")
    print(f"  Taxa de erro global: {profile['overall_error_rate'] * 100:.1f}%")
    print(f"  Fraquezas recorrentes: {len(profile['weaknesses'])}")
    for w in profile["weaknesses"]:
        print(f"    - {w['concept']}: {w['error_occurrences']} erros ({w['error_rate']*100:.0f}% das ocorrências)")

    # 4. Diagnóstico pela IA
    print("\n[main] Executando diagnóstico por IA...")
    silman_concepts = load_silman_concepts()
    diagnosis = diagnose(profile, silman_concepts)

    diagnosis_path = f"{OUTPUT_DIR}/{player_name}_diagnosis.json"
    with open(diagnosis_path, "w", encoding="utf-8") as f:
        json.dump(diagnosis, f, indent=2, ensure_ascii=False)

    print(f"\n=== DIAGNÓSTICO FINAL ===")
    print(f"Causa raiz: {diagnosis['root_cause']['name']}")
    print(f"Descrição: {diagnosis['root_cause']['description']}")
    print(f"Confiança: {diagnosis['confidence']}")
    print(f"\nPrioridade de estudo (Silman):")
    for item in diagnosis.get("study_priority", []):
        print(f"  #{item['priority_rank']} — {item.get('silman_name', item['concept'])} "
              f"(Capítulo {item.get('silman_chapter', '?')}, p.{item.get('silman_page', '?')})")
        print(f"     Motivo: {item['reason']}")

    print(f"\nArquivos salvos em '{OUTPUT_DIR}/'")
    return profile, diagnosis


def analyze_player_from_username(username: str, n_months: int = 3):
    """
    Pipeline completo de análise a partir de um username do Chess.com.

    Busca automaticamente os jogos mais recentes via API pública do Chess.com,
    detecta a cor do jogador em cada partida, e executa o pipeline completo.

    username: nome de usuário no Chess.com
    n_months: quantos meses recentes buscar (padrão: 3)
    """
    print(f"\n=== Iniciando análise de {username} via Chess.com API ===\n")
    print(f"[main] Buscando jogos dos últimos {n_months} meses...")

    game_color_pairs = fetch_recent_games(username, n_months=n_months)
    print(f"[main] {len(game_color_pairs)} partidas carregadas do Chess.com")

    games_data = []
    for i, (game, player_color) in enumerate(game_color_pairs):
        print(f"[main] Processando partida {i + 1}/{len(game_color_pairs)}...")
        game_positions = []
        positions_to_validate = []

        for board_before, move_played, board_after in iterate_positions(game, player_color):
            concepts = detect_concepts(board_before, player_color)
            positions_to_validate.append((board_before.copy(), move_played))
            game_positions.append({
                "fen": board_before.fen(),
                "move_played": move_played.uci(),
                "concepts_detected": concepts,
                "stockfish_validation": None
            })

        validations = batch_validate(positions_to_validate)
        for j, validation in enumerate(validations):
            game_positions[j]["stockfish_validation"] = validation

        games_data.append({
            "game_id": f"game_{i + 1}",
            "positions": game_positions
        })

    print("\n[main] Construindo perfil de fraquezas...")
    profile = build_profile(games_data)
    save_profile(profile, f"{OUTPUT_DIR}/{username}_profile.json")

    print(f"\n[main] Resumo do perfil:")
    print(f"  Partidas analisadas: {profile['total_games']}")
    print(f"  Posições analisadas: {profile['total_positions_analyzed']}")
    print(f"  Taxa de erro global: {profile['overall_error_rate'] * 100:.1f}%")
    print(f"  Fraquezas recorrentes: {len(profile['weaknesses'])}")
    for w in profile["weaknesses"]:
        print(f"    - {w['concept']}: {w['error_occurrences']} erros ({w['error_rate']*100:.0f}% das ocorrências)")

    print("\n[main] Executando diagnóstico por IA...")
    silman_concepts = load_silman_concepts()
    diagnosis = diagnose(profile, silman_concepts)

    diagnosis_path = f"{OUTPUT_DIR}/{username}_diagnosis.json"
    with open(diagnosis_path, "w", encoding="utf-8") as f:
        json.dump(diagnosis, f, indent=2, ensure_ascii=False)

    print(f"\n=== DIAGNÓSTICO FINAL ===")
    print(f"Causa raiz: {diagnosis['root_cause']['name']}")
    print(f"Descrição: {diagnosis['root_cause']['description']}")
    print(f"Confiança: {diagnosis['confidence']}")
    print(f"\nPrioridade de estudo (Silman):")
    for item in diagnosis.get("study_priority", []):
        print(f"  #{item['priority_rank']} — {item.get('silman_name', item['concept'])} "
              f"(Capítulo {item.get('silman_chapter', '?')}, p.{item.get('silman_page', '?')})")
        print(f"     Motivo: {item['reason']}")

    print(f"\nArquivos salvos em '{OUTPUT_DIR}/'")
    return profile, diagnosis


if __name__ == "__main__":
    # Usar Chess.com API (recomendado)
    analyze_player_from_username(username="sprandel", n_months=3)

    # Alternativa: usar arquivo PGN local
    # analyze_player(pgn_path="partidas.pgn", player_name="sprandel", player_color=chess.WHITE)
