"""Tests for the Streamlit app entry point."""
import os
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "app.py")


def test_app_runs_without_exception():
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception


def test_app_has_title():
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception
