"""Atribuição erro → conceito (modules/attribution.py).

As posições vêm do conjunto de referência (data/gold_attributions.json), com os
vereditos humanos de docs/qualitative_analysis.md. Sem Stockfish: as linhas do
engine são passadas explicitamente quando o teste precisa delas.
"""
import chess

from modules.attribution import (
    allowed_tactic_gain,
    attribute_error,
    is_endgame,
    is_tactical_opportunity,
    line_material_gain,
)
from modules.position_analyzer import detect_concepts


def _attribute(fen, played, best, color=None, best_line=None, refutation=None):
    board = chess.Board(fen)
    color = board.turn if color is None else color
    validation = {"best_move": best, "best_line": best_line, "refutation_line": refutation}
    return attribute_error(board, played, validation, detect_concepts(board, color), color)


# Garfo de cavalo: Nc7+ ataca rei e torre.
FORK = "r3k3/8/8/1N6/8/8/8/4K3 w - - 0 1"


class TestLineMaterial:
    def test_fork_line_wins_the_rook(self):
        assert line_material_gain(chess.Board(FORK), ["b5c7", "e8d7", "c7a8"], chess.WHITE) == 500

    def test_pending_recapture_is_discounted(self):
        # Dama toma peão defendido e a linha termina antes da recaptura.
        board = chess.Board("4k3/8/2p5/3p4/8/8/8/3QK3 w - - 0 1")
        assert line_material_gain(board, ["d1d5"], chess.WHITE) == 100 - 900

    def test_illegal_line_is_cut(self):
        assert line_material_gain(chess.Board(FORK), ["b5c7", "a1a2"], chess.WHITE) == 0

    def test_allowed_fork(self):
        # Brancas tiram a torre para a1; Nc2+ garfa rei e torre.
        board = chess.Board("4k3/8/8/8/3n4/R7/8/4K3 w - - 0 1")
        gain = allowed_tactic_gain(board, chess.Move.from_uci("a3a1"),
                                   ["d4c2", "e1d2", "c2a1"], chess.WHITE)
        assert gain == 500


class TestTacticalPrecedence:
    def test_missed_fork_found_through_engine_line(self):
        a = _attribute(FORK, "e1e2", "b5c7", best_line=["b5c7", "e8d7", "c7a8"])
        assert (a["concept"], a["motif"], a["gain_cp"]) == ("missed_tactic", "line", 500)

    def test_allowed_tactic(self):
        a = _attribute("4k3/8/8/8/3n4/R7/8/4K3 w - - 0 1", "a3a1", "e1d2",
                       refutation=["d4c2", "e1d2", "c2a1"])
        assert (a["concept"], a["motif"]) == ("allowed_tactic", "refutation")

    def test_forcing_check_does_not_leak_into_space(self):
        # Veredito ❌: space_advantage atribuído quando o melhor lance era Qe4+.
        a = _attribute("r1b1kb1r/ppp2p1p/2n3p1/3qp3/8/5N2/PPPP1PPP/RNBQK2R b KQkq - 1 8",
                       "e5e4", "d5e4")
        assert (a["concept"], a["motif"]) == ("missed_tactic", "check")

    def test_converted_opportunity(self):
        assert is_tactical_opportunity(chess.Board(FORK), "b5c7", ["b5c7", "e8d7", "c7a8"], True)
        assert not is_tactical_opportunity(chess.Board(FORK), "e1e2", ["e1e2"], True)


class TestStructuralGates:
    def test_capture_elsewhere_does_not_count_for_backward_pawn(self):
        # Veredito ❌: peão atrasado em c3 apontado, mas o melhor lance é Rxd5.
        a = _attribute("2r1kb1r/pp3pp1/1p2b2p/3p1n2/1P5P/2P5/P3QP2/3RK2R w k - 3 22",
                       "d1c1", "d1d5")
        assert a["concept"] != "backward_pawn"

    def test_backward_pawn_break_kept(self):
        # Veredito ✅ (b6 → d5): o melhor lance avança o próprio peão atrasado.
        a = _attribute("r1b2r2/pp3pkp/3ppqp1/2p5/4P2P/2NPQP2/PPP2P2/R3K2R b KQ - 2 15",
                       "b7b6", "d6d5")
        assert (a["concept"], a["motif"]) == ("backward_pawn", "structural")

    def test_castling_attributed_to_king_safety(self):
        # Veredito ✅ (Nc6 → O-O).
        a = _attribute("1nbqk2r/2p1bppp/1p2pn2/2Pp4/1P1P4/2N1PN2/3B1PPP/Q3KB1R b Kk - 0 11",
                       "b8c6", "e8g8")
        assert a["concept"] == "king_safety"

    def test_rook_to_open_file(self):
        # Veredito ✅ (Nd2 → Rhe8).
        a = _attribute("2r4r/p3k2p/7R/1Np5/4nP2/1P4P1/P1P4P/5RK1 b - - 0 26", "e4d2", "h8e8")
        assert a["concept"] == "open_file"

    def test_hanging_piece_saved(self):
        # Veredito ✅ (c6 → Nc6 defende e5).
        a = _attribute("rnbqkbnr/ppp2ppp/8/3pp3/8/1P4P1/PBPPPP1P/RN1QKBNR b KQkq - 1 3",
                       "c7c6", "b8c6")
        assert (a["concept"], a["motif"]) == ("hanging_piece", "hanging")


class TestFailClosed:
    def test_no_best_move(self):
        assert _attribute(FORK, "e1e2", None)["concept"] is None

    def test_best_equals_played(self):
        assert _attribute(FORK, "b5c7", "b5c7")["concept"] is None

    def test_illegal_best_move(self):
        assert _attribute(FORK, "e1e2", "a1a8")["concept"] is None


def test_endgame_detection():
    assert is_endgame(chess.Board("8/1p6/5k2/2PK1p2/4nN1P/6P1/8/8 w - - 10 43"))
    assert not is_endgame(chess.Board())
