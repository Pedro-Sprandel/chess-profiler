"""
attribution.py — decide a qual conceito pertence um erro confirmado pelo Stockfish.

Substitui a atribuição "todo conceito detectado que passa em is_instructive" por uma
cascata com precedência, que separa erros táticos de estratégicos e exige vínculo
causal concreto entre o melhor lance e o conceito. Motivação: a validação qualitativa
do TCC (docs/qualitative_analysis.md) mostrou que os falsos positivos têm sempre a
mesma assinatura — melhor lance forçante (xeque, captura) vazando para conceitos
estruturais por co-ocorrência.

Ordem de precedência (o primeiro que se aplica leva o erro, e só ele):

  1. missed_tactic   — o melhor lance ganhava material: captura vantajosa por SEE, ou
                       a linha principal do Stockfish ganha ≥ TACTIC_LINE_GAIN_CP para o
                       jogador em poucos lances (garfos, cravadas, descobertas…).
  2. hanging_piece   — o jogador tinha peça pendurada e o melhor lance cuida dela.
  3. allowed_tactic  — o lance jogado entrega material: a melhor resposta do adversário
                       ganha ≥ TACTIC_LINE_GAIN_CP ao longo da linha de refutação.
  4. missed_tactic   — o melhor lance é um xeque (lance forçante sem ganho imediato).
  5. um conceito estratégico — entre os detectados na posição, o de maior ganho
                       relativo ao seu limiar, desde que passe em TODOS os filtros:
                         · não é um final para conceitos de meio-jogo;
                         · tipo de peça exigido pelo conceito;
                         · melhor lance não é xeque;
                         · captura só conta se capturar numa casa do próprio conceito;
                         · localidade: o melhor lance sai de, chega a ou ataca as casas
                           que o detector apontou;
                         · ganho de placar do conceito ≥ limiar meio lance depois.
  6. nenhum          — o erro fica "sem conceito" (candidato ao classificador LLM).

Em caso de dúvida (sem melhor lance, exceção), não atribui: a precisão vem antes da
cobertura; o que sobra vai para o classificador LLM com origem marcada.

Avaliado em data/gold_attributions.json (scripts/evaluate_precision.py). Um filtro de
"persistência" (exigir que o ganho estrutural continue no fim das linhas do engine)
foi testado e descartado: não removeu nenhum falso positivo julgado e derrubou
rupturas de peão legítimas (d3-d4, g3-g4), porque as trocas seguintes na linha mudam
a estrutura de novo.
"""

import chess

from config import TACTIC_LINE_GAIN_CP
from modules.concept_relevance import (
    CONCEPT_REQUIRED_PIECE,
    CONCEPT_SCORE_THRESHOLD,
    _DEFAULT_THRESHOLD,
    _concept_score,
    _is_material_winning_capture,
)
from modules.position_analyzer import detect_concepts, static_exchange_gain

# Conceitos derivados (não vêm de detect_concepts).
TACTICAL_CONCEPTS = ("missed_tactic", "allowed_tactic")

_VALUE = {chess.PAWN: 100, chess.KNIGHT: 300, chess.BISHOP: 300,
          chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}
_NON_PAWN = {chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}

# Final: material de peças (sem peões e reis) somado dos dois lados ≤ isto.
# Torre + peça menor para cada lado (16) é final; duas torres + peça (26) não.
ENDGAME_NON_PAWN_MATERIAL = 20

# Conceitos de meio-jogo que perdem o sentido num final simplificado.
MIDDLEGAME_ONLY = {"space_advantage", "center_control"}

# Tipo de peça exigido além do de concept_relevance: espaço se ganha com peões
# (Silman: o espaço é definido pelas cadeias de peões).
EXTRA_REQUIRED_PIECE = {"space_advantage": {chess.PAWN}}

# Ordem de desempate (mais específico primeiro).
_TIE_ORDER = ["king_safety", "open_file", "rook_on_7th", "knight_outpost", "passed_pawn",
              "backward_pawn", "isolated_pawn", "doubled_pawn", "weak_square", "bad_bishop",
              "bishop_pair", "overloaded_piece", "pawn_majority", "center_control",
              "space_advantage", "piece_activity"]
_CENTER = {chess.D4, chess.D5, chess.E4, chess.E5}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _moves(line) -> list[chess.Move]:
    out = []
    for m in line or []:
        try:
            out.append(m if isinstance(m, chess.Move) else chess.Move.from_uci(m))
        except ValueError:
            break
    return out


def _balance(board: chess.Board, color: bool) -> int:
    """Material de `color` menos o do adversário (cp)."""
    total = 0
    for piece in board.piece_map().values():
        v = _VALUE[piece.piece_type]
        total += v if piece.color == color else -v
    return total


