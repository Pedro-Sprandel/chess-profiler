"""
db.py — SQLite persistence layer for Chess Strategic Profiler.

Three tables:
  fen_cache        : Stockfish evaluation cache keyed by (fen, depth).
                     Avoids re-analyzing the same position twice.
  positions        : FEN positions imported from real games (Chess.com or PGN).
                     Each row is one position from one game at one move.
  analysis_results : Concept detection + Stockfish verdict for each position.
                     Links back to positions via position_id.

Usage:
    from modules.db import Database

    db = Database()                   # uses default path (data/profiler.db)
    db = Database("path/to/file.db")  # custom path

    # Stockfish cache
    db.cache_eval(fen, depth, score_cp, best_move)
    result = db.get_cached_eval(fen, depth)   # None if not cached

    # Positions
    pos_id = db.insert_position({...})
    positions = db.query_positions(min_rating=1400, eco="B20")

    # Analysis results
    db.insert_analysis_result(position_id, concept_key, detected, details, is_error, magnitude)
    rows = db.get_analysis_results(position_id)

    db.close()
"""

import json
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "profiler.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS fen_cache (
    fen         TEXT    NOT NULL,
    depth       INTEGER NOT NULL,
    score_cp    INTEGER,
    best_move   TEXT,
    analyzed_at TEXT    DEFAULT (datetime('now')),
    PRIMARY KEY (fen, depth)
);

CREATE TABLE IF NOT EXISTS positions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    fen          TEXT    NOT NULL,
    move_number  INTEGER,
    move_played  TEXT,
    player_color TEXT,
    white        TEXT,
    black        TEXT,
    white_rating INTEGER,
    black_rating INTEGER,
    opening      TEXT,
    eco          TEXT,
    game_url     TEXT,
    source       TEXT,
    imported_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_positions_eco          ON positions(eco);
CREATE INDEX IF NOT EXISTS idx_positions_white_rating ON positions(white_rating);
CREATE INDEX IF NOT EXISTS idx_positions_black_rating ON positions(black_rating);

CREATE TABLE IF NOT EXISTS analysis_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id     INTEGER NOT NULL REFERENCES positions(id) ON DELETE CASCADE,
    concept_key     TEXT    NOT NULL,
    detected        INTEGER NOT NULL,
    details_json    TEXT,
    is_error        INTEGER NOT NULL DEFAULT 0,
    error_magnitude REAL    DEFAULT 0,
    analyzed_at     TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_analysis_position  ON analysis_results(position_id);
