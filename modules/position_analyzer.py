import chess


def detect_concepts(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta conceitos estratégicos presentes numa posição.
    Retorna dicionário com conceitos detectados e seus detalhes.

    board: posição ANTES do lance do jogador
    player_color: cor do jogador sendo analisado
    """
    results = {}

    results["weak_square"] = detect_weak_squares(board, player_color)
    results["open_file"] = detect_open_files(board, player_color)
    results["isolated_pawn"] = detect_isolated_pawns(board, player_color)
    results["bishop_pair"] = detect_bishop_pair(board, player_color)
    results["knight_outpost"] = detect_knight_outpost(board, player_color)
    results["king_safety"] = detect_king_safety(board, player_color)
    results["space_advantage"] = detect_space_advantage(board, player_color)

    return results


def detect_weak_squares(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta casas fracas no campo do jogador (casas que seus peões não defendem).
    Uma casa fraca é aquela que nenhum peão aliado pode atacar agora ou futuramente.
    """
    weak_squares = []
    opponent_color = not player_color

    for square in chess.SQUARES:
        file = chess.square_file(square)
        rank = chess.square_rank(square)

        # Foca no campo do jogador (metade do tabuleiro)
        if player_color == chess.WHITE and rank < 4:
            continue
        if player_color == chess.BLACK and rank > 3:
            continue

        # Verifica se nenhum peão aliado pode defender essa casa
        can_be_defended = False
        for adj_file in [file - 1, file + 1]:
            if 0 <= adj_file <= 7:
                for r in range(8):
                    sq = chess.square(adj_file, r)
                    piece = board.piece_at(sq)
                    if piece and piece.piece_type == chess.PAWN and piece.color == player_color:
                        can_be_defended = True
                        break

        if not can_be_defended:
            # Verifica se o adversário tem peça que poderia ocupar essa casa
            if board.is_attacked_by(opponent_color, square):
                weak_squares.append(chess.square_name(square))

    return {
        "detected": len(weak_squares) > 0,
        "squares": weak_squares,
        "count": len(weak_squares)
    }


def detect_open_files(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta colunas abertas e semi-abertas.
    Verifica se o jogador tem torres/dama posicionadas para aproveitá-las.
    """
    open_files = []
    semi_open_files = []

    for file_idx in range(8):
        file_name = chess.FILE_NAMES[file_idx]
        white_pawn = False
        black_pawn = False

        for rank_idx in range(8):
            sq = chess.square(file_idx, rank_idx)
            piece = board.piece_at(sq)
            if piece and piece.piece_type == chess.PAWN:
                if piece.color == chess.WHITE:
                    white_pawn = True
                else:
                    black_pawn = True

        if not white_pawn and not black_pawn:
            open_files.append(file_name)
        elif player_color == chess.WHITE and not white_pawn and black_pawn:
            semi_open_files.append(file_name)
        elif player_color == chess.BLACK and not black_pawn and white_pawn:
            semi_open_files.append(file_name)

    # Verifica se o jogador tem torre/dama nessas colunas
    has_rook_on_open = False
    for file_name in open_files + semi_open_files:
        file_idx = chess.FILE_NAMES.index(file_name)
        for rank_idx in range(8):
            sq = chess.square(file_idx, rank_idx)
            piece = board.piece_at(sq)
            if piece and piece.color == player_color and piece.piece_type in [chess.ROOK, chess.QUEEN]:
                has_rook_on_open = True
                break

    return {
        "detected": len(open_files) > 0 or len(semi_open_files) > 0,
        "open_files": open_files,
        "semi_open_files": semi_open_files,
        "player_has_rook_on_open": has_rook_on_open
    }


def detect_isolated_pawns(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta peões isolados do jogador.
    Peão isolado: sem peões aliados nas colunas adjacentes.
    """
    isolated = []

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if not piece or piece.piece_type != chess.PAWN or piece.color != player_color:
            continue

        file = chess.square_file(square)
        has_neighbor = False

        for adj_file in [file - 1, file + 1]:
            if 0 <= adj_file <= 7:
                for rank in range(8):
                    sq = chess.square(adj_file, rank)
                    p = board.piece_at(sq)
                    if p and p.piece_type == chess.PAWN and p.color == player_color:
                        has_neighbor = True
                        break

        if not has_neighbor:
            isolated.append(chess.square_name(square))

    return {
        "detected": len(isolated) > 0,
        "squares": isolated,
        "count": len(isolated)
    }


def detect_bishop_pair(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta se o jogador tem par de bispos enquanto o adversário não.
    """
    opponent_color = not player_color

    player_bishops = sum(1 for sq in chess.SQUARES
                         if board.piece_at(sq) and
                         board.piece_at(sq).piece_type == chess.BISHOP and
                         board.piece_at(sq).color == player_color)

    opponent_bishops = sum(1 for sq in chess.SQUARES
                           if board.piece_at(sq) and
                           board.piece_at(sq).piece_type == chess.BISHOP and
                           board.piece_at(sq).color == opponent_color)

    has_pair = player_bishops >= 2
    opponent_has_pair = opponent_bishops >= 2

    return {
        "detected": has_pair and not opponent_has_pair,
        "player_bishops": player_bishops,
        "opponent_bishops": opponent_bishops
    }


def detect_knight_outpost(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta cavalos do jogador em postos avançados (casas fracas no campo adversário).
    """
    opponent_color = not player_color
    outposts = []

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if not piece or piece.piece_type != chess.KNIGHT or piece.color != player_color:
            continue

        rank = chess.square_rank(square)

        # Cavalo deve estar no campo adversário
        if player_color == chess.WHITE and rank < 4:
            continue
        if player_color == chess.BLACK and rank > 3:
            continue

        # Casa não pode ser atacada por peões adversários
        attacked_by_opponent_pawn = False
        file = chess.square_file(square)

        pawn_attack_ranks = [rank + 1] if player_color == chess.WHITE else [rank - 1]
        for pr in pawn_attack_ranks:
            if 0 <= pr <= 7:
                for pf in [file - 1, file + 1]:
                    if 0 <= pf <= 7:
                        sq = chess.square(pf, pr)
                        p = board.piece_at(sq)
                        if p and p.piece_type == chess.PAWN and p.color == opponent_color:
                            attacked_by_opponent_pawn = True

        if not attacked_by_opponent_pawn:
            outposts.append(chess.square_name(square))

    return {
        "detected": len(outposts) > 0,
        "squares": outposts
    }


def detect_king_safety(board: chess.Board, player_color: bool) -> dict:
    """
    Avalia a segurança do rei baseada em cobertura de peões.
    """
    king_square = board.king(player_color)
    if king_square is None:
        return {"detected": False, "exposed": False, "shield_pawns": 0}

    king_file = chess.square_file(king_square)
    king_rank = chess.square_rank(king_square)

    shield_pawns = 0
    pawn_ranks = [king_rank + 1] if player_color == chess.WHITE else [king_rank - 1]

    for pf in range(max(0, king_file - 1), min(8, king_file + 2)):
        for pr in pawn_ranks:
            if 0 <= pr <= 7:
                sq = chess.square(pf, pr)
                p = board.piece_at(sq)
                if p and p.piece_type == chess.PAWN and p.color == player_color:
                    shield_pawns += 1

    # Rei está exposto se tiver menos de 2 peões de escudo e ainda não roque
    has_castled = (player_color == chess.WHITE and king_file in [6, 2]) or \
                  (player_color == chess.BLACK and king_file in [6, 2])
    exposed = shield_pawns < 2

    return {
        "detected": exposed,
        "exposed": exposed,
        "shield_pawns": shield_pawns,
        "king_square": chess.square_name(king_square),
        "has_castled_position": has_castled
    }


def detect_space_advantage(board: chess.Board, player_color: bool) -> dict:
    """
    Calcula vantagem de espaço baseada em casas controladas no campo adversário.
    """
    opponent_color = not player_color
    player_space = 0
    opponent_space = 0

    for square in chess.SQUARES:
        rank = chess.square_rank(square)

        # Espaço no campo adversário (ranks 5-7 para brancas, 0-2 para pretas)
        if player_color == chess.WHITE and rank >= 4:
            if board.is_attacked_by(player_color, square):
                player_space += 1
        elif player_color == chess.BLACK and rank <= 3:
            if board.is_attacked_by(player_color, square):
                player_space += 1

        if opponent_color == chess.WHITE and rank >= 4:
            if board.is_attacked_by(opponent_color, square):
                opponent_space += 1
        elif opponent_color == chess.BLACK and rank <= 3:
            if board.is_attacked_by(opponent_color, square):
                opponent_space += 1

    advantage = player_space - opponent_space

    return {
        "detected": advantage > 5,
        "player_space": player_space,
        "opponent_space": opponent_space,
        "advantage": advantage
    }
