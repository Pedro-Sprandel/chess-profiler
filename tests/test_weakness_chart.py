"""Tests for weakness_chart helper components."""
import plotly.graph_objects as go
from ui.components.weakness_chart import build_error_count_chart, build_error_magnitude_chart

SAMPLE_WEAKNESSES = [
    {"concept": "weak_square", "error_occurrences": 10, "avg_error_magnitude_cp": 120.5},
    {"concept": "isolated_pawn", "error_occurrences": 5, "avg_error_magnitude_cp": 80.0},
    {"concept": "king_safety", "error_occurrences": 3, "avg_error_magnitude_cp": 200.0},
]


def test_error_count_chart_returns_figure():
    fig = build_error_count_chart(SAMPLE_WEAKNESSES)
    assert isinstance(fig, go.Figure)


def test_error_count_chart_has_data():
    fig = build_error_count_chart(SAMPLE_WEAKNESSES)
    assert len(fig.data) > 0
    assert len(fig.data[0].x) == 3


def test_error_count_chart_sorted_descending():
    fig = build_error_count_chart(SAMPLE_WEAKNESSES)
    y_values = list(fig.data[0].y)
    assert y_values == sorted(y_values, reverse=True)


def test_error_magnitude_chart_returns_figure():
    fig = build_error_magnitude_chart(SAMPLE_WEAKNESSES)
    assert isinstance(fig, go.Figure)


def test_error_magnitude_chart_has_data():
    fig = build_error_magnitude_chart(SAMPLE_WEAKNESSES)
    assert len(fig.data) > 0
    assert len(fig.data[0].x) == 3


def test_charts_handle_empty_list():
    fig = build_error_count_chart([])
    assert isinstance(fig, go.Figure)
    fig2 = build_error_magnitude_chart([])
    assert isinstance(fig2, go.Figure)
