import chess

_PIECE_VALUE = {
    chess.PAWN:   100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    # Rei "vale" mais que tudo: numa troca simulada, capturar com o rei numa casa
    # ainda defendida gera recaptura de valor altíssimo, o que descarta a sequência
    # — aproximação do fato de que essa captura seria ilegal.
    chess.KING:   10000,
}


def _least_valuable_attacker(board: chess.Board, square: int, color: bool):
    """Retorna (casa, valor) do atacante mais barato de `color` sobre `square`, ou None."""
    best = None
    for a in board.attackers(color, square):
        piece = board.piece_at(a)
        if piece is None:
            continue
        value = _PIECE_VALUE.get(piece.piece_type, 0)
        if best is None or value < best[1]:
            best = (a, value)
    return best


def static_exchange_gain(board: chess.Board, square: int, color: bool) -> int:
    """
    SEE (static exchange evaluation) simplificado: ganho material líquido (em
    centipawns, peão=100) que `color` obtém iniciando a sequência de capturas na
    casa `square`, com ambos os lados capturando sempre com a peça mais barata e
    podendo parar quando continuar perde material.

    > 0 significa que capturar na casa ganha material. Ignora cravadas e raios X.
    """
    target = board.piece_at(square)
    if target is None:
        return 0
    attacker = _least_valuable_attacker(board, square, color)
    if attacker is None:
        return 0

    attacker_sq, _ = attacker
    b = board.copy(stack=False)
    piece = b.piece_at(attacker_sq)
    b.remove_piece_at(attacker_sq)
    b.set_piece_at(square, piece)
    gain = _PIECE_VALUE.get(target.piece_type, 0) - static_exchange_gain(b, square, not color)
    return max(0, gain)


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
    results["passed_pawn"] = detect_passed_pawns(board, player_color)
    results["doubled_pawn"] = detect_doubled_pawns(board, player_color)
    results["rook_on_7th"] = detect_rook_on_7th(board, player_color)
    results["bad_bishop"] = detect_bad_bishop(board, player_color)
    results["pawn_majority"] = detect_pawn_majority(board, player_color)
    results["piece_activity"] = detect_piece_activity(board, player_color)
    results["overloaded_piece"] = detect_overloaded_piece(board, player_color)
    results["hanging_piece"] = detect_hanging_piece(board, player_color)
    results["backward_pawn"] = detect_backward_pawn(board, player_color)
    results["center_control"] = detect_center_control(board, player_color)

    return results


