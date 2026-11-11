"""Login, cadastro e sessão persistente da interface.

Fluxo:
  - Contas e sessões ficam no AppStore (modules/app_store.py — Postgres ou SQLite).
  - Ao entrar, é criada uma sessão no banco; o token vai para um cookie do navegador
    (`cp_session`), então recarregar a página ou voltar dias depois mantém o login.
  - A cada execução do script, o token (do session_state ou do cookie) é revalidado
    no banco: sair, trocar a senha ou expirar a sessão derruba o acesso na hora.

O Streamlit não grava cookies pelo servidor; o cookie é escrito por um script num
components.html (mesma origem — o mesmo mecanismo do scroll-spy em app.py) e lido de
volta por st.context.cookies na próxima conexão. Por isso ele não é HttpOnly: o banco
guarda só o SHA-256 do token, e a sessão pode ser revogada a qualquer momento.
"""
import hmac
import json

import streamlit as st
import streamlit.components.v1 as components

import config
from modules.app_store import AppStore, AuthError
from ui.i18n import t

COOKIE_NAME = "cp_session"
_KEEP_ON_RESET = ("lang",)


# ── Estado da sessão ──────────────────────────────────────────────────────────

def current_user() -> dict | None:
    auth = st.session_state.get("auth")
    return auth["user"] if auth else None


def current_user_id() -> int | None:
    user = current_user()
    return user["id"] if user else None


def _cookie_token() -> str | None:
    try:
        value = st.context.cookies.get(COOKIE_NAME)
    except Exception:  # fora de um navegador (ex.: AppTest) não há cookies
        return None
    return value if isinstance(value, str) and value else None


def _reset_session_state():
    """Esquece tudo da conta anterior (análise ativa, tabelas, formulários…)."""
    for key in list(st.session_state.keys()):
        if key not in _KEEP_ON_RESET:
            del st.session_state[key]


def _start_session(user: dict, token: str):
    _reset_session_state()
    st.session_state["auth"] = {"user": user, "token": token}
    st.session_state["_cookie_op"] = ("set", token)
    st.rerun()


def logout():
    auth = st.session_state.get("auth") or {}
    try:
        with AppStore() as store:
            store.revoke_session(auth.get("token"))
    except Exception:
        pass  # mesmo com o banco fora do ar, a sessão local é encerrada
    _reset_session_state()
    st.session_state["_cookie_op"] = ("clear", None)
    st.rerun()


def flush_cookie_ops():
    """Aplica no navegador a gravação/remoção de cookie pendente (após login/logout)."""
    op = st.session_state.pop("_cookie_op", None)
    if not op:
        return
    action, token = op
    if action == "set":
        max_age = config.SESSION_TTL_DAYS * 86400
        value = json.dumps(f"{COOKIE_NAME}={token}; Path=/; Max-Age={max_age}; SameSite=Strict")
    else:
        value = json.dumps(f"{COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Strict")
    components.html(
        f"""<script>
        (function () {{
            var w = window.parent;
            var secure = w.location.protocol === 'https:' ? '; Secure' : '';
            w.document.cookie = {value} + secure;
        }})();
        </script>""",
        height=0,
    )


def require_login(on_login_page=None) -> dict:
    """Devolve o usuário logado; sem login válido, desenha a tela de entrada e para.

    on_login_page: callback opcional desenhado junto da tela de entrada (sidebar).
    """
    auth = st.session_state.get("auth")
    token = auth["token"] if auth else _cookie_token()
    if token and token != st.session_state.get("_dead_token"):
        try:
            with AppStore() as store:
                user = store.user_for_token(token)
        except Exception as e:
            st.error(t("auth.err.storage", e=e))
            st.stop()
        if user:
            if auth is None:  # sessão retomada pelo cookie (recarregou a página)
                st.session_state["auth"] = {"user": user, "token": token}
            else:
                auth["user"] = user
            return user
        # Sessão expirada/revogada: volta ao login e apaga o cookie.
        if auth is not None:
            _reset_session_state()
        st.session_state["_dead_token"] = token
        st.session_state["_cookie_op"] = ("clear", None)

    if on_login_page:
        on_login_page()
    _render_login_page()
    flush_cookie_ops()
    st.stop()


