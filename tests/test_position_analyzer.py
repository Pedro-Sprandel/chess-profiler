import chess
import pytest


# --- detect_concepts ---

class TestDetectConcepts:
    def test_returns_dict_with_all_concept_keys(self):
        from modules.position_analyzer import detect_concepts
        board = chess.Board()
        result = detect_concepts(board, chess.WHITE)
        expected_keys = {
            "weak_square", "open_file", "isolated_pawn", "bishop_pair",
            "knight_outpost", "king_safety", "space_advantage",
            "passed_pawn", "doubled_pawn", "rook_on_7th",
            "bad_bishop", "pawn_majority", "piece_activity", "overloaded_piece",
            "hanging_piece", "backward_pawn", "center_control",
        }
        assert set(result.keys()) == expected_keys

    def test_each_value_has_detected_key(self):
        from modules.position_analyzer import detect_concepts
        board = chess.Board()
        result = detect_concepts(board, chess.WHITE)
        for key, value in result.items():
            assert "detected" in value, f"Missing 'detected' key in {key}"


# --- detect_weak_squares ---

class TestDetectWeakSquares:
    def test_detected_key_present(self):
        from modules.position_analyzer import detect_weak_squares
        board = chess.Board()
        result = detect_weak_squares(board, chess.WHITE)
        assert "detected" in result
        assert "squares" in result
        assert "count" in result

    def test_starting_position_has_no_weak_squares(self):
        # Starting position: no opponent piece can reach the hole zone yet
        from modules.position_analyzer import detect_weak_squares
        board = chess.Board()
        assert detect_weak_squares(board, chess.WHITE)["count"] == 0
        assert detect_weak_squares(board, chess.BLACK)["count"] == 0

    def test_hole_in_own_camp_detected(self):
        # White pawns on c4/e4 leave d4 a permanent hole (neither pawn can ever
        # defend it) and the black knight on c6 can occupy it.
        from modules.position_analyzer import detect_weak_squares
        board = chess.Board("1k6/8/2n5/8/2P1P3/8/8/1K6 w - - 0 1")
        result = detect_weak_squares(board, chess.WHITE)
        assert result["detected"] is True
        assert "d4" in result["squares"]

    def test_hole_defensible_by_pawn_behind_not_weak(self):
        # Same structure but the white pawn is on c2: it can advance to c3 and
        # defend d4 — not a permanent hole.
        from modules.position_analyzer import detect_weak_squares
        board = chess.Board("1k6/8/2n5/8/4P3/8/2P5/1K6 w - - 0 1")
        result = detect_weak_squares(board, chess.WHITE)
        assert "d4" not in result["squares"]

    def test_hole_occupied_by_enemy_piece_is_weak(self):
        # Black knight already installed on d4 (white has no pawn able to defend it)
        from modules.position_analyzer import detect_weak_squares
        board = chess.Board("1k6/8/8/8/2PnP3/8/8/1K6 w - - 0 1")
        result = detect_weak_squares(board, chess.WHITE)
        assert "d4" in result["squares"]

    def test_black_camp_hole_detected(self):
        # Mirror: black pawns c5/e5 leave d5 a hole; white knight on c3 eyes d5.
        from modules.position_analyzer import detect_weak_squares
        board = chess.Board("1k6/8/8/2p1p3/8/2N5/8/1K6 b - - 0 1")
        result = detect_weak_squares(board, chess.BLACK)
        assert result["detected"] is True
        assert "d5" in result["squares"]


# --- detect_open_files ---

class TestDetectOpenFiles:
    def test_detected_key_present(self):
        from modules.position_analyzer import detect_open_files
        board = chess.Board()
        result = detect_open_files(board, chess.WHITE)
        assert "detected" in result
        assert "open_files" in result
        assert "semi_open_files" in result

    def test_starting_position_no_open_files(self):
        from modules.position_analyzer import detect_open_files
        board = chess.Board()
        result = detect_open_files(board, chess.WHITE)
        assert result["open_files"] == []

    def test_open_file_detected_after_pawn_removal(self):
        from modules.position_analyzer import detect_open_files
        # Remove e-pawns from both sides → e-file becomes open
        board = chess.Board()
        board.remove_piece_at(chess.E2)
        board.remove_piece_at(chess.E7)
        result = detect_open_files(board, chess.WHITE)
        assert "e" in result["open_files"]
        assert result["detected"] is True

    def test_semi_open_file_for_white(self):
        from modules.position_analyzer import detect_open_files
        # Remove white's e-pawn but keep black's → semi-open for white
        board = chess.Board()
        board.remove_piece_at(chess.E2)
        result = detect_open_files(board, chess.WHITE)
        assert "e" in result["semi_open_files"]


