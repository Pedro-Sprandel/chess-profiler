"""
fen_fetcher.py — Busca posições reais em formato FEN a partir do Chess.com.

Filtros disponíveis:
  - min_rating / max_rating : rating do adversário
  - opening_eco             : código ECO da abertura (ex: "B20", "E60")
  - opening_name            : substring do nome da abertura (ex: "Sicilian", "French")
  - move_range              : tupla (min_move, max_move) para selecionar posições
                              apenas dentro desse intervalo de lances
  - time_class              : "bullet", "blitz", "rapid", "daily" (None = todos)

Retorno de fetch_positions():
  Lista de dicts, cada um representando uma posição extraída de uma partida real:
  {
    "fen"          : str   — posição em formato FEN
    "move_number"  : int   — número do lance na partida
    "move_played"  : str   — lance jogado pelo jogador analisado (UCI)
    "player_color" : str   — "white" | "black"
    "white"        : str   — username das brancas
    "black"        : str   — username das pretas
    "white_rating" : int
    "black_rating" : int
    "opening"      : str   — nome da abertura
    "eco"          : str   — código ECO (ex: "B20")
    "game_url"     : str
  }
"""

import io
import re
import chess
import chess.pgn
import requests

CHESS_COM_API = "https://api.chess.com/pub/player"
HEADERS = {"User-Agent": "ChessStrategicProfiler/1.0 (github.com/sprandel)"}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _parse_eco_url(eco_url: str) -> tuple[str, str]:
    """
    Parses a Chess.com ECO URL into (eco_code, opening_name).

    Chess.com returns ECO as a URL like:
      https://www.chess.com/openings/Sicilian-Defense-Kan-Variation
    or a plain code like "B41".
    """
    if not eco_url:
        return ("", "")

    # Plain code (e.g. "B41")
    if re.match(r"^[A-E]\d{2}$", eco_url.strip()):
        return (eco_url.strip(), "")

    # URL — extract the last path segment
    slug = eco_url.rstrip("/").split("/")[-1]
    # ECO code is the 3-char prefix if it matches, otherwise infer from slug
    eco_code = ""
    opening_name = slug.replace("-", " ").title()

    # Some URLs have the ECO code embedded: /openings/B41-Sicilian-...
    code_match = re.match(r"^([A-E]\d{2})[- ]?(.*)", slug)
    if code_match:
        eco_code = code_match.group(1)
        opening_name = code_match.group(2).replace("-", " ").title()

    return (eco_code, opening_name)


def _extract_eco_from_pgn(pgn_str: str) -> tuple[str, str]:
    """Reads ECO and Opening headers from a PGN string."""
    eco = ""
    opening = ""
    for line in pgn_str.splitlines():
        m = re.match(r'\[ECO\s+"([^"]+)"\]', line)
        if m:
            eco = m.group(1)
        m = re.match(r'\[Opening\s+"([^"]+)"\]', line)
        if m:
            opening = m.group(1)
    return eco, opening


def _matches_filters(
    white_rating: int,
    black_rating: int,
    eco: str,
    opening: str,
    player_color: str,
    min_rating: int | None,
    max_rating: int | None,
    opening_eco: str | None,
    opening_name: str | None,
    time_class_game: str | None,
    time_class_filter: str | None,
) -> bool:
    # Time class filter
    if time_class_filter and time_class_game:
        if time_class_game.lower() != time_class_filter.lower():
            return False

    # Rating filter applies to the opponent's rating
    opponent_rating = black_rating if player_color == "white" else white_rating
    if min_rating is not None and opponent_rating < min_rating:
        return False
    if max_rating is not None and opponent_rating > max_rating:
        return False

    # Opening ECO filter (prefix match: "B" matches all B-codes, "B20" exact)
    if opening_eco:
        if not eco.upper().startswith(opening_eco.upper()):
            return False

    # Opening name filter (case-insensitive substring)
    if opening_name:
        if opening_name.lower() not in opening.lower():
            return False

    return True


