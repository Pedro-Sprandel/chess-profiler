import chess
import chess.pgn
import io
import requests

CHESS_COM_API = "https://api.chess.com/pub/player"
HEADERS = {"User-Agent": "ChessStrategicProfiler/1.0 (github.com/sprandel)"}


def fetch_archives(username: str) -> list:
    """
    Fetches the list of monthly archive URLs for a Chess.com user.
    Returns a list of archive URL strings.
    """
    url = f"{CHESS_COM_API}/{username}/games/archives"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()["archives"]


def fetch_games_from_archive(archive_url: str) -> list:
    """
    Fetches all games from a Chess.com monthly archive URL.
    Returns a list of raw game dicts as returned by the API.
    """
    resp = requests.get(archive_url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()["games"]


def fetch_recent_games(username: str, n_games: int = 50) -> list:
    """
    Fetches the n_games most recent games for a Chess.com user.

    Iterates monthly archives from most recent backwards and stops as soon
    as n_games valid games have been collected.

    Returns a list of (chess.pgn.Game, player_color) tuples where
    player_color is chess.WHITE or chess.BLACK depending on which side
    the username played in each game.

    Games with empty or unparseable PGN are skipped.
    Username comparison is case-insensitive.
    """
    archives = fetch_archives(username)

    results = []
    for archive_url in reversed(archives):
        if len(results) >= n_games:
            break

        raw_games = fetch_games_from_archive(archive_url)
        for raw in reversed(raw_games):  # most recent first within the month
            if len(results) >= n_games:
                break

            pgn_str = raw.get("pgn", "").strip()
            if not pgn_str:
                continue

            game = chess.pgn.read_game(io.StringIO(pgn_str))
            if game is None:
                continue

            white_username = raw.get("white", {}).get("username", "")
            if white_username.lower() == username.lower():
                player_color = chess.WHITE
            else:
                player_color = chess.BLACK

            results.append((game, player_color))

    # Return in chronological order (oldest first)
    return list(reversed(results))
