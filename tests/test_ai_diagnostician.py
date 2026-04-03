import json
import pytest
from unittest.mock import MagicMock, patch


MOCK_DIAGNOSIS = {
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


def make_mock_client(response_text: str):
    """Build a mock Anthropic client returning a given text response."""
    client = MagicMock()
    message = MagicMock()
    content_block = MagicMock()
    content_block.text = response_text
    message.content = [content_block]
    client.messages.create.return_value = message
    return client


class TestLoadSilmanConcepts:
    def test_returns_dict_keyed_by_detection_key(self):
        from modules.ai_diagnostician import load_silman_concepts
        result = load_silman_concepts("data/silman_concepts.json")
        assert isinstance(result, dict)
        assert "weak_square" in result

    def test_loads_all_seven_concepts(self):
        from modules.ai_diagnostician import load_silman_concepts
        result = load_silman_concepts("data/silman_concepts.json")
        expected = {
            "weak_square", "open_file", "isolated_pawn",
            "bishop_pair", "knight_outpost", "king_safety", "space_advantage"
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

        assert result["root_cause"]["id"] == "static_thinking"
        assert result["confidence"] == "HIGH"

    def test_handles_markdown_fenced_json_response(self):
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        silman = load_silman_concepts("data/silman_concepts.json")
        fenced = f"```json\n{json.dumps(MOCK_DIAGNOSIS)}\n```"
        mock_client = make_mock_client(fenced)

        with patch("modules.ai_diagnostician.anthropic.Anthropic", return_value=mock_client):
            result = diagnose(SAMPLE_PROFILE, silman)

        assert result["root_cause"]["id"] == "static_thinking"

    def test_enriches_study_priority_with_silman_metadata(self):
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        silman = load_silman_concepts("data/silman_concepts.json")
        mock_client = make_mock_client(json.dumps(MOCK_DIAGNOSIS))

        with patch("modules.ai_diagnostician.anthropic.Anthropic", return_value=mock_client):
            result = diagnose(SAMPLE_PROFILE, silman)

        priority_item = result["study_priority"][0]
        assert "silman_name" in priority_item
        assert "silman_page" in priority_item
        assert priority_item["silman_page"] == 67  # weak_square page from silman_concepts.json

    def test_returns_dict_with_required_keys(self):
        from modules.ai_diagnostician import diagnose, load_silman_concepts
        silman = load_silman_concepts("data/silman_concepts.json")
        mock_client = make_mock_client(json.dumps(MOCK_DIAGNOSIS))

        with patch("modules.ai_diagnostician.anthropic.Anthropic", return_value=mock_client):
            result = diagnose(SAMPLE_PROFILE, silman)

        assert "root_cause" in result
        assert "weakness_classification" in result
        assert "study_priority" in result
        assert "cognitive_pattern" in result
        assert "confidence" in result
