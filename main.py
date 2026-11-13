import argparse
import chess
import json
import os
from modules.pgn_loader import load_games_from_file, iterate_positions
from modules.chess_com_loader import fetch_recent_games
from modules.position_analyzer import detect_concepts
from modules.stockfish_validator import batch_validate, open_engine
from modules.profile_builder import annotate_attributions, build_profile, save_profile, load_profile
from modules.error_classifier import classify_unattributed
from modules.ai_diagnostician import diagnose, load_silman_concepts
from modules.app_store import AppStore
from modules.db import Database
from config import OUTPUT_DIR, STOCKFISH_DEPTH, OPENING_MOVES_TO_SKIP, VALIDATE_ALL_POSITIONS

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Validation placeholder for positions without a detected concept (no Stockfish call).
_NO_ERROR = {"is_error": False, "eval_before": None, "eval_after": None, "error_magnitude": 0,
             "best_move": None, "best_line": [], "refutation_line": []}


def _emit(on_progress, stage, current, total, message):
    """Prints a progress message and forwards it to the optional UI callback."""
    print(message)
    if on_progress:
        on_progress(stage, current, total, message)


def _persist_games_to_db(db: Database, games_data: list, source: str):
    """Persists all positions and their analysis results to the SQLite database."""
    for game in games_data:
        for pos in game["positions"]:
            # Dedupe: re-análises do mesmo jogador re-visitam as mesmas posições —
            # não duplicar a linha nem os resultados de análise associados.
            existing = db.find_position(
                fen=pos["fen"], move_played=pos["move_played"],
                white=game["white"], black=game["black"], source=source,
            )
            if existing is not None:
                continue

            pos_id = db.insert_position({
                "fen":          pos["fen"],
                "move_number":  pos.get("move_number"),
                "move_played":  pos["move_played"],
                "player_color": game["player_color"],
                "white":        game["white"],
                "black":        game["black"],
                "white_rating": game.get("white_rating", 0),
                "black_rating": game.get("black_rating", 0),
                "opening":      game.get("opening", ""),
                "eco":          game.get("eco", ""),
                "game_url":     game.get("game_url", ""),
                "source":       source,
            })

            validation = pos["stockfish_validation"]
            bulk_rows = [
                (
                    pos_id,
                    concept_key,
                    concept_data.get("detected", False),
                    concept_data,
                    validation["is_error"],
                    validation["error_magnitude"],
                )
                for concept_key, concept_data in pos["concepts_detected"].items()
            ]
            db.insert_analysis_results_bulk(bulk_rows)


def _int_header(headers, key) -> int:
    try:
        return int(headers.get(key, 0) or 0)
    except ValueError:
        return 0


def _opening_name(headers) -> str:
    """Nome da abertura: header Opening, ou derivado do ECOUrl do Chess.com."""
    opening = headers.get("Opening", "")
    if opening and opening != "?":
        return opening
    eco_url = headers.get("ECOUrl", "")
    if eco_url:
        return eco_url.rstrip("/").split("/")[-1].replace("-", " ")
    return ""


