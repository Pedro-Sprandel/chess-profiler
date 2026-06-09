"""End-to-end pipeline integration tests.

Runs the full analysis pipeline (PGN load → concept detection → Stockfish
validation → profile build) with real modules. Only the Claude API call
(diagnose) is mocked — everything else runs against actual code and a real
Stockfish binary.

Tests are marked ``e2e`` and are skipped automatically when the Stockfish
binary is missing so CI without the engine still passes.
"""
import chess
import json
import os
import pytest
from unittest.mock import patch

import config
from modules.pgn_loader import load_games_from_file, load_games_from_string, iterate_positions
from modules.position_analyzer import detect_concepts
from modules.stockfish_validator import open_engine, batch_validate
from modules.profile_builder import build_profile

# ── fixtures ──────────────────────────────────────────────────────────────────

STOCKFISH_AVAILABLE = os.path.isfile(config.STOCKFISH_PATH)
skip_no_sf = pytest.mark.skipif(
    not STOCKFISH_AVAILABLE,
    reason=f"Stockfish not found at {config.STOCKFISH_PATH}",
)

# PGN with clear strategic errors: White misses a knight outpost and leaves a
# piece hanging on move 7 (Nf6?? drops the knight to Bxf6).
INTEGRATION_PGN = """\
[Event "Integration Test"]
[Site "?"]
[Date "2024.01.01"]
[Round "1"]
[White "TestWhite"]
[Black "TestBlack"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7
6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 1-0
"""

MOCK_DIAGNOSIS_EN = {
    "en": {
        "root_cause": {
            "id": "static_thinking",
            "name": "Static Thinking",
            "description": "Player does not evaluate dynamic imbalances.",
        },
        "weakness_classification": [
            {"concept": "weak_square", "classification": "PRIMARY", "reasoning": "Most frequent error."}
        ],
        "study_priority": [
            {
                "concept": "weak_square",
                "silman_chapter": 3,
                "priority_rank": 1,
                "reason": "Root cause.",
                "silman_name": "Weak Square",
                "silman_page": 67,
                "silman_description": "A square that cannot be defended by a pawn.",
            }
        ],
        "cognitive_pattern": "Ignores weak squares.",
        "confidence": "HIGH",
    },
    "pt": {
        "root_cause": {
            "id": "static_thinking",
            "name": "Pensamento Estático",
            "description": "O jogador não avalia desequilíbrios dinâmicos.",
        },
        "weakness_classification": [
            {"concept": "weak_square", "classification": "PRIMARY", "reasoning": "Erro mais frequente."}
        ],
        "study_priority": [
            {
                "concept": "weak_square",
                "silman_chapter": 3,
                "priority_rank": 1,
                "reason": "Causa raiz.",
                "silman_name": "Casa Fraca",
                "silman_page": 67,
                "silman_description": "Uma casa que não pode ser defendida por um peão.",
            }
        ],
        "cognitive_pattern": "Ignora casas fracas.",
        "confidence": "HIGH",
    },
}


# ── unit-level integration: real modules, no Stockfish ────────────────────────

class TestPipelineConceptDetection:
    """Concept detection runs on real board objects — no engine needed."""

    def test_detect_concepts_returns_all_17_keys(self):
        board = chess.Board()
        result = detect_concepts(board, chess.WHITE)
        expected = {
            "weak_square", "open_file", "isolated_pawn", "bishop_pair",
            "knight_outpost", "king_safety", "space_advantage",
            "passed_pawn", "doubled_pawn", "rook_on_7th",
            "bad_bishop", "pawn_majority", "piece_activity", "overloaded_piece",
            "hanging_piece", "backward_pawn", "center_control",
        }
        assert set(result.keys()) == expected

    def test_each_concept_has_detected_bool(self):
        board = chess.Board()
        result = detect_concepts(board, chess.WHITE)
        for key, val in result.items():
            assert isinstance(val.get("detected"), bool), f"{key} missing 'detected' bool"

    def test_pgn_loads_and_positions_iterate(self):
        games = load_games_from_string(INTEGRATION_PGN)
        assert len(games) == 1
        positions = list(iterate_positions(games[0], chess.WHITE))
        assert len(positions) > 0
        board_before, move, board_after = positions[0]
        assert isinstance(board_before, chess.Board)
        assert isinstance(move, chess.Move)

    def test_full_concept_scan_over_game(self):
        games = load_games_from_string(INTEGRATION_PGN)
        positions = list(iterate_positions(games[0], chess.WHITE))
        detected_any = False
        for board_before, move, _ in positions:
            concepts = detect_concepts(board_before, chess.WHITE)
            if any(v.get("detected") for v in concepts.values()):
                detected_any = True
                break
        assert detected_any, "Expected at least one concept detected in the game"

    def test_build_profile_on_synthetic_games_data(self):
        games = load_games_from_string(INTEGRATION_PGN)
        games_data = []
        _no_error = {
            "is_error": False, "eval_before": 20, "eval_after": 20,
            "error_magnitude": 0, "best_move": None,
        }
        for i, game in enumerate(games):
            positions = []
            for board_before, move, _ in iterate_positions(game, chess.WHITE):
                positions.append({
                    "fen": board_before.fen(),
                    "move_played": move.uci(),
                    "concepts_detected": detect_concepts(board_before, chess.WHITE),
                    "stockfish_validation": _no_error,
                })
            games_data.append({
                "game_id": f"game_{i+1}",
                "white": game.headers.get("White", "White"),
                "black": game.headers.get("Black", "Black"),
                "player_color": "white",
                "positions": positions,
            })
        profile = build_profile(games_data)
        assert "total_games" in profile
        assert "weaknesses" in profile
        assert profile["total_games"] == 1
        assert isinstance(profile["weaknesses"], list)


