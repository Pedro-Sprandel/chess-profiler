"""
error_classifier.py — classificador LLM para erros que nenhuma regra explica.

As regras de modules/attribution.py priorizam precisão: um erro só recebe conceito
quando há vínculo concreto. O que sobra ("sem conceito") vem para cá. O LLM NÃO lê o
tabuleiro sozinho: recebe uma ficha determinística por erro (lances em SAN, linhas do
Stockfish, material ganho/perdido ao longo delas, peças penduradas dos dois lados,
conceitos detectados e quanto o melhor lance melhora cada um) e escolhe, numa lista
fechada, o conceito que os fatos sustentam — ou "none".

Controles de custo:
  - só erros sem conceito, no máximo LLM_CLASSIFY_MAX_ERRORS por análise (maior perda
    primeiro);
  - lotes de BATCH_SIZE erros por chamada, com o catálogo de conceitos num bloco de
    sistema estável (cacheável);
  - cache por (fen, lance, versão do prompt) no AppStore: re-análises não pagam de novo;
  - sem ANTHROPIC_API_KEY, com LLM_CLASSIFY_ERRORS=0 ou em falha da API, o pipeline
    segue sem a classificação (os erros ficam "sem conceito").

Só rótulos com confiança high/medium são aceitos; a atribuição fica marcada com
source="llm" e a justificativa curta, e a interface mostra "inferido pela IA".
"""

import json
import time

import anthropic
import chess

import config
from modules.app_store import AppStore
from modules.attribution import (
    allowed_tactic_gain,
    is_endgame,
    line_material_gain,
    _moves,
)
from modules.concept_relevance import CONCEPT_SCORE_THRESHOLD, _DEFAULT_THRESHOLD, _concept_score
from modules.position_analyzer import detect_concepts

PROMPT_VERSION = "v1"
BATCH_SIZE = 20
_MAX_RETRIES = 3
_ACCEPTED_CONFIDENCE = ("high", "medium")

# Campos de detalhe que ajudam o modelo, por conceito (o resto é ruído).
_DETAIL_FIELDS = ("squares", "files", "open_files", "semi_open_files", "overloaded_squares",
                  "advantage", "exposed", "shield_pawns", "king_square",
                  "queenside_majority", "kingside_majority")


def _san_line(board: chess.Board, line) -> list[str]:
    b = board.copy(stack=False)
    out = []
    for move in _moves(line):
        if move not in b.legal_moves:
            break
        out.append(b.san(move))
        b.push(move)
    return out


def _pov(cp, white: bool):
    if cp is None:
        return None
    return round((cp if white else -cp) / 100, 2)


def fact_sheet(item_id: str, game: dict, position: dict) -> dict:
    """Fatos determinísticos sobre um erro, prontos para o prompt."""
    board = chess.Board(position["fen"])
    color = game.get("player_color", "white") == "white"
    validation = position["stockfish_validation"]
    played = chess.Move.from_uci(position["move_played"])
    best = chess.Move.from_uci(validation["best_move"])

    after_played = board.copy(stack=False)
    after_played.push(played)
    after_best = board.copy(stack=False)
    after_best.push(best)

    concepts = position.get("concepts_detected") or detect_concepts(board, color)
    concepts_played = detect_concepts(after_played, color)
    concepts_best = detect_concepts(after_best, color)
    detected = {}
    for key, details in concepts.items():
        if not details.get("detected"):
            continue
        threshold = CONCEPT_SCORE_THRESHOLD.get(key, _DEFAULT_THRESHOLD)
        detected[key] = {
            **{f: details[f] for f in _DETAIL_FIELDS if f in details},
            "gain_best_vs_played": round(_concept_score(concepts_best, key)
                                         - _concept_score(concepts_played, key), 2),
            "rule_threshold": threshold,
        }

    opponent_hanging = detect_concepts(board, not color)["hanging_piece"].get("squares", [])
    best_line = validation.get("best_line") or [best.uci()]
    refutation = validation.get("refutation_line") or []
    return {
        "id": item_id,
        "side": "white" if color else "black",
        "move_number": position.get("move_number"),
        "phase": "endgame" if is_endgame(board) else "middlegame",
        "fen": position["fen"],
        "played": board.san(played),
        "best": board.san(best),
        "best_line": _san_line(board, best_line),
        "refutation_line": _san_line(after_played, refutation),
        "eval_before_pawns": _pov(validation.get("eval_before"), color),
        "eval_after_pawns": _pov(validation.get("eval_after"), color),
        "best_move": {
            "piece": chess.piece_name(board.piece_at(best.from_square).piece_type),
            "capture": board.is_capture(best),
            "check": board.gives_check(best),
            "castling": board.is_castling(best),
        },
        "material_gain_best_line_cp": line_material_gain(board, best_line, color),
        "material_lost_refutation_cp": allowed_tactic_gain(board, played, refutation, color),
        "own_hanging_before": concepts.get("hanging_piece", {}).get("squares", []),
        "opponent_hanging_before": opponent_hanging,
        "concepts_detected": detected,
    }


def _catalog(silman_concepts: dict) -> str:
    lines = []
    for key, c in silman_concepts.items():
        lines.append(f"- {key}: {c.get('name_en') or c.get('name')} — {c.get('description', '')}")
    return "\n".join(lines)


