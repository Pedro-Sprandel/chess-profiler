# Tech Stack

## Language
- **Python 3.10+**

## Core Libraries
- **python-chess (`chess`):** PGN parsing, board representation, move generation,
  and UCI engine communication.
- **Stockfish (local binary):** External chess engine for position evaluation and
  best-move analysis via `chess.engine.SimpleEngine`.
- **Anthropic Python SDK (`anthropic`):** Claude API client for LLM-based diagnosis.
- **python-dotenv (`python-dotenv`):** Environment variable management for API keys.

## AI Model
- **Claude claude-opus-4-6** (`claude-opus-4-6`): Used for root-cause reasoning over
  quantitative weakness profiles. Called via the Anthropic Messages API.

## Data Formats
- **PGN:** Input format for chess games.
- **JSON:** All intermediate and output data (profiles, diagnoses, knowledge base).
- **FEN:** Internal position representation.
- **UCI:** Move notation for Stockfish communication.

## Infrastructure
- **Local execution only** — no web server, no database, no cloud engine.
- **Stockfish binary** installed locally (path configured in `config.py`).
- **`.env` file** for secrets (not committed to version control).

## Dependencies (`requirements.txt`)
```
chess
anthropic
python-dotenv
```
