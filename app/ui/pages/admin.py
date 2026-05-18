"""Admin page: user management."""

from __future__ import annotations

import streamlit as st

from app.auth import AuthenticatedUser, AuthService, hash_password
from app.db import get_session
from app.db.models import User, UserRole
from app.db.repositories import UserRepository
from app.exceptions import PermissionDeniedError, UserAlreadyExistsError
from app.logging_setup import get_logger
from app.ui.components.nav import render_app_nav
from app.ui.styles import inject_admin_styles, render_sidebar_brand, render_sidebar_reopen_control

logger = get_logger(__name__)


def render_admin(current_user: AuthenticatedUser) -> None:
    """Render the admin console."""

    AuthService().require_admin(current_user)
    inject_admin_styles()
    render_sidebar_reopen_control()

    with st.sidebar:
        render_app_nav(current_user)
        st.divider()
        render_sidebar_brand(current_user.username, is_admin=True)
        st.caption("Manage users and access from this panel.")
        if st.button("Sign out", use_container_width=True, type="secondary", key="admin_logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    with get_session() as session:
        repo = UserRepository(session)
        users = list(repo.list_all())
        total = len(users)
        active = sum(1 for u in users if u.is_active)
        admins = sum(1 for u in users if u.role is UserRole.ADMIN)

    st.markdown(
        """
        <div class="admin-header">
            <h1 style="margin:0;font-size:1.75rem;">Admin console</h1>
            <p style="margin:0.35rem 0 0;color:#64748B;">
                Manage team accounts and access
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total users", total)
    with m2:
        st.metric("Active", active)
    with m3:
        st.metric("Admins", admins)

    st.divider()
    _render_user_table(users)
    st.divider()
    _render_create_user_form()


def _render_user_table(users: list[User]) -> None:
    st.subheader("All users")

    if not users:
        st.info("No users registered yet.")
        return

    rows = [
        {
            "Username": u.username,
            "Email": u.email,
            "Role": u.role.value,
            "Active": "Yes" if u.is_active else "No",
            "Created": u.created_at.strftime("%Y-%m-%d %H:%M"),
            "Last login": (u.last_login_at.strftime("%Y-%m-%d %H:%M") if u.last_login_at else "—"),
        }
        for u in users
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    with st.expander("Activate / deactivate user"):
        by_name = {u.username: u.id for u in users}
        selected_name = st.selectbox("User", list(by_name.keys()), key="admin_user_pick")
        selected_id = by_name[selected_name]
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Deactivate", use_container_width=True, type="secondary"):
                _set_active(selected_id, is_active=False)
                st.toast(f"Deactivated {selected_name}")
                st.rerun()
        with c2:
            if st.button("Activate", use_container_width=True, type="primary"):
                _set_active(selected_id, is_active=True)
                st.toast(f"Activated {selected_name}")
                st.rerun()


def _render_create_user_form() -> None:
    st.subheader("Create user")
    with st.form("admin_create_user", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            username = st.text_input("Username")
            email = st.text_input("Email")
        with c2:
            password = st.text_input("Password", type="password", help="Minimum 8 characters")
            role = st.selectbox("Role", [r.value for r in UserRole])
        submitted = st.form_submit_button("Create user", type="primary", use_container_width=True)

    if not submitted:
        return

    if len(password) < 8:
        st.error("Password must be at least 8 characters.")
        return

    try:
        with get_session() as session:
            UserRepository(session).create(
                username=username.strip().lower(),
                email=email.strip().lower(),
                hashed_password=hash_password(password),
                role=UserRole(role),
            )
    except UserAlreadyExistsError as exc:
        st.error(exc.user_message)
    except PermissionDeniedError as exc:
        st.error(exc.user_message)
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.toast(f"User {username!r} created")
        st.success(f"Created user {username!r}.")
        logger.info("admin.user_created", username=username, role=role)
        st.rerun()


def _set_active(user_id: str, *, is_active: bool) -> None:
    with get_session() as session:
        UserRepository(session).set_active(user_id, is_active=is_active)
    logger.info("admin.user_active_toggled", user_id=user_id, is_active=is_active)