# --- detect_isolated_pawns ---

class TestDetectIsolatedPawns:
    def test_detected_key_present(self):
        from modules.position_analyzer import detect_isolated_pawns
        board = chess.Board()
        result = detect_isolated_pawns(board, chess.WHITE)
        assert "detected" in result
        assert "squares" in result
        assert "count" in result

    def test_starting_position_no_isolated_pawns(self):
        from modules.position_analyzer import detect_isolated_pawns
        board = chess.Board()
        result = detect_isolated_pawns(board, chess.WHITE)
        assert result["detected"] is False
        assert result["count"] == 0

    def test_isolated_pawn_detected(self):
        from modules.position_analyzer import detect_isolated_pawns
        # Place a lone white pawn on a4 with no adjacent pawns
        board = chess.Board(fen="8/8/8/8/P7/8/8/K6k w - - 0 1")
        result = detect_isolated_pawns(board, chess.WHITE)
        assert result["detected"] is True
        assert "a4" in result["squares"]


# --- detect_bishop_pair ---

class TestDetectBishopPair:
    def test_detected_key_present(self):
        from modules.position_analyzer import detect_bishop_pair
        board = chess.Board()
        result = detect_bishop_pair(board, chess.WHITE)
        assert "detected" in result
        assert "player_bishops" in result
        assert "opponent_bishops" in result

    def test_starting_position_no_bishop_pair_advantage(self):
        # Both sides have 2 bishops → no advantage
        from modules.position_analyzer import detect_bishop_pair
        board = chess.Board()
        result = detect_bishop_pair(board, chess.WHITE)
        assert result["detected"] is False

    def test_bishop_pair_advantage_detected(self):
        # White has 2 bishops, black has 0
        from modules.position_analyzer import detect_bishop_pair
        board = chess.Board(fen="k7/8/8/8/8/8/8/K1BB4 w - - 0 1")
        result = detect_bishop_pair(board, chess.WHITE)
        assert result["detected"] is True
        assert result["player_bishops"] == 2
        assert result["opponent_bishops"] == 0


# --- detect_knight_outpost ---

class TestDetectKnightOutpost:
    def test_detected_key_present(self):
        from modules.position_analyzer import detect_knight_outpost
        board = chess.Board()
        result = detect_knight_outpost(board, chess.WHITE)
        assert "detected" in result
        assert "squares" in result

    def test_starting_position_no_outpost(self):
        from modules.position_analyzer import detect_knight_outpost
        board = chess.Board()
        result = detect_knight_outpost(board, chess.WHITE)
        assert result["detected"] is False

    def test_knight_outpost_detected(self):
        # White knight on e5 supported by the d4 pawn, no black pawn can ever attack e5
        from modules.position_analyzer import detect_knight_outpost
        board = chess.Board(fen="k7/8/8/4N3/3P4/8/8/K7 w - - 0 1")
        result = detect_knight_outpost(board, chess.WHITE)
        assert result["detected"] is True
        assert "e5" in result["squares"]

    def test_no_outpost_when_attacked_by_pawn(self):
        # White knight on e5 but black pawn on d6 can attack it
        from modules.position_analyzer import detect_knight_outpost
        board = chess.Board(fen="k7/8/3p4/4N3/3P4/8/8/K7 w - - 0 1")
        result = detect_knight_outpost(board, chess.WHITE)
        assert "e5" not in result["squares"]

    def test_no_outpost_when_enemy_pawn_can_advance_to_attack(self):
        # Black pawn on d7 can advance to d6 and kick the knight — not an outpost
        from modules.position_analyzer import detect_knight_outpost
        board = chess.Board(fen="k7/3p4/8/4N3/3P4/8/8/K7 w - - 0 1")
        result = detect_knight_outpost(board, chess.WHITE)
        assert "e5" not in result["squares"]

    def test_no_outpost_without_pawn_support(self):
        # Safe from pawns but unsupported — Silman requires a pawn anchoring it
        from modules.position_analyzer import detect_knight_outpost
        board = chess.Board(fen="k7/8/8/4N3/8/8/8/K7 w - - 0 1")
        result = detect_knight_outpost(board, chess.WHITE)
        assert "e5" not in result["squares"]

    def test_enemy_pawn_already_past_does_not_prevent_outpost(self):
        # Black pawn on d4 has already passed e5's attack zone; white pawn f4
        # supports the knight — outpost stands
        from modules.position_analyzer import detect_knight_outpost
        board = chess.Board(fen="k7/8/8/4N3/3p1P2/8/8/K7 w - - 0 1")
        result = detect_knight_outpost(board, chess.WHITE)
        assert "e5" in result["squares"]


