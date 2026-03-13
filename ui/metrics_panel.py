"""
ui/metrics_panel.py
-------------------
Renders the horizontal metrics bar shown below the title.
"""

import streamlit as st
from utils import get_meta, get_messages, estimate_history_tokens


def render_metrics_bar() -> None:
    """Display a row of key metrics at the top of the main area."""
    meta   = get_meta()
    msgs   = get_messages()
    tokens = estimate_history_tokens(msgs)
    total  = meta.get("total_queries", 0)
    avg    = (
        round(meta["total_elapsed"] / total, 1)
        if total else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💬 Queries",        total)
    c2.metric("🔤 ~Tokens Used",   tokens)
    c3.metric("⏱ Avg Latency",    f"{avg}s")
    c4.metric("📝 Messages",       len(msgs))
