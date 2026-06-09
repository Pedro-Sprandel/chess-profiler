import chess
import chess.engine
from config import (
    STOCKFISH_PATH,
    STOCKFISH_DEPTH,
    ERROR_THRESHOLD_CP,
    MATE_SCORE,
    TACTICAL_THRESHOLD_CP,
    validate_stockfish_path,
)

# Optional cache — imported lazily to avoid circular imports
_db = None

def _get_db():
    global _db
    if _db is None:
        try:
            from modules.db import Database
            _db = Database()
        except Exception:
            pass
    return _db


def open_engine() -> chess.engine.SimpleEngine:
    """
    Opens and returns a Stockfish engine instance. Caller is responsible for closing it.
    Valida o caminho do binário antes de abrir, dando erro claro se ausente.
    """
    validate_stockfish_path()
    return chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)


def evaluate_fen(fen: str, depth: int = STOCKFISH_DEPTH, use_cache: bool = True) -> dict:
    """
    Recebe uma posição FEN e retorna a avaliação numérica do Stockfish.

    Retorna dicionário com:
    - score_cp: avaliação em centipawns do ponto de vista das brancas
                (positivo = vantagem brancas, negativo = vantagem pretas)
    - score_side: avaliação em centipawns do ponto de vista do lado que vai jogar
    - is_mate: True se a posição é mate em N lances
    - mate_in: número de lances até o mate (None se não for mate)
    - best_move: melhor lance em notação UCI
    - depth: profundidade usada na análise
    - turn: 'white' ou 'black'
    """
    board = chess.Board(fen)

    # Check cache first
    if use_cache:
        db = _get_db()
        if db:
            cached = db.get_cached_eval(fen, depth)
            if cached:
                score_cp = cached["score_cp"]
                return {
                    "score_cp": score_cp,
                    "score_side": score_cp if board.turn == chess.WHITE else -score_cp,
                    "is_mate": abs(score_cp) >= MATE_SCORE,
                    "mate_in": None,
                    "best_move": cached["best_move"],
                    "depth": depth,
                    "turn": "white" if board.turn == chess.WHITE else "black",
                    "fen": fen,
                    "from_cache": True,
                }

    engine = open_engine()

    try:
        info = engine.analyse(board, chess.engine.Limit(depth=depth))
        score = info["score"]
        best_move = info["pv"][0] if "pv" in info and info["pv"] else None

        is_mate = score.is_mate()
        mate_in = score.white().mate() if is_mate else None
        score_cp = score.white().score(mate_score=MATE_SCORE)
        score_side = score.relative.score(mate_score=MATE_SCORE)
        best_move_uci = best_move.uci() if best_move else None

        # Store in cache
        if use_cache:
            db = _get_db()
            if db:
                db.cache_eval(fen, depth, score_cp, best_move_uci)

        return {
            "score_cp": score_cp,
            "score_side": score_side,
            "is_mate": is_mate,
            "mate_in": mate_in,
            "best_move": best_move_uci,
            "depth": depth,
            "turn": "white" if board.turn == chess.WHITE else "black",
            "fen": fen,
            "from_cache": False,
        }
    finally:
        engine.quit()


def validate_move(board_before: chess.Board, move_played: chess.Move) -> dict:
    """
    Usa o Stockfish para validar se o lance jogado foi um erro.

    Compara a avaliação ANTES do lance (melhor lance possível) com a avaliação
    DEPOIS do lance jogado. Se a diferença superar ERROR_THRESHOLD_CP, é um erro.

    Retorna dicionário com:
    - is_error: bool
    - eval_before: centipawns antes (melhor lance)
    - eval_after: centipawns depois (lance jogado)
    - error_magnitude: diferença em centipawns
    - best_move: melhor lance segundo Stockfish
    """
    engine = open_engine()

    try:
        info_before = engine.analyse(board_before, chess.engine.Limit(depth=STOCKFISH_DEPTH))
        score_before = info_before["score"].white().score(mate_score=MATE_SCORE)
        best_move = info_before["pv"][0] if "pv" in info_before else None

        board_after = board_before.copy()
        board_after.push(move_played)
        info_after = engine.analyse(board_after, chess.engine.Limit(depth=STOCKFISH_DEPTH))
        score_after = info_after["score"].white().score(mate_score=MATE_SCORE)

        if board_before.turn == chess.BLACK:
            error_magnitude = score_after - score_before
        else:
            error_magnitude = score_before - score_after

        played_best = best_move is not None and move_played == best_move
        involves_mate = abs(score_before) >= TACTICAL_THRESHOLD_CP or abs(score_after) >= TACTICAL_THRESHOLD_CP

        return {
            "is_error": not played_best and error_magnitude > ERROR_THRESHOLD_CP,
            "eval_before": score_before,
            "eval_after": score_after,
            "error_magnitude": error_magnitude,
            "involves_mate": involves_mate,
            "best_move": best_move.uci() if best_move else None,
        }

    finally:
        engine.quit()


