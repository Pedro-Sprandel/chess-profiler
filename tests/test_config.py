import pytest


def test_stockfish_depth():
    import config
    assert config.STOCKFISH_DEPTH == 10


def test_error_threshold_cp():
    import config
    assert config.ERROR_THRESHOLD_CP == 50


def test_min_occurrences():
    import config
    assert config.MIN_OCCURRENCES == 3


def test_stockfish_path_is_non_empty_string():
    import config
    assert isinstance(config.STOCKFISH_PATH, str)
    assert len(config.STOCKFISH_PATH) > 0
