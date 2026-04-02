import chess.pgn
import io


def load_games_from_file(pgn_path: str) -> list:
    """
    Carrega todas as partidas de um arquivo PGN.
    Retorna lista de objetos chess.pgn.Game.
    """
    games = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            games.append(game)
    print(f"[pgn_loader] {len(games)} partidas carregadas de {pgn_path}")
    return games


def load_games_from_string(pgn_string: str) -> list:
    """
    Carrega partidas a partir de uma string PGN.
    Útil para testes sem arquivo.
    """
    games = []
    pgn_io = io.StringIO(pgn_string)
    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break
        games.append(game)
    return games


def iterate_positions(game, player_color: bool):
    """
    Itera sobre todas as posições de uma partida onde é a vez do jogador analisado.
    Yields: (board_before, move_played, board_after)

    player_color: chess.WHITE ou chess.BLACK
    """
    board = game.board()
    for move in game.mainline_moves():
        if board.turn == player_color:
            board_before = board.copy()
            board.push(move)
            board_after = board.copy()
            yield board_before, move, board_after
        else:
            board.push(move)