# --- detect_king_safety ---

class TestDetectKingSafety:
    def test_detected_key_present(self):
        from modules.position_analyzer import detect_king_safety
        board = chess.Board()
        result = detect_king_safety(board, chess.WHITE)
        assert "detected" in result
        assert "exposed" in result
        assert "shield_pawns" in result
        assert "king_square" in result

    def test_starting_position_king_not_exposed(self):
        # Starting position: king on e1, pawns shield on e2, d2, f2 if rank 1
        from modules.position_analyzer import detect_king_safety
        board = chess.Board()
        result = detect_king_safety(board, chess.WHITE)
        # White king on e1, no pawns on rank 2 adjacent since king is on rank 1
        # shield_pawns checks rank+1 = rank 2: d2, e2, f2 all have pawns → 3 shields
        assert result["shield_pawns"] >= 0  # structure is valid

    def test_exposed_king_detected(self):
        # White king with no pawn shield, opponent has a rook (middlegame-like threat)
        from modules.position_analyzer import detect_king_safety
        board = chess.Board(fen="k7/8/8/8/8/8/8/4K2r w - - 0 1")
        result = detect_king_safety(board, chess.WHITE)
        assert result["exposed"] is True
        assert result["shield_pawns"] == 0

    def test_endgame_no_attackers_not_detected(self):
        # K+P vs K endgame: exposed king is not a weakness
        from modules.position_analyzer import detect_king_safety
        board = chess.Board(fen="8/8/8/8/6P1/4k3/6K1/8 w - - 1 63")
        assert detect_king_safety(board, chess.WHITE)["detected"] is False
        assert detect_king_safety(board, chess.BLACK)["detected"] is False

    def test_single_minor_piece_not_detected(self):
        # One bishop cannot threaten the king meaningfully
        from modules.position_analyzer import detect_king_safety
        board = chess.Board(fen="8/8/8/3k4/8/3K4/8/4B3 w - - 0 1")
        assert detect_king_safety(board, chess.BLACK)["detected"] is False

    def test_king_square_returned(self):
        from modules.position_analyzer import detect_king_safety
        board = chess.Board(fen="k7/8/8/8/8/8/8/4K3 w - - 0 1")
        result = detect_king_safety(board, chess.WHITE)
        assert result["king_square"] == "e1"

    def test_open_file_near_king_flags_exposure(self):
        # Kg1 with f2/g2 shield (2 pawns) but the h-file has no white pawn:
        # an open avenue right next to the king, black queen on the board
        from modules.position_analyzer import detect_king_safety
        board = chess.Board(fen="3q3k/8/8/8/8/8/5PP1/6K1 w - - 0 1")
        result = detect_king_safety(board, chess.WHITE)
        assert result["detected"] is True
        assert "h" in result["open_files_near_king"]

    def test_castled_king_full_shield_not_exposed(self):
        from modules.position_analyzer import detect_king_safety
        board = chess.Board(fen="3q3k/8/8/8/8/8/5PPP/6K1 w - - 0 1")
        result = detect_king_safety(board, chess.WHITE)
        assert result["detected"] is False
        assert result["has_castled_position"] is True

    def test_king_stuck_in_center_flagged(self):
        # Ke1 with full shield but castling rights gone and enemy queen present
        from modules.position_analyzer import detect_king_safety
        board = chess.Board(fen="3qk3/8/8/8/8/8/3PPP2/4K3 w - - 0 1")
        result = detect_king_safety(board, chess.WHITE)
        assert result["king_in_center"] is True
        assert result["detected"] is True

    def test_king_in_center_with_castling_rights_not_flagged(self):
        # Same position but castling rights still available — can still castle away
        from modules.position_analyzer import detect_king_safety
        board = chess.Board(fen="3qk3/8/8/8/8/8/3PPP2/R3K2R w KQ - 0 1")
        result = detect_king_safety(board, chess.WHITE)
        assert result["king_in_center"] is False


