"""Helpers for per-person profile namespacing.

On the private deploy several friends share one backend. Profiles are stored as
`{name}_profile.json`, so without a prefix two people analyzing the same chess.com
nickname would overwrite each other. We prefix the stored name with an owner slug:

    {owner}__{subject}_profile.json   e.g.  pedro__magnuscarlsen_profile.json

The owner slug is restricted to [A-Za-z0-9-] (no underscores), so splitting on the
first "__" unambiguously recovers (owner, subject) even when the subject contains
underscores.
"""

import re

SEP = "__"


def owner_slug(name: str) -> str:
    """Filename-safe slug for an owner name (no underscores, so SEP stays unambiguous)."""
    return re.sub(r"[^A-Za-z0-9-]+", "-", (name or "").strip()).strip("-")


def make_profile_name(owner: str, subject: str) -> str:
    """Combine an owner with a subject (chess.com username / player name).

    Returns the bare subject when no owner is given (backward compatible).
    """
    o = owner_slug(owner)
    return f"{o}{SEP}{subject}" if o else subject


def display_label(profile_filename: str) -> str:
    """Human label for a profile filename: 'owner · subject' (or just 'subject')."""
    base = profile_filename
    for suffix in ("_profile.json", "_diagnosis.json"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    if SEP in base:
        owner, subject = base.split(SEP, 1)
        return f"{owner} · {subject}"
    return base
