"""
utils/token_counter.py
----------------------
Lightweight token estimator (no tiktoken dependency needed).
Uses the ~4 chars/token rule-of-thumb for English text.
"""

from typing import List, Dict


def estimate_tokens(text: str) -> int:
    """Estimate token count for a single string."""
    return max(1, len(text) // 4)


def estimate_history_tokens(messages: List[Dict]) -> int:
    """Sum estimated tokens across the full message history."""
    return sum(estimate_tokens(m.get("content", "")) for m in messages)
