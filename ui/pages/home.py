import streamlit as st

from ui.i18n import t
from ui.style import anchor, section_header


def render():
    anchor("home")
    section_header(t("home.eyebrow"), t("home.title"))
    st.markdown(f'<div class="cp-hero">{_md_italics(t("home.lead"))}</div>', unsafe_allow_html=True)
    st.write("")

    cols = st.columns(3)
    for i, col in enumerate(cols, start=1):
        col.markdown(
            f"""<div class="cp-card">
                  <div class="cp-step-n">0{i}</div>
                  <h4>{t(f"home.step{i}.title")}</h4>
                  <p>{t(f"home.step{i}.body")}</p>
                </div>""",
            unsafe_allow_html=True,
        )


def _md_italics(text: str) -> str:
    """Render *x* as <em>x</em> inside raw HTML blocks."""
    parts = text.split("*")
    return "".join(f"<em>{p}</em>" if i % 2 else p for i, p in enumerate(parts))
