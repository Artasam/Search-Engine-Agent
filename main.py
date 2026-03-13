"""
main.py
-------
Entry point for Search-Engine-Agent.
Run with:  streamlit run main.py

Architecture
------------
  main.py          ← orchestration only
  config/          ← all constants & model catalogue
  tools/           ← one file per tool + central registry
  agents/          ← factory + high-level runner
  utils/           ← logger, history, token counter, export
  ui/              ← theme, sidebar, chat, metrics (all rendering)

API Key resolution order (first non-empty value wins)
------------------------------------------------------
  1. Sidebar text input  (user-provided at runtime)
  2. st.secrets["GROQ_API_KEY"]  (Streamlit Cloud → secrets.toml)
  3. OS environment variable GROQ_API_KEY  (local .env via dotenv)
"""

import os
from dotenv import load_dotenv
import streamlit as st

# ── Bootstrap ────────────────────────────────────────────────────────────────
load_dotenv()

from config.settings import APP_TITLE, APP_SUBTITLE, APP_ICON, APP_LAYOUT
from ui import (
    apply_theme, render_sidebar,
    render_messages, get_user_input,
    render_metrics_bar,
    init_youtube_state, render_youtube_panel, set_video,
)
from utils import init_history, add_message, record_run_meta, get_messages
from tools import get_tools
from agents import run_agent
from youtube import search_youtube


def resolve_api_key(sidebar_key: str) -> str:
    """
    Resolve the Groq API key using a three-tier fallback chain:

      1. Sidebar input  — typed by the user at runtime
      2. st.secrets     — set via Streamlit Cloud > App settings > Secrets
                          (key name: GROQ_API_KEY)
      3. Environment    — local .env file loaded by python-dotenv,
                          or any shell export GROQ_API_KEY=...

    Returns the first non-empty string found, or "" if none exist.
    """
    # Tier 1: sidebar
    if sidebar_key:
        return sidebar_key

    # Tier 2: Streamlit secrets (safe — returns None if key absent)
    try:
        secret = st.secrets.get("GROQ_API_KEY", "")
        if secret:
            return secret
    except Exception:
        pass  # st.secrets unavailable in some local setups — that's fine

    # Tier 3: environment / .env
    return os.getenv("GROQ_API_KEY", "")


# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout=APP_LAYOUT,
    initial_sidebar_state="expanded",
)

apply_theme()
init_history()
init_youtube_state()

# ── Sidebar ───────────────────────────────────────────────────────────────────
settings = render_sidebar()

# ── Resolve API key across all sources ───────────────────────────────────────
api_key = resolve_api_key(settings["api_key"])

# If a key was resolved from secrets/env, show a subtle indicator in sidebar
# so the user knows authentication is already configured.
if api_key and not settings["api_key"]:
    st.sidebar.success("🔑 API key loaded from secrets/env", icon="✅")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="brand-header">'
    '<span class="status-dot"></span>'
    '&nbsp;&nbsp;<span class="accent">SEARCH · ENGINE · AGENT</span>'
    '&nbsp;&nbsp;·&nbsp;&nbsp;v2.0'
    '</div>',
    unsafe_allow_html=True,
)
st.title("AI Research Assistant")
st.caption(APP_SUBTITLE)

# ── Metrics bar ───────────────────────────────────────────────────────────────
render_metrics_bar()
st.divider()

# ── Chat history ──────────────────────────────────────────────────────────────
render_messages(get_messages())

# ── User input ────────────────────────────────────────────────────────────────
prompt = get_user_input()

if prompt:
    # Validate prerequisites
    if not api_key:
        st.error(
            "🔑 No API key found. "
            "Enter it in the sidebar, add `GROQ_API_KEY` to your "
            "`secrets.toml` (Streamlit Cloud), or set it as an environment variable."
        )
        st.stop()

    selected_tool_names = settings["selected_tools"]
    if not selected_tool_names:
        st.error("🛠 Please enable at least one tool in the sidebar.")
        st.stop()

    # Record user message FIRST, then re-render full history
    add_message("user", prompt)

    # Re-render all messages (includes the new user message)
    # Clear previous render by letting Streamlit handle it on rerun
    # We show the new messages directly here instead
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build tools
    tools = get_tools(selected_tool_names)

    # Run agent
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = run_agent(
                query=prompt,
                history=get_messages()[:-1],
                api_key=api_key,
                model_id=settings["model_id"],
                tools=tools,
                temperature=settings["temperature"],
                callbacks=[],
            )

        response   = result["response"]
        elapsed    = result["elapsed_sec"]
        tools_used = result["tools_used"]

        st.markdown(response)

        if tools_used:
            badges = "".join(f'<span class="tool-badge">{t}</span>' for t in tools_used)
            st.markdown(f"{badges} &nbsp;⏱ {elapsed}s", unsafe_allow_html=True)

    # Persist assistant reply
    add_message("assistant", response, tools_used=tools_used, elapsed_sec=elapsed)
    record_run_meta(elapsed, tools_used)

    # ── YouTube: auto-fetch relevant video ───────────────────────────────────
    if settings.get("youtube_enabled", True):
        with st.spinner("🎬 Finding relevant YouTube video…"):
            video = search_youtube(prompt)
        if video:
            set_video(video)
            st.rerun()

# ── YouTube Learning Panel ────────────────────────────────────────────────────
render_youtube_panel(api_key=api_key, model_id=settings["model_id"])