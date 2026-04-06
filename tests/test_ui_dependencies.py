"""Tests that all UI dependencies are installed and importable."""


def test_streamlit_importable():
    import streamlit  # noqa: F401


def test_plotly_importable():
    import plotly  # noqa: F401
    import plotly.express  # noqa: F401


def test_chess_svg_importable():
    import chess.svg  # noqa: F401
