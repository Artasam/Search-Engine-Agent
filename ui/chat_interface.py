"""
ui/chat_interface.py
--------------------
Renders message history and handles the chat input widget.
Separated from sidebar and metrics to keep each file focused.
"""

import streamlit as st
from typing import List, Dict


def render_messages(messages: List[Dict]) -> None:
    """Render all messages in the chat history."""
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        ts = msg.get("timestamp", "")

        with st.chat_message(role):
            st.markdown(content)

            # Show tool badges if recorded on an assistant message
            tools = msg.get("tools_used", [])
            elapsed = msg.get("elapsed_sec")
            if tools or elapsed:
                parts = []
                for t in tools:
                    parts.append(f'<span class="tool-badge">{t}</span>')
                time_str = f"&nbsp;⏱ {elapsed}s" if elapsed else ""
                st.markdown(
                    " ".join(parts) + time_str +
                    (f'&nbsp;&nbsp;<span class="msg-ts">{ts}</span>' if ts else ""),
                    unsafe_allow_html=True,
                )


def get_user_input() -> str | None:
    """Render the chat input box and return user text, or None."""
    return st.chat_input("Ask me anything…")
