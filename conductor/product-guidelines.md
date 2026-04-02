# Product Guidelines

## Tone & Communication Style
- Output is technical and concise — targeted at developers and the thesis evaluator.
- CLI output uses bracket-prefixed module labels (e.g., `[pgn_loader]`, `[main]`) for clarity.
- No decorative UI — progress is communicated via print statements only.

## Code Style & Quality
- Python 3.10+ idioms; type hints on all public functions.
- Functions are single-responsibility and independently testable.
- No premature abstraction — build only what the pipeline requires.
- Error handling at system boundaries only (file I/O, Stockfish subprocess, API calls).

## Data & Output Conventions
- All structured outputs are UTF-8 encoded JSON with 2-space indentation.
- File naming: `<player_name>_profile.json`, `<player_name>_diagnosis.json`.
- FEN strings and UCI move notation are the canonical formats for positions and moves.

## Academic Integrity
- The Silman knowledge base (`silman_concepts.json`) is manually extracted to preserve
  interpretive fidelity — do not auto-generate or infer Silman content.
- The LLM acts as a reasoning component over quantitative data, not a content generator.
- All design decisions should be documentable in the TCC as justified architectural choices.

## Constraints
- Stockfish must run as a local binary (no cloud engine).
- The Anthropic API key is loaded exclusively from environment variables via `.env`.
- The system processes one player at a time (single PGN file per run).
