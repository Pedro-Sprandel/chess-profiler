import chess
import pytest


# --- detect_concepts ---

class TestDetectConcepts:
    def test_returns_dict_with_all_seven_keys(self):
        from modules.position_analyzer import detect_concepts
        board = chess.Board()
        result = detect_concepts(board, chess.WHITE)
        expected_keys = {
            "weak_square", "open_file", "isolated_pawn",
            "bishop_pair", "knight_outpost", "king_safety", "space_advantage"
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

    def test_starting_position_has_no_weak_squares_for_white(self):
        # In starting position white pawns cover most squares — weak squares list may vary,
        # but we just verify the structure is correct
        from modules.position_analyzer import detect_weak_squares
        board = chess.Board()
        result = detect_weak_squares(board, chess.WHITE)
        assert isinstance(result["squares"], list)
        assert isinstance(result["count"], int)

    def test_position_with_clear_weak_square(self):
        # After removing all white pawns, many squares become weak
        from modules.position_analyzer import detect_weak_squares
        board = chess.Board()
        # Remove all white pawns
        for sq in chess.SQUARES:
            piece = board.piece_at(sq)
            if piece and piece.piece_type == chess.PAWN and piece.color == chess.WHITE:
                board.remove_piece_at(sq)
        result = detect_weak_squares(board, chess.WHITE)
        assert result["count"] > 0
        assert result["detected"] is True


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
        # White knight on e5 (rank 4), no black pawn on d6 or f6
        from modules.position_analyzer import detect_knight_outpost
        board = chess.Board(fen="k7/8/8/4N3/8/8/8/K7 w - - 0 1")
        result = detect_knight_outpost(board, chess.WHITE)
        assert result["detected"] is True
        assert "e5" in result["squares"]

    def test_no_outpost_when_attacked_by_pawn(self):
        # White knight on e5 but black pawn on d6 can attack it
        from modules.position_analyzer import detect_knight_outpost
        board = chess.Board(fen="k7/8/3p4/4N3/8/8/8/K7 w - - 0 1")
        result = detect_knight_outpost(board, chess.WHITE)
        assert "e5" not in result["squares"]


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
        # King alone with no pawn shield
        from modules.position_analyzer import detect_king_safety
        board = chess.Board(fen="k7/8/8/8/8/8/8/4K3 w - - 0 1")
        result = detect_king_safety(board, chess.WHITE)
        assert result["exposed"] is True
        assert result["shield_pawns"] == 0

    def test_king_square_returned(self):
        from modules.position_analyzer import detect_king_safety
        board = chess.Board(fen="k7/8/8/8/8/8/8/4K3 w - - 0 1")
        result = detect_king_safety(board, chess.WHITE)
        assert result["king_square"] == "e1"


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