def _system_prompt(silman_concepts: dict) -> str:
    return f"""You label chess mistakes for a strategic profiler based on Jeremy Silman's
"The Amateur's Mind". Each mistake was confirmed by Stockfish, but the profiler's
deterministic rules could not tie it to any concept. You receive computed facts about
each mistake: moves in SAN, the engine's best line and its refutation of the played
move, material won or lost along those lines, hanging pieces, the concepts the
detectors saw and how much the best move improves each of them versus the played move.

Base your choice ONLY on these facts. Do not reconstruct the position from the FEN
beyond what the facts state.

Allowed labels (exact keys):
{_catalog(silman_concepts)}
- none: no concept above is supported by the facts (e.g. a calculation or endgame-technique
  mistake with no clear theme).

Rules:
- Choose the single concept that best explains why the best move is better.
- missed_tactic / allowed_tactic only when the facts show forcing play or material
  changing hands along the lines.
- A strategic concept needs support in the facts: it was detected, or the best move is
  clearly about it (e.g. the best move is a pawn break against a weak pawn).
- Prefer "none" with low confidence over a guess.
- confidence: "high" when the facts clearly support the label, "medium" when they
  support it but another reading is possible, "low" otherwise.

Answer ONLY with a JSON array, one object per mistake, in the input order:
[{{"id": "...", "concept": "<label>", "confidence": "high|medium|low",
   "reason_en": "<= 20 words", "reason_pt": "<= 20 words, Brazilian Portuguese"}}]"""


def _call(client, system: str, items: list[dict]) -> list[dict]:
    payload = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    last_error = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.messages.create(
                model=config.ANTHROPIC_CLASSIFIER_MODEL,
                max_tokens=4096,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": f"Mistakes:\n{payload}"}],
            )
            break
        except (anthropic.RateLimitError, anthropic.APIConnectionError,
                anthropic.InternalServerError) as e:
            last_error = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(2.0 * (2 ** attempt))
    else:
        raise RuntimeError(f"classificador LLM indisponível: {last_error}")

    text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), "")
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        raise ValueError("resposta do classificador sem JSON")
    data = json.loads(text[start:end + 1])
    return data if isinstance(data, list) else []


def _to_attribution(label: dict, valid: set[str]) -> dict | None:
    concept = label.get("concept")
    if concept not in valid or label.get("confidence") not in _ACCEPTED_CONFIDENCE:
        return None
    return {"concept": concept, "source": "llm", "motif": "llm",
            "confidence": label.get("confidence"),
            "reason": {"en": (label.get("reason_en") or "")[:200],
                       "pt": (label.get("reason_pt") or "")[:200]}}


def classify_unattributed(pairs: list[tuple[dict, dict]], silman_concepts: dict,
                          on_progress=None, client=None) -> dict:
    """Classifica erros sem conceito e grava position["attribution"] nos aceitos.

    pairs: (game, position) vindos de profile_builder.annotate_attributions.
    Retorna estatísticas {"candidates", "cached", "sent", "accepted", "skipped"}.
    """
    stats = {"candidates": len(pairs), "cached": 0, "sent": 0, "accepted": 0, "skipped": 0}
    if not pairs or not config.LLM_CLASSIFY_ERRORS:
        stats["skipped"] = len(pairs)
        return stats

    valid = set(silman_concepts)
    ranked = sorted(pairs, key=lambda gp: -abs(gp[1]["stockfish_validation"].get("error_magnitude") or 0))
    selected = ranked[: max(0, config.LLM_CLASSIFY_MAX_ERRORS)]
    stats["skipped"] = len(pairs) - len(selected)

    keys = [(p["fen"], p["move_played"]) for _, p in selected]
    try:
        with AppStore() as store:
            cached = store.get_error_labels(keys, PROMPT_VERSION)
    except Exception:
        cached = {}

    pending = []
    for game, position in selected:
        label = cached.get((position["fen"], position["move_played"]))
        if label is not None:
            stats["cached"] += 1
            attribution = _to_attribution(label, valid)
            if attribution:
                position["attribution"] = attribution
                stats["accepted"] += 1
        else:
            pending.append((game, position))

    if not pending:
        return stats
    if client is None:
        if not config.ANTHROPIC_API_KEY:
            stats["skipped"] += len(pending)
            return stats
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    system = _system_prompt(silman_concepts)
    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start:start + BATCH_SIZE]
        if on_progress:
            on_progress("classify", start, len(pending),
                        f"[main] Classifying unexplained mistakes ({start + len(batch)}/{len(pending)})...")
        items, by_id = [], {}
        for i, (game, position) in enumerate(batch):
            try:
                item_id = f"m{start + i}"
                items.append(fact_sheet(item_id, game, position))
                by_id[item_id] = position
            except Exception:
                continue  # posição malformada: fica sem conceito
        if not items:
            continue
        try:
            labels = _call(client, system, items)
        except Exception as e:
            print(f"[error_classifier] lote ignorado: {e}")
            stats["skipped"] += len(items)
            continue
        stats["sent"] += len(items)

        try:
            store = AppStore()
        except Exception:
            store = None
        try:
            for label in labels:
                position = by_id.get(label.get("id")) if isinstance(label, dict) else None
                if position is None:
                    continue
                if store is not None:
                    store.save_error_label(position["fen"], position["move_played"],
                                           PROMPT_VERSION, config.ANTHROPIC_CLASSIFIER_MODEL, label)
                attribution = _to_attribution(label, valid)
                if attribution:
                    position["attribution"] = attribution
                    stats["accepted"] += 1
        finally:
            if store is not None:
                store.close()
    return stats