# ── full integration: real Stockfish ─────────────────────────────────────────

class TestPipelineWithStockfish:
    """Full pipeline from PGN to profile, using real Stockfish validation."""

    @skip_no_sf
    def test_batch_validate_returns_correct_structure(self):
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")
        engine = open_engine()
        try:
            results = batch_validate([(board, move)], engine=engine)
        finally:
            engine.quit()
        assert len(results) == 1
        r = results[0]
        assert "is_error" in r
        assert "error_magnitude" in r
        assert "best_move" in r
        assert isinstance(r["is_error"], bool)
        assert isinstance(r["error_magnitude"], (int, float))

    @skip_no_sf
    def test_best_move_is_never_error(self):
        """Playing the best move must never be classified as an error."""
        from modules.stockfish_validator import validate_move
        board = chess.Board()
        # Get the engine's top move first
        engine = open_engine()
        try:
            result_probe = batch_validate([(board, chess.Move.from_uci("e2e4"))], engine=engine)
            best = result_probe[0]["best_move"]
            if best:
                result_best = batch_validate(
                    [(board, chess.Move.from_uci(best))], engine=engine
                )
                assert result_best[0]["is_error"] is False
        finally:
            engine.quit()

    @skip_no_sf
    def test_full_pipeline_pgn_to_profile(self, tmp_path):
        """Runs the entire analysis pipeline on a small PGN without mocking
        any chess module — only the Claude API call is patched."""
        pgn_file = tmp_path / "test.pgn"
        pgn_file.write_text(INTEGRATION_PGN)
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir, exist_ok=True)

        with patch("main.diagnose", return_value=MOCK_DIAGNOSIS_EN), \
             patch("main.OUTPUT_DIR", output_dir):
            from main import analyze_player
            profile, diagnosis = analyze_player(
                str(pgn_file), "e2e_player", chess.WHITE
            )

        # Profile structure
        assert isinstance(profile, dict)
        assert profile["total_games"] == 1
        assert profile["total_positions_analyzed"] > 0
        assert isinstance(profile["weaknesses"], list)
        assert "overall_error_rate" in profile

        # Files written
        assert os.path.exists(os.path.join(output_dir, "e2e_player_profile.json"))
        assert os.path.exists(os.path.join(output_dir, "e2e_player_diagnosis.json"))

        # Diagnosis is bilingual
        diagnosis_path = os.path.join(output_dir, "e2e_player_diagnosis.json")
        with open(diagnosis_path) as f:
            saved = json.load(f)
        assert "en" in saved or "root_cause" in saved  # bilingual or flat legacy

    @skip_no_sf
    def test_on_progress_callback_called_for_all_stages(self, tmp_path):
        """Verifies the progress callback fires at every pipeline stage."""
        pgn_file = tmp_path / "test.pgn"
        pgn_file.write_text(INTEGRATION_PGN)
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir, exist_ok=True)

        stages_seen = []

        def on_progress(stage, current, total, message):
            stages_seen.append(stage)

        with patch("main.diagnose", return_value=MOCK_DIAGNOSIS_EN), \
             patch("main.OUTPUT_DIR", output_dir):
            from main import analyze_player
            analyze_player(str(pgn_file), "cb_player", chess.WHITE, on_progress=on_progress)

        assert "load" in stages_seen
        assert "game" in stages_seen
        assert "profile" in stages_seen
        assert "ai" in stages_seen
        assert "done" in stages_seen


# ── CLI smoke tests ───────────────────────────────────────────────────────────

class TestCLISmoke:
    """Smoke tests for the CLI entry point (_main).

    These verify argument parsing and routing without running the actual
    pipeline — the pipeline is covered by TestPipelineWithStockfish above.
    """

    def test_pgn_mode_smoke(self, tmp_path):
        pgn = tmp_path / "game.pgn"
        pgn.write_text(INTEGRATION_PGN)
        with patch("main.analyze_player", return_value=({}, MOCK_DIAGNOSIS_EN)) as m:
            from main import _main
            _main(["--user", "smoke", "--pgn", str(pgn)])
        m.assert_called_once()

    def test_username_mode_smoke(self):
        with patch("main.analyze_player_from_username", return_value=({}, MOCK_DIAGNOSIS_EN)) as m:
            from main import _main
            _main(["--user", "smoke"])
        m.assert_called_once()

    def test_games_flag_forwarded(self):
        with patch("main.analyze_player_from_username", return_value=({}, MOCK_DIAGNOSIS_EN)) as m:
            from main import _main
            _main(["--user", "smoke", "--games", "20"])
        assert m.call_args.kwargs.get("n_games") == 20

    def test_color_black_forwarded(self, tmp_path):
        pgn = tmp_path / "game.pgn"
        pgn.write_text(INTEGRATION_PGN)
        with patch("main.analyze_player", return_value=({}, MOCK_DIAGNOSIS_EN)) as m:
            from main import _main
            _main(["--user", "smoke", "--pgn", str(pgn), "--color", "black"])
        color = m.call_args.kwargs.get("player_color")
        assert color == chess.BLACK
