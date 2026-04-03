# Plan: Chess Strategic Profiler MVP

**Track ID:** chess_profiler_mvp_20260402
**Status:** new

---

## Phase 1: Project Setup & Infrastructure [checkpoint: d915632]

### Tasks

- [x] Task 1.1: Create project directory structure [aa7125d]
  - Create `modules/`, `data/`, `output/`, `tests/` directories
  - Create `requirements.txt` with `chess`, `anthropic`, `python-dotenv`, `pytest`, `pytest-cov`
  - Create `.env.example` with `ANTHROPIC_API_KEY=your_key_here`
  - Create `.gitignore` ignoring `.env`, `output/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`

- [x] Task 1.2: Write tests for config.py (Red Phase) [d954637]
  - Create `tests/test_config.py`
  - Test that `STOCKFISH_DEPTH` equals 15
  - Test that `ERROR_THRESHOLD_CP` equals 50
  - Test that `MIN_OCCURRENCES` equals 3
  - Test that `STOCKFISH_PATH` is a non-empty string
  - Run tests and confirm they fail

- [x] Task 1.3: Implement config.py (Green Phase) [7f9eb98]
  - Implement `config.py` per spec: load `.env`, define all constants
  - Run tests and confirm they pass
  - Run `pytest --cov=. --cov-report=term` and verify coverage

- [x] Task 1.4: Create `data/silman_concepts.json` [90a03fc]
  - Populate with all 7 concepts: `weak_square`, `open_file`, `isolated_pawn`,
    `bishop_pair`, `knight_outpost`, `king_safety`, `space_advantage`
  - Each entry must include: `id`, `name`, `silman_chapter`, `silman_page`,
    `silman_category`, `description`, `strategic_implications`, `detection_key`

- [ ] Task: Conductor - User Manual Verification 'Phase 1: Project Setup & Infrastructure' (Protocol in workflow.md)

---

## Phase 2: PGN Loader Module [checkpoint: 0847d17]

### Tasks

- [x] Task 2.1: Write tests for pgn_loader.py (Red Phase) [eb90198]
  - Create `tests/test_pgn_loader.py`
  - Test `load_games_from_string()` with a minimal valid PGN — assert 1 game returned
  - Test `load_games_from_string()` with multiple games — assert correct count
  - Test `load_games_from_string()` with empty string — assert empty list
  - Test `load_games_from_file()` by writing a temp PGN file and reading it back
  - Test `iterate_positions()` yields `(board_before, move, board_after)` tuples
  - Test `iterate_positions()` only yields positions for the specified player color
  - Run tests and confirm they fail

- [x] Task 2.2: Implement modules/pgn_loader.py (Green Phase) [48cc75f]
  - Implement `load_games_from_file()`, `load_games_from_string()`, `iterate_positions()`
  - Run tests and confirm they pass
  - Run coverage and verify >80%

- [ ] Task: Conductor - User Manual Verification 'Phase 2: PGN Loader Module' (Protocol in workflow.md)

---

## Phase 3: Position Analyzer Module [checkpoint: 3430e18]

### Tasks

- [x] Task 3.1: Write tests for position_analyzer.py (Red Phase) [32902ac]
  - Create `tests/test_position_analyzer.py`
  - For each of the 7 detectors, create at least one test with a known FEN position
    where the concept IS present and one where it is NOT present
  - Test `detect_concepts()` returns a dict with all 7 keys
  - Test each sub-detector returns a dict with at minimum a `"detected"` key
  - Run tests and confirm they fail

- [x] Task 3.2: Implement modules/position_analyzer.py (Green Phase) [efbd1a4]
  - Implement all 7 detector functions and `detect_concepts()` per spec
  - Run tests and confirm they pass
  - Run coverage and verify >80%

- [ ] Task: Conductor - User Manual Verification 'Phase 3: Position Analyzer Module' (Protocol in workflow.md)

---

## Phase 4: Stockfish Validator Module [checkpoint: 9406564]

### Tasks

- [x] Task 4.1: Write tests for stockfish_validator.py (Red Phase) [2b5392a]
  - Create `tests/test_stockfish_validator.py`
  - Mock `chess.engine.SimpleEngine.popen_uci` to avoid requiring a real Stockfish binary
  - Test `validate_move()` returns dict with keys: `is_error`, `eval_before`,
    `eval_after`, `error_magnitude`, `best_move`
  - Test `validate_move()` sets `is_error=True` when `error_magnitude > 50`
  - Test `validate_move()` sets `is_error=False` when `error_magnitude <= 50`
  - Test `validate_move()` always calls `engine.quit()` (even on exception)
  - Test `batch_validate()` returns a list of the same length as input
  - Test `batch_validate()` calls `engine.quit()` exactly once
  - Run tests and confirm they fail

