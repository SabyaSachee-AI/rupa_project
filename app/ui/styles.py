"""Centralised CSS and layout helpers for the Streamlit UI.

Design tokens (mood-aware accents, neutrals, typography) live here so pages
stay focused on structure and behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import streamlit as st
import streamlit.components.v1 as components


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ThemePalette:
    """Colour and gradient tokens for one mood."""

    accent: str
    accent_soft: str
    accent_muted: str
    gradient_bg: str
    gradient_sidebar: str
    shadow: str
    chip_bg: str


_HAPPY: Final = ThemePalette(
    accent="#E11D8F",
    accent_soft="#F472B6",
    accent_muted="rgba(225, 29, 143, 0.12)",
    gradient_bg="linear-gradient(160deg, #FFF5FA 0%, #F8FAFC 45%, #FFFFFF 100%)",
    gradient_sidebar="linear-gradient(180deg, #FFFFFF 0%, #FFF8FC 100%)",
    shadow="0 4px 24px rgba(225, 29, 143, 0.08)",
    chip_bg="rgba(225, 29, 143, 0.08)",
)

_SAD: Final = ThemePalette(
    accent="#3B82F6",
    accent_soft="#93C5FD",
    accent_muted="rgba(59, 130, 246, 0.12)",
    gradient_bg="linear-gradient(160deg, #F0F4FF 0%, #F8FAFC 45%, #FFFFFF 100%)",
    gradient_sidebar="linear-gradient(180deg, #FFFFFF 0%, #F5F8FF 100%)",
    shadow="0 4px 24px rgba(59, 130, 246, 0.08)",
    chip_bg="rgba(59, 130, 246, 0.08)",
)

_FONT_IMPORT: Final = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700"
    "&family=Noto+Sans+Bengali:wght@400;500;600&display=swap');"
)

_BASE_CSS: Final = """
{_font}
:root {{
    --rupa-accent: {accent};
    --rupa-accent-soft: {accent_soft};
    --rupa-accent-muted: {accent_muted};
    --rupa-text: #0F172A;
    --rupa-text-muted: #64748B;
    --rupa-border: #E2E8F0;
    --rupa-surface: #FFFFFF;
    --rupa-radius: 14px;
    --rupa-radius-lg: 20px;
    --rupa-shadow: {shadow};
    --rupa-font: 'DM Sans', 'Noto Sans Bengali', system-ui, sans-serif;
}}

/* App shell */
.stApp {{
    background: {gradient_bg};
    font-family: var(--rupa-font);
    color: var(--rupa-text);
}}

/* Hide hamburger menu & footer only — keep header so sidebar collapse/expand works */
#MainMenu, footer {{
    visibility: hidden !important;
    height: 0 !important;
    min-height: 0 !important;
    overflow: hidden !important;
}}

/* Minimal header: must stay visible for the sidebar toggle (» / «) */
header[data-testid="stHeader"] {{
    visibility: visible !important;
    height: auto !important;
    min-height: 3.25rem !important;
    background: rgba(255, 255, 255, 0.9) !important;
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--rupa-border);
}}

/* Always show Streamlit's sidebar open/close control */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
button[data-testid="stBaseButton-headerNoPadding"] {{
    visibility: visible !important;
    opacity: 1 !important;
    display: flex !important;
    z-index: 9999 !important;
}}

/* When collapsed, keep the edge « expand tab clickable */
[data-testid="stSidebarCollapsedControl"] {{
    position: fixed !important;
    left: 0 !important;
    top: 0.75rem !important;
}}

.main .block-container {{
    padding-top: 1.25rem;
    padding-bottom: 7rem;
    max-width: 920px;
}}

/* Typography */
h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {{
    font-family: var(--rupa-font);
}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background: {gradient_sidebar};
    border-right: 1px solid var(--rupa-border);
}}

[data-testid="stSidebar"] > div:first-child {{
    padding-top: 1.5rem;
}}

[data-testid="stSidebar"] .stMarkdown h3,
[data-testid="stSidebar"] .stMarkdown h4 {{
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--rupa-text-muted);
    margin-bottom: 0.5rem;
}}

/* Primary buttons */
.stButton > button[kind="primary"],
.stButton > button {{
    border-radius: 10px;
    font-weight: 600;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}}

