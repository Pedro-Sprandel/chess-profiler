import hmac

import streamlit as st
import streamlit.components.v1 as components

from config import APP_PASSWORD

st.set_page_config(
    page_title="Chess Profiler",
    page_icon="♟",
    layout="wide",
)

from ui.i18n import t
from ui.profiles import analysis_label
from ui.store import delete_analysis, ensure_legacy_imported, list_analyses, normalize_name
from ui.style import inject_css

inject_css()

# ── Session state defaults ────────────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "pt"


def _check_password() -> bool:
    """Shared-password gate for the private deploy.

    If APP_PASSWORD is unset (local/dev) there is no gate. Otherwise the app is
    blocked until the visitor enters the matching password. This is a lightweight
    gate for a trusted handful of friends — not a real auth/identity system.
    """
    if not APP_PASSWORD:
        return True
    if st.session_state.get("_authenticated"):
        return True

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown(f'<div class="cp-title" style="margin:4rem 0 1.5rem">{t("auth.title")}</div>',
                    unsafe_allow_html=True)
        entered = st.text_input(t("auth.password"), type="password", key="_password_input")
        if entered:
            if hmac.compare_digest(entered, APP_PASSWORD):
                st.session_state["_authenticated"] = True
                del st.session_state["_password_input"]
                st.rerun()
            else:
                st.error(t("auth.wrong"))
    return False


if not _check_password():
    st.stop()

# ── Saved analyses (SQLite is the single source of truth) ─────────────────────
ensure_legacy_imported()
analyses = list_analyses()
summaries = {a["name"]: a for a in analyses}

# Default to the most recent analysis; drop a selection that no longer exists.
active = normalize_name(st.session_state.get("active_profile"))
if "active_profile" not in st.session_state or (active and active not in summaries):
    active = analyses[0]["name"] if analyses else None
st.session_state.active_profile = active

_busy = st.session_state.get("analysis_running", False) or st.session_state.get("diagnosis_running", False)


def _on_profile_change():
    st.session_state.active_profile = st.session_state.profile_widget


with st.sidebar:
    st.markdown(
        f'<div class="cp-brand">{t("nav.title")}</div><div class="cp-brand-sub">{t("nav.subtitle")}</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    # ── Analysis selector ─────────────────────────────────────────────────────
    # The widget mirrors active_profile: programmatic changes (a new analysis, a
    # row picked in the history table) are pushed into the widget before it is
    # drawn, and user changes flow back through the on_change callback.
    if analyses:
        if st.session_state.get("profile_widget") != active:
            st.session_state.profile_widget = active
        st.selectbox(
            t("sidebar.profile"),
            list(summaries),
            key="profile_widget",
            on_change=_on_profile_change,
            disabled=_busy,
            format_func=lambda n: analysis_label(summaries[n]),
        )

        with st.popover(t("sidebar.delete"), use_container_width=True, disabled=_busy):
            label = analysis_label(summaries[active])
            st.markdown(t("sidebar.delete_warn", name=label))
            if st.button(t("sidebar.delete_confirm"), type="primary", use_container_width=True,
                         key="delete_confirm"):
                delete_analysis(active)
                st.session_state.pop("active_profile", None)
                st.session_state.pop("profile_widget", None)
                st.toast(t("sidebar.deleted", name=label))
                st.rerun()
    else:
        st.caption(t("sidebar.no_profiles"))

    st.write("")

    # ── Navigation ────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="cp-eyebrow" style="margin-bottom:.4rem">{t("nav.sections")}</div>
        <nav id="section-nav">
          <a href="#home"              class="nav-link">{t("nav.home")}</a>
          <a href="#analyze"           class="nav-link">{t("nav.analyze")}</a>
          <a href="#profile-dashboard" class="nav-link">{t("nav.profile")}</a>
          <a href="#game-explorer"     class="nav-link">{t("nav.explorer")}</a>
          <a href="#diagnosis-report"  class="nav-link">{t("nav.diagnosis")}</a>
        </nav>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    st.write("")

    # ── Language ──────────────────────────────────────────────────────────────
    # Disabled while an analysis is running: switching widgets mid-run triggers a
    # rerun that would interrupt the in-flight pipeline.
    st.radio(
        t("lang.label"),
        options=["pt", "en"],
        format_func=lambda x: "Português" if x == "pt" else "English",
        horizontal=True,
        key="lang",
        disabled=_busy,
    )

from ui.pages.home import render as render_home
from ui.pages.analyze import render as render_analyze
from ui.pages.profile import render as render_profile
from ui.pages.explorer import render as render_explorer
from ui.pages.diagnosis import render as render_diagnosis

render_home()
st.divider()
render_analyze()
st.divider()
render_profile()
st.divider()
render_explorer()
st.divider()
render_diagnosis()

# ── Scroll-spy: highlight active section in the sidebar ───────────────────────
components.html(
    """
    <script>
    (function () {
        function setup() {
            var doc = window.parent.document;
            var sections = Array.from(doc.querySelectorAll('a[name]'));
            var navLinks = Array.from(doc.querySelectorAll('#section-nav a.nav-link'));

            if (!sections.length || !navLinks.length) {
                setTimeout(setup, 400);
                return;
            }

            var scrollEl = doc.querySelector('[data-testid="stMain"]')
                        || doc.scrollingElement
                        || doc.documentElement;

            function getActiveId() {
                var threshold = window.parent.innerHeight * 0.35;
                var active = null;
                sections.forEach(function (s) {
                    if (s.getBoundingClientRect().top <= threshold) {
                        active = s.getAttribute('name');
                    }
                });
                return active || sections[0].getAttribute('name');
            }

            function update() {
                var activeId = getActiveId();
                navLinks.forEach(function (link) {
                    var id = (link.getAttribute('href') || '').slice(1);
                    link.classList.toggle('active', id === activeId);
                });
            }

            if (window.parent._spyListener && window.parent._spyEl) {
                window.parent._spyEl.removeEventListener('scroll', window.parent._spyListener);
            }
            window.parent._spyListener = update;
            window.parent._spyEl = scrollEl;
            scrollEl.addEventListener('scroll', update, { passive: true });
            update();
        }

        setup();
    })();
    </script>
    """,
    height=0,
)