def _process_games(game_color_pairs: list, on_progress=None, depth: int = STOCKFISH_DEPTH) -> list:
    """
    Analisa cada partida: detecta conceitos por posição e valida no Stockfish todas
    as posições (VALIDATE_ALL_POSITIONS; senão, só as com conceito detectado).

    Os primeiros OPENING_MOVES_TO_SKIP lances completos são ignorados: são
    majoritariamente teoria de abertura, onde conceito detectado é ruído.

    game_color_pairs: lista de (chess.pgn.Game, player_color bool)
    depth: profundidade UCI usada na validação Stockfish.
    Retorna games_data — lista de dicts prontos para build_profile / persistência.
    Usa uma única instância do Stockfish para todas as partidas.
    """
    games_data = []
    total = len(game_color_pairs)
    engine = open_engine()
    try:
        for i, (game, player_color) in enumerate(game_color_pairs):
            _emit(on_progress, "game", i, total, f"[main] Analyzing game {i + 1}/{total}...")
            game_positions = []
            to_validate = []  # (original_index, board_before, move_played)

            for board_before, move_played, board_after in iterate_positions(game, player_color):
                if board_before.fullmove_number <= OPENING_MOVES_TO_SKIP:
                    continue
                concepts = detect_concepts(board_before, player_color)
                pos_idx = len(game_positions)
                if VALIDATE_ALL_POSITIONS or any(v.get("detected") for v in concepts.values()):
                    to_validate.append((pos_idx, board_before.copy(), move_played))
                game_positions.append({
                    "fen": board_before.fen(),
                    "move_number": board_before.fullmove_number,
                    "move_played": move_played.uci(),
                    "concepts_detected": concepts,
                    "stockfish_validation": _NO_ERROR,
                })

            if to_validate:
                idxs, boards, moves = zip(*to_validate)
                validations = batch_validate(list(zip(boards, moves)), engine=engine, depth=depth)
                for idx, validation in zip(idxs, validations):
                    game_positions[idx]["stockfish_validation"] = validation

            headers = game.headers
            games_data.append({
                "game_id": f"game_{i + 1}",
                "white": headers.get("White", "White"),
                "black": headers.get("Black", "Black"),
                "white_rating": _int_header(headers, "WhiteElo"),
                "black_rating": _int_header(headers, "BlackElo"),
                "date": headers.get("UTCDate", headers.get("Date", "")),
                "game_url": headers.get("Link", ""),
                "eco": headers.get("ECO", ""),
                "opening": _opening_name(headers),
                "player_color": "white" if player_color else "black",
                "positions": game_positions,
            })
    finally:
        engine.quit()

    return games_data


def _build_profile_phase(games_data: list, name: str, source: str, on_progress=None,
                         depth: int = STOCKFISH_DEPTH, subject: str | None = None,
                         n_games: int | None = None, export_json: bool = True,
                         owner_id: int | None = None) -> dict:
    """
    Persiste as posições no SQLite local, constrói o perfil de fraquezas e o grava
    na tabela `analyses` do AppStore (fonte única da UI; Postgres no deploy), com
    `owner_id` como dono. Com export_json=True (CLI) também exporta
    output/{name}_profile.json. Não roda o diagnóstico da IA.

    Esta é a fase "rápida" (local): tudo que a UI precisa para exibir o painel de
    perfil e o explorador de partidas, antes de aguardar a chamada à API da IA.
    """
    # Persiste no SQLite
    _emit(on_progress, "profile", 0, 1, "[main] Persisting to database...")
    with Database() as db:
        _persist_games_to_db(db, games_data, source=source)
        print(f"[main] {db.count_positions()} total positions in DB | cache: {db.cache_stats()['cached_evals']} evals")

    # Atribui cada erro a no máximo um conceito (regras determinísticas); os que
    # nenhuma regra explica vão para o classificador LLM (limitado e com cache).
    _emit(on_progress, "profile", 0, 1, "[main] Attributing mistakes to concepts...")
    unattributed = annotate_attributions(games_data)
    llm_stats = classify_unattributed(unattributed, load_silman_concepts(), on_progress)
    if llm_stats["candidates"]:
        print(f"[main] Erros sem conceito pelas regras: {llm_stats['candidates']} | "
              f"classificados pela IA: {llm_stats['accepted']} "
              f"(cache {llm_stats['cached']}, enviados {llm_stats['sent']}, "
              f"fora do teto/sem IA {llm_stats['skipped']})")

    # Constrói perfil de fraquezas
    _emit(on_progress, "profile", 0, 1, "[main] Building weakness profile...")
    profile = build_profile(games_data)
    profile["metadata"] = {
        "player": subject or name,
        "source": source,
        "depth": depth,
        "llm_classification": llm_stats,
    }
    with AppStore() as store:
        store.save_analysis(name, profile, subject=subject or name, source=source,
                            depth=depth, n_games=n_games, owner_id=owner_id)
    if export_json:
        save_profile(profile, f"{OUTPUT_DIR}/{name}_profile.json")

    print(f"\n[main] Resumo do perfil:")
    print(f"  Partidas analisadas: {profile['total_games']}")
    print(f"  Posições analisadas: {profile['total_positions_analyzed']}")
    print(f"  Taxa de erro global: {profile['overall_error_rate'] * 100:.1f}%")
    print(f"  Fraquezas recorrentes: {len(profile['weaknesses'])}")
    for w in profile["weaknesses"]:
        print(f"    - {w['concept']}: {w['error_occurrences']} erros ({w['error_rate']*100:.0f}% das ocorrências)")

    return profile