.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, var(--rupa-accent) 0%, var(--rupa-accent-soft) 100%);
    border: none;
    color: white;
}}

.stButton > button[kind="primary"]:hover {{
    transform: translateY(-1px);
    box-shadow: var(--rupa-shadow);
}}

/* Form inputs */
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div {{
    border-radius: 10px !important;
    border-color: var(--rupa-border) !important;
}}

.stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: var(--rupa-accent) !important;
    box-shadow: 0 0 0 3px var(--rupa-accent-muted) !important;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    gap: 8px;
    background: transparent;
}}

.stTabs [data-baseweb="tab"] {{
    border-radius: 10px;
    padding: 0.5rem 1.25rem;
    font-weight: 600;
}}

.stTabs [aria-selected="true"] {{
    background: var(--rupa-accent-muted) !important;
    color: var(--rupa-accent) !important;
}}

/* Expanders */
.streamlit-expanderHeader {{
    border-radius: var(--rupa-radius);
    font-weight: 600;
}}

/* Dividers */
hr {{
    margin: 1rem 0;
    border-color: var(--rupa-border);
}}

/* Alerts */
[data-testid="stAlert"] {{
    border-radius: var(--rupa-radius);
}}
"""


_CHAT_CSS: Final = """
/* Compose row: hold-to-talk mic + chat input */
[data-testid="stHorizontalBlock"]:has([data-testid="stChatInput"]) {{
    position: fixed;
    bottom: 1.25rem;
    left: 50% !important;
    transform: translateX(-50%) !important;
    width: min(720px, calc(100% - 2rem)) !important;
    z-index: 999;
    align-items: flex-end !important;
    gap: 0.35rem !important;
}}

[data-testid="stHorizontalBlock"]:has([data-testid="stChatInput"])
    [data-testid="column"]:first-child {{
    flex: 0 0 4.25rem !important;
    min-width: 4.25rem !important;
    max-width: 4.25rem !important;
}}

[data-testid="stHorizontalBlock"]:has([data-testid="stChatInput"])
    [data-testid="column"]:last-child {{
    flex: 1 1 auto !important;
}}

[data-testid="stHorizontalBlock"]:has([data-testid="stChatInput"])
    [data-testid="stCustomComponentV1"] iframe {{
    border: none !important;
    min-height: 72px;
}}

[data-testid="stHorizontalBlock"]:has([data-testid="stChatInput"])
    [data-testid="stChatInput"],
[data-testid="stHorizontalBlock"]:has([data-testid="stChatInput"])
    motion-div[data-testid="stChatInput"] {{
    position: static !important;
    width: 100% !important;
    transform: none !important;
}}

[data-testid="stHorizontalBlock"]:has([data-testid="stChatInput"])
    [data-testid="stChatInput"] > div,
[data-testid="stHorizontalBlock"]:has([data-testid="stChatInput"])
    motion-div[data-testid="stChatInput"] > div {{
    background: var(--rupa-surface);
    border-radius: var(--rupa-radius-lg);
    box-shadow: 0 8px 32px rgba(15, 23, 42, 0.12);
    border: 1px solid var(--rupa-border);
    padding: 0.25rem;
}}

[data-testid="stHorizontalBlock"]:has([data-testid="stChatInput"])
    [data-testid="stChatInput"]:focus-within > div,
[data-testid="stHorizontalBlock"]:has([data-testid="stChatInput"])
    motion-div[data-testid="stChatInput"]:focus-within > div {{
    border-color: var(--rupa-accent);
    box-shadow: 0 8px 32px rgba(15, 23, 42, 0.12), 0 0 0 3px var(--rupa-accent-muted);
}}

