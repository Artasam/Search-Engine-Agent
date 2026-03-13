"""
ui/sidebar.py
-------------
Renders the sidebar: API key, model picker, tool selector,
run parameters, session stats, and export buttons.
Returns a settings dict consumed by main.py.
"""

from typing import Dict, Any, List
import streamlit as st
from config.settings import GROQ_MODELS, DEFAULT_MODEL_ID
from tools import get_all_tool_names
from utils import (
    get_meta, clear_history,
    export_as_json, export_as_markdown,
    get_messages, estimate_history_tokens,
)


def render_sidebar() -> Dict[str, Any]:
    """
    Draw the full sidebar and return a settings dict:
    {
        api_key, model_id, selected_tools,
        temperature, streaming, show_thoughts
    }
    """
    st.sidebar.markdown(
        '<div class="brand-header">'
        '<span class="status-dot"></span>'
        '&nbsp;&nbsp;<span class="accent">CONFIG</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── API Key ──────────────────────────────────────────────────────────────
    api_key = st.sidebar.text_input(
        "Groq API Key", type="password",
        placeholder="gsk_...",
        help="Get your free key at https://console.groq.com",
    )

    # ── Model selection ──────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🤖 Model**")
    model_labels = [m.label for m in GROQ_MODELS]
    model_ids    = [m.id    for m in GROQ_MODELS]
    default_idx  = model_ids.index(DEFAULT_MODEL_ID)
    chosen_label = st.sidebar.selectbox("Select Model", model_labels, index=default_idx, label_visibility="collapsed")
    chosen_model = GROQ_MODELS[model_labels.index(chosen_label)]

    # Show best-for tags
    if chosen_model.best_for:
        tags = "".join(f'<span class="tool-badge">{t}</span>' for t in chosen_model.best_for)
        st.sidebar.markdown(tags, unsafe_allow_html=True)
    st.sidebar.caption(f"Context window: **{chosen_model.context_k}k** tokens")

    # ── Tool selector ────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🛠 Active Tools**")
    all_tools = get_all_tool_names()
    selected_tools: List[str] = []
    for tool_name in all_tools:
        if st.sidebar.checkbox(tool_name, value=True, key=f"tool_{tool_name}"):
            selected_tools.append(tool_name)
    if not selected_tools:
        st.sidebar.warning("⚠️ Select at least one tool.")

    # ── YouTube mode ─────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("**▶ YouTube Mode**")
    youtube_enabled = st.sidebar.toggle(
        "Auto-fetch YouTube video",
        value=True,
        key="yt_enabled",
        help="When enabled, the agent will automatically find and embed a relevant YouTube video for each query.",
    )

    # ── Run parameters ───────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🎛 Parameters**")
    temperature = st.sidebar.slider(
        "Temperature", 0.0, 1.0, 0.0, 0.05,
        help="0 = deterministic, 1 = creative",
    )

    # ── Session stats ────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📊 Session Stats**")
    meta   = get_meta()
    msgs   = get_messages()
    tokens = estimate_history_tokens(msgs)
    c1, c2 = st.sidebar.columns(2)
    c1.metric("Queries",  meta.get("total_queries", 0))
    c2.metric("~Tokens",  tokens)
    avg = (
        round(meta["total_elapsed"] / meta["total_queries"], 1)
        if meta.get("total_queries") else 0
    )
    st.sidebar.caption(f"Avg response time: **{avg}s**")

    tf = meta.get("tools_frequency", {})
    if tf:
        st.sidebar.markdown("**Tool usage:**")
        for name, count in sorted(tf.items(), key=lambda x: -x[1]):
            st.sidebar.progress(min(count / max(tf.values()), 1.0), text=f"{name}: {count}×")

    # ── Export ───────────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("**💾 Export Chat**")
    col1, col2 = st.sidebar.columns(2)
    col1.download_button(
        "JSON", export_as_json(),
        file_name="chat_history.json",
        mime="application/json",
        use_container_width=True,
    )
    col2.download_button(
        "MD", export_as_markdown(),
        file_name="chat_history.md",
        mime="text/markdown",
        use_container_width=True,
    )

    # ── Clear ────────────────────────────────────────────────────────────────
    if st.sidebar.button("🗑 Clear History", use_container_width=True):
        clear_history()
        st.rerun()

    return {
        "api_key":         api_key,
        "model_id":        chosen_model.id,
        "selected_tools":  selected_tools,
        "temperature":     temperature,
        "youtube_enabled": youtube_enabled,
    }