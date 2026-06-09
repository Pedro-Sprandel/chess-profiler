import chess
import chess.pgn
import io
import requests
from config import HTTP_TIMEOUT

CHESS_COM_API = "https://api.chess.com/pub/player"
HEADERS = {"User-Agent": "ChessStrategicProfiler/1.0 (github.com/sprandel)"}


class ChessComError(RuntimeError):
    """Erro ao comunicar com a API pública do Chess.com."""


def _get_json(url: str, not_found_msg: str | None = None) -> dict:
    """
    Faz um GET na API do Chess.com com timeout e traduz falhas em mensagens claras.

    not_found_msg: mensagem a usar quando a resposta for 404 (ex: usuário inexistente).
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
    except requests.Timeout as e:
        raise ChessComError(f"Timeout ao acessar o Chess.com ({url}).") from e
    except requests.ConnectionError as e:
        raise ChessComError(f"Falha de conexão com o Chess.com ({url}).") from e

    if resp.status_code == 404 and not_found_msg:
        raise ChessComError(not_found_msg)
    if resp.status_code == 429:
        raise ChessComError(
            "Chess.com retornou 429 (limite de requisições atingido). "
            "Aguarde alguns instantes e tente novamente."
        )
    resp.raise_for_status()
    return resp.json()


def fetch_archives(username: str) -> list:
    """
    Fetches the list of monthly archive URLs for a Chess.com user.
    Returns a list of archive URL strings.
    """
    url = f"{CHESS_COM_API}/{username}/games/archives"
    data = _get_json(url, not_found_msg=f"Usuário '{username}' não encontrado no Chess.com.")
    return data["archives"]


def fetch_games_from_archive(archive_url: str) -> list:
    """
    Fetches all games from a Chess.com monthly archive URL.
    Returns a list of raw game dicts as returned by the API.
    """
    return _get_json(archive_url)["games"]


def fetch_recent_games(username: str, n_games: int = 50) -> list[tuple[chess.pgn.Game, bool]]:
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