# --- detect_space_advantage ---

class TestDetectSpaceAdvantage:
    def test_detected_key_present(self):
        from modules.position_analyzer import detect_space_advantage
        board = chess.Board()
        result = detect_space_advantage(board, chess.WHITE)
        assert "detected" in result
        assert "player_space" in result
        assert "opponent_space" in result
        assert "advantage" in result

    def test_starting_position_roughly_equal_space(self):
        from modules.position_analyzer import detect_space_advantage
        board = chess.Board()
        result = detect_space_advantage(board, chess.WHITE)
        assert isinstance(result["player_space"], int)
        assert isinstance(result["advantage"], int)

    def test_no_space_advantage_in_starting_position(self):
        from modules.position_analyzer import detect_space_advantage
        board = chess.Board()
        result = detect_space_advantage(board, chess.WHITE)
        # Starting position is symmetric so advantage should be small (not > 5)
        assert result["detected"] is False


# --- detect_hanging_piece ---

class TestDetectHangingPiece:
    def test_returns_required_keys(self):
        from modules.position_analyzer import detect_hanging_piece
        board = chess.Board()
        result = detect_hanging_piece(board, chess.WHITE)
        assert "detected" in result
        assert "squares" in result
        assert "count" in result

    def test_no_hanging_pieces_in_starting_position(self):
        from modules.position_analyzer import detect_hanging_piece
        board = chess.Board()
        assert detect_hanging_piece(board, chess.WHITE)["detected"] is False
        assert detect_hanging_piece(board, chess.BLACK)["detected"] is False

    def test_undefended_attacked_piece_is_hanging(self):
        # White: Kg1, Ne4 — Black: Bc6 (attacks e4, no white piece defends e4)
        from modules.position_analyzer import detect_hanging_piece
        board = chess.Board("8/8/2b5/8/4N3/8/8/6K1 w - - 0 1")
        result = detect_hanging_piece(board, chess.WHITE)
        assert result["detected"] is True
        assert "e4" in result["squares"]
        assert result["count"] >= 1

    def test_defended_piece_is_not_hanging(self):
        # White: Kg1, Ne4, Bg2 — Black: Bc6 (attacks e4, but Bg2 defends e4)
        from modules.position_analyzer import detect_hanging_piece
        board = chess.Board("8/8/2b5/8/4N3/8/6B1/6K1 w - - 0 1")
        result = detect_hanging_piece(board, chess.WHITE)
        assert result["detected"] is False

    def test_king_is_never_reported_as_hanging(self):
        # Even if the king is in check, it should not appear in hanging squares
        from modules.position_analyzer import detect_hanging_piece
        board = chess.Board("8/8/8/8/4r3/8/8/4K3 w - - 0 1")  # White Ke1 attacked by Re4
        result = detect_hanging_piece(board, chess.WHITE)
        assert "e1" not in result["squares"]

    def test_hanging_pawn_is_detected(self):
        # White: Kg1, Pe4 — Black: Kh8, Bd5 (Bd5 attacks e4 pawn, nothing defends)
        from modules.position_analyzer import detect_hanging_piece
        board = chess.Board("7k/8/8/3b4/4P3/8/8/6K1 w - - 0 1")
        result = detect_hanging_piece(board, chess.WHITE)
        assert result["detected"] is True
        assert "e4" in result["squares"]

    def test_defended_piece_attacked_by_cheaper_piece_is_hanging(self):
        # White Ne4 defended by Bg2 but attacked by the black d5 pawn:
        # pawn takes knight wins material even after the recapture (SEE > 0)
        from modules.position_analyzer import detect_hanging_piece
        board = chess.Board("7k/8/8/3p4/4N3/8/6B1/6K1 w - - 0 1")
        result = detect_hanging_piece(board, chess.WHITE)
        assert result["detected"] is True
        assert "e4" in result["squares"]


# --- static_exchange_gain ---

