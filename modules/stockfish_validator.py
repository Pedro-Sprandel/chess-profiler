import chess
import chess.engine
from config import STOCKFISH_PATH, STOCKFISH_DEPTH, ERROR_THRESHOLD_CP


def open_engine() -> chess.engine.SimpleEngine:
    """Opens and returns a Stockfish engine instance. Caller is responsible for closing it."""
    return chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)


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
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

    try:
        info_before = engine.analyse(board_before, chess.engine.Limit(depth=STOCKFISH_DEPTH))
        score_before = info_before["score"].white().score(mate_score=10000)
        best_move = info_before["pv"][0] if "pv" in info_before else None

        board_after = board_before.copy()
        board_after.push(move_played)
        info_after = engine.analyse(board_after, chess.engine.Limit(depth=STOCKFISH_DEPTH))
        score_after = info_after["score"].white().score(mate_score=10000)

        if board_before.turn == chess.BLACK:
            error_magnitude = score_after - score_before
        else:
            error_magnitude = score_before - score_after

        is_error = error_magnitude > ERROR_THRESHOLD_CP

        return {
            "is_error": is_error,
            "eval_before": score_before,
            "eval_after": score_after,
            "error_magnitude": error_magnitude,
            "best_move": best_move.uci() if best_move else None
        }

    finally:
        engine.quit()


def batch_validate(positions: list, engine: chess.engine.SimpleEngine = None) -> list:
    """
    Valida múltiplas posições reutilizando a mesma instância do Stockfish.
    positions: lista de (board_before, move_played)
    engine: instância existente do Stockfish (se None, cria e fecha uma nova)
    Retorna lista de dicts com resultados.
    """
    owns_engine = engine is None
    if owns_engine:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

    results = []
    try:
        for board_before, move_played in positions:
            info_before = engine.analyse(board_before, chess.engine.Limit(depth=STOCKFISH_DEPTH))
            score_before = info_before["score"].white().score(mate_score=10000)
            best_move = info_before["pv"][0] if "pv" in info_before else None

            board_after = board_before.copy()
            board_after.push(move_played)
            info_after = engine.analyse(board_after, chess.engine.Limit(depth=STOCKFISH_DEPTH))
            score_after = info_after["score"].white().score(mate_score=10000)

            if board_before.turn == chess.BLACK:
                error_magnitude = score_after - score_before
            else:
                error_magnitude = score_before - score_after

            # If the player played Stockfish's own best move it cannot be an error,
            # regardless of centipawn difference between the two independent analyses
            # (which can diverge due to the horizon effect at fixed depth).
            played_best = best_move is not None and move_played == best_move

            results.append({
                "is_error": not played_best and error_magnitude > ERROR_THRESHOLD_CP,
                "eval_before": score_before,
                "eval_after": score_after,
                "error_magnitude": error_magnitude,
                "best_move": best_move.uci() if best_move else None
            })

    finally:
        if owns_engine:
            engine.quit()

    return results