# ── Tela de entrada ───────────────────────────────────────────────────────────

def _render_login_page():
    _, col, _ = st.columns([1, 1.3, 1])
    with col:
        st.markdown(
            f'<div class="cp-title" style="margin:3.5rem 0 .3rem">{t("auth.title")}</div>'
            f'<div class="cp-brand-sub" style="margin-bottom:1.2rem">{t("auth.subtitle")}</div>',
            unsafe_allow_html=True,
        )
        try:
            with AppStore() as store:
                n_users = store.user_count()
        except Exception as e:
            st.error(t("auth.err.storage", e=e))
            return

        tab_login, tab_signup = st.tabs([t("auth.tab.login"), t("auth.tab.signup")])
        with tab_login:
            _login_form()
        with tab_signup:
            _signup_form(n_users)


def _login_form():
    with st.form("login_form"):
        username = st.text_input(t("auth.username"), key="login_username")
        password = st.text_input(t("auth.password"), type="password", key="login_password")
        submitted = st.form_submit_button(t("auth.btn.login"), type="primary",
                                          key="login_submit", use_container_width=True)
    if not submitted:
        return
    try:
        with AppStore() as store:
            user = store.authenticate(username, password)
            token = store.create_session(user["id"])
    except AuthError as e:
        st.error(t(f"auth.err.{e.code}"))
        return
    _start_session(user, token)


def _signup_form(n_users: int):
    if not config.ALLOW_SIGNUP:
        st.info(t("auth.signup.closed"))
        return
    if n_users == 0:
        st.caption(t("auth.signup.first_admin"))

    with st.form("signup_form"):
        username = st.text_input(t("auth.username"), key="signup_username")
        password = st.text_input(t("auth.password"), type="password", key="signup_password")
        confirm = st.text_input(t("auth.password_confirm"), type="password", key="signup_confirm")
        code = None
        if config.SIGNUP_CODE:
            code = st.text_input(t("auth.signup_code"), type="password", key="signup_code",
                                 help=t("auth.signup_code.help"))
        st.caption(t("auth.signup.hint"))
        submitted = st.form_submit_button(t("auth.btn.signup"), type="primary",
                                          key="signup_submit", use_container_width=True)
    if not submitted:
        return
    if config.SIGNUP_CODE and not hmac.compare_digest((code or "").encode(),
                                                      config.SIGNUP_CODE.encode()):
        st.error(t("auth.err.signup_code"))
        return
    if password != confirm:
        st.error(t("auth.err.password_mismatch"))
        return
    try:
        with AppStore() as store:
            user = store.create_user(username, password)
            token = store.create_session(user["id"])
    except AuthError as e:
        st.error(t(f"auth.err.{e.code}"))
        return
    _start_session(user, token)


# ── Barra lateral (usuário logado) ────────────────────────────────────────────

def render_account_sidebar(user: dict, busy: bool = False):
    st.caption(t("auth.signed_in_as", name=user["username"]))
    c1, c2 = st.columns(2)
    with c1:
        with st.popover(t("auth.account"), use_container_width=True, disabled=busy):
            _change_password_form()
    with c2:
        if st.button(t("auth.logout"), key="logout_btn", use_container_width=True, disabled=busy):
            logout()


def _change_password_form():
    st.markdown(f"**{t('auth.change_password')}**")
    with st.form("change_password_form", clear_on_submit=True):
        current = st.text_input(t("auth.password_current"), type="password", key="pw_current")
        new = st.text_input(t("auth.password_new"), type="password", key="pw_new")
        confirm = st.text_input(t("auth.password_confirm"), type="password", key="pw_confirm")
        submitted = st.form_submit_button(t("auth.btn.change_password"), key="pw_submit")
    if not submitted:
        return
    if new != confirm:
        st.error(t("auth.err.password_mismatch"))
        return
    auth = st.session_state["auth"]
    try:
        with AppStore() as store:
            store.change_password(auth["user"]["id"], current, new, keep_token=auth["token"])
    except AuthError as e:
        st.error(t(f"auth.err.{e.code}"))
        return
    st.success(t("auth.password_changed"))
