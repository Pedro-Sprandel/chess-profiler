"""Helpers for profile naming.

Several friends share one backend, and a person may re-run the same nickname with
different settings. To avoid collisions/overwrites we give every analysis its own
self-describing, unique profile name:

    {subject}__d{depth}[_g{n_games}]_{uid}      e.g.  magnuscarlsen__d12_g30_a1b2c3

`subject` is the chess.com username (or PGN player name). The random uid makes each
run unique; depth and game count make the profile self-describing in the selector.
"""

import uuid

SEP = "__"


def make_profile_name(subject: str, depth: int, n_games: int | None = None) -> str:
    """Build a unique profile base name encoding subject, depth, game count and a uid."""
    meta = [f"d{depth}"]
    if n_games is not None:
        meta.append(f"g{n_games}")
    meta.append(uuid.uuid4().hex[:6])
    return f"{subject}{SEP}{'_'.join(meta)}"


def display_label(profile_filename: str) -> str:
    """Human label for a profile filename, e.g. 'magnuscarlsen · 30 games · depth 12 · a1b2c3'.

    Falls back to the raw base for legacy/unstructured names.
    """
    base = profile_filename
    for suffix in ("_profile.json", "_diagnosis.json"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break

    if SEP not in base:
        return base
    subject, meta = base.rsplit(SEP, 1)
    tokens = meta.split("_")

    # Recognize our format only when it starts with d<digits>; else show raw.
    if not (tokens[0].startswith("d") and tokens[0][1:].isdigit()):
        return base

    depth = tokens[0][1:]
    games = uid = None
    if len(tokens) == 3 and tokens[1].startswith("g"):
        games, uid = tokens[1][1:], tokens[2]
    elif len(tokens) == 2:
        uid = tokens[1]

    extras = []
    if games:
        extras.append(f"{games} games")
    extras.append(f"depth {depth}")
    if uid:
        extras.append(uid)
    return f"{subject} · " + " · ".join(extras)
