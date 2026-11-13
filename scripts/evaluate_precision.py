"""Mede a precisão da atribuição erro → conceito no conjunto de referência.

Usa data/gold_attributions.json (ver scripts/build_gold_set.py): 183 posições reais de
erro com o conceito atribuído pelo pipeline antigo, 38 delas com veredito humano
(coerente / parcial / falso positivo). Para cada posição, recalcula as linhas do
Stockfish (melhor lance do dataset + continuação; refutação do lance jogado) e roda a
atribuição atual (modules/attribution.py).

Métricas sobre os vereditos:
  - coerentes mantidos: o conceito julgado coerente continua sendo o atribuído;
  - falsos positivos removidos: o conceito julgado errado deixou de ser atribuído;
  - parciais: quantos continuam com o mesmo conceito (informativo).

    python scripts/evaluate_precision.py                # depth 16, cache SQLite local
    python scripts/evaluate_precision.py --depth 12 --details
    python scripts/evaluate_precision.py --baseline data/gold_baseline.json

Requer Stockfish (STOCKFISH_PATH).
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import chess

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import PV_PLIES, STOCKFISH_CONFIRM_DEPTH  # noqa: E402
from modules.attribution import attribute_error  # noqa: E402
from modules.position_analyzer import detect_concepts  # noqa: E402
from modules.stockfish_validator import _analyse, _get_db, open_engine  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "gold_attributions.json"


def engine_lines(board, played, best, depth, get_engine, db):
    after_best = board.copy(stack=False)
    after_best.push(best)
    after_played = board.copy(stack=False)
    after_played.push(played)
    cont = _analyse(after_best, depth, get_engine, db, need_pv=True)["pv"]
    refutation = _analyse(after_played, depth, get_engine, db, need_pv=True)["pv"]
    return ([best.uci()] + [m.uci() for m in cont])[:PV_PLIES], [m.uci() for m in refutation]


def evaluate(depth: int) -> list[dict]:
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    db = _get_db()
    engine = None

    def get_engine():
        nonlocal engine
        if engine is None:
            engine = open_engine()
        return engine

    results = []
    try:
        for e in gold["positions"]:
            board = chess.Board(e["fen"])
            color = e["player_color"] == "white"
            played = chess.Move.from_uci(e["move_played"])
            best = chess.Move.from_uci(e["best_move"])
            best_line, refutation = engine_lines(board, played, best, depth, get_engine, db)
            validation = {"best_move": e["best_move"], "best_line": best_line,
                          "refutation_line": refutation}
            attribution = attribute_error(board, e["move_played"], validation,
                                          detect_concepts(board, color), color)
            results.append({**e, "new": attribution})
    finally:
        if engine is not None:
            engine.quit()
    return results


def report(results: list[dict], baseline: dict | None, details: bool) -> str:
    lines = []
    old_new = Counter()
    for r in results:
        new = r["new"]["concept"] or "—"
        for old in r["old_concepts"]:
            old_new[(old, new)] += 1
    lines.append(f"Posições: {len(results)}")
    lines.append("Novo conceito atribuído:")
    for concept, n in Counter((r["new"]["concept"] or "— sem conceito") for r in results).most_common():
        lines.append(f"  {concept:<22} {n}")
    lines.append("Motivo da decisão:")
    for motif, n in Counter((r["new"]["motif"] or "—") for r in results).most_common():
        lines.append(f"  {motif:<22} {n}")

    judged = [(r, c, v) for r in results for c, v in r["verdicts"].items()]
    by = Counter()
    for r, concept, v in judged:
        kept = r["new"]["concept"] == concept
        by[(v["verdict"], kept)] += 1
    coh = by[("coherent", True)], by[("coherent", True)] + by[("coherent", False)]
    fp = by[("false_positive", False)], by[("false_positive", True)] + by[("false_positive", False)]
    part = by[("partial", True)], by[("partial", True)] + by[("partial", False)]
    lines.append("")
    lines.append(f"Vereditos humanos: {len(judged)}")
    lines.append(f"  coerentes mantidos:        {coh[0]}/{coh[1]}")
    lines.append(f"  falsos positivos removidos: {fp[0]}/{fp[1]}")
    lines.append(f"  parciais mantidos:          {part[0]}/{part[1]}")
    # Precisão estimada da amostra julgada: entre as atribuições que continuam, quantas
    # são coerentes (parcial conta meio).
    kept = [(v["verdict"]) for r, c, v in judged if r["new"]["concept"] == c]
    if kept:
        score = sum({"coherent": 1, "partial": 0.5, "false_positive": 0}[v] for v in kept)
        lines.append(f"  precisão das atribuições mantidas: {score / len(kept):.0%} "
                     f"({len(kept)} atribuições)")

    if baseline:
        base = {(b["fen"], b["move_played"]): b["concepts"] for b in baseline["positions"]}
        multi = sum(1 for b in base.values() if len(b) > 1)
        lines.append("")
        lines.append(f"Linha de base ({baseline.get('code', '?')}): {multi} posições com 2+ conceitos; "
                     f"{sum(1 for b in base.values() if not b)} sem conceito")
        bk = Counter()
        for r, concept, v in judged:
            bk[(v["verdict"], concept in base.get((r["fen"], r["move_played"]), []))] += 1
        lines.append(f"  base — coerentes mantidos {bk[('coherent', True)]}, "
                     f"falsos positivos ainda presentes {bk[('false_positive', True)]}, "
                     f"parciais mantidos {bk[('partial', True)]}")

    if details:
        lines.append("")
        lines.append("Detalhe dos vereditos:")
        for r, concept, v in judged:
            mark = "=" if r["new"]["concept"] == concept else "→"
            lines.append(f"  [{v['verdict'][:5]}] {r['profile']} g{r['game']} {r['played_san']} → {r['best_san']}: "
                         f"{concept} {mark} {r['new']['concept']} ({r['new']['motif']})")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--depth", type=int, default=STOCKFISH_CONFIRM_DEPTH)
    parser.add_argument("--baseline", type=Path, help="JSON com as atribuições do código anterior")
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--json", type=Path, help="grava os resultados por posição")
    args = parser.parse_args(argv)

    results = evaluate(args.depth)
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
    print(report(results, baseline, args.details))
    if args.json:
        args.json.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
