"""Tests for diagnosis_card helper components."""
from ui.components.diagnosis_card import format_root_cause, format_weakness_table, format_study_priority

SAMPLE_DIAGNOSIS = {
    "root_cause": {
        "name": "Static Thinking",
        "description": "Player fails to consider dynamic imbalances.",
    },
    "confidence": "HIGH",
    "weakness_classification": [
        {"concept": "weak_square", "classification": "PRIMARY", "reasoning": "Most frequent error."},
        {"concept": "king_safety", "classification": "SECONDARY", "reasoning": "Consequence of weak squares."},
    ],
    "study_priority": [
        {"concept": "weak_square", "silman_name": "Weak Square", "silman_chapter": 3,
         "silman_page": 67, "priority_rank": 1, "reason": "Root cause."},
        {"concept": "king_safety", "silman_name": "King Safety", "silman_chapter": 7,
         "silman_page": 156, "priority_rank": 2, "reason": "Secondary issue."},
    ],
    "cognitive_pattern": "Player ignores long-term positional consequences.",
}


def test_format_root_cause_returns_dict():
    result = format_root_cause(SAMPLE_DIAGNOSIS)
    assert isinstance(result, dict)
    assert result["name"] == "Static Thinking"
    assert result["confidence"] == "HIGH"
    assert "description" in result


def test_format_weakness_table_returns_list():
    result = format_weakness_table(SAMPLE_DIAGNOSIS)
    assert isinstance(result, list)
    assert len(result) == 2
    assert "Concept" in result[0]
    assert "Classification" in result[0]
    assert "Reasoning" in result[0]


def test_format_study_priority_returns_sorted_list():
    result = format_study_priority(SAMPLE_DIAGNOSIS)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["rank"] == 1
    assert result[1]["rank"] == 2


def test_format_root_cause_handles_missing_keys():
    result = format_root_cause({})
    assert result["name"] == ""
    assert result["confidence"] == "LOW"


def test_format_weakness_table_handles_empty():
    result = format_weakness_table({})
    assert result == []


def test_format_study_priority_handles_empty():
    result = format_study_priority({})
    assert result == []
