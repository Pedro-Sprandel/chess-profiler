import chess
import chess.engine
from config import (
    STOCKFISH_PATH,
    STOCKFISH_DEPTH,
    ERROR_THRESHOLD_CP,
    MATE_SCORE,
    TACTICAL_THRESHOLD_CP,
    DECISIVE_THRESHOLD_CP,
    validate_stockfish_path,
)

_PIECE_VALUE = {
    chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
    chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0,
}


def _is_winning_capture(board: chess.Board, move: chess.Move) -> bool:
    """True if `move` captures a piece worth at least a minor (≥2) more than the capturer.

    A clearly material-winning capture (e.g. pawn takes bishop) that the engine only
    rates as a small inaccuracy is almost always a shallow-search artifact: the player
    recovered material, so it shouldn't be flagged as an error.
    """
    if not board.is_capture(move):
        return False
    if board.is_en_passant(move):
        captured = chess.PAWN
    else:
        cap = board.piece_at(move.to_square)
        captured = cap.piece_type if cap else None
    mover = board.piece_at(move.from_square)
    if captured is None or mover is None:
        return False
    return _PIECE_VALUE[captured] - _PIECE_VALUE[mover.piece_type] >= 2


def _classify(board_before: chess.Board, move_played: chess.Move,
              score_before: int, score_after: int, best_move_obj) -> dict:
    """Build a validation result dict from white-POV scores, applying the error guards.

    Centralizes the logic shared by validate_move and both branches of batch_validate.
    """
    if board_before.turn == chess.BLACK:
        error_magnitude = score_after - score_before
        player_before, player_after = -score_before, -score_after
    else:
        error_magnitude = score_before - score_after
        player_before, player_after = score_before, score_after

    played_best = best_move_obj is not None and move_played == best_move_obj
    involves_mate = abs(score_before) >= TACTICAL_THRESHOLD_CP or abs(score_after) >= TACTICAL_THRESHOLD_CP

    # Guard 1: position already decided — same side winning big before AND after the
    # move. Swings inside a settled position aren't instructive (and at low depth are
    # mostly noise).
    already_decided = (
        (player_before >= DECISIVE_THRESHOLD_CP and player_after >= DECISIVE_THRESHOLD_CP)
        or (player_before <= -DECISIVE_THRESHOLD_CP and player_after <= -DECISIVE_THRESHOLD_CP)
    )
    # Guard 2: the played move recovers material (clearly winning capture). Flagging a
    # piece-winning recapture as an error is a shallow-search false positive.
    recovers_material = _is_winning_capture(board_before, move_played)

    is_error = (
        not played_best
        and error_magnitude > ERROR_THRESHOLD_CP
        and not already_decided
        and not recovers_material
    )

    return {
        "is_error": is_error,
        "eval_before": score_before,
        "eval_after": score_after,
        "error_magnitude": error_magnitude,
        "involves_mate": involves_mate,
        "best_move": best_move_obj.uci() if best_move_obj else None,
    }

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


def validate_move(board_before: chess.Board, move_played: chess.Move,
                  depth: int = STOCKFISH_DEPTH) -> dict:
    """
    Usa o Stockfish para validar se o lance jogado foi um erro.

    Compara a avaliação ANTES do lance (melhor lance possível) com a avaliação
    DEPOIS do lance jogado. Se a diferença superar ERROR_THRESHOLD_CP — e os guardas
    de _classify não a descartarem — é um erro.

    Retorna dicionário com:
    - is_error: bool
    - eval_before: centipawns antes (melhor lance)
    - eval_after: centipawns depois (lance jogado)
    - error_magnitude: diferença em centipawns
    - best_move: melhor lance segundo Stockfish
    """
    engine = open_engine()

    try:
        info_before = engine.analyse(board_before, chess.engine.Limit(depth=depth))
        score_before = info_before["score"].white().score(mate_score=MATE_SCORE)
        best_move = info_before["pv"][0] if "pv" in info_before and info_before["pv"] else None

        board_after = board_before.copy()
        board_after.push(move_played)
        info_after = engine.analyse(board_after, chess.engine.Limit(depth=depth))
        score_after = info_after["score"].white().score(mate_score=MATE_SCORE)

        return _classify(board_before, move_played, score_before, score_after, best_move)

    finally:
        engine.quit()


def batch_validate(positions: list, engine: chess.engine.SimpleEngine = None,
                   depth: int = STOCKFISH_DEPTH) -> list:
    """
    Valida múltiplas posições reutilizando a mesma instância do Stockfish.
    Verifica o cache SQLite antes de chamar o Stockfish — posições já analisadas
    são resolvidas sem abrir o engine.

    positions: lista de (board_before, move_played)
    engine: instância existente do Stockfish (se None, cria e fecha uma nova)
    depth: profundidade UCI (default STOCKFISH_DEPTH). O cache é por (fen, depth).
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

        cb = db.get_cached_eval(fen_before, depth) if db else None
        ca = db.get_cached_eval(fen_after,  depth) if db else None

        if cb and ca:
            best_move_uci = cb["best_move"]
            best_move_obj = chess.Move.from_uci(best_move_uci) if best_move_uci else None
            results[i] = _classify(board_before, move_played,
                                   cb["score_cp"], ca["score_cp"], best_move_obj)
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

            info_before   = engine.analyse(board_before, chess.engine.Limit(depth=depth))
            score_before  = info_before["score"].white().score(mate_score=MATE_SCORE)
            best_move_obj = info_before["pv"][0] if "pv" in info_before and info_before["pv"] else None
            best_move_uci = best_move_obj.uci() if best_move_obj else None

            board_after = board_before.copy()
            board_after.push(move_played)
            fen_after    = board_after.fen()
            info_after   = engine.analyse(board_after, chess.engine.Limit(depth=depth))
            score_after  = info_after["score"].white().score(mate_score=MATE_SCORE)

            if db:
                db.cache_eval(fen_before, depth, score_before, best_move_uci)
                db.cache_eval(fen_after,  depth, score_after,  None)

            results[i] = _classify(board_before, move_played,
                                   score_before, score_after, best_move_obj)
    finally:
        if owns_engine:
            engine.quit()

    return results