def _positions_from_game(
    game: chess.pgn.Game,
    player_color: str,
    move_range: tuple[int, int],
) -> list[dict]:
    """
    Iterates through a game and yields position dicts within move_range.
    move_range is (min_move, max_move) in full-move numbers.
    """
    board = game.board()
    positions = []
    color = chess.WHITE if player_color == "white" else chess.BLACK

    for move in game.mainline_moves():
        full_move = board.fullmove_number
        is_player_turn = board.turn == color

        if full_move > move_range[1]:
            break

        if is_player_turn and full_move >= move_range[0]:
            positions.append({
                "fen": board.fen(),
                "move_number": full_move,
                "move_played": move.uci(),
            })

        board.push(move)

    return positions


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_positions(
    username: str,
    n_games: int = 50,
    min_rating: int | None = None,
    max_rating: int | None = None,
    opening_eco: str | None = None,
    opening_name: str | None = None,
    move_range: tuple[int, int] = (8, 40),
    time_class: str | None = None,
    max_positions: int | None = None,
) -> list[dict]:
    """
    Busca posições FEN de partidas reais do Chess.com com filtros.

    Parâmetros:
        username      : nome de usuário no Chess.com
        n_games       : quantas partidas buscar antes de aplicar filtros
        min_rating    : rating mínimo do adversário
        max_rating    : rating máximo do adversário
        opening_eco   : prefixo do código ECO (ex: "B", "B20", "E60")
        opening_name  : substring do nome da abertura (ex: "Sicilian", "French Defense")
        move_range    : (lance mínimo, lance máximo) para extrair posições
        time_class    : "bullet" | "blitz" | "rapid" | "daily" | None (todos)
        max_positions : limite total de posições retornadas (None = sem limite)

    Retorna:
        Lista de dicts com campos: fen, move_number, move_played, player_color,
        white, black, white_rating, black_rating, opening, eco, game_url.
    """
    url = f"{CHESS_COM_API}/{username}/games/archives"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    archives = resp.json()["archives"]

    collected_games = []
    for archive_url in reversed(archives):
        if len(collected_games) >= n_games:
            break
        resp = requests.get(archive_url, headers=HEADERS)
        resp.raise_for_status()
        raw_games = resp.json()["games"]
        for raw in reversed(raw_games):
            if len(collected_games) >= n_games:
                break
            if raw.get("pgn", "").strip():
                collected_games.append(raw)

    positions = []

    for raw in collected_games:
        pgn_str = raw.get("pgn", "").strip()
        if not pgn_str:
            continue

        # Determine player color
        white_user = raw.get("white", {}).get("username", "")
        player_color = "white" if white_user.lower() == username.lower() else "black"

        white_rating = raw.get("white", {}).get("rating", 0)
        black_rating = raw.get("black", {}).get("rating", 0)
        white_user_display = raw.get("white", {}).get("username", "White")
        black_user_display = raw.get("black", {}).get("username", "Black")
        game_url = raw.get("url", "")
        time_class_game = raw.get("time_class", "")

        # Parse ECO from PGN headers (more reliable than the API field)
        eco_pgn, opening_pgn = _extract_eco_from_pgn(pgn_str)

        # Use the API ECO URL for the opening name if PGN header didn't provide it
        eco_url = raw.get("eco", "")
        eco_api, eco_name = _parse_eco_url(eco_url)
        if not eco_pgn:
            eco_pgn = eco_api
        if not opening_pgn:
            opening_pgn = eco_name

        if not _matches_filters(
            white_rating, black_rating,
            eco_pgn, opening_pgn,
            player_color,
            min_rating, max_rating,
            opening_eco, opening_name,
            time_class_game, time_class,
        ):
            continue

        game = chess.pgn.read_game(io.StringIO(pgn_str))
        if game is None:
            continue

        for pos in _positions_from_game(game, player_color, move_range):
            positions.append({
                **pos,
                "player_color": player_color,
                "white": white_user_display,
                "black": black_user_display,
                "white_rating": white_rating,
                "black_rating": black_rating,
                "opening": opening_pgn,
                "eco": eco_pgn,
                "game_url": game_url,
            })
            if max_positions and len(positions) >= max_positions:
                return positions

    return positions


def fetch_positions_summary(positions: list[dict]) -> dict:
    """
    Returns a summary dict from a list of positions returned by fetch_positions().
    Useful for quickly inspecting what was collected.
    """
    if not positions:
        return {"total": 0}

    openings = {}
    for p in positions:
        key = f"{p['eco']} {p['opening']}".strip()
        openings[key] = openings.get(key, 0) + 1

    ratings = [
        p["black_rating"] if p["player_color"] == "white" else p["white_rating"]
        for p in positions
    ]

    return {
        "total_positions": len(positions),
        "unique_games": len({p["game_url"] for p in positions}),
        "move_range": (
            min(p["move_number"] for p in positions),
            max(p["move_number"] for p in positions),
        ),
        "opponent_rating": {
            "min": min(ratings),
            "max": max(ratings),
            "avg": round(sum(ratings) / len(ratings)),
        },
        "openings": dict(sorted(openings.items(), key=lambda x: -x[1])[:10]),
    }