def _diagnose_and_save(profile: dict, name: str, on_progress=None,
                       export_json: bool = True) -> dict:
    """Roda o diagnóstico da IA, grava em `analyses` e (CLI) em output/{name}_diagnosis.json."""
    _emit(on_progress, "ai", 0, 1, "[main] Running AI diagnosis...")
    silman_concepts = load_silman_concepts()
    diagnosis = diagnose(profile, silman_concepts)

    with AppStore() as store:
        store.save_diagnosis(name, diagnosis)
    if export_json:
        diagnosis_path = f"{OUTPUT_DIR}/{name}_diagnosis.json"
        with open(diagnosis_path, "w", encoding="utf-8") as f:
            json.dump(diagnosis, f, indent=2, ensure_ascii=False)

    # Console summary only — best-effort. The diagnosis is already persisted above,
    # so a missing/odd field here must never abort the pipeline.
    # Accepts bilingual {"en":{}, "pt":{}} or a legacy flat dict.
    _d = diagnosis.get("en") or diagnosis.get("pt") or diagnosis
    rc = (_d.get("root_cause") or {}) if isinstance(_d, dict) else {}
    print(f"\n=== DIAGNÓSTICO FINAL ===")
    print(f"Causa raiz: {rc.get('name', '(n/d)')}")
    print(f"Confiança: {_d.get('confidence', '(n/d)') if isinstance(_d, dict) else '(n/d)'}")
    _emit(on_progress, "done", 1, 1, "Analysis complete.")
    return diagnosis


def run_diagnosis(name: str, on_progress=None, export_json: bool = False) -> dict:
    """
    Carrega o perfil `name` do banco (AppStore) e roda apenas o diagnóstico da IA.

    Usado pela UI para a segunda fase (progressiva): o perfil já foi construído e
    exibido; esta chamada cobre só a espera pela API da Anthropic. Cai para
    output/{name}_profile.json se o perfil não estiver no banco.
    """
    with AppStore() as store:
        record = store.get_analysis(name)
    if record is not None:
        profile = record["profile"]
    else:
        profile = load_profile(f"{OUTPUT_DIR}/{name}_profile.json")
    return _diagnose_and_save(profile, name, on_progress, export_json=export_json)


def analyze_profile(pgn_path: str, player_name: str, player_color: bool = chess.WHITE,
                    on_progress=None, depth: int = STOCKFISH_DEPTH,
                    subject: str | None = None, export_json: bool = True,
                    owner_id: int | None = None) -> dict:
    """
    Constrói (e salva) apenas o perfil de fraquezas a partir de um arquivo PGN,
    sem rodar o diagnóstico da IA. Retorna o profile_dict.

    player_name: chave única da análise; subject: nome exibido (default: player_name);
    owner_id: id da conta dona da análise (None = sem dono, ex.: CLI).
    """
    print(f"\n=== Iniciando análise de {player_name} (depth {depth}) ===\n")

    _emit(on_progress, "load", 0, 1, "Loading PGN file...")
    games = load_games_from_file(pgn_path)
    _emit(on_progress, "load", 1, 1, f"{len(games)} games loaded")

    game_color_pairs = [(game, player_color) for game in games]
    games_data = _process_games(game_color_pairs, on_progress, depth=depth)
    return _build_profile_phase(games_data, player_name, "pgn", on_progress, depth=depth,
                                subject=subject, n_games=len(games),
                                export_json=export_json, owner_id=owner_id)


