"""Nomes localizados e categorias dos conceitos Silman para a UI.

Fonte única: data/silman_concepts.json (name = PT, name_en = EN,
silman_category = categoria em PT usada como chave canônica).
"""
import functools

import streamlit as st

from modules.ai_diagnostician import load_silman_concepts

CATEGORY_LABELS = {
    "desequilíbrios estáticos": {"pt": "Desequilíbrios estáticos", "en": "Static imbalances"},
    "desequilíbrios dinâmicos": {"pt": "Desequilíbrios dinâmicos", "en": "Dynamic imbalances"},
    "estrutura de peões":       {"pt": "Estrutura de peões",       "en": "Pawn structure"},
    "desequilíbrios de material": {"pt": "Desequilíbrios de material", "en": "Material imbalances"},
    "dinâmica":                 {"pt": "Dinâmica",                 "en": "Dynamics"},
    "tática":                   {"pt": "Tática",                   "en": "Tactics"},
}


@functools.lru_cache(maxsize=1)
def _concepts() -> dict:
    try:
        return load_silman_concepts()
    except Exception:
        return {}


def _lang() -> str:
    return st.session_state.get("lang", "pt")


def concept_label(key: str) -> str:
    """Nome do conceito no idioma ativo; fallback: detection_key legível."""
    concept = _concepts().get(key)
    fallback = key.replace("_", " ").title()
    if not concept:
        return fallback
    if _lang() == "en":
        return concept.get("name_en") or fallback
    return concept.get("name") or fallback


def concept_category(key: str) -> str | None:
    """Categoria Silman canônica (PT) do conceito, ou None."""
    concept = _concepts().get(key)
    return concept.get("silman_category") if concept else None


def category_label(category: str) -> str:
    """Categoria no idioma ativo."""
    labels = CATEGORY_LABELS.get(category)
    if not labels:
        return category
    return labels.get(_lang(), category)
