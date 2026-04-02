# Spec: Chess Strategic Profiler MVP

## Overview

Build a complete, end-to-end CLI pipeline that:
1. Loads chess games from a PGN file
2. Detects strategic concepts in each position (deterministic rules)
3. Validates each move with Stockfish to identify errors
4. Aggregates results into a weakness profile
5. Calls Claude (claude-opus-4-6) to diagnose root causes
6. Outputs structured JSON reports

---

## Functional Requirements

### FR-01: PGN Loading
- The system MUST load all games from a `.pgn` file using `chess.pgn.read_game`.
- The system MUST support loading games from a string (for testing).
- The system MUST iterate over positions where it is the analyzed player's turn,
  yielding `(board_before, move_played, board_after)` tuples.

### FR-02: Strategic Concept Detection
The system MUST detect the following 7 concepts per position:

| Concept | Detection Key | Description |
|---|---|---|
| Weak Square | `weak_square` | Squares in player's half undefendable by pawns and attacked by opponent |
| Open File | `open_file` | Files with no pawns; semi-open files with only opponent pawns |
| Isolated Pawn | `isolated_pawn` | Player pawns with no allied pawns on adjacent files |
| Bishop Pair | `bishop_pair` | Player has 2 bishops, opponent does not |
| Knight Outpost | `knight_outpost` | Player knight in opponent's half, not attackable by opponent pawns |
| King Safety | `king_safety` | Fewer than 2 pawn shield squares near the king |
| Space Advantage | `space_advantage` | Player controls >5 more squares in opponent's half |

Each concept detector returns a dict with at minimum a `"detected": bool` key.

### FR-03: Stockfish Validation
- For each player position, compare the move played against Stockfish's best move.
- Compute `error_magnitude` in centipawns (from the player's perspective).
- A move is an error if `error_magnitude > ERROR_THRESHOLD_CP` (default: 50).
- The system MUST support batch validation (reusing one engine instance per game).

### FR-04: Profile Building
- Aggregate concept occurrences and error co-occurrences across all games.
- A weakness qualifies if it has `>= MIN_OCCURRENCES` (default: 3) error co-occurrences.
- Output includes: `total_games`, `total_positions_analyzed`, `total_errors_detected`,
  `overall_error_rate`, and a ranked `weaknesses` list.

### FR-05: AI Diagnosis
- Send the weakness profile + Silman knowledge base to Claude.
- Claude returns a structured JSON with:
  - `root_cause`: the underlying cognitive/strategic problem
  - `weakness_classification`: PRIMARY / SECONDARY / NOISE per concept
  - `study_priority`: ranked list of Silman chapters to study
  - `cognitive_pattern`: description of the thinking pattern to change
  - `confidence`: HIGH / MEDIUM / LOW

### FR-06: Output
- Save `<player_name>_profile.json` and `<player_name>_diagnosis.json` to `output/`.
- Print a human-readable summary to stdout.

---

## Non-Functional Requirements

- **NFR-01:** Stockfish is always closed after use (even on error) via `engine.quit()` in a `finally` block.
- **NFR-02:** The Anthropic API key is never hardcoded; loaded from `.env` via `python-dotenv`.
- **NFR-03:** All JSON output is UTF-8 encoded with 2-space indentation.
- **NFR-04:** All public functions have type hints and docstrings.
- **NFR-05:** Test coverage for all modules must exceed 80%.

---

## Data Files

### `data/silman_concepts.json`
Contains 7 concept entries manually extracted from "The Amateur's Mind":
`weak_square`, `open_file`, `isolated_pawn`, `bishop_pair`, `knight_outpost`,
`king_safety`, `space_advantage`.

Each entry includes: `id`, `name`, `silman_chapter`, `silman_page`,
`silman_category`, `description`, `strategic_implications`, `detection_key`.

---

## File Structure

```
chess_profiler/
├── requirements.txt
├── config.py
├── main.py
├── data/
│   └── silman_concepts.json
├── modules/
│   ├── pgn_loader.py
│   ├── position_analyzer.py
│   ├── stockfish_validator.py
│   ├── profile_builder.py
│   └── ai_diagnostician.py
├── tests/
│   ├── test_pgn_loader.py
│   ├── test_position_analyzer.py
│   ├── test_stockfish_validator.py
│   ├── test_profile_builder.py
│   └── test_ai_diagnostician.py
└── output/
```

---

## Acceptance Criteria

- Running `python main.py` with a valid `partidas.pgn` produces both output JSON files.
- The weakness profile correctly counts concept co-occurrences with errors.
- The AI diagnosis returns valid JSON matching the expected schema.
- All unit tests pass with >80% coverage (`pytest --cov=modules --cov-report=term`).
