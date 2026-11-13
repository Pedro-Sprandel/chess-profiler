"""Monta data/gold_attributions.json a partir da validação qualitativa do TCC.

Junta duas fontes já versionadas em docs/:
  - qualitative_dataset.md  → todas as posições de erro atribuídas (FEN, lances UCI,
                              conceito, partida, cor do jogador, perda em cp)
  - qualitative_analysis.md → vereditos humanos (✅ coerente, ⚠️ parcial, ❌ falso
                              positivo) para uma amostra, identificados por
                              conceito + partida + perda + lances em SAN

O resultado é o conjunto de referência usado por scripts/evaluate_precision.py:
cada posição traz o conceito que o pipeline antigo atribuiu e, quando houver, o
veredito humano sobre essa atribuição.

    python scripts/build_gold_set.py
"""
import json
import re
import sys
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "docs" / "qualitative_dataset.md"
ANALYSIS = ROOT / "docs" / "qualitative_analysis.md"
OUT = ROOT / "data" / "gold_attributions.json"

VERDICTS = {"✅": "coherent", "⚠️": "partial", "❌": "false_positive"}


def _parse_dataset(text: str) -> list[dict]:
    positions = []
    profiles = re.split(r"\n## Perfil \d+ — ", text)[1:]
    for block in profiles:
        profile = block.split("\n", 1)[0].strip()
        for concept_block in re.split(r"\n### ", block)[1:]:
            m = re.search(r"\(`([a-z_]+)`\)", concept_block.split("\n", 1)[0])
            if not m:
                continue
            concept = m.group(1)
            for ex in re.split(r"\n\*\*Exemplo \d+\*\*", concept_block)[1:]:
                game = re.search(r"partida `game_(\d+)`", ex)
                color = re.search(r"jogador de (white|black)", ex)
                moves = re.search(r"Lance jogado: `([a-h1-8qrbn]+)`\s*\|\s*melhor lance: `([a-h1-8qrbn]+)`"
                                  r"\s*\|\s*perda: \*\*(-?\d+) cp\*\*", ex)
                fen = re.search(r"FEN: `([^`]+)`", ex)
                if not (game and color and moves and fen):
                    continue
                positions.append({
                    "profile": profile,
                    "game": int(game.group(1)),
                    "player_color": color.group(1),
                    "fen": fen.group(1),
                    "move_played": moves.group(1),
                    "best_move": moves.group(2),
                    "loss_cp": int(moves.group(3)),
                    "old_concept": concept,
                })
    return positions


def _parse_verdicts(text: str) -> list[dict]:
    verdicts = []
    for block in re.split(r"\n## Perfil \d+: ", text)[1:]:
        profile = block.split(" ", 1)[0].strip()
        for line in block.splitlines():
            m = re.match(r"\|\s*(.+?)\s*\|\s*g(\d+) \((\d+)cp\)\s*\|\s*`([^`]+)` → \*\*`([^`]+)`\*\*\s*\|"
                         r"\s*(✅|⚠️|❌)\s*\|\s*(.+?)\s*\|\s*$", line)
            if not m:
                continue
            for concept in re.findall(r"`([a-z_]+)`", m.group(1)):
                verdicts.append({
                    "profile": profile, "concept": concept, "game": int(m.group(2)),
                    "loss_cp": int(m.group(3)), "played_san": m.group(4),
                    "best_san": m.group(5), "verdict": VERDICTS[m.group(6)],
                    "note": m.group(7),
                })
    return verdicts


def _san(fen: str, uci: str) -> str | None:
    try:
        board = chess.Board(fen)
        return board.san(chess.Move.from_uci(uci))
    except ValueError:
        return None


def _strip(san: str) -> str:
    return san.rstrip("+#")


def build() -> dict:
    positions = _parse_dataset(DATASET.read_text(encoding="utf-8"))
    verdicts = _parse_verdicts(ANALYSIS.read_text(encoding="utf-8"))

    # Uma posição pode aparecer em mais de um conceito: agrupa por posição.
    by_key: dict = {}
    for p in positions:
        key = (p["profile"], p["fen"], p["move_played"])
        entry = by_key.setdefault(key, {**{k: p[k] for k in (
            "profile", "game", "player_color", "fen", "move_played", "best_move", "loss_cp")},
            "old_concepts": [], "verdicts": {}})
        entry["old_concepts"].append(p["old_concept"])
        entry["played_san"] = _san(p["fen"], p["move_played"])
        entry["best_san"] = _san(p["fen"], p["best_move"])

    unmatched = []
    for v in verdicts:
        candidates = [e for e in by_key.values()
                      if e["profile"] == v["profile"] and e["game"] == v["game"]
                      and v["concept"] in e["old_concepts"]
                      and abs(e["loss_cp"] - v["loss_cp"]) <= 1
                      and e["played_san"] and _strip(e["played_san"]) == _strip(v["played_san"])
                      and e["best_san"] and _strip(e["best_san"]) == _strip(v["best_san"])]
        if not candidates:
            # Erro de digitação no lance jogado da análise (ex.: "e5" por "e4"): aceita
            # o par único de partida + conceito + perda + melhor lance.
            candidates = [e for e in by_key.values()
                          if e["profile"] == v["profile"] and e["game"] == v["game"]
                          and v["concept"] in e["old_concepts"]
                          and abs(e["loss_cp"] - v["loss_cp"]) <= 1
                          and e["best_san"] and _strip(e["best_san"]) == _strip(v["best_san"])]
        if len(candidates) != 1:
            unmatched.append(v)
            continue
        candidates[0]["verdicts"][v["concept"]] = {"verdict": v["verdict"], "note": v["note"]}

    entries = sorted(by_key.values(), key=lambda e: (e["profile"], e["game"], e["fen"]))
    return {
        "source": "docs/qualitative_dataset.md + docs/qualitative_analysis.md",
        "n_positions": len(entries),
        "n_verdicts": sum(len(e["verdicts"]) for e in entries),
        "unmatched_verdicts": unmatched,
        "positions": entries,
    }


if __name__ == "__main__":
    data = build()
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{data['n_positions']} posições, {data['n_verdicts']} vereditos casados, "
          f"{len(data['unmatched_verdicts'])} sem par → {OUT.relative_to(ROOT)}")
    for v in data["unmatched_verdicts"]:
        print("  sem par:", v["profile"], v["concept"], f"g{v['game']}", v["played_san"], "→", v["best_san"],
              file=sys.stderr)
