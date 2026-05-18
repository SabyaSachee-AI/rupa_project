"""Login page (and inline register form)."""

from __future__ import annotations

import streamlit as st

from app.auth import AuthService
from app.exceptions import AuthError, UserAlreadyExistsError, ValidationError
from app.logging_setup import get_logger
from app.ui.styles import inject_login_styles

logger = get_logger(__name__)


def render_login() -> None:
    """Render the login / register experience. Sets ``st.session_state.user`` on success."""

    inject_login_styles()

    _col_hero, col_form = st.columns([1.1, 1], gap="large")

    with _col_hero:
        st.markdown(
            """
            <div class="login-hero">
                <h1>Rupa AI</h1>
                <p>
                    Your bilingual assistant for natural conversations in Bangla and English —
                    with memory, voice, and a personality you can shape.
                </p>
                <div class="feature-pills">
                    <span class="feature-pill">🌐 Bangla & English</span>
                    <span class="feature-pill">🎙️ Voice chat</span>
                    <span class="feature-pill">📚 Knowledge base</span>
                    <span class="feature-pill">🔒 Secure accounts</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_form:
        st.markdown(
            """
            <div class="login-card-shell">
                <h2>Welcome</h2>
                <p class="subtitle">Sign in or create an account to continue</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        login_tab, register_tab = st.tabs(["Sign in", "Create account"])
        auth = AuthService()

        with login_tab:
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input(
                    "Username",
                    placeholder="e.g. admin",
                    autocomplete="username",
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="••••••••",
                    autocomplete="current-password",
                )
                submitted = st.form_submit_button(
                    "Sign in",
                    type="primary",
                    use_container_width=True,
                )

            if submitted:
                if not username.strip() or not password:
                    st.warning("Enter both username and password.")
                else:
                    try:
                        user = auth.login(username, password)
                    except AuthError as exc:
                        st.error(exc.user_message)
                    else:
                        st.session_state["user"] = user
                        st.session_state["page"] = "chat"
                        st.toast(f"Welcome back, {user.username}!")
                        st.rerun()

        with register_tab:
            with st.form("register_form", clear_on_submit=False):
                r_username = st.text_input(
                    "Username",
                    placeholder="choose a username",
                    key="reg_user",
                )
                r_email = st.text_input(
                    "Email",
                    placeholder="you@example.com",
                    key="reg_email",
                )
                r_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="min. 8 characters",
                    help="Use at least 8 characters with letters and numbers.",
                    key="reg_pw",
                )
                r_password2 = st.text_input(
                    "Confirm password",
                    type="password",
                    placeholder="repeat password",
                    key="reg_pw2",
                )
                r_submitted = st.form_submit_button(
                    "Create account",
                    type="primary",
                    use_container_width=True,
                )

            if r_submitted:
                if r_password != r_password2:
                    st.error("Passwords do not match.")
                elif len(r_password) < 8:
                    st.error("Password must be at least 8 characters.")
                elif "@" not in r_email:
                    st.error("Enter a valid email address.")
                else:
                    try:
                        user = auth.register(r_username, r_email, r_password)
                    except UserAlreadyExistsError as exc:
                        st.error(exc.user_message)
                    except (AuthError, ValidationError) as exc:
                        st.error(exc.user_message)
                    else:
                        st.session_state["user"] = user
                        st.success("Account created. Redirecting...")
                        st.rerun()
