import math

import chess
import chess.engine
from config import (
    STOCKFISH_PATH,
    STOCKFISH_DEPTH,
    STOCKFISH_CONFIRM_DEPTH,
    ERROR_THRESHOLD_CP,
    WINP_ERROR_THRESHOLD,
    MATE_SCORE,
    TACTICAL_THRESHOLD_CP,
    validate_stockfish_path,
)

# Se o lance jogado era a segunda melhor opção do engine com gap menor que isto,
# a posição era "difícil", não um erro instrutivo (usado na passada de confirmação).
_SECOND_BEST_GAP_CP = 50

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


def _cp_to_winp(cp: int) -> float:
    """Converte centipawns em probabilidade de vitória (modelo do Lichess).

    WinP = 1/(1+e^(-0.00368*cp)). Normaliza o significado de um swing de avaliação:
    100cp perto da igualdade mudam muito a probabilidade de vitória; 100cp quando
    já se está +5 não mudam quase nada.
    """
    return 1.0 / (1.0 + math.exp(-0.00368208 * cp))


def _classify(board_before: chess.Board, move_played: chess.Move,
              score_before: int, score_after: int, best_move_obj) -> dict:
    """Build a validation result dict from white-POV scores, applying the error guards.

    Centralizes the logic shared by validate_move and both passes of batch_validate.
    """
    if board_before.turn == chess.BLACK:
        error_magnitude = score_after - score_before
        player_before, player_after = -score_before, -score_after
    else:
        error_magnitude = score_before - score_after
        player_before, player_after = score_before, score_after

    played_best = best_move_obj is not None and move_played == best_move_obj
    involves_mate = abs(score_before) >= TACTICAL_THRESHOLD_CP or abs(score_after) >= TACTICAL_THRESHOLD_CP

    # Guard 1: o erro precisa reduzir a probabilidade de vitória do jogador de forma
    # relevante. Substitui o antigo guard de "posição já decidida": um swing de cp
    # dentro de uma posição ganha/perdida quase não muda a WinP e é descartado.
    delta_winp = _cp_to_winp(player_before) - _cp_to_winp(player_after)

    # Guard 2: the played move recovers material (clearly winning capture). Flagging a
    # piece-winning recapture as an error is a shallow-search false positive.
    recovers_material = _is_winning_capture(board_before, move_played)

    is_error = (
        not played_best
        and error_magnitude > ERROR_THRESHOLD_CP
        and delta_winp > WINP_ERROR_THRESHOLD
        and not recovers_material
    )

    return {
        "is_error": is_error,
        "eval_before": score_before,
        "eval_after": score_after,
        "error_magnitude": error_magnitude,
        "delta_winp": round(delta_winp, 3),
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


def _analyse(board: chess.Board, depth: int, get_engine, db, multipv: int = 1) -> dict:
    """
    Analisa uma posição resolvendo pelo cache SQLite quando possível.

    get_engine: callable que retorna (abrindo se necessário) a instância do engine —
    assim o engine só é aberto se alguma posição não estiver em cache.

    Retorna {"score_cp" (POV brancas), "best_move" (Move|None),
             "second_move" (Move|None), "second_score_cp" (int|None)}.
    O cache guarda só a linha principal; num cache hit a segunda linha vem vazia.
    """
    fen = board.fen()
    if db:
        cached = db.get_cached_eval(fen, depth)
        if cached:
            bm = chess.Move.from_uci(cached["best_move"]) if cached["best_move"] else None
            return {"score_cp": cached["score_cp"], "best_move": bm,
                    "second_move": None, "second_score_cp": None}

    engine = get_engine()
    limit = chess.engine.Limit(depth=depth)
    if multipv > 1:
        info = engine.analyse(board, limit, multipv=multipv)
    else:
        info = engine.analyse(board, limit)
    infos = info if isinstance(info, list) else [info]

    main = infos[0]
    score_cp = main["score"].white().score(mate_score=MATE_SCORE)
    best_move = main["pv"][0] if main.get("pv") else None

    second_move = second_score_cp = None
    if len(infos) > 1 and infos[1].get("pv"):
        second_move = infos[1]["pv"][0]
        second_score_cp = infos[1]["score"].white().score(mate_score=MATE_SCORE)

    if db:
        db.cache_eval(fen, depth, score_cp, best_move.uci() if best_move else None)

    return {"score_cp": score_cp, "best_move": best_move,
            "second_move": second_move, "second_score_cp": second_score_cp}


def batch_validate(positions: list, engine: chess.engine.SimpleEngine = None,
                   depth: int = STOCKFISH_DEPTH, confirm_depth: int | None = None) -> list:
    """
    Valida múltiplas posições reutilizando a mesma instância do Stockfish, em
    duas passadas:

      1. Triagem em `depth`: classifica todos os lances (barato).
      2. Confirmação em `confirm_depth` (default STOCKFISH_CONFIRM_DEPTH): apenas
         os lances flagados como erro são re-analisados em profundidade maior.
         Erros que a busca profunda não confirma são descartados (falsos positivos
         de horizonte). A confirmação também usa MultiPV=2: se o lance jogado era
         a segunda melhor opção com gap pequeno, a posição era difícil — não erro.

    Verifica o cache SQLite antes de chamar o Stockfish em ambas as passadas
    (cache por (fen, depth)).

    positions: lista de (board_before, move_played)
    engine: instância existente do Stockfish (se None, cria e fecha a própria)
    Retorna lista de dicts com resultados (formato de _classify).
    """
    if confirm_depth is None:
        confirm_depth = STOCKFISH_CONFIRM_DEPTH

    db = _get_db()
    results = [None] * len(positions)
    owns_engine = engine is None
    eng = engine

    def get_engine():
        nonlocal eng
        if eng is None:
            eng = open_engine()
        return eng

    try:
        # ── Passada 1: triagem em `depth` ────────────────────────────────────
        for i, (board_before, move_played) in enumerate(positions):
            board_after = board_before.copy()
            board_after.push(move_played)

            before = _analyse(board_before, depth, get_engine, db)
            after  = _analyse(board_after,  depth, get_engine, db)
            results[i] = _classify(board_before, move_played,
                                   before["score_cp"], after["score_cp"],
                                   before["best_move"])

        # ── Passada 2: confirmação dos erros em `confirm_depth` ─────────────
        if confirm_depth > depth:
            for i, screened in enumerate(results):
                if not screened["is_error"]:
                    continue
                board_before, move_played = positions[i]
                board_after = board_before.copy()
                board_after.push(move_played)

                before = _analyse(board_before, confirm_depth, get_engine, db, multipv=2)
                after  = _analyse(board_after,  confirm_depth, get_engine, db)
                confirmed = _classify(board_before, move_played,
                                      before["score_cp"], after["score_cp"],
                                      before["best_move"])

                # Lance jogado era a 2ª melhor opção com gap pequeno → posição
                # difícil, não um erro instrutivo.
                if (confirmed["is_error"]
                        and before["second_move"] == move_played
                        and before["second_score_cp"] is not None
                        and abs(before["score_cp"] - before["second_score_cp"]) <= _SECOND_BEST_GAP_CP):
                    confirmed["is_error"] = False

                results[i] = confirmed
    finally:
        if owns_engine and eng is not None:
            eng.quit()

    return results