def detect_weak_squares(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta casas fracas (buracos) no campo do jogador: casas nas fileiras 3-4
    (6-5 para as pretas) que nenhum peão aliado pode vir a defender e que uma
    peça adversária pode ocupar (Silman: "hole in your camp").

    Três condições:
      1. Casa na zona de buracos do próprio campo (fileiras 3-4 / 6-5)
      2. Nenhum peão aliado ATRÁS da casa nas colunas adjacentes — só peões que
         ainda não passaram da casa podem um dia defendê-la
      3. Uma peça adversária já ocupa a casa, ou pode ocupá-la (cavalo, bispo,
         torre ou dama atacando a casa vazia)
    """
    weak_squares = []
    opponent_color = not player_color
    _OCCUPIERS = (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
    relevant_ranks = (2, 3) if player_color == chess.WHITE else (5, 4)

    for square in chess.SQUARES:
        rank = chess.square_rank(square)
        if rank not in relevant_ranks:
            continue
        file = chess.square_file(square)

        occupant = board.piece_at(square)
        if occupant and occupant.color == player_color:
            continue  # casa ocupada por peça própria — não há o que infiltrar

        # Só peões atrás da casa (que ainda podem avançar até defendê-la) contam
        can_be_defended = False
        behind_ranks = range(0, rank) if player_color == chess.WHITE else range(rank + 1, 8)
        for adj_file in [file - 1, file + 1]:
            if not 0 <= adj_file <= 7:
                continue
            for r in behind_ranks:
                piece = board.piece_at(chess.square(adj_file, r))
                if piece and piece.piece_type == chess.PAWN and piece.color == player_color:
                    can_be_defended = True
                    break
            if can_be_defended:
                break
        if can_be_defended:
            continue

        if occupant is not None:
            # Peça adversária já instalada no buraco — fraqueza consumada
            if occupant.piece_type in _OCCUPIERS:
                weak_squares.append(chess.square_name(square))
            continue

        # Casa vazia: o adversário precisa de uma peça capaz de ocupá-la
        occupiable = any(
            (p := board.piece_at(a)) and p.piece_type in _OCCUPIERS
            for a in board.attackers(opponent_color, square)
        )
        if occupiable:
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
    Detecta cavalos do jogador em postos avançados (definição de Silman):
      1. Cavalo no campo adversário
      2. Nenhum peão adversário nas colunas adjacentes pode atacar a casa —
         nem agora, nem avançando (o cavalo não pode ser expulso por peões)
      3. Cavalo apoiado por um peão aliado
    """
    opponent_color = not player_color
    outposts = []

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if not piece or piece.piece_type != chess.KNIGHT or piece.color != player_color:
            continue

        rank = chess.square_rank(square)
        file = chess.square_file(square)

        # Cavalo deve estar no campo adversário
        if player_color == chess.WHITE and rank < 4:
            continue
        if player_color == chess.BLACK and rank > 3:
            continue

        # Nenhum peão adversário nas colunas adjacentes pode jamais atacar a casa.
        # Para as brancas: um peão preto em (coluna adjacente, fileira > rank) ainda
        # pode avançar até rank+1 e atacar o cavalo.
        can_be_kicked = False
        threat_ranks = range(rank + 1, 8) if player_color == chess.WHITE else range(rank - 1, -1, -1)
        for pf in [file - 1, file + 1]:
            if not 0 <= pf <= 7:
                continue
            for pr in threat_ranks:
                p = board.piece_at(chess.square(pf, pr))
                if p and p.piece_type == chess.PAWN and p.color == opponent_color:
                    can_be_kicked = True
                    break
            if can_be_kicked:
                break
        if can_be_kicked:
            continue

        # Apoio de peão aliado: peão em coluna adjacente uma fileira atrás
        support_rank = rank - 1 if player_color == chess.WHITE else rank + 1
        supported = False
        if 0 <= support_rank <= 7:
            for pf in [file - 1, file + 1]:
                if 0 <= pf <= 7:
                    p = board.piece_at(chess.square(pf, support_rank))
                    if p and p.piece_type == chess.PAWN and p.color == player_color:
                        supported = True
                        break
        if not supported:
            continue

        outposts.append(chess.square_name(square))

    return {
        "detected": len(outposts) > 0,
        "squares": outposts
    }


def detect_king_safety(board: chess.Board, player_color: bool) -> dict:
    """
    Avalia a segurança do rei baseada em cobertura de peões.

    Só é relevante no middlegame: requer que o adversário tenha pelo menos
    uma dama, uma torre, ou dois ou mais peças menores. Em finais de rei e
    peões a exposição do rei é desejável, não uma fraqueza.
    """
    king_square = board.king(player_color)
    if king_square is None:
        return {"detected": False, "exposed": False, "shield_pawns": 0,
                "open_files_near_king": [], "king_in_center": False}

    opponent_color = not player_color
    _ATTACKERS = (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
    opponent_pieces = [
        board.piece_at(sq).piece_type
        for sq in chess.SQUARES
        if (p := board.piece_at(sq)) and p.color == opponent_color and p.piece_type in _ATTACKERS
    ]
    has_queen_or_rook = any(pt in (chess.QUEEN, chess.ROOK) for pt in opponent_pieces)
    # King safety is only a concern when opponent can realistically attack:
    # at least one major piece, or two or more minor pieces.
    if not has_queen_or_rook and len(opponent_pieces) < 2:
        return {
            "detected": False,
            "exposed": False,
            "shield_pawns": 0,
            "open_files_near_king": [],
            "king_in_center": False,
            "king_square": chess.square_name(king_square),
            "has_castled_position": False,
        }

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

    # Colunas sem peão aliado na região do rei (aberta ou semi-aberta contra ele):
    # avenidas diretas para torres e dama adversárias.
    open_files_near_king = []
    for pf in range(max(0, king_file - 1), min(8, king_file + 2)):
        has_own_pawn = any(
            (p := board.piece_at(chess.square(pf, r))) and
            p.piece_type == chess.PAWN and p.color == player_color
            for r in range(8)
        )
        if not has_own_pawn:
            open_files_near_king.append(chess.FILE_NAMES[pf])

    # Rei preso no centro: nas colunas c-f, sem direito de roque restante,
    # com a dama adversária ainda no tabuleiro.
    opponent_has_queen = any(pt == chess.QUEEN for pt in opponent_pieces)
    king_in_center = (
        king_file in (2, 3, 4, 5)
        and not board.has_castling_rights(player_color)
        and opponent_has_queen
    )

    back_rank = 0 if player_color == chess.WHITE else 7
    has_castled = king_rank == back_rank and king_file in [6, 2]
    exposed = shield_pawns < 2 or bool(open_files_near_king) or king_in_center

    return {
        "detected": exposed,
        "exposed": exposed,
        "shield_pawns": shield_pawns,
        "open_files_near_king": open_files_near_king,
        "king_in_center": king_in_center,
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


def detect_passed_pawns(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta peões passados: sem peões adversários à frente na mesma coluna
    ou nas colunas adjacentes.
    """
    opponent_color = not player_color
    passed = []

    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece or piece.piece_type != chess.PAWN or piece.color != player_color:
            continue

        file = chess.square_file(sq)
        rank = chess.square_rank(sq)
        is_passed = True

        ranks_ahead = range(rank + 1, 8) if player_color == chess.WHITE else range(rank - 1, -1, -1)
        for r in ranks_ahead:
            for f in [file - 1, file, file + 1]:
                if 0 <= f <= 7:
                    s = chess.square(f, r)
                    p = board.piece_at(s)
                    if p and p.piece_type == chess.PAWN and p.color == opponent_color:
                        is_passed = False
                        break
            if not is_passed:
                break

        if is_passed:
            passed.append(chess.square_name(sq))

    return {
        "detected": len(passed) > 0,
        "squares": passed,
        "count": len(passed)
    }


def detect_doubled_pawns(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta peões dobrados: duas ou mais peões do jogador na mesma coluna.
    """
    file_counts = [0] * 8
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece and piece.piece_type == chess.PAWN and piece.color == player_color:
            file_counts[chess.square_file(sq)] += 1

    doubled_files = [chess.FILE_NAMES[f] for f in range(8) if file_counts[f] >= 2]

    return {
        "detected": len(doubled_files) > 0,
        "files": doubled_files,
        "count": len(doubled_files)
    }


def detect_rook_on_7th(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta torres do jogador na 7ª fileira (rank 6 para brancas, rank 1 para pretas).
    """
    target_rank = 6 if player_color == chess.WHITE else 1
    squares = []

    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece and piece.piece_type == chess.ROOK and piece.color == player_color:
            if chess.square_rank(sq) == target_rank:
                squares.append(chess.square_name(sq))

    return {
        "detected": len(squares) > 0,
        "squares": squares
    }


def detect_bad_bishop(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta bispos ruins: bispos cujos peões aliados estão majoritariamente
    nas mesmas casas de cor, bloqueando-o.
    """
    bad_bishops = []

    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece or piece.piece_type != chess.BISHOP or piece.color != player_color:
            continue

        bishop_color_parity = (chess.square_file(sq) + chess.square_rank(sq)) % 2

        same_color_pawns = 0
        total_pawns = 0
        for psq in chess.SQUARES:
            p = board.piece_at(psq)
            if p and p.piece_type == chess.PAWN and p.color == player_color:
                total_pawns += 1
                if (chess.square_file(psq) + chess.square_rank(psq)) % 2 == bishop_color_parity:
                    same_color_pawns += 1

        # Bispo é ruim se 60%+ dos próprios peões estão na mesma cor
        if total_pawns >= 3 and same_color_pawns / total_pawns >= 0.6:
            bad_bishops.append(chess.square_name(sq))

    return {
        "detected": len(bad_bishops) > 0,
        "squares": bad_bishops,
        "count": len(bad_bishops)
    }


def detect_pawn_majority(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta maioria de peões em um dos flancos (dama: colunas a-d, rei: colunas e-h).
    """
    opponent_color = not player_color
    player_qs = player_ks = opp_qs = opp_ks = 0

    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece or piece.piece_type != chess.PAWN:
            continue
        f = chess.square_file(sq)
        if piece.color == player_color:
            if f <= 3:
                player_qs += 1
            else:
                player_ks += 1
        else:
            if f <= 3:
                opp_qs += 1
            else:
                opp_ks += 1

    has_qs_majority = player_qs > opp_qs
    has_ks_majority = player_ks > opp_ks

    return {
        "detected": has_qs_majority or has_ks_majority,
        "queenside_majority": has_qs_majority,
        "kingside_majority": has_ks_majority,
        "player_queenside": player_qs,
        "player_kingside": player_ks,
        "opponent_queenside": opp_qs,
        "opponent_kingside": opp_ks
    }


def detect_piece_activity(board: chess.Board, player_color: bool) -> dict:
    """
    Compara a mobilidade média das peças do jogador com as do adversário.
    Exclui peões e reis.
    """
    opponent_color = not player_color

    def avg_mobility(color):
        total = 0
        count = 0
        for sq in chess.SQUARES:
            piece = board.piece_at(sq)
            if piece and piece.color == color and piece.piece_type not in [chess.PAWN, chess.KING]:
                total += len(board.attacks(sq))
                count += 1
        return total / count if count > 0 else 0.0

    player_mob = avg_mobility(player_color)
    opp_mob = avg_mobility(opponent_color)
    advantage = player_mob - opp_mob

    return {
        "detected": advantage > 3.0,
        "player_mobility": round(player_mob, 1),
        "opponent_mobility": round(opp_mob, 1),
        "advantage": round(advantage, 1)
    }


def _is_real_threat(board: chess.Board, sq: int, player_color: bool) -> bool:
    """
    True when the attack on sq constitutes a genuine material threat.

    A threat is real only if the cheapest attacker's value ≤ the target's value
    (capture is at worst an even exchange), OR the piece is completely undefended.
    Diferente do SEE, trocas IGUAIS contam: para fins de sobrecarga, uma peça em
    troca igual ainda depende do defensor — se ele sair, ela simplesmente cai.
    """
    attacker = _least_valuable_attacker(board, sq, player_color)
    if attacker is None:
        return False

    target = board.piece_at(sq)
    target_value = _PIECE_VALUE.get(target.piece_type, 0)
    is_defended = bool(board.attackers(not player_color, sq))
    return attacker[1] <= target_value or not is_defended


def detect_overloaded_piece(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta peças do adversário que estão sobrecarregadas: defendem duas ou mais
    peças adversárias que estão sob ameaça real do jogador.

    Ameaça real: o atacante mais barato tem valor ≤ valor do alvo (troca igual ou
    vantajosa), ou a peça está completamente desprotegida.

    Isso exclui casos como dama ameaçando peão defendido — capturas economicamente
    inviáveis não constituem pressão genuína de sobrecarga.
    """
    opponent_color = not player_color

    threatened = [
        sq for sq in chess.SQUARES
        if board.piece_at(sq)
        and board.piece_at(sq).color == opponent_color
        and board.piece_at(sq).piece_type != chess.KING
        and _is_real_threat(board, sq, player_color)
    ]

    if len(threatened) < 2:
        return {"detected": False, "overloaded_squares": []}

    defender_to_threats: dict = {}
    for threat_sq in threatened:
        for def_sq in chess.SQUARES:
            def_piece = board.piece_at(def_sq)
            if not def_piece or def_piece.color != opponent_color:
                continue
            if threat_sq in board.attacks(def_sq):
                defender_to_threats.setdefault(def_sq, []).append(threat_sq)

    overloaded = [
        chess.square_name(sq)
        for sq, threats in defender_to_threats.items()
        if len(threats) >= 2
    ]

    return {
        "detected": len(overloaded) > 0,
        "overloaded_squares": overloaded,
    }


def detect_hanging_piece(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta peças do jogador que estão penduradas: o adversário ganha material
    capturando-as segundo a avaliação estática de trocas (SEE). Cobre tanto a
    peça atacada e indefesa quanto a peça defendida mas atacada por peça mais
    barata (ex.: cavalo defendido atacado por peão).

    board: posição ANTES do lance do jogador. Captura casos onde o jogador
    deixou uma peça pendurada no lance anterior e não a salva aqui.

    Exclui o rei (coberto por detect_king_safety).
    """
    hanging = []

    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece or piece.color != player_color or piece.piece_type == chess.KING:
            continue

        if static_exchange_gain(board, sq, not player_color) > 0:
            hanging.append(chess.square_name(sq))

    return {
        "detected": len(hanging) > 0,
        "squares": hanging,
        "count": len(hanging),
    }


def detect_backward_pawn(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta peões atrasados do jogador.
    Um peão está atrasado quando não pode avançar com segurança (a casa à frente
    é controlada por um peão adversário) e não tem apoio de peões aliados por
    trás nas colunas adjacentes.
    """
    opponent_color = not player_color
    backward = []

    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece or piece.piece_type != chess.PAWN or piece.color != player_color:
            continue

        rank = chess.square_rank(sq)
        file = chess.square_file(sq)

        advance_rank = rank + 1 if player_color == chess.WHITE else rank - 1
        if not (0 <= advance_rank <= 7):
            continue

        # Verifica se a casa de avanço é controlada por um peão adversário
        # Peões adversários que atacariam a casa de avanço estão um rank à frente dela
        opp_pawn_rank = advance_rank + 1 if player_color == chess.WHITE else advance_rank - 1
        advance_controlled = False
        if 0 <= opp_pawn_rank <= 7:
            for pf in [file - 1, file + 1]:
                if 0 <= pf <= 7:
                    p = board.piece_at(chess.square(pf, opp_pawn_rank))
                    if p and p.piece_type == chess.PAWN and p.color == opponent_color:
                        advance_controlled = True
                        break

        if not advance_controlled:
            continue

        # Verifica se há peão aliado por trás nas colunas adjacentes (apoio)
        has_support = False
        behind_ranks = range(rank - 1, -1, -1) if player_color == chess.WHITE else range(rank + 1, 8)
        for adj_file in [file - 1, file + 1]:
            if 0 <= adj_file <= 7:
                for r in behind_ranks:
                    p = board.piece_at(chess.square(adj_file, r))
                    if p and p.piece_type == chess.PAWN and p.color == player_color:
                        has_support = True
                        break
            if has_support:
                break

        if not has_support:
            backward.append(chess.square_name(sq))

    return {
        "detected": len(backward) > 0,
        "squares": backward,
        "count": len(backward),
    }


def detect_center_control(board: chess.Board, player_color: bool) -> dict:
    """
    Avalia o controle das quatro casas centrais (d4, e4, d5, e5).
    Detectado quando o jogador ataca pelo menos 2 casas centrais a mais que o adversário.
    """
    opponent_color = not player_color
    CENTER = [chess.D4, chess.D5, chess.E4, chess.E5]

    player_attacks = sum(1 for sq in CENTER if board.is_attacked_by(player_color, sq))
    opponent_attacks = sum(1 for sq in CENTER if board.is_attacked_by(opponent_color, sq))
    advantage = player_attacks - opponent_attacks

    return {
        "detected": advantage >= 2,
        "player_center_attacks": player_attacks,
        "opponent_center_attacks": opponent_attacks,
        "advantage": advantage,
    }