def line_material_gain(board: chess.Board, line, color: bool) -> int:
    """Ganho de material de `color` ao longo de uma linha do engine (cp).

    Mede só em posições "assentadas" (é a vez de `color`, ou seja, o adversário já
    respondeu). Se a linha termina logo depois de uma captura de `color`, desconta a
    recaptura pendente por SEE. Linhas inválidas são cortadas no primeiro lance ilegal.
    """
    b = board.copy(stack=False)
    start = _balance(b, color)
    settled = start
    last_to = None
    for move in _moves(line):
        if move not in b.legal_moves:
            break
        last_to = move.to_square
        b.push(move)
        if b.turn == color:
            settled = _balance(b, color)
    if b.turn != color and last_to is not None and b.move_stack:
        pending = _balance(b, color) - static_exchange_gain(b, last_to, b.turn)
        settled = pending
    return settled - start


def is_endgame(board: chess.Board) -> bool:
    material = sum(_NON_PAWN.get(p.piece_type, 0) for p in board.piece_map().values())
    return material <= ENDGAME_NON_PAWN_MATERIAL


def _squares(names) -> set[int]:
    out = set()
    for n in names or []:
        try:
            out.add(chess.parse_square(n))
        except ValueError:
            pass
    return out


def _file_squares(files) -> set[int]:
    out = set()
    for f in files or []:
        idx = "abcdefgh".find(f)
        if idx >= 0:
            out |= {chess.square(idx, r) for r in range(8)}
    return out


def relevant_squares(board: chess.Board, concept: str, details: dict,
                     player_color: bool) -> set[int] | None:
    """Casas a que o melhor lance precisa estar ligado para o erro ser do conceito.

    None = o conceito não tem casas próprias (o vínculo fica a cargo do placar e
    dos outros filtros).
    """
    if concept in ("weak_square", "isolated_pawn", "backward_pawn", "passed_pawn",
                   "bad_bishop", "hanging_piece", "knight_outpost", "rook_on_7th"):
        return _squares(details.get("squares"))
    if concept == "doubled_pawn":
        files = _file_squares(details.get("files"))
        return {sq for sq in files
                if (p := board.piece_at(sq)) and p.piece_type == chess.PAWN and p.color == player_color}
    if concept == "open_file":
        return _file_squares((details.get("open_files") or []) + (details.get("semi_open_files") or []))
    if concept == "overloaded_piece":
        defenders = _squares(details.get("overloaded_squares"))
        defended = set()
        for sq in defenders:
            defended |= set(board.attacks(sq))
        return defenders | defended
    if concept == "king_safety":
        king = board.king(player_color)
        if king is None:
            return None
        return {sq for sq in chess.SQUARES if chess.square_distance(sq, king) <= 2}
    if concept == "center_control":
        return set(_CENTER)
    if concept == "pawn_majority":
        files = set()
        if details.get("queenside_majority"):
            files |= set("abcd")
        if details.get("kingside_majority"):
            files |= set("efgh")
        return _file_squares(files)
    return None


def _touches(board: chess.Board, move: chess.Move, squares: set[int]) -> bool:
    if move.from_square in squares or move.to_square in squares:
        return True
    after = board.copy(stack=False)
    after.push(move)
    return bool(set(after.attacks(move.to_square)) & squares)


# ── Camada tática ─────────────────────────────────────────────────────────────

def missed_tactic_motif(board: chess.Board, best_move: chess.Move | None, best_line,
                        player_color: bool) -> str | None:
    """'capture' / 'line' quando o melhor lance ganhava material; senão None."""
    if best_move is None:
        return None
    if _is_material_winning_capture(board, best_move):
        return "capture"
    line = _moves(best_line)
    if not line or line[0] != best_move:
        line = [best_move]
    if line_material_gain(board, line, player_color) >= TACTIC_LINE_GAIN_CP:
        return "line"
    return None


def allowed_tactic_gain(board: chess.Board, move_played: chess.Move, refutation_line,
                        player_color: bool) -> int:
    """Material que o adversário ganha ao longo da refutação do lance jogado (cp)."""
    line = _moves(refutation_line)
    if not line:
        return 0
    after = board.copy(stack=False)
    after.push(move_played)
    return line_material_gain(after, line, not player_color)


def is_tactical_opportunity(board: chess.Board, best_move_uci: str | None, best_line,
                            player_color: bool) -> bool:
    """O melhor lance era tático (ganho de material ou xeque) — para o denominador."""
    if not best_move_uci:
        return False
    try:
        best = chess.Move.from_uci(best_move_uci)
        if best not in board.legal_moves:
            return False
        return (missed_tactic_motif(board, best, best_line, player_color) is not None
                or board.gives_check(best))
    except ValueError:
        return False


# ── Conceitos estratégicos ────────────────────────────────────────────────────

