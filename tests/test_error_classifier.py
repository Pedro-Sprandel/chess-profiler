"""Classificador LLM de erros sem conceito (modules/error_classifier.py), API simulada."""
import json
from unittest.mock import MagicMock

import pytest

import config
from modules.ai_diagnostician import load_silman_concepts
from modules.error_classifier import BATCH_SIZE, PROMPT_VERSION, classify_unattributed, fact_sheet

# Lance ruim de torre num final (sem regra que o explique) — o conteúdo não importa
# para estes testes, só a mecânica.
FEN = "2r1kb1r/pp3pp1/1p2b2p/3p1n2/1P5P/2P5/P3QP2/3RK2R w k - 3 22"


def _position(i=0, magnitude=150):
    return {
        "fen": FEN,
        "move_played": ["d1c1", "d1b1", "d1a1", "h1g1", "h1h2", "h1h3"][i % 6],
        "move_number": 22,
        "concepts_detected": {},
        "stockfish_validation": {
            "is_error": True, "eval_before": 120, "eval_after": -30,
            "error_magnitude": magnitude, "best_move": "d1d5",
            "best_line": ["d1d5", "e8e7"], "refutation_line": ["f5e3"],
        },
    }


def _pairs(n):
    game = {"game_id": "g1", "player_color": "white"}
    return [(game, _position(i, 100 + i)) for i in range(n)]


def _client(answer_for):
    """Cliente falso: responde a cada lote com answer_for(items)."""
    client = MagicMock()

    def create(**kwargs):
        items = json.loads(kwargs["messages"][0]["content"].split("\n", 1)[1])
        block = MagicMock()
        block.type = "text"
        block.text = json.dumps(answer_for(items))
        return MagicMock(content=[block])

    client.messages.create.side_effect = create
    return client


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(config, "LLM_CLASSIFY_ERRORS", True)
    monkeypatch.setattr(config, "LLM_CLASSIFY_MAX_ERRORS", 60)


@pytest.fixture(scope="module")
def silman():
    return load_silman_concepts()


def _label(items, concept="weak_square", confidence="high"):
    return [{"id": it["id"], "concept": concept, "confidence": confidence,
             "reason_en": "Rook should take d5.", "reason_pt": "A torre devia tomar d5."}
            for it in items]


def test_fact_sheet_is_computed_not_read_from_fen():
    sheet = fact_sheet("m0", {"player_color": "white"}, _position())
    assert sheet["played"] == "Rc1" and sheet["best"] == "Rxd5"
    assert sheet["best_line"] == ["Rxd5", "Ke7"]  # Bxd5 seria ilegal: bispo cravado em e6
    assert sheet["best_move"]["capture"] is True
    assert "material_gain_best_line_cp" in sheet and "own_hanging_before" in sheet


def test_disabled_does_nothing(silman):
    pairs = _pairs(3)
    stats = classify_unattributed(pairs, silman, client=MagicMock())
    assert stats["skipped"] == 3 and stats["sent"] == 0
    assert all("attribution" not in p for _, p in pairs)


def test_labels_accepted_and_marked_as_llm(enabled, silman):
    pairs = _pairs(3)
    stats = classify_unattributed(pairs, silman, client=_client(_label))
    assert stats["accepted"] == 3 and stats["sent"] == 3
    a = pairs[0][1]["attribution"]
    assert a["concept"] == "weak_square" and a["source"] == "llm"
    assert a["reason"] == {"en": "Rook should take d5.", "pt": "A torre devia tomar d5."}


@pytest.mark.parametrize("label", [
    {"concept": "weak_square", "confidence": "low"},
    {"concept": "none", "confidence": "high"},
    {"concept": "made_up_concept", "confidence": "high"},
])
def test_low_confidence_none_and_unknown_are_rejected(enabled, silman, label):
    pairs = _pairs(1)
    classify_unattributed(pairs, silman,
                          client=_client(lambda items: [{"id": items[0]["id"], **label}]))
    assert "attribution" not in pairs[0][1]


def test_cap_keeps_the_largest_mistakes(enabled, silman, monkeypatch):
    monkeypatch.setattr(config, "LLM_CLASSIFY_MAX_ERRORS", 2)
    pairs = _pairs(5)  # magnitudes 100..104
    stats = classify_unattributed(pairs, silman, client=_client(_label))
    assert stats["sent"] == 2 and stats["skipped"] == 3
    labelled = sorted(p["stockfish_validation"]["error_magnitude"] for _, p in pairs if "attribution" in p)
    assert labelled == [103, 104]


def test_batches(enabled, silman):
    client = _client(_label)
    classify_unattributed(_pairs(BATCH_SIZE + 5), silman, client=client)
    assert client.messages.create.call_count == 2


def test_cache_avoids_paying_twice(enabled, silman):
    first = _client(_label)
    classify_unattributed(_pairs(3), silman, client=first)
    second = _client(_label)
    again = _pairs(3)
    stats = classify_unattributed(again, silman, client=second)
    assert second.messages.create.call_count == 0
    assert stats["cached"] == 3 and stats["accepted"] == 3
    assert again[0][1]["attribution"]["source"] == "llm"


def test_api_failure_leaves_mistakes_unattributed(enabled, silman):
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("boom")
    pairs = _pairs(2)
    stats = classify_unattributed(pairs, silman, client=client)
    assert stats["sent"] == 0 and stats["skipped"] == 2
    assert all("attribution" not in p for _, p in pairs)


def test_no_api_key_skips(enabled, silman, monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", None)
    stats = classify_unattributed(_pairs(2), silman)
    assert stats["skipped"] == 2


def test_prompt_uses_closed_label_list_and_cached_system_block(enabled, silman):
    client = _client(_label)
    classify_unattributed(_pairs(1), silman, client=client)
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["model"] == config.ANTHROPIC_CLASSIFIER_MODEL
    system = kwargs["system"][0]
    assert system["cache_control"] == {"type": "ephemeral"}
    assert "allowed_tactic" in system["text"] and "- none:" in system["text"]
    assert PROMPT_VERSION