CREATE INDEX IF NOT EXISTS idx_analysis_concept   ON analysis_results(concept_key);
CREATE INDEX IF NOT EXISTS idx_analysis_is_error  ON analysis_results(is_error);
"""


class Database:
    def __init__(self, path: str | Path = DEFAULT_DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # ── Stockfish evaluation cache ────────────────────────────────────────────

    def get_cached_eval(self, fen: str, depth: int) -> dict | None:
        """Returns cached Stockfish result for (fen, depth), or None."""
        row = self._conn.execute(
            "SELECT score_cp, best_move FROM fen_cache WHERE fen = ? AND depth = ?",
            (fen, depth),
        ).fetchone()
        if row is None:
            return None
        return {"score_cp": row["score_cp"], "best_move": row["best_move"]}

    def cache_eval(self, fen: str, depth: int, score_cp: int, best_move: str | None):
        """Inserts or replaces a Stockfish evaluation in the cache."""
        self._conn.execute(
            """
            INSERT INTO fen_cache (fen, depth, score_cp, best_move)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(fen, depth) DO UPDATE SET
                score_cp    = excluded.score_cp,
                best_move   = excluded.best_move,
                analyzed_at = datetime('now')
            """,
            (fen, depth, score_cp, best_move),
        )
        self._conn.commit()

    def cache_stats(self) -> dict:
        """Returns how many evaluations are cached."""
        row = self._conn.execute("SELECT COUNT(*) AS n FROM fen_cache").fetchone()
        return {"cached_evals": row["n"]}

    # ── Positions ─────────────────────────────────────────────────────────────

    def insert_position(self, pos: dict) -> int:
        """
        Inserts a position dict and returns its row id.
        Expected keys (all optional except fen):
            fen, move_number, move_played, player_color,
            white, black, white_rating, black_rating,
            opening, eco, game_url, source
        """
        cur = self._conn.execute(
            """
            INSERT INTO positions
                (fen, move_number, move_played, player_color,
                 white, black, white_rating, black_rating,
                 opening, eco, game_url, source)
            VALUES
                (:fen, :move_number, :move_played, :player_color,
                 :white, :black, :white_rating, :black_rating,
                 :opening, :eco, :game_url, :source)
            """,
            {
                "fen":          pos.get("fen"),
                "move_number":  pos.get("move_number"),
                "move_played":  pos.get("move_played"),
                "player_color": pos.get("player_color"),
                "white":        pos.get("white"),
                "black":        pos.get("black"),
                "white_rating": pos.get("white_rating"),
                "black_rating": pos.get("black_rating"),
                "opening":      pos.get("opening"),
                "eco":          pos.get("eco"),
                "game_url":     pos.get("game_url"),
                "source":       pos.get("source", "unknown"),
            },
        )
        self._conn.commit()
        return cur.lastrowid

    def insert_positions_bulk(self, positions: list[dict], source: str = "chess_com") -> list[int]:
        """Inserts multiple positions and returns their ids."""
        ids = []
        for pos in positions:
            pos.setdefault("source", source)
            ids.append(self.insert_position(pos))
        return ids

    def query_positions(
        self,
        min_rating: int | None = None,
        max_rating: int | None = None,
        eco: str | None = None,
        opening_name: str | None = None,
        player_color: str | None = None,
        source: str | None = None,
        limit: int = 500,
    ) -> list[dict]:
        """
        Queries stored positions with optional filters.
        Rating filter applies to the opponent (based on player_color).
        eco supports prefix matching (e.g. "B" matches all B-codes).
        """
        conditions = []
        params: list = []

        if min_rating is not None:
            conditions.append(
                "(CASE WHEN player_color='white' THEN black_rating ELSE white_rating END) >= ?"
            )
            params.append(min_rating)
        if max_rating is not None:
            conditions.append(
                "(CASE WHEN player_color='white' THEN black_rating ELSE white_rating END) <= ?"
            )
            params.append(max_rating)
        if eco:
            conditions.append("eco LIKE ?")
            params.append(eco.upper() + "%")
        if opening_name:
            conditions.append("opening LIKE ?")
            params.append(f"%{opening_name}%")
        if player_color:
            conditions.append("player_color = ?")
            params.append(player_color)
        if source:
            conditions.append("source = ?")
            params.append(source)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = self._conn.execute(
            f"SELECT * FROM positions {where} LIMIT ?",
            params + [limit],
        ).fetchall()
        return [dict(r) for r in rows]

    def count_positions(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]

    # ── Analysis results ──────────────────────────────────────────────────────

    def insert_analysis_result(
        self,
        position_id: int,
        concept_key: str,
        detected: bool,
        details: dict,
        is_error: bool,
        error_magnitude: float,
    ):
        self._conn.execute(
            """
            INSERT INTO analysis_results
                (position_id, concept_key, detected, details_json, is_error, error_magnitude)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                position_id,
                concept_key,
                int(detected),
                json.dumps(details),
                int(is_error),
                error_magnitude,
            ),
        )
        self._conn.commit()

    def insert_analysis_results_bulk(self, rows: list[tuple]):
        """
        Bulk-inserts analysis results in a single transaction.
        rows: list of (position_id, concept_key, detected, details_dict, is_error, error_magnitude)
        """
        self._conn.executemany(
            """
            INSERT INTO analysis_results
                (position_id, concept_key, detected, details_json, is_error, error_magnitude)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (pos_id, key, int(det), json.dumps(details), int(err), mag)
                for pos_id, key, det, details, err, mag in rows
            ],
        )
        self._conn.commit()

    def get_analysis_results(self, position_id: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM analysis_results WHERE position_id = ?",
            (position_id,),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["details"] = json.loads(d.pop("details_json") or "{}")
            results.append(d)
        return results

    def concept_error_summary(self) -> list[dict]:
        """
        Aggregates error counts per concept across all stored analysis results.
        Returns list sorted by error_occurrences descending.
        """
        rows = self._conn.execute(
            """
            SELECT
                concept_key,
                COUNT(*) AS total_occurrences,
                SUM(is_error) AS error_occurrences,
                ROUND(AVG(CASE WHEN is_error THEN error_magnitude END), 1) AS avg_error_magnitude
            FROM analysis_results
            WHERE detected = 1
            GROUP BY concept_key
            ORDER BY error_occurrences DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Housekeeping ──────────────────────────────────────────────────────────

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