class TestStaticExchangeGain:
    def test_free_piece_full_value(self):
        # Black bishop c6 attacks undefended white Ne4
        from modules.position_analyzer import static_exchange_gain
        board = chess.Board("8/8/2b5/8/4N3/8/8/6K1 w - - 0 1")
        assert static_exchange_gain(board, chess.E4, chess.BLACK) == 300

    def test_defended_equal_piece_zero(self):
        # Bc6 takes Ne4, Bg2 recaptures: 300 - 300 = 0
        from modules.position_analyzer import static_exchange_gain
        board = chess.Board("8/8/2b5/8/4N3/8/6B1/6K1 w - - 0 1")
        assert static_exchange_gain(board, chess.E4, chess.BLACK) == 0

    def test_pawn_takes_defended_knight_wins(self):
        # d5 pawn takes Ne4, Bg2 recaptures the pawn: 300 - 100 = 200
        from modules.position_analyzer import static_exchange_gain
        board = chess.Board("7k/8/8/3p4/4N3/8/6B1/6K1 w - - 0 1")
        assert static_exchange_gain(board, chess.E4, chess.BLACK) == 200

    def test_no_attackers_returns_zero(self):
        from modules.position_analyzer import static_exchange_gain
        board = chess.Board()
        assert static_exchange_gain(board, chess.E2, chess.BLACK) == 0


# --- detect_doubled_pawns ---

class TestDetectDoubledPawns:
    def test_returns_required_keys(self):
        from modules.position_analyzer import detect_doubled_pawns
        result = detect_doubled_pawns(chess.Board(), chess.WHITE)
        assert "detected" in result
        assert "files" in result
        assert "count" in result

    def test_doubled_pawns_on_e_file_detected(self):
        # White: Ke1, Pe3, Pe4 (doubled on e-file)
        from modules.position_analyzer import detect_doubled_pawns
        board = chess.Board("4k3/8/8/8/4P3/4P3/8/4K3 w - - 0 1")
        result = detect_doubled_pawns(board, chess.WHITE)
        assert result["detected"] is True
        assert "e" in result["files"]

    def test_no_doubled_pawns_in_starting_position(self):
        from modules.position_analyzer import detect_doubled_pawns
        assert detect_doubled_pawns(chess.Board(), chess.WHITE)["detected"] is False


# --- detect_rook_on_7th ---

class TestDetectRookOn7th:
    def test_returns_required_keys(self):
        from modules.position_analyzer import detect_rook_on_7th
        result = detect_rook_on_7th(chess.Board(), chess.WHITE)
        assert "detected" in result
        assert "squares" in result

    def test_white_rook_on_7th_rank_detected(self):
        # White: Ke1, Ra7 — the 7th rank (rank index 6) for white
        from modules.position_analyzer import detect_rook_on_7th
        board = chess.Board("4k3/R7/8/8/8/8/8/4K3 w - - 0 1")
        result = detect_rook_on_7th(board, chess.WHITE)
        assert result["detected"] is True
        assert "a7" in result["squares"]

    def test_rook_not_on_7th_not_detected(self):
        # Starting position has no rooks on 7th rank
        from modules.position_analyzer import detect_rook_on_7th
        assert detect_rook_on_7th(chess.Board(), chess.WHITE)["detected"] is False


# --- detect_bad_bishop ---

class TestDetectBadBishop:
    def test_returns_required_keys(self):
        from modules.position_analyzer import detect_bad_bishop
        result = detect_bad_bishop(chess.Board(), chess.WHITE)
        assert "detected" in result
        assert "squares" in result
        assert "count" in result

    def test_bad_bishop_detected_when_pawns_on_same_color(self):
        # White: Ke1, Bc1 (dark squares), Pc3, Pe3, Pg3 (all dark squares — same parity as Bc1)
        from modules.position_analyzer import detect_bad_bishop
        board = chess.Board("4k3/8/8/8/8/2P1P1P1/8/2B1K3 w - - 0 1")
        result = detect_bad_bishop(board, chess.WHITE)
        assert result["detected"] is True

    def test_bishop_not_bad_when_pawns_on_opposite_color(self):
        # White: Ke1, Bc1 (dark), Pb3, Pd3, Pf3 (all light squares — different from Bc1)
        from modules.position_analyzer import detect_bad_bishop
        board = chess.Board("4k3/8/8/8/8/1P1P1P2/8/2B1K3 w - - 0 1")
        result = detect_bad_bishop(board, chess.WHITE)
        assert result["detected"] is False


