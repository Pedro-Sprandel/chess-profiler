import chess
import pytest
from unittest.mock import patch, MagicMock

MINIMAL_PGN = """[Event "Live Chess"]
[Site "Chess.com"]
[Date "2024.01.01"]
[Round "-"]
[White "sprandel"]
[Black "opponent"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""

ARCHIVE_RESPONSE = {
    "archives": [
        "https://api.chess.com/pub/player/sprandel/games/2024/01",
        "https://api.chess.com/pub/player/sprandel/games/2024/02",
        "https://api.chess.com/pub/player/sprandel/games/2024/03",
    ]
}

GAMES_RESPONSE = {
    "games": [
        {
            "white": {"username": "sprandel", "rating": 1200},
            "black": {"username": "opponent", "rating": 1180},
            "pgn": MINIMAL_PGN,
            "time_control": "600",
            "rated": True,
        }
    ]
}


def make_mock_response(json_data):
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def make_status_response(status_code: int):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {}
    resp.raise_for_status.return_value = None
    return resp


class TestNetworkErrorHandling:
    def test_404_raises_user_not_found(self):
        import requests
        from modules.chess_com_loader import fetch_archives, ChessComError
        with patch("modules.chess_com_loader.requests.get",
                   return_value=make_status_response(404)):
            with pytest.raises(ChessComError, match="não encontrado"):
                fetch_archives("ghost_user")

    def test_429_raises_rate_limit_error(self):
        from modules.chess_com_loader import fetch_archives, ChessComError
        with patch("modules.chess_com_loader.requests.get",
                   return_value=make_status_response(429)):
            with pytest.raises(ChessComError, match="429"):
                fetch_archives("sprandel")

    def test_timeout_raises_chesscom_error(self):
        import requests
        from modules.chess_com_loader import fetch_archives, ChessComError
        with patch("modules.chess_com_loader.requests.get",
                   side_effect=requests.Timeout()):
            with pytest.raises(ChessComError, match="Timeout"):
                fetch_archives("sprandel")

    def test_connection_error_raises_chesscom_error(self):
        import requests
        from modules.chess_com_loader import fetch_games_from_archive, ChessComError
        with patch("modules.chess_com_loader.requests.get",
                   side_effect=requests.ConnectionError()):
            with pytest.raises(ChessComError, match="conexão"):
                fetch_games_from_archive("https://api.chess.com/pub/x")

    def test_request_includes_timeout(self):
        from modules.chess_com_loader import fetch_archives
        with patch("modules.chess_com_loader.requests.get",
                   return_value=make_mock_response(ARCHIVE_RESPONSE)) as mock_get:
            fetch_archives("sprandel")
        assert mock_get.call_args.kwargs.get("timeout") is not None


class TestFetchArchives:
    def test_returns_list_of_archive_urls(self):
        from modules.chess_com_loader import fetch_archives
        with patch("modules.chess_com_loader.requests.get",
                   return_value=make_mock_response(ARCHIVE_RESPONSE)):
            result = fetch_archives("sprandel")
        assert isinstance(result, list)
        assert len(result) == 3

    def test_calls_correct_api_endpoint(self):
        from modules.chess_com_loader import fetch_archives
        with patch("modules.chess_com_loader.requests.get",
                   return_value=make_mock_response(ARCHIVE_RESPONSE)) as mock_get:
            fetch_archives("sprandel")
        called_url = mock_get.call_args[0][0]
        assert "sprandel" in called_url
        assert "archives" in called_url

    def test_sends_user_agent_header(self):
        from modules.chess_com_loader import fetch_archives
        with patch("modules.chess_com_loader.requests.get",
                   return_value=make_mock_response(ARCHIVE_RESPONSE)) as mock_get:
            fetch_archives("sprandel")
        headers = mock_get.call_args[1].get("headers", {})
        assert "User-Agent" in headers


class TestFetchGamesFromArchive:
    def test_returns_list_of_game_dicts(self):
        from modules.chess_com_loader import fetch_games_from_archive
        url = "https://api.chess.com/pub/player/sprandel/games/2024/01"
        with patch("modules.chess_com_loader.requests.get",
                   return_value=make_mock_response(GAMES_RESPONSE)):
            result = fetch_games_from_archive(url)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_each_game_dict_has_pgn(self):
        from modules.chess_com_loader import fetch_games_from_archive
        url = "https://api.chess.com/pub/player/sprandel/games/2024/01"
        with patch("modules.chess_com_loader.requests.get",
                   return_value=make_mock_response(GAMES_RESPONSE)):
            result = fetch_games_from_archive(url)
        assert "pgn" in result[0]


class TestFetchRecentGames:
    def test_returns_list_of_game_color_tuples(self):
        from modules.chess_com_loader import fetch_recent_games
        with patch("modules.chess_com_loader.fetch_archives",
                   return_value=ARCHIVE_RESPONSE["archives"]), \
             patch("modules.chess_com_loader.fetch_games_from_archive",
                   return_value=GAMES_RESPONSE["games"]):
            result = fetch_recent_games("sprandel", n_games=50)
        assert isinstance(result, list)
        assert len(result) > 0
        game, color = result[0]
        assert isinstance(color, bool)  # chess.WHITE or chess.BLACK are bool

    def test_player_color_is_white_when_username_matches_white(self):
        from modules.chess_com_loader import fetch_recent_games
        with patch("modules.chess_com_loader.fetch_archives",
                   return_value=ARCHIVE_RESPONSE["archives"]), \
             patch("modules.chess_com_loader.fetch_games_from_archive",
                   return_value=GAMES_RESPONSE["games"]):
            result = fetch_recent_games("sprandel", n_games=50)
        _, color = result[0]
        assert color == chess.WHITE

    def test_player_color_is_black_when_username_matches_black(self):
        from modules.chess_com_loader import fetch_recent_games
        black_game = {
            "white": {"username": "opponent", "rating": 1200},
            "black": {"username": "sprandel", "rating": 1180},
            "pgn": MINIMAL_PGN.replace("White \"sprandel\"", "White \"opponent\"")
                              .replace("Black \"opponent\"", "Black \"sprandel\""),
            "time_control": "600",
            "rated": True,
        }
        with patch("modules.chess_com_loader.fetch_archives",
                   return_value=ARCHIVE_RESPONSE["archives"]), \
             patch("modules.chess_com_loader.fetch_games_from_archive",
                   return_value=[black_game]):
            result = fetch_recent_games("sprandel", n_games=50)
        _, color = result[0]
        assert color == chess.BLACK

    def test_respects_n_games_limit(self):
        from modules.chess_com_loader import fetch_recent_games
        many_archives = [f"https://api.chess.com/pub/player/sprandel/games/2024/{i:02d}" for i in range(1, 13)]
        with patch("modules.chess_com_loader.fetch_archives", return_value=many_archives), \
             patch("modules.chess_com_loader.fetch_games_from_archive",
                   return_value=GAMES_RESPONSE["games"]):
            result = fetch_recent_games("sprandel", n_games=1)
        assert len(result) == 1

    def test_skips_games_with_missing_pgn(self):
        from modules.chess_com_loader import fetch_recent_games
        games_with_missing = [
            {"white": {"username": "sprandel"}, "black": {"username": "opp"}, "pgn": ""},
            GAMES_RESPONSE["games"][0],
        ]
        single_archive = [ARCHIVE_RESPONSE["archives"][0]]
        with patch("modules.chess_com_loader.fetch_archives", return_value=single_archive), \
             patch("modules.chess_com_loader.fetch_games_from_archive",
                   return_value=games_with_missing):
            result = fetch_recent_games("sprandel", n_games=50)
        assert len(result) == 1

    def test_username_comparison_is_case_insensitive(self):
        from modules.chess_com_loader import fetch_recent_games
        upper_game = {**GAMES_RESPONSE["games"][0],
                      "white": {"username": "SPRANDEL", "rating": 1200}}
        with patch("modules.chess_com_loader.fetch_archives",
                   return_value=ARCHIVE_RESPONSE["archives"]), \
             patch("modules.chess_com_loader.fetch_games_from_archive",
                   return_value=[upper_game]):
            result = fetch_recent_games("sprandel", n_games=50)
        _, color = result[0]
        assert color == chess.WHITE
