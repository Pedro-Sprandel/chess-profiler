"""UI-side access to saved analyses (profile + diagnosis), backed by SQLite.

The `analyses` table is the single source of truth. Legacy `output/*_profile.json`
files are imported once per session so older runs keep showing up.
"""
import os

import streamlit as st

from config import OUTPUT_DIR
from modules import db as db_module
from modules.analysis_store import DIAGNOSIS_SUFFIX, PROFILE_SUFFIX, import_legacy_outputs


def _db():
    return db_module.Database()


def normalize_name(name: str | None) -> str | None:
    """Accept legacy `{name}_profile.json` values stored in session state."""
    if name and name.endswith(PROFILE_SUFFIX):
        return name[: -len(PROFILE_SUFFIX)]
    return name


def ensure_legacy_imported():
    if st.session_state.get("_legacy_imported"):
        return
    try:
        with _db() as db:
            import_legacy_outputs(db, OUTPUT_DIR)
    finally:
        st.session_state["_legacy_imported"] = True


def list_analyses() -> list[dict]:
    with _db() as db:
        return db.list_analyses()


def get_analysis(name: str | None) -> dict | None:
    name = normalize_name(name)
    if not name:
        return None
    with _db() as db:
        return db.get_analysis(name)


def delete_analysis(name: str):
    """Remove the analysis and any exported JSON files of the same name."""
    with _db() as db:
        db.delete_analysis(name)
        db.mark_legacy_imported(name)  # never re-import it from a leftover file
    for suffix in (PROFILE_SUFFIX, DIAGNOSIS_SUFFIX):
        path = os.path.join(OUTPUT_DIR, name + suffix)
        if os.path.exists(path):
            os.remove(path)


def get_explanation(fen, move_played, concept_key, lang) -> str | None:
    with _db() as db:
        return db.get_explanation(fen, move_played, concept_key, lang)


def save_explanation(fen, move_played, concept_key, lang, text):
    with _db() as db:
        db.save_explanation(fen, move_played, concept_key, lang, text)