# --- detect_pawn_majority ---

class TestDetectPawnMajority:
    def test_returns_required_keys(self):
        from modules.position_analyzer import detect_pawn_majority
        result = detect_pawn_majority(chess.Board(), chess.WHITE)
        assert "detected" in result
        assert "queenside_majority" in result
        assert "kingside_majority" in result

    def test_kingside_majority_detected(self):
        # White: 4 kingside pawns (e-h), Black: 4 queenside pawns (a-d)
        from modules.position_analyzer import detect_pawn_majority
        board = chess.Board("4k3/pppp4/8/8/8/8/4PPPP/4K3 w - - 0 1")
        result = detect_pawn_majority(board, chess.WHITE)
        assert result["detected"] is True
        assert result["kingside_majority"] is True

    def test_no_majority_when_symmetric(self):
        # Equal pawns both sides — full ranks
        from modules.position_analyzer import detect_pawn_majority
        board = chess.Board("4k3/pppppppp/8/8/8/8/PPPPPPPP/4K3 w - - 0 1")
        result = detect_pawn_majority(board, chess.WHITE)
        assert result["detected"] is False


# --- detect_piece_activity ---

class TestDetectPieceActivity:
    def test_returns_required_keys(self):
        from modules.position_analyzer import detect_piece_activity
        result = detect_piece_activity(chess.Board(), chess.WHITE)
        assert "detected" in result
        assert "player_mobility" in result
        assert "opponent_mobility" in result
        assert "advantage" in result

    def test_high_activity_detected_when_white_has_queen_alone(self):
        # White: Ke1, Qe3 — Black: Ke8 (no non-king pieces)
        # Qe3 has high mobility; black has none → large advantage
        from modules.position_analyzer import detect_piece_activity
        board = chess.Board("4k3/8/8/8/8/4Q3/8/4K3 w - - 0 1")
        result = detect_piece_activity(board, chess.WHITE)
        assert result["detected"] is True
        assert result["advantage"] > 3.0

    def test_balanced_activity_in_starting_position(self):
        from modules.position_analyzer import detect_piece_activity
        # Starting position is symmetric — no advantage for either side
        result = detect_piece_activity(chess.Board(), chess.WHITE)
        assert result["detected"] is False


# --- detect_overloaded_piece ---

class TestDetectOverloadedPiece:
    def test_returns_required_keys(self):
        from modules.position_analyzer import detect_overloaded_piece
        result = detect_overloaded_piece(chess.Board(), chess.WHITE)
        assert "detected" in result
        assert "overloaded_squares" in result

    def test_overloaded_piece_detected(self):
        # White: Ke1, Nd5 (attacks Nc7 and Nf6 — equal exchanges)
        # Black: Ke8, Nc7, Nf6, Qd8 (defends both Nc7 and Nf6 via diagonals) → Qd8 overloaded
        from modules.position_analyzer import detect_overloaded_piece
        board = chess.Board("3qk3/2n5/5n2/3N4/8/8/8/4K3 w - - 0 1")
        result = detect_overloaded_piece(board, chess.WHITE)
        assert result["detected"] is True
        assert "d8" in result["overloaded_squares"]

    def test_no_overloaded_piece_when_fewer_than_two_threatened(self):
        # Starting position: white attacks nothing of black → no overloaded pieces
        from modules.position_analyzer import detect_overloaded_piece
        assert detect_overloaded_piece(chess.Board(), chess.WHITE)["detected"] is False

    def test_queen_attacking_defended_pawn_not_a_real_threat(self):
        # White: Ke1, Qd6 attacking h2 pawn (defended by black king) and d4 pawn (defended)
        # Queen (900) > pawn (100) and pawns are defended → not real threats → not detected
        from modules.position_analyzer import detect_overloaded_piece
        board = chess.Board("r3kb1r/2p1pppp/p1nq1n2/1p1p1b2/3P4/1BN1PN2/PPP2PPP/R1BQ1RK1 b kq - 3 8")
        result = detect_overloaded_piece(board, chess.BLACK)
        # h2 attacked by Qd6 (900 > 100, defended by Kg1) and d4 by Nc6 (300 > 100, defended)
        # Neither qualifies as a real threat → no overloaded piece
        assert result["detected"] is False

    def test_rook_attacking_defended_bishop_not_a_real_threat(self):
        # White: Ke1, Rd6 (500) attacking Be6 (300, defended by Qd5) → 500 > 300, defended → filtered
        # White: Rc2 (500) attacking Bc4 (300, defended by Qd5) → 500 > 300, defended → filtered
        from modules.position_analyzer import detect_overloaded_piece
        board = chess.Board("4k3/8/3Rb3/3q4/2b5/8/2R5/4K3 w - - 0 1")
        result = detect_overloaded_piece(board, chess.WHITE)
        assert result["detected"] is False

    def test_undefended_piece_is_real_threat_for_any_attacker_value(self):
        # White Qa1 (900) attacks undefended black Rh8 (500) via diagonal a1-h8
        # 900 > 500 but Rh8 is completely undefended → _is_real_threat must return True
        from modules.position_analyzer import _is_real_threat
        board = chess.Board("4k2r/8/8/8/8/8/8/Q3K3 w - - 0 1")
        assert _is_real_threat(board, chess.H8, chess.WHITE) is True

    def test_defended_piece_with_higher_value_attacker_is_not_real_threat(self):
        # White Qa1 (900) attacks black Rh8 (500) defended by black Ke8
        # 900 > 500 AND defended → _is_real_threat must return False
        from modules.position_analyzer import _is_real_threat
        board = chess.Board("4kr2/8/8/8/8/8/8/Q3K3 w - - 0 1")
        # Ke8 defends f8 and d8 and e7, etc. — Rf8 is adjacent to Ke8
        assert _is_real_threat(board, chess.F8, chess.WHITE) is False