def structural_candidates(board: chess.Board, move_played: chess.Move, best_move: chess.Move,
                          concepts_before: dict, player_color: bool) -> list[tuple[str, float]]:
    """Conceitos estratégicos que explicam o erro, com o ganho relativo ao limiar.

    Retorna [(conceito, razão)] ordenado do mais forte para o mais fraco; vazio se
    nenhum passa em todos os filtros (ver docstring do módulo).
    """
    if board.gives_check(best_move):
        return []  # forçante: tratado na camada tática

    endgame = is_endgame(board)
    is_capture = board.is_capture(best_move)
    mover = board.piece_at(best_move.from_square)
    if mover is None:
        return []

    after_played = board.copy(stack=False)
    after_played.push(move_played)
    after_best = board.copy(stack=False)
    after_best.push(best_move)
    concepts_played = detect_concepts(after_played, player_color)
    concepts_best = detect_concepts(after_best, player_color)

    out = []
    for concept, details in concepts_before.items():
        if concept in ("hanging_piece",) or not details.get("detected"):
            continue
        try:
            if endgame and concept in MIDDLEGAME_ONLY:
                continue
            required = CONCEPT_REQUIRED_PIECE.get(concept) or EXTRA_REQUIRED_PIECE.get(concept)
            if required and mover.piece_type not in required:
                continue

            squares = relevant_squares(board, concept, details, player_color)
            if is_capture:
                # Uma captura muda contagens de estrutura "de graça": só vale se for
                # na própria casa do conceito (ex.: tomar o peão atrasado apontado).
                if not squares or best_move.to_square not in squares:
                    continue
            if squares is not None:
                if not squares or not _touches(board, best_move, squares):
                    continue

            threshold = CONCEPT_SCORE_THRESHOLD.get(concept, _DEFAULT_THRESHOLD)
            delta = _concept_score(concepts_best, concept) - _concept_score(concepts_played, concept)
            if delta < threshold:
                continue

            out.append((concept, delta / threshold))
        except Exception:
            continue  # na dúvida, não atribui

    order = {c: i for i, c in enumerate(_TIE_ORDER)}
    out.sort(key=lambda cr: (-cr[1], order.get(cr[0], len(order))))
    return out


def _hanging_piece_explains(board: chess.Board, move_played: chess.Move, best_move: chess.Move,
                            details: dict, player_color: bool) -> bool:
    """Peça do jogador pendurada e o melhor lance a salva (move, defende ou reduz)."""
    if not details.get("detected"):
        return False
    squares = _squares(details.get("squares"))
    if not squares or not _touches(board, best_move, squares):
        return False
    after_played = board.copy(stack=False)
    after_played.push(move_played)
    after_best = board.copy(stack=False)
    after_best.push(best_move)
    hanging_played = detect_concepts(after_played, player_color)["hanging_piece"].get("count", 0)
    hanging_best = detect_concepts(after_best, player_color)["hanging_piece"].get("count", 0)
    return hanging_best < hanging_played


# ── API ───────────────────────────────────────────────────────────────────────

def attribute_error(board: chess.Board, move_played_uci: str | None, validation: dict,
                    concepts_before: dict, player_color: bool) -> dict:
    """Atribui um erro confirmado a no máximo um conceito.

    Retorna {"concept": str | None, "source": "rule" | None, "motif": str | None,
             "gain_cp": int | None}. "motif" descreve o caminho da decisão:
    capture / line (tática perdida), refutation (tática permitida), check (forçante),
    hanging (peça pendurada), structural (conceito estratégico).
    """
    none = {"concept": None, "source": None, "motif": None, "gain_cp": None}
    best_uci = validation.get("best_move")
    if not best_uci or not move_played_uci or best_uci == move_played_uci:
        return none
    try:
        best = chess.Move.from_uci(best_uci)
        played = chess.Move.from_uci(move_played_uci)
        if best not in board.legal_moves or played not in board.legal_moves:
            return none
    except ValueError:
        return none

    best_line = validation.get("best_line")
    refutation = validation.get("refutation_line")

    motif = missed_tactic_motif(board, best, best_line, player_color)
    if motif:
        gain = line_material_gain(board, _moves(best_line) or [best], player_color)
        return {"concept": "missed_tactic", "source": "rule", "motif": motif, "gain_cp": gain}

    if _hanging_piece_explains(board, played, best, concepts_before.get("hanging_piece", {}),
                               player_color):
        return {"concept": "hanging_piece", "source": "rule", "motif": "hanging", "gain_cp": None}

    lost = allowed_tactic_gain(board, played, refutation, player_color)
    if lost >= TACTIC_LINE_GAIN_CP:
        return {"concept": "allowed_tactic", "source": "rule", "motif": "refutation", "gain_cp": lost}

    if board.gives_check(best):
        return {"concept": "missed_tactic", "source": "rule", "motif": "check", "gain_cp": None}

    candidates = structural_candidates(board, played, best, concepts_before, player_color)
    if candidates:
        return {"concept": candidates[0][0], "source": "rule", "motif": "structural",
                "gain_cp": None}
    return none
