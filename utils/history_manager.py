"""
utils/history_manager.py
------------------------
Manages chat history stored in st.session_state.
Provides add / clear / export helpers.
"""

import json
import datetime
from typing import List, Dict
import streamlit as st
from config.settings import MAX_HISTORY_MESSAGES, DEFAULT_SYSTEM_MSG


_KEY = "chat_messages"
_META_KEY = "chat_metadata"


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_history() -> None:
    """Initialise session state keys if they don't exist yet."""
    if _KEY not in st.session_state:
        st.session_state[_KEY] = [
            {"role": "assistant", "content": DEFAULT_SYSTEM_MSG, "timestamp": _now()}
        ]
    if _META_KEY not in st.session_state:
        st.session_state[_META_KEY] = {
            "total_queries":   0,
            "total_elapsed":   0.0,
            "tools_frequency": {},
        }


def get_messages() -> List[Dict]:
    return st.session_state.get(_KEY, [])


def add_message(role: str, content: str, **extra) -> None:
    """Append a message; prune oldest if over the limit."""
    msgs = get_messages()
    msgs.append({"role": role, "content": content, "timestamp": _now(), **extra})
    # Keep only the system seed + last N user/assistant pairs
    if len(msgs) > MAX_HISTORY_MESSAGES:
        msgs = msgs[-MAX_HISTORY_MESSAGES:]
    st.session_state[_KEY] = msgs


def record_run_meta(elapsed: float, tools_used: List[str]) -> None:
    """Update aggregate run statistics."""
    meta = st.session_state[_META_KEY]
    meta["total_queries"] += 1
    meta["total_elapsed"] += elapsed
    for t in tools_used:
        meta["tools_frequency"][t] = meta["tools_frequency"].get(t, 0) + 1


def get_meta() -> Dict:
    return st.session_state.get(_META_KEY, {})


def clear_history() -> None:
    """Reset conversation to initial state."""
    if _KEY in st.session_state:
        del st.session_state[_KEY]
    if _META_KEY in st.session_state:
        del st.session_state[_META_KEY]
    init_history()


def export_as_json() -> str:
    """Serialise history to a pretty-printed JSON string."""
    return json.dumps(get_messages(), indent=2, ensure_ascii=False)


def export_as_markdown() -> str:
    """Serialise history to a Markdown string."""
    lines = ["# Chat Export\n"]
    for m in get_messages():
        role = "**User**" if m["role"] == "user" else "**Assistant**"
        ts   = m.get("timestamp", "")
        lines.append(f"### {role}  _{ts}_\n\n{m['content']}\n\n---\n")
    return "\n".join(lines)
