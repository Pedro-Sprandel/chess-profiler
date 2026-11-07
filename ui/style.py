"""Visual system for the Streamlit UI: palette, global CSS and small HTML helpers.

Kept deliberately restrained — neutral greys, one slate accent, one muted red for
errors — so the data (charts, boards, diagnosis) carries the page, not decoration.
"""
from html import escape

import streamlit as st

# ── Palette (mirrors .streamlit/config.toml, dark) ────────────────────────────
BG = "#0F1216"           # page background
CARD = "#151A20"         # cards, chart and board background
SURFACE = "#1A1F26"      # inputs, quote blocks
GRID = "#232932"         # chart gridlines
BORDER = "#2A3038"
INK = "#E3E7EC"
MUTED = "#9AA4B2"
SUBTLE = "#6B7685"
ACCENT = "#7FA3C7"       # slate blue — primary data series
ACCENT_SOFT = "#4C6884"
ACCENT_FILL = "rgba(127, 163, 199, 0.18)"
ERROR = "#D9765F"        # muted brick — "move played" / errors
GOOD = "#6DBE8C"         # muted green — "best move"
WARN = "#D6A548"

CLASSIFICATION_COLORS = {
    "PRIMARY": ERROR,
    "SECONDARY": WARN,
    "NOISE": SUBTLE,
}

CONFIDENCE_COLORS = {
    "HIGH": GOOD,
    "MEDIUM": WARN,
    "LOW": SUBTLE,
}

_CSS = f"""
<style>
/* Layout */
.block-container {{ padding-top: 2.5rem; padding-bottom: 4rem; max-width: 1180px; }}
[data-testid="stSidebar"] {{ border-right: 1px solid {BORDER}; }}
[data-testid="stSidebar"] .block-container {{ padding-top: 1.5rem; }}
hr {{ margin: 2.5rem 0 !important; border-color: {BORDER} !important; }}

/* Typography */
h1, h2, h3 {{ letter-spacing: -0.01em; color: {INK}; }}
h1 {{ font-weight: 650 !important; }}
h3 {{ font-weight: 600 !important; font-size: 1.15rem !important; }}

/* Section header */
.cp-eyebrow {{
  font-size: 0.72rem; font-weight: 600; letter-spacing: 0.09em;
  text-transform: uppercase; color: {SUBTLE}; margin-bottom: 0.15rem;
}}
.cp-title {{ font-size: 1.75rem; font-weight: 650; color: {INK}; line-height: 1.2; margin: 0; }}
.cp-subtitle {{ color: {MUTED}; font-size: 0.95rem; margin: 0.35rem 0 1.25rem 0; }}

/* Brand */
.cp-brand {{ font-size: 1.05rem; font-weight: 650; color: {INK}; letter-spacing: -0.01em; }}
.cp-brand-sub {{ font-size: 0.8rem; color: {SUBTLE}; margin-top: 0.1rem; }}

/* Sidebar nav */
#section-nav a.nav-link {{
  display: block; padding: 5px 0 5px 12px; text-decoration: none;
  color: {MUTED}; font-size: 0.9rem;
  border-left: 2px solid {BORDER}; transition: color .15s, border-color .15s;
}}
#section-nav a.nav-link:hover {{ color: {INK}; }}
#section-nav a.nav-link.active {{ color: {INK}; font-weight: 600; border-left-color: {ACCENT}; }}

/* Cards */
.cp-card {{
  border: 1px solid {BORDER}; border-radius: 6px; padding: 1rem 1.15rem;
  background: {CARD}; margin-bottom: 0.75rem;
}}
.cp-card h4 {{ margin: 0 0 0.35rem 0; font-size: 1rem; font-weight: 600; color: {INK}; }}
.cp-card p {{ margin: 0; color: {MUTED}; font-size: 0.92rem; line-height: 1.55; }}
.cp-step-n {{ font-size: 0.75rem; font-weight: 600; color: {ACCENT}; letter-spacing: 0.06em; }}
.cp-hero {{ font-size: 1.05rem; color: {MUTED}; line-height: 1.6; max-width: 46rem; }}

/* Badges */
.cp-badge {{
  display: inline-block; padding: 1px 8px; border-radius: 3px;
  font-size: 0.7rem; font-weight: 600; letter-spacing: 0.05em;
  text-transform: uppercase; border: 1px solid currentColor; vertical-align: middle;
}}

/* Key/value list (explorer) */
table.cp-kv {{ border-collapse: collapse; width: 100%; font-size: 0.92rem; border: none !important; }}
table.cp-kv tr {{ background: transparent !important; border: none !important; }}
table.cp-kv td {{
  padding: 7px 0 !important; border: none !important;
  border-bottom: 1px solid {BORDER} !important; vertical-align: top; background: transparent !important;
}}
table.cp-kv td:first-child {{ color: {SUBTLE}; width: 42%; padding-right: 12px; }}
table.cp-kv td:last-child {{ color: {INK}; font-weight: 500; }}
.cp-swatch {{
  display: inline-block; width: 10px; height: 10px; border-radius: 2px;
  margin-right: 6px; vertical-align: baseline;
}}

/* Quote */
.cp-quote {{
  border-left: 3px solid {ACCENT}; padding: 0.6rem 1rem; background: {SURFACE};
  color: {INK}; font-size: 0.98rem; line-height: 1.6; border-radius: 0 4px 4px 0;
}}

/* Metrics */
[data-testid="stMetricLabel"] p {{ font-size: 0.78rem !important; color: {MUTED}; }}
[data-testid="stMetricValue"] {{ font-size: 1.6rem !important; font-weight: 600; }}
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def anchor(name: str):
    """Invisible scroll target used by the sidebar navigation."""
    st.markdown(f'<a name="{name}"></a>', unsafe_allow_html=True)


def section_header(eyebrow: str, title: str, subtitle: str | None = None):
    html = f'<div class="cp-eyebrow">{escape(eyebrow)}</div><div class="cp-title">{escape(title)}</div>'
    html += f'<div class="cp-subtitle">{escape(subtitle)}</div>' if subtitle else '<div style="height:1rem"></div>'
    st.markdown(html, unsafe_allow_html=True)


def badge(text: str, color: str) -> str:
    return f'<span class="cp-badge" style="color:{color}">{escape(text)}</span>'


def swatch(color: str) -> str:
    return f'<span class="cp-swatch" style="background:{color}"></span>'
