"""
eval_fen.py — Avalia uma posição FEN com o Stockfish e retorna a avaliação numérica.

Uso:
    python eval_fen.py "<FEN>"
    python eval_fen.py "<FEN>" --depth 15
    python eval_fen.py "<FEN>" --json

Exemplos:
    python eval_fen.py "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    python eval_fen.py "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4" --depth 15
"""

import argparse
import json
import sys
from modules.stockfish_validator import evaluate_fen


def format_score(result: dict) -> str:
    if result["is_mate"]:
        m = result["mate_in"]
        if m is None:
            return "Mate (unknown side)"
        side = "White" if m > 0 else "Black"
        return f"Mate in {abs(m)} ({side} wins)"

    cp = result["score_cp"]
    side_cp = result["score_side"]
    turn = result["turn"].capitalize()

    pawns = cp / 100
    side_pawns = side_cp / 100

    sign = "+" if pawns >= 0 else ""
    side_sign = "+" if side_pawns >= 0 else ""

    return (
        f"Score (white's perspective): {sign}{pawns:.2f} pawns ({cp:+d} cp)\n"
        f"Score ({turn} to move):       {side_sign}{side_pawns:.2f} pawns ({side_cp:+d} cp)\n"
        f"Best move:                    {result['best_move']}\n"
        f"Depth:                        {result['depth']}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a chess position using Stockfish."
    )
    parser.add_argument("fen", help="FEN string of the position to evaluate")
    parser.add_argument(
        "--depth", type=int, default=None,
        help="Analysis depth (default: STOCKFISH_DEPTH from config.py)"
    )
    parser.add_argument(
        "--json", action="store_true", dest="output_json",
        help="Output raw JSON instead of formatted text"
    )
    args = parser.parse_args()

    kwargs = {}
    if args.depth is not None:
        kwargs["depth"] = args.depth

    try:
        result = evaluate_fen(args.fen, **kwargs)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\nFEN: {args.fen}\n")
        print(format_score(result))
        print()


if __name__ == "__main__":
    main()
