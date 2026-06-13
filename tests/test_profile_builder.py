import json
import os
import tempfile
import pytest


def make_position(concepts_detected: dict, is_error: bool, error_magnitude: float = 0.0, eval_before: int = 20) -> dict:
    """Helper to build a position dict for games_data."""
    return {
        "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        "move_played": "e2e4",
        "concepts_detected": concepts_detected,
        "stockfish_validation": {
            "is_error": is_error,
            "eval_before": eval_before,
            "eval_after": eval_before - error_magnitude,
            "error_magnitude": error_magnitude,
            "best_move": None  # None bypasses is_instructive gate so profile tests stay focused
        }
    }


def make_game(game_id: str, positions: list) -> dict:
    return {"game_id": game_id, "positions": positions}


class TestBuildProfile:
    def test_empty_games_returns_zeroed_profile(self):
        from modules.profile_builder import build_profile
        result = build_profile([])
        assert result["total_games"] == 0
        assert result["total_positions_analyzed"] == 0
        assert result["total_errors_detected"] == 0
        assert result["overall_error_rate"] == 0
        assert result["weaknesses"] == []

    def test_counts_total_positions_correctly(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": False}}
        game = make_game("g1", [
            make_position(concepts, is_error=False),
            make_position(concepts, is_error=False),
            make_position(concepts, is_error=False),
        ])
        result = build_profile([game])
        assert result["total_positions_analyzed"] == 3

    def test_counts_total_errors_correctly(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": False}}
        game = make_game("g1", [
            make_position(concepts, is_error=True, error_magnitude=100),
            make_position(concepts, is_error=False),
            make_position(concepts, is_error=True, error_magnitude=80),
        ])
        result = build_profile([game])
        assert result["total_errors_detected"] == 2

    def test_excludes_weaknesses_below_min_occurrences(self):
        from modules.profile_builder import build_profile
        # Only 2 errors for weak_square — below MIN_OCCURRENCES=3
        concepts = {"weak_square": {"detected": True}}
        game = make_game("g1", [
            make_position(concepts, is_error=True, error_magnitude=100),
            make_position(concepts, is_error=True, error_magnitude=80),
        ])
        result = build_profile([game])
        assert result["weaknesses"] == []

    def test_includes_weaknesses_at_min_occurrences(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": True}}
        positions = [make_position(concepts, is_error=True, error_magnitude=100)] * 3
        game = make_game("g1", positions)
        result = build_profile([game])
        assert len(result["weaknesses"]) == 1
        assert result["weaknesses"][0]["concept"] == "weak_square"

    def test_weaknesses_sorted_by_error_occurrences_descending(self):
        from modules.profile_builder import build_profile
        c_weak = {"weak_square": {"detected": True}, "open_file": {"detected": False}}
        c_open = {"weak_square": {"detected": False}, "open_file": {"detected": True}}

        # weak_square: 5 errors, open_file: 3 errors
        positions = (
            [make_position(c_weak, is_error=True, error_magnitude=100)] * 5 +
            [make_position(c_open, is_error=True, error_magnitude=100)] * 3
        )
        game = make_game("g1", positions)
        result = build_profile([game])
        assert result["weaknesses"][0]["concept"] == "weak_square"
        assert result["weaknesses"][1]["concept"] == "open_file"

    def test_overall_error_rate_calculated_correctly(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": False}}
        game = make_game("g1", [
            make_position(concepts, is_error=True, error_magnitude=100),
            make_position(concepts, is_error=False),
            make_position(concepts, is_error=False),
            make_position(concepts, is_error=False),
        ])
        result = build_profile([game])
        assert result["overall_error_rate"] == round(1 / 4, 3)

    def test_weakness_has_expected_fields(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": True}}
        positions = [make_position(concepts, is_error=True, error_magnitude=100)] * 3
        game = make_game("g1", positions)
        result = build_profile([game])
        w = result["weaknesses"][0]
        assert "concept" in w
        assert "total_occurrences" in w
        assert "error_occurrences" in w
        assert "error_rate" in w
        assert "avg_error_magnitude_cp" in w
        assert "sample_positions" in w


class TestMissedCheckmate:
    def test_missed_checkmate_counted_in_metric(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": True}}
        # eval_before=9500 with player_color="white" → white had forced mate
        pos = make_position(concepts, is_error=True, error_magnitude=200, eval_before=9500)
        game = {"game_id": "g1", "player_color": "white", "positions": [pos]}
        result = build_profile([game])
        assert result["total_missed_checkmates"] == 1

    def test_missed_checkmate_not_counted_in_concepts(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": True}}
        # 4 missed checkmates + 3 normal errors with the same concept
        mc_pos = make_position(concepts, is_error=True, error_magnitude=200, eval_before=9500)
        normal_pos = make_position(concepts, is_error=True, error_magnitude=100)
        game = {
            "game_id": "g1",
            "player_color": "white",
            "positions": [mc_pos] * 4 + [normal_pos] * 3,
        }
        result = build_profile([game])
        assert result["total_missed_checkmates"] == 4
        # only the 3 normal errors should count toward the concept
        assert result["weaknesses"][0]["error_occurrences"] == 3

    def test_missed_checkmate_still_counts_as_total_error(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": False}}
        pos = make_position(concepts, is_error=True, error_magnitude=200, eval_before=9500)
        game = {"game_id": "g1", "player_color": "white", "positions": [pos]}
        result = build_profile([game])
        assert result["total_errors_detected"] == 1
        assert result["total_missed_checkmates"] == 1

    def test_black_player_missed_checkmate_detected(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": True}}
        # eval_before=-9500 from white's perspective → black has forced mate
        pos = make_position(concepts, is_error=True, error_magnitude=200, eval_before=-9500)
        game = {"game_id": "g1", "player_color": "black", "positions": [pos]}
        result = build_profile([game])
        assert result["total_missed_checkmates"] == 1
        assert result["weaknesses"] == []  # filtered from concepts

    def test_opponent_has_mate_is_not_a_missed_checkmate(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": True}}
        # eval_before=-9500 with white player → opponent has forced mate against white
        # This is an allowed_checkmate (not missed_checkmate), so concepts are filtered
        pos = make_position(concepts, is_error=True, error_magnitude=200, eval_before=-9500)
        game = {"game_id": "g1", "player_color": "white", "positions": [pos]}
        result = build_profile([game])
        assert result["total_missed_checkmates"] == 0
        assert result["total_allowed_checkmates"] == 1

    def test_empty_games_has_zero_missed_checkmates(self):
        from modules.profile_builder import build_profile
        result = build_profile([])
        assert result["total_missed_checkmates"] == 0


class TestAllowedCheckmate:
    def test_allowed_mate_via_blunder_counted_in_metric(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": True}}
        # eval_before=20, eval_after=-9500 → player's move handed opponent forced mate
        pos = make_position(concepts, is_error=True, error_magnitude=9520, eval_before=20)
        pos["stockfish_validation"]["eval_after"] = -9500
        game = {"game_id": "g1", "player_color": "white", "positions": [pos]}
        result = build_profile([game])
        assert result["total_allowed_checkmates"] == 1

    def test_allowed_mate_already_mated_before_counted(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": True}}
        # eval_before=-9500 → player was already in a forced mate
        pos = make_position(concepts, is_error=True, error_magnitude=200, eval_before=-9500)
        game = {"game_id": "g1", "player_color": "white", "positions": [pos]}
        result = build_profile([game])
        assert result["total_allowed_checkmates"] == 1

    def test_allowed_mate_not_counted_in_concepts(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": True}}
        am_pos = make_position(concepts, is_error=True, error_magnitude=200, eval_before=-9500)
        normal_pos = make_position(concepts, is_error=True, error_magnitude=100)
        game = {
            "game_id": "g1",
            "player_color": "white",
            "positions": [am_pos] * 4 + [normal_pos] * 3,
        }
        result = build_profile([game])
        assert result["total_allowed_checkmates"] == 4
        assert result["weaknesses"][0]["error_occurrences"] == 3

    def test_allowed_mate_still_counts_as_total_error(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": False}}
        pos = make_position(concepts, is_error=True, error_magnitude=200, eval_before=-9500)
        game = {"game_id": "g1", "player_color": "white", "positions": [pos]}
        result = build_profile([game])
        assert result["total_errors_detected"] == 1
        assert result["total_allowed_checkmates"] == 1

    def test_black_player_allowed_mate_detected(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": True}}
        # eval_before=9500 from white's perspective → opponent (white) has forced mate against black
        pos = make_position(concepts, is_error=True, error_magnitude=200, eval_before=9500)
        game = {"game_id": "g1", "player_color": "black", "positions": [pos]}
        result = build_profile([game])
        assert result["total_allowed_checkmates"] == 1
        assert result["weaknesses"] == []

    def test_empty_games_has_zero_allowed_checkmates(self):
        from modules.profile_builder import build_profile
        result = build_profile([])
        assert result["total_allowed_checkmates"] == 0

    def test_missed_and_allowed_are_mutually_exclusive(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": False}}
        mc = make_position(concepts, is_error=True, error_magnitude=200, eval_before=9500)
        am = make_position(concepts, is_error=True, error_magnitude=200, eval_before=-9500)
        game = {"game_id": "g1", "player_color": "white", "positions": [mc, am]}
        result = build_profile([game])
        assert result["total_missed_checkmates"] == 1
        assert result["total_allowed_checkmates"] == 1


class TestMissedTacticPrecedence:
    # White to move; black bishop on f3 is hanging. Best move g5f3 (Nxf3) wins it.
    _FEN = "r3k3/pp2r1pp/2pR4/2n1p1N1/2P1P3/nP3b2/P6P/2K3R1 w - - 5 25"

    def _missed_tactic_position(self):
        """An error where weak_square co-occurs but the real fault is a declined free capture."""
        return {
            "fen": self._FEN,
            "move_played": "g1e1",
            "concepts_detected": {"weak_square": {"detected": True}},
            "stockfish_validation": {
                "is_error": True,
                "eval_before": 100,
                "eval_after": -17,
                "error_magnitude": 117,
                "best_move": "g5f3",
            },
        }

    def test_missed_tactic_attributed_to_its_own_concept(self):
        from modules.profile_builder import build_profile
        game = make_game("g1", [self._missed_tactic_position()] * 3)
        result = build_profile([game])
        concepts = {w["concept"] for w in result["weaknesses"]}
        assert "missed_tactic" in concepts

    def test_missed_tactic_does_not_leak_into_strategic_concept(self):
        from modules.profile_builder import build_profile
        game = make_game("g1", [self._missed_tactic_position()] * 3)
        result = build_profile([game])
        concepts = {w["concept"] for w in result["weaknesses"]}
        # The error must NOT be counted against weak_square — that was the bug.
        assert "weak_square" not in concepts


class TestSaveAndLoadProfile:
    def test_save_profile_writes_valid_json(self):
        from modules.profile_builder import build_profile, save_profile
        profile = build_profile([])
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp_path = f.name
        try:
            save_profile(profile, tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded["total_games"] == 0
        finally:
            os.unlink(tmp_path)

    def test_load_profile_reads_saved_file(self):
        from modules.profile_builder import build_profile, save_profile, load_profile
        profile = build_profile([])
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp_path = f.name
        try:
            save_profile(profile, tmp_path)
            loaded = load_profile(tmp_path)
            assert loaded == profile
        finally:
            os.unlink(tmp_path)


class TestSamplePositionsStoreAll:
    def test_stores_all_error_positions_not_just_three(self):
        from modules.profile_builder import build_profile
        concepts = {"weak_square": {"detected": True}}
        # 5 instructive errors for one concept (best_move None bypasses is_instructive)
        game = make_game("g1", [
            make_position(concepts, is_error=True, error_magnitude=100 + i)
            for i in range(5)
        ])
        result = build_profile([game])
        w = result["weaknesses"][0]
        assert w["error_occurrences"] == 5
        assert len(w["sample_positions"]) == 5