def analyze_profile_from_username(username: str, n_games: int = 50, on_progress=None,
                                  profile_name: str | None = None,
                                  depth: int = STOCKFISH_DEPTH,
                                  export_json: bool = True,
                                  owner_id: int | None = None) -> dict:
    """
    Constrói (e salva) apenas o perfil de fraquezas a partir de um username do
    Chess.com, sem rodar o diagnóstico da IA. Retorna o profile_dict.

    profile_name: nome usado para salvar o perfil (default: username). Permite à UI
    prefixar o perfil com o dono (namespacing por pessoa) sem afetar a busca.
    depth: profundidade UCI da validação Stockfish.
    owner_id: id da conta dona da análise (None = sem dono, ex.: CLI).
    """
    print(f"\n=== Iniciando análise de {username} via Chess.com API (depth {depth}) ===\n")

    _emit(on_progress, "fetch", 0, 1, f"Fetching last {n_games} games from Chess.com...")
    game_color_pairs = fetch_recent_games(username, n_games=n_games)
    _emit(on_progress, "fetch", 1, 1, f"{len(game_color_pairs)} games loaded from Chess.com")

    games_data = _process_games(game_color_pairs, on_progress, depth=depth)
    return _build_profile_phase(games_data, profile_name or username, "chess_com",
                                on_progress, depth=depth, subject=username,
                                n_games=len(game_color_pairs), export_json=export_json,
                                owner_id=owner_id)


def analyze_player(pgn_path: str, player_name: str, player_color: bool = chess.WHITE,
                   on_progress=None, depth: int = STOCKFISH_DEPTH, owner_id: int | None = None):
    """
    Pipeline completo de análise de um jogador a partir de um arquivo PGN.

    pgn_path: caminho para o arquivo PGN com as partidas
    player_name: nome do jogador (para identificação e nome dos arquivos de saída)
    player_color: chess.WHITE ou chess.BLACK
    on_progress: optional callback(stage, current, total, message)
    depth: profundidade UCI da validação Stockfish.
    Salva output/{player_name}_profile.json e output/{player_name}_diagnosis.json.
    """
    profile = analyze_profile(pgn_path, player_name, player_color, on_progress, depth=depth,
                              owner_id=owner_id)
    diagnosis = _diagnose_and_save(profile, player_name, on_progress)
    print(f"\nArquivos salvos em '{OUTPUT_DIR}/'")
    return profile, diagnosis


def analyze_player_from_username(username: str, n_games: int = 50, on_progress=None,
                                 depth: int = STOCKFISH_DEPTH, owner_id: int | None = None):
    """
    Pipeline completo de análise a partir de um username do Chess.com.

    Busca automaticamente os jogos mais recentes via API pública do Chess.com,
    detecta a cor do jogador em cada partida, e executa o pipeline completo.

    username: nome de usuário no Chess.com
    n_games: quantas partidas recentes buscar (padrão: 50)
    on_progress: optional callback(stage, current, total, message)
    depth: profundidade UCI da validação Stockfish.
    """
    profile = analyze_profile_from_username(username, n_games, on_progress, depth=depth,
                                            owner_id=owner_id)
    diagnosis = _diagnose_and_save(profile, username, on_progress)
    print(f"\nArquivos salvos em '{OUTPUT_DIR}/'")
    return profile, diagnosis


def _main(argv=None):
    parser = argparse.ArgumentParser(description="Chess Strategic Profiler")
    parser.add_argument("--user", required=True, help="Chess.com username to analyze")
    parser.add_argument("--games", type=int, default=50, help="Number of recent games to fetch (default: 50)")
    parser.add_argument("--pgn", help="Path to a local PGN file (overrides --user)")
    parser.add_argument("--color", choices=["white", "black"], default="white",
                        help="Player color when using --pgn (default: white)")
    parser.add_argument("--depth", type=int, default=STOCKFISH_DEPTH,
                        help=f"Stockfish search depth (default: {STOCKFISH_DEPTH})")
    parser.add_argument("--owner", help="Account (login) that will own the analysis in the web UI. "
                                        "Without it, the admin account claims it on next login.")
    args = parser.parse_args(argv)

    owner_id = None
    if args.owner:
        with AppStore() as store:
            owner = store.get_user_by_username(args.owner)
        if owner is None:
            parser.error(f"unknown account: {args.owner!r} (create it with: python manage.py create-user)")
        owner_id = owner["id"]

    if args.pgn:
        analyze_player(
            pgn_path=args.pgn,
            player_name=args.user,
            player_color=chess.WHITE if args.color == "white" else chess.BLACK,
            depth=args.depth,
            owner_id=owner_id,
        )
    else:
        analyze_player_from_username(username=args.user, n_games=args.games, depth=args.depth,
                                     owner_id=owner_id)


if __name__ == "__main__":
    _main()
