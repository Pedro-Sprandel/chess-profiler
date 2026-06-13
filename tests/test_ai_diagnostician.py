import json
import pytest
from unittest.mock import MagicMock, patch


MOCK_DIAGNOSIS = {
    "en": {
        "root_cause": {
            "id": "static_thinking",
            "name": "Static Thinking",
            "description": "Player does not evaluate dynamic imbalances."
        },
        "weakness_classification": [
            {"concept": "weak_square", "classification": "PRIMARY", "reasoning": "Root of the problem."}
        ],
        "study_priority": [
            {"concept": "weak_square", "silman_chapter": 3, "priority_rank": 1, "reason": "Root cause."}
        ],
        "cognitive_pattern": "Ignores weak squares in opponent's field.",
        "confidence": "HIGH"
    },
    "pt": {
        "root_cause": {
            "id": "static_thinking",
            "name": "Pensamento Estático",
            "description": "O jogador não avalia desequilíbrios dinâmicos."
        },
        "weakness_classification": [
            {"concept": "weak_square", "classification": "PRIMARY", "reasoning": "Raiz do problema."}
        ],
        "study_priority": [
            {"concept": "weak_square", "silman_chapter": 3, "priority_rank": 1, "reason": "Causa raiz."}
        ],
        "cognitive_pattern": "Ignora casas fracas no campo adversário.",
        "confidence": "HIGH"
    }
}

SAMPLE_PROFILE = {
    "total_games": 5,
    "total_positions_analyzed": 100,
    "overall_error_rate": 0.15,
    "weaknesses": [
        {
            "concept": "weak_square",
            "error_occurrences": 5,
            "total_occurrences": 10,
            "error_rate": 0.5,
            "avg_error_magnitude_cp": 80.0,
            "sample_positions": []
        }
    ]
}


def make_mock_message(response_text: str):
    """Build a mock Anthropic message with a single text content block."""
    message = MagicMock()
    content_block = MagicMock()
    content_block.text = response_text
    message.content = [content_block]
    return message


def make_mock_client(response_text: str):
    """Build a mock Anthropic client returning a given text response."""
    client = MagicMock()
    client.messages.create.return_value = make_mock_message(response_text)
    return client


class TestLoadSilmanConcepts:
    def test_returns_dict_keyed_by_detection_key(self):
        from modules.ai_diagnostician import load_silman_concepts
        result = load_silman_concepts("data/silman_concepts.json")
        assert isinstance(result, dict)
        assert "weak_square" in result

    def test_loads_all_concepts(self):
        from modules.ai_diagnostician import load_silman_concepts
        result = load_silman_concepts("data/silman_concepts.json")
        expected = {
            "weak_square", "open_file", "isolated_pawn", "bishop_pair",
            "knight_outpost", "king_safety", "space_advantage",
            "passed_pawn", "doubled_pawn", "rook_on_7th",
            "bad_bishop", "pawn_majority", "piece_activity", "overloaded_piece",
            "hanging_piece", "backward_pawn", "center_control",
            "missed_tactic",
        }
        assert set(result.keys()) == expected

    def test_each_concept_has_required_fields(self):
        from modules.ai_diagnostician import load_silman_concepts
        result = load_silman_concepts("data/silman_concepts.json")
        for key, concept in result.items():
            assert "name" in concept
            assert "silman_chapter" in concept
            assert "silman_page" in concept
            assert "detection_key" in concept


