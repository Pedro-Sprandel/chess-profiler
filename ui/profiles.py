"""Helpers for naming and labelling saved analyses.

Every run gets a unique internal key so re-running the same nickname never
overwrites an earlier analysis:

    {subject}__d{depth}[_g{n_games}]_{uid}      e.g.  magnuscarlsen__d12_g30_a1b2c3

That key is never shown to the user: labels are built from the stored summary
(subject, date, number of games, depth).
"""

import uuid
from datetime import datetime, timezone

from modules.analysis_store import NAME_SEP as SEP, parse_profile_name
from ui.i18n import t


def make_profile_name(subject: str, depth: int, n_games: int | None = None) -> str:
    """Build a unique profile base name encoding subject, depth, game count and a uid."""
    meta = [f"d{depth}"]
    if n_games is not None:
        meta.append(f"g{n_games}")
    meta.append(uuid.uuid4().hex[:6])
    return f"{subject}{SEP}{'_'.join(meta)}"


def format_date(utc_str: str | None) -> str:
    """'2026-11-07 14:32:05' (UTC) → '07/11/2026 14:32' (local server time)."""
    if not utc_str:
        return "—"
    try:
        dt = datetime.strptime(utc_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return utc_str
    return dt.astimezone().strftime("%d/%m/%Y %H:%M")


def analysis_label(summary: dict) -> str:
    """'magnuscarlsen · 07/11/2026 14:32 · 30 games · depth 12'."""
    parts = [summary.get("subject") or summary.get("name", "?"), format_date(summary.get("created_at"))]
    games = summary.get("total_games") or summary.get("n_games")
    if games:
        parts.append(t("label.games", n=games))
    if summary.get("depth"):
        parts.append(t("label.depth", n=summary["depth"]))
    return " · ".join(parts)


def display_label(name: str) -> str:
    """Fallback label from the key alone (no DB summary available)."""
    for suffix in ("_profile.json", "_diagnosis.json"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    parsed = parse_profile_name(name)
    return analysis_label({"subject": parsed["subject"], "n_games": parsed["n_games"],
                           "depth": parsed["depth"], "created_at": None}).replace(" · —", "")
