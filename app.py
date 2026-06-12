import hmac
import os
import streamlit as st
import streamlit.components.v1 as components

from config import APP_PASSWORD, OUTPUT_DIR
from ui.profiles import display_label

st.set_page_config(
    page_title="Chess Strategic Profiler",
    page_icon="♟",
    layout="wide",
)


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

    st.title("🔒 Chess Strategic Profiler")
    entered = st.text_input("Password", type="password", key="_password_input")
    if entered:
        if hmac.compare_digest(entered, APP_PASSWORD):
            st.session_state["_authenticated"] = True
            del st.session_state["_password_input"]
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


if not _check_password():
    st.stop()

# ── Session state defaults ────────────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "pt"

if "active_profile" not in st.session_state:
    profile_files = sorted(
        f for f in os.listdir(OUTPUT_DIR) if f.endswith("_profile.json")
    ) if os.path.isdir(OUTPUT_DIR) else []
    st.session_state.active_profile = profile_files[0] if profile_files else None

from ui.i18n import t

_busy = st.session_state.get("analysis_running", False) or st.session_state.get("diagnosis_running", False)

with st.sidebar:
    st.title(t("nav.title"))

    # ── Language selector ─────────────────────────────────────────────────────
    # Disabled while an analysis is running: switching widgets mid-run triggers a
    # rerun that would interrupt the in-flight pipeline.
    st.radio(
        t("lang.label"),
        options=["en", "pt"],
        format_func=lambda x: "🇺🇸 English" if x == "en" else "🇧🇷 Português",
        horizontal=True,
        key="lang",
        disabled=_busy,
    )

    st.divider()

    # ── Shared profile selector ───────────────────────────────────────────────
    profile_files = sorted(
        f for f in os.listdir(OUTPUT_DIR) if f.endswith("_profile.json")
    ) if os.path.isdir(OUTPUT_DIR) else []

    if profile_files:
        current = st.session_state.active_profile
        idx = profile_files.index(current) if current in profile_files else 0
        chosen = st.selectbox(
            t("sidebar.profile"),
            profile_files,
            index=idx,
            key="profile_widget",
            disabled=_busy,
            format_func=display_label,
        )
        # Sync manual sidebar selection back to active_profile
        st.session_state.active_profile = chosen

        # ── Delete profile ────────────────────────────────────────────────────
        with st.expander(t("sidebar.delete")):
            st.warning(t("sidebar.delete_warn", name=display_label(chosen)))
            if st.button(t("sidebar.delete_confirm"), type="primary", use_container_width=True, disabled=_busy):
                base = chosen[: -len("_profile.json")]
                for suffix in ("_profile.json", "_diagnosis.json"):
                    fpath = os.path.join(OUTPUT_DIR, base + suffix)
                    if os.path.exists(fpath):
                        os.remove(fpath)
                st.session_state.active_profile = None
                st.session_state.pop("profile_widget", None)
                st.toast(t("sidebar.deleted", name=display_label(chosen)))
                st.rerun()
    else:
        st.caption(t("sidebar.no_profiles"))

    st.divider()

    # ── Navigation ────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <nav id="section-nav">
        <a href="#home"              class="nav-link" style="display:block;padding:6px 0 6px 12px;text-decoration:none;color:white;border-left:3px solid transparent;transition:all 0.15s">{t("nav.home")}</a>
        <a href="#analyze"           class="nav-link" style="display:block;padding:6px 0 6px 12px;text-decoration:none;color:white;border-left:3px solid transparent;transition:all 0.15s">{t("nav.analyze")}</a>
        <a href="#profile-dashboard" class="nav-link" style="display:block;padding:6px 0 6px 12px;text-decoration:none;color:white;border-left:3px solid transparent;transition:all 0.15s">{t("nav.profile")}</a>
        <a href="#game-explorer"     class="nav-link" style="display:block;padding:6px 0 6px 12px;text-decoration:none;color:white;border-left:3px solid transparent;transition:all 0.15s">{t("nav.explorer")}</a>
        <a href="#diagnosis-report"  class="nav-link" style="display:block;padding:6px 0 6px 12px;text-decoration:none;color:white;border-left:3px solid transparent;transition:all 0.15s">{t("nav.diagnosis")}</a>
        </nav>
        """,
        unsafe_allow_html=True,
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
                    var on = id === activeId;
                    link.style.fontWeight   = on ? '700'                : '400';
                    link.style.color        = on ? '#ff4b4b'            : 'white';
                    link.style.borderLeft   = on ? '3px solid #ff4b4b' : '3px solid transparent';
                    link.style.paddingLeft  = on ? '9px'                : '12px';
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