def batch_validate(positions: list, engine: chess.engine.SimpleEngine = None) -> list:
    """
    Valida múltiplas posições reutilizando a mesma instância do Stockfish.
    Verifica o cache SQLite antes de chamar o Stockfish — posições já analisadas
    são resolvidas sem abrir o engine.

    positions: lista de (board_before, move_played)
    engine: instância existente do Stockfish (se None, cria e fecha uma nova)
    Retorna lista de dicts com resultados.
    """
    db = _get_db()

    # Pre-resolve from cache; track which indices still need Stockfish
    results = [None] * len(positions)
    needs_engine = []

    for i, (board_before, move_played) in enumerate(positions):
        fen_before = board_before.fen()
        board_after = board_before.copy()
        board_after.push(move_played)
        fen_after = board_after.fen()

        cb = db.get_cached_eval(fen_before, STOCKFISH_DEPTH) if db else None
        ca = db.get_cached_eval(fen_after,  STOCKFISH_DEPTH) if db else None

        if cb and ca:
            score_before   = cb["score_cp"]
            score_after    = ca["score_cp"]
            best_move_uci  = cb["best_move"]
            best_move_obj  = chess.Move.from_uci(best_move_uci) if best_move_uci else None
            if board_before.turn == chess.BLACK:
                error_magnitude = score_after - score_before
            else:
                error_magnitude = score_before - score_after
            played_best = best_move_obj is not None and move_played == best_move_obj
            involves_mate = abs(score_before) >= TACTICAL_THRESHOLD_CP or abs(score_after) >= TACTICAL_THRESHOLD_CP
            results[i] = {
                "is_error": not played_best and error_magnitude > ERROR_THRESHOLD_CP,
                "eval_before": score_before,
                "eval_after":  score_after,
                "error_magnitude": error_magnitude,
                "involves_mate": involves_mate,
                "best_move": best_move_uci,
            }
        else:
            needs_engine.append(i)

    if not needs_engine:
        return results

    # Open engine only if at least one position is uncached
    owns_engine = engine is None
    if owns_engine:
        engine = open_engine()

    try:
        for i in needs_engine:
            board_before, move_played = positions[i]
            fen_before = board_before.fen()

            info_before   = engine.analyse(board_before, chess.engine.Limit(depth=STOCKFISH_DEPTH))
            score_before  = info_before["score"].white().score(mate_score=MATE_SCORE)
            best_move_obj = info_before["pv"][0] if "pv" in info_before else None
            best_move_uci = best_move_obj.uci() if best_move_obj else None

            board_after = board_before.copy()
            board_after.push(move_played)
            fen_after    = board_after.fen()
            info_after   = engine.analyse(board_after, chess.engine.Limit(depth=STOCKFISH_DEPTH))
            score_after  = info_after["score"].white().score(mate_score=MATE_SCORE)

            if db:
                db.cache_eval(fen_before, STOCKFISH_DEPTH, score_before, best_move_uci)
                db.cache_eval(fen_after,  STOCKFISH_DEPTH, score_after,  None)

            if board_before.turn == chess.BLACK:
                error_magnitude = score_after - score_before
            else:
                error_magnitude = score_before - score_after

            played_best = best_move_obj is not None and move_played == best_move_obj
            involves_mate = abs(score_before) >= TACTICAL_THRESHOLD_CP or abs(score_after) >= TACTICAL_THRESHOLD_CP
            results[i] = {
                "is_error": not played_best and error_magnitude > ERROR_THRESHOLD_CP,
                "eval_before": score_before,
                "eval_after":  score_after,
                "error_magnitude": error_magnitude,
                "involves_mate": involves_mate,
                "best_move": best_move_uci,
            }
    finally:
        if owns_engine:
            engine.quit()

    return results