- [x] Task 4.2: Implement modules/stockfish_validator.py (Green Phase) [649c8be]
  - Implement `validate_move()` and `batch_validate()` per spec
  - Ensure `engine.quit()` is in a `finally` block
  - Run tests and confirm they pass
  - Run coverage and verify >80%

- [ ] Task: Conductor - User Manual Verification 'Phase 4: Stockfish Validator Module' (Protocol in workflow.md)

---

## Phase 5: Profile Builder Module [checkpoint: c44181b]

### Tasks

- [x] Task 5.1: Write tests for profile_builder.py (Red Phase) [43b1b75]
  - Create `tests/test_profile_builder.py`
  - Test `build_profile()` with empty games list returns zeroed profile
  - Test `build_profile()` counts `total_positions_analyzed` correctly
  - Test `build_profile()` counts `total_errors_detected` correctly
  - Test `build_profile()` only includes weaknesses with `>= MIN_OCCURRENCES` errors
  - Test `build_profile()` sorts weaknesses by `error_occurrences` descending
  - Test `save_profile()` writes valid JSON to disk
  - Test `load_profile()` reads back the saved file correctly
  - Run tests and confirm they fail

- [x] Task 5.2: Implement modules/profile_builder.py (Green Phase) [3ef1521]
  - Implement `build_profile()`, `save_profile()`, `load_profile()` per spec
  - Run tests and confirm they pass
  - Run coverage and verify >80%

- [ ] Task: Conductor - User Manual Verification 'Phase 5: Profile Builder Module' (Protocol in workflow.md)

---

## Phase 6: AI Diagnostician Module

### Tasks

- [x] Task 6.1: Write tests for ai_diagnostician.py (Red Phase) [d3bfaaf]
  - Create `tests/test_ai_diagnostician.py`
  - Mock the Anthropic client to avoid real API calls
  - Test `load_silman_concepts()` returns a dict keyed by `detection_key`
  - Test `load_silman_concepts()` loads all 7 concepts from `data/silman_concepts.json`
  - Test `diagnose()` calls the Anthropic API with the correct model (`claude-opus-4-6`)
  - Test `diagnose()` parses valid JSON response correctly
  - Test `diagnose()` handles markdown-fenced JSON response (strips ```json ... ```)
  - Test `diagnose()` enriches `study_priority` items with Silman metadata
  - Run tests and confirm they fail

- [ ] Task 6.2: Implement modules/ai_diagnostician.py (Green Phase)
  - Implement `load_silman_concepts()` and `diagnose()` per spec
  - Run tests and confirm they pass
  - Run coverage and verify >80%

- [ ] Task: Conductor - User Manual Verification 'Phase 6: AI Diagnostician Module' (Protocol in workflow.md)

---

## Phase 7: Main Pipeline & End-to-End Integration

### Tasks

- [ ] Task 7.1: Write integration tests for main.py (Red Phase)
  - Create `tests/test_main.py`
  - Mock `load_games_from_file`, `batch_validate`, and `diagnose` to avoid external deps
  - Test `analyze_player()` calls each pipeline stage in order
  - Test `analyze_player()` writes `<player_name>_profile.json` to `output/`
  - Test `analyze_player()` writes `<player_name>_diagnosis.json` to `output/`
  - Test `analyze_player()` returns `(profile, diagnosis)` tuple
  - Run tests and confirm they fail

- [ ] Task 7.2: Implement main.py (Green Phase)
  - Implement `analyze_player()` orchestrating all pipeline stages
  - Create `output/` directory on startup
  - Run tests and confirm they pass
  - Run `pytest --cov=modules --cov=main --cov-report=term` and verify >80% overall

- [ ] Task 7.3: Full coverage verification
  - Run `pytest --cov=modules --cov=main --cov-report=term-missing`
  - Identify any uncovered branches and add targeted tests
  - Confirm final coverage >80% for all modules

- [ ] Task: Conductor - User Manual Verification 'Phase 7: Main Pipeline & End-to-End Integration' (Protocol in workflow.md)
