"""UI-side access to saved analyses (profile + diagnosis), scoped to the logged-in user.

The `analyses` table in the AppStore (PostgreSQL when DATABASE_URL is set, SQLite
otherwise) is the single source of truth. Every read/delete is filtered by the
current account, so one user never sees or touches another user's analyses.
Legacy `output/*_profile.json` files are imported once per session.
"""
import os

import streamlit as st

from config import OUTPUT_DIR
from modules.analysis_store import DIAGNOSIS_SUFFIX, PROFILE_SUFFIX, import_legacy_outputs
from modules.app_store import AppStore
from ui.auth import current_user, current_user_id


def _store():
    return AppStore()


def _owner() -> int:
    owner = current_user_id()
    if owner is None:  # app.py only renders pages after require_login()
        raise RuntimeError("no logged-in user")
    return owner


def normalize_name(name: str | None) -> str | None:
    """Accept legacy `{name}_profile.json` values stored in session state."""
    if name and name.endswith(PROFILE_SUFFIX):
        return name[: -len(PROFILE_SUFFIX)]
    return name


def ensure_legacy_imported() -> int:
    """Import leftover JSON files and, for the admin, adopt analyses with no owner.

    Analyses created before login existed (or by the CLI without --owner) have no
    owner; the administrator account (the first one created) receives them.
    Returns how many analyses were assigned to the current user.
    """
    if st.session_state.get("_legacy_imported"):
        return 0
    claimed = 0
    try:
        with _store() as store:
            import_legacy_outputs(store, OUTPUT_DIR)
            user = current_user()
            if user and user["is_admin"]:
                claimed = store.claim_orphan_analyses(user["id"])
    finally:
        st.session_state["_legacy_imported"] = True
    return claimed


def list_analyses() -> list[dict]:
    with _store() as store:
        return store.list_analyses(owner_id=_owner())


def get_analysis(name: str | None) -> dict | None:
    name = normalize_name(name)
    if not name:
        return None
    with _store() as store:
        return store.get_analysis(name, owner_id=_owner())


def delete_analysis(name: str) -> bool:
    """Remove the user's analysis and any exported JSON files of the same name."""
    with _store() as store:
        if not store.delete_analysis(name, owner_id=_owner()):
            return False
        store.mark_legacy_imported(name)  # never re-import it from a leftover file
    for suffix in (PROFILE_SUFFIX, DIAGNOSIS_SUFFIX):
        path = os.path.join(OUTPUT_DIR, name + suffix)
        if os.path.exists(path):
            os.remove(path)
    return True


def get_explanation(fen, move_played, concept_key, lang) -> str | None:
    with _store() as store:
        return store.get_explanation(fen, move_played, concept_key, lang)


def save_explanation(fen, move_played, concept_key, lang, text):
    with _store() as store:
        store.save_explanation(fen, move_played, concept_key, lang, text)