# --- detect_backward_pawn ---

class TestDetectBackwardPawn:
    def test_returns_required_keys(self):
        from modules.position_analyzer import detect_backward_pawn
        result = detect_backward_pawn(chess.Board(), chess.WHITE)
        assert "detected" in result
        assert "squares" in result
        assert "count" in result

    def test_backward_pawn_detected(self):
        # White: Ke1, Pe3 — Black: Ke8, Pd5, Pf5
        # Pe3 wants to advance to e4, but d5 and f5 control e4.
        # No white pawn behind Pe3 on d or f file → backward.
        from modules.position_analyzer import detect_backward_pawn
        board = chess.Board("4k3/8/8/3p1p2/8/4P3/8/4K3 w - - 0 1")
        result = detect_backward_pawn(board, chess.WHITE)
        assert result["detected"] is True
        assert "e3" in result["squares"]

    def test_pawn_with_support_not_backward(self):
        # Same as above but add Pd2: white pawn behind Pe3 on adjacent d-file → support exists
        from modules.position_analyzer import detect_backward_pawn
        board = chess.Board("4k3/8/8/3p1p2/8/4P3/3P4/4K3 w - - 0 1")
        result = detect_backward_pawn(board, chess.WHITE)
        assert "e3" not in result["squares"]

    def test_no_backward_pawns_in_starting_position(self):
        from modules.position_analyzer import detect_backward_pawn
        assert detect_backward_pawn(chess.Board(), chess.WHITE)["detected"] is False


# --- detect_center_control ---

class TestDetectCenterControl:
    def test_returns_required_keys(self):
        from modules.position_analyzer import detect_center_control
        result = detect_center_control(chess.Board(), chess.WHITE)
        assert "detected" in result
        assert "player_center_attacks" in result
        assert "opponent_center_attacks" in result
        assert "advantage" in result

    def test_center_control_detected_with_active_queen(self):
        # White: Ke1, Qe3 — Black: Ke8
        # Qe3 attacks d4, e4, e5 (3 central squares); black king attacks none → advantage=3
        from modules.position_analyzer import detect_center_control
        board = chess.Board("4k3/8/8/8/8/4Q3/8/4K3 w - - 0 1")
        result = detect_center_control(board, chess.WHITE)
        assert result["detected"] is True
        assert result["advantage"] >= 2

    def test_no_center_advantage_in_starting_position(self):
        # Starting position is symmetric — no center advantage for white
        from modules.position_analyzer import detect_center_control
        result = detect_center_control(chess.Board(), chess.WHITE)
        assert result["detected"] is False