class TestDiagnose:
    def test_calls_anthropic_api_with_correct_model(self):
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        silman = load_silman_concepts("data/silman_concepts.json")
        mock_client = make_mock_client(json.dumps(MOCK_DIAGNOSIS))

        with patch("modules.ai_diagnostician.anthropic.Anthropic", return_value=mock_client):
            diagnose(SAMPLE_PROFILE, silman)

        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-opus-4-6"

    def test_parses_valid_json_response(self):
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        silman = load_silman_concepts("data/silman_concepts.json")
        mock_client = make_mock_client(json.dumps(MOCK_DIAGNOSIS))

        with patch("modules.ai_diagnostician.anthropic.Anthropic", return_value=mock_client):
            result = diagnose(SAMPLE_PROFILE, silman)

        assert result["en"]["root_cause"]["id"] == "static_thinking"
        assert result["en"]["confidence"] == "HIGH"

    def test_handles_markdown_fenced_json_response(self):
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        silman = load_silman_concepts("data/silman_concepts.json")
        fenced = f"```json\n{json.dumps(MOCK_DIAGNOSIS)}\n```"
        mock_client = make_mock_client(fenced)

        with patch("modules.ai_diagnostician.anthropic.Anthropic", return_value=mock_client):
            result = diagnose(SAMPLE_PROFILE, silman)

        assert result["en"]["root_cause"]["id"] == "static_thinking"

    def test_returns_bilingual_structure(self):
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        silman = load_silman_concepts("data/silman_concepts.json")
        mock_client = make_mock_client(json.dumps(MOCK_DIAGNOSIS))

        with patch("modules.ai_diagnostician.anthropic.Anthropic", return_value=mock_client):
            result = diagnose(SAMPLE_PROFILE, silman)

        assert "en" in result and "pt" in result

    def test_enriches_study_priority_with_silman_metadata(self):
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        silman = load_silman_concepts("data/silman_concepts.json")
        mock_client = make_mock_client(json.dumps(MOCK_DIAGNOSIS))

        with patch("modules.ai_diagnostician.anthropic.Anthropic", return_value=mock_client):
            result = diagnose(SAMPLE_PROFILE, silman)

        for lang in ("en", "pt"):
            priority_item = result[lang]["study_priority"][0]
            assert "silman_name" in priority_item
            assert "silman_page" in priority_item
            assert priority_item["silman_page"] == 67  # weak_square page from silman_concepts.json

    def test_returns_dict_with_required_keys(self):
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        silman = load_silman_concepts("data/silman_concepts.json")
        mock_client = make_mock_client(json.dumps(MOCK_DIAGNOSIS))

        with patch("modules.ai_diagnostician.anthropic.Anthropic", return_value=mock_client):
            result = diagnose(SAMPLE_PROFILE, silman)

        for lang in ("en", "pt"):
            assert "root_cause" in result[lang]
            assert "weakness_classification" in result[lang]
            assert "study_priority" in result[lang]
            assert "cognitive_pattern" in result[lang]
            assert "confidence" in result[lang]


class TestDiagnoseErrorHandling:
    def test_raises_clear_error_without_api_key(self):
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        silman = load_silman_concepts("data/silman_concepts.json")
        with patch("modules.ai_diagnostician.ANTHROPIC_API_KEY", None):
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                diagnose(SAMPLE_PROFILE, silman)

    def test_raises_on_malformed_json_response(self):
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        silman = load_silman_concepts("data/silman_concepts.json")
        mock_client = make_mock_client("Sorry, I cannot help with that.")
        with patch("modules.ai_diagnostician.anthropic.Anthropic", return_value=mock_client):
            with pytest.raises(ValueError):
                diagnose(SAMPLE_PROFILE, silman)

    def test_extracts_json_with_surrounding_prose(self):
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        silman = load_silman_concepts("data/silman_concepts.json")
        noisy = f"Here is the diagnosis:\n{json.dumps(MOCK_DIAGNOSIS)}\nHope this helps!"
        mock_client = make_mock_client(noisy)
        with patch("modules.ai_diagnostician.anthropic.Anthropic", return_value=mock_client):
            result = diagnose(SAMPLE_PROFILE, silman)
        assert result["en"]["root_cause"]["id"] == "static_thinking"

    def test_retries_on_transient_error_then_succeeds(self):
        import httpx
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        import anthropic
        silman = load_silman_concepts("data/silman_concepts.json")

        req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        transient = anthropic.APIConnectionError(message="boom", request=req)
        good_message = make_mock_message(json.dumps(MOCK_DIAGNOSIS))

        client = MagicMock()
        client.messages.create.side_effect = [transient, good_message]

        with patch("modules.ai_diagnostician.anthropic.Anthropic", return_value=client), \
             patch("modules.ai_diagnostician.time.sleep"):
            result = diagnose(SAMPLE_PROFILE, silman)

        assert client.messages.create.call_count == 2
        assert result["en"]["confidence"] == "HIGH"

    def test_raises_after_exhausting_retries(self):
        import httpx
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        import anthropic
        silman = load_silman_concepts("data/silman_concepts.json")

        req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        transient = anthropic.APIConnectionError(message="boom", request=req)
        client = MagicMock()
        client.messages.create.side_effect = transient

        with patch("modules.ai_diagnostician.anthropic.Anthropic", return_value=client), \
             patch("modules.ai_diagnostician.time.sleep"):
            with pytest.raises(RuntimeError, match="tentativas"):
                diagnose(SAMPLE_PROFILE, silman)