/* Chat messages */
[data-testid="stChatMessage"] {{
    background: var(--rupa-surface);
    border-radius: var(--rupa-radius);
    padding: 0.85rem 1rem;
    margin-bottom: 0.75rem;
    border: 1px solid var(--rupa-border);
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {{
    border-left: 3px solid var(--rupa-accent);
    background: linear-gradient(90deg, var(--rupa-accent-muted) 0%, var(--rupa-surface) 12%);
}}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {{
    border-left: 3px solid #94A3B8;
}}

/* Radio pills in sidebar */
[data-testid="stSidebar"] .stRadio > div {{
    flex-direction: row;
    gap: 0.5rem;
}}

[data-testid="stSidebar"] .stRadio label {{
    background: var(--rupa-surface);
    border: 1px solid var(--rupa-border);
    border-radius: 999px;
    padding: 0.35rem 0.85rem;
    font-weight: 500;
}}

[data-testid="stSidebar"] .stRadio label[data-checked="true"] {{
    background: var(--rupa-accent-muted);
    border-color: var(--rupa-accent);
    color: var(--rupa-accent);
}}
"""


_LOGIN_CSS: Final = """
.stApp {{
    background: linear-gradient(135deg, #FFF5FA 0%, #EEF2FF 50%, #F8FAFC 100%);
}}

.main .block-container {{
    max-width: 100%;
    padding: 0;
}}

.login-wrap {{
    min-height: 88vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem 1rem;
}}

.login-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 3rem;
    max-width: 960px;
    width: 100%;
    align-items: center;
}}

@media (max-width: 768px) {{
    .login-grid {{
        grid-template-columns: 1fr;
    }}
    .login-hero {{
        text-align: center;
    }}
}}

.login-hero h1 {{
    font-size: 2.75rem;
    font-weight: 700;
    line-height: 1.15;
    margin: 0 0 0.75rem 0;
    background: linear-gradient(135deg, #E11D8F 0%, #6366F1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

.login-hero p {{
    color: #64748B;
    font-size: 1.05rem;
    line-height: 1.6;
    margin: 0 0 1.5rem 0;
}}

.feature-pills {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}}

.feature-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.4rem 0.85rem;
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 500;
    color: #475569;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}}

.login-card-shell {{
    background: white;
    border-radius: 20px;
    padding: 2rem 2rem 1.5rem;
    box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08);
    border: 1px solid #E2E8F0;
}}

.login-card-shell h2 {{
    margin: 0 0 0.25rem 0;
    font-size: 1.5rem;
    font-weight: 700;
}}

.login-card-shell .subtitle {{
    color: #64748B;
    font-size: 0.9rem;
    margin-bottom: 1.25rem;
}}
"""


_ADMIN_CSS: Final = """
.admin-header {{
    background: white;
    border-radius: var(--rupa-radius-lg);
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.5rem;
    border: 1px solid var(--rupa-border);
    box-shadow: var(--rupa-shadow);
}}

.admin-metric {{
    background: white;
    border-radius: var(--rupa-radius);
    padding: 1rem 1.25rem;
    border: 1px solid var(--rupa-border);
    text-align: center;
}}

.admin-metric .value {{
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--rupa-accent);
}}

.admin-metric .label {{
    font-size: 0.75rem;
    color: var(--rupa-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
"""


def palette_for_mood(mood: str) -> ThemePalette:
    return _SAD if mood == "Sad" else _HAPPY


def _inject_css(css: str, **kwargs: str) -> None:
    st.markdown(
        f"<style>{css.format(_font=_FONT_IMPORT, **kwargs)}</style>",
        unsafe_allow_html=True,
    )


def inject_base_styles(mood: str = "Happy") -> None:
    """Shared app chrome (fonts, sidebar, buttons). Call on every authenticated page."""

    p = palette_for_mood(mood)
    _inject_css(
        _BASE_CSS,
        accent=p.accent,
        accent_soft=p.accent_soft,
        accent_muted=p.accent_muted,
        gradient_bg=p.gradient_bg,
        gradient_sidebar=p.gradient_sidebar,
        shadow=p.shadow,
    )


def render_sidebar_reopen_control() -> None:
    """In-main fallback button if the native sidebar toggle is hard to find."""

    col_btn, col_hint = st.columns([1, 5])
    with col_btn:
        reopen = st.button(
            "☰ Menu",
            key="rupa_sidebar_reopen",
            help="Reopen the settings sidebar",
            type="secondary",
        )
    with col_hint:
        st.caption("Settings · chats · voice · mood")

    if reopen:
        components.html(
            """
            <script>
            (function () {
                const doc = window.parent.document;
                const toggle = doc.querySelector(
                    '[data-testid="stSidebarCollapsedControl"] button, '
                    + '[data-testid="collapsedControl"] button'
                );
                if (toggle) {
                    toggle.click();
                    return;
                }
                const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (sidebar) {
                    sidebar.style.transform = 'translateX(0px)';
                    sidebar.style.visibility = 'visible';
                    sidebar.setAttribute('aria-expanded', 'true');
                }
            })();
            </script>
            """,
            height=0,
        )


def inject_chat_styles(mood: str) -> None:
    """Chat-specific layout (messages, input dock)."""

    inject_base_styles(mood)
    _inject_css(_CHAT_CSS)


def inject_login_styles() -> None:
    """Login / register page."""

    _inject_css(_LOGIN_CSS)


def inject_admin_styles() -> None:
    """Admin console."""

    inject_base_styles("Happy")
    _inject_css(
        _ADMIN_CSS,
        accent=_HAPPY.accent,
        accent_soft=_HAPPY.accent_soft,
        accent_muted=_HAPPY.accent_muted,
        shadow=_HAPPY.shadow,
    )


def render_chat_header(
    *,
    title: str,
    mood: str,
    language: str,
    username: str,
) -> None:
    """Top-of-page header for the chat view."""

    p = palette_for_mood(mood)
    mood_emoji = "✨" if mood == "Happy" else "🌧️"
    lang_label = "বাংলা" if language == "Bangla" else "English"

    st.markdown(
        f"""
        <div class="chat-header" style="
            background: white;
            border-radius: 16px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.25rem;
            border: 1px solid #E2E8F0;
            box-shadow: {p.shadow};
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 0.75rem;
        ">
            <div>
                <div style="font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em;
                    text-transform: uppercase; color: #64748B;">Conversation</div>
                <div style="font-size: 1.25rem; font-weight: 700; color: #0F172A;
                    margin-top: 0.15rem;">{_escape_html(title[:80])}</div>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center;">
                <span style="background: {p.chip_bg}; color: {p.accent}; padding: 0.35rem 0.75rem;
                    border-radius: 999px; font-size: 0.8rem; font-weight: 600;">
                    {mood_emoji} {mood}
                </span>
                <span style="background: #F1F5F9; color: #475569; padding: 0.35rem 0.75rem;
                    border-radius: 999px; font-size: 0.8rem; font-weight: 600;">
                    {lang_label}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_chat_welcome(*, language: str) -> None:
    """Welcome card when a conversation has no messages yet."""

    if language == "Bangla":
        headline = "রূপার সাথে কথা বলুন"
        hint = "নিচে লিখুন, মাইক ধরে রেখে কথা বলুন, অথবা একটি পরামর্শ বেছে নিন।"
    else:
        headline = "Say hello to Rupa"
        hint = "Type below, hold the mic to talk, or pick a suggestion to get started."

    st.markdown(
        f"""
        <div style="
            text-align: center;
            padding: 3rem 1.5rem;
            margin: 2rem 0;
            background: white;
            border-radius: 20px;
            border: 1px dashed #E2E8F0;
        ">
            <div style="font-size: 3rem; margin-bottom: 0.75rem;">💬</div>
            <div style="font-size: 1.35rem; font-weight: 700; color: #0F172A; margin-bottom: 0.5rem;">
                {_escape_html(headline)}
            </div>
            <div style="color: #64748B; font-size: 0.95rem; max-width: 400px; margin: 0 auto;">
                {_escape_html(hint)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_chat_state(*, language: str) -> None:
    """Alias for ``render_empty_chat_welcome``."""

    render_empty_chat_welcome(language=language)


def render_sidebar_brand(username: str, *, is_admin: bool) -> None:
    """Sidebar header with user avatar placeholder."""

    role_badge = (
        '<span style="background:#EEF2FF;color:#4F46E5;padding:2px 8px;'
        'border-radius:6px;font-size:0.65rem;font-weight:600;">ADMIN</span>'
        if is_admin
        else ""
    )
    initial = (username[:1] or "?").upper()

    st.markdown(
        f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem;
            background: white;
            border-radius: 14px;
            border: 1px solid #E2E8F0;
            margin-bottom: 1rem;
        ">
            <div style="
                width: 42px; height: 42px; border-radius: 12px;
                background: linear-gradient(135deg, #E11D8F, #6366F1);
                color: white; display: flex; align-items: center; justify-content: center;
                font-weight: 700; font-size: 1.1rem;
            ">{initial}</div>
            <div>
                <div style="font-weight: 700; font-size: 0.95rem; color: #0F172A;">
                    {_escape_html(username)}
                </div>
                <div style="margin-top: 2px;">{role_badge}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
