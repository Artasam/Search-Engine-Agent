"""
agents/search_agent.py
----------------------
Runs the LangGraph ReAct agent and returns a structured result dict.

LangGraph's compiled graph (from langgraph.prebuilt.create_react_agent):
  - Input  : {"messages": [HumanMessage(content=...)]}
  - Output : {"messages": [..., AIMessage(content=final_answer)]}
"""

import re
import time
from typing import List, Dict, Any, Optional

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from .agent_factory import build_agent
from utils.logger import get_logger

logger = get_logger(__name__)

# Regex to detect raw tool-call leakage in the final AI response
_TOOL_CALL_PATTERN = re.compile(
    r'<[a-z_]+>\{.*?\}</(?:function|[a-z_]+)>|'   # <web_search>{...}</function>
    r'\{"type"\s*:\s*"function".*?\}|'              # {"type": "function", ...}
    r'<function=["\w]+>.*?</function>',             # <function="name">...</function>
    re.DOTALL,
)


def _is_raw_tool_call(text: str) -> bool:
    """Return True if the text looks like a leaked raw tool invocation."""
    return bool(_TOOL_CALL_PATTERN.search(text))


def _extract_clean_response(messages: list) -> str:
    """
    Walk the message list in reverse and return the first AIMessage whose
    content is a real human-readable answer (not a raw tool call).
    Falls back to the last AIMessage content if nothing clean is found.
    """
    ai_messages = [m for m in messages if isinstance(m, AIMessage) and m.content]

    if not ai_messages:
        return "No response generated."

    # Prefer the last AI message that doesn't look like a raw tool call
    for msg in reversed(ai_messages):
        content = msg.content.strip()
        if content and not _is_raw_tool_call(content):
            return content

    # Last resort — return the final AIMessage even if it looks odd
    return ai_messages[-1].content.strip() or "No response generated."


def run_agent(
    query: str,
    history: List[Dict[str, str]],
    api_key: str,
    model_id: str,
    tools: List[BaseTool],
    temperature: float,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
) -> Dict[str, Any]:
    """
    Run the LangGraph ReAct agent and return a structured result dict.

    Returns
    -------
    {
        "response"     : str,
        "elapsed_sec"  : float,
        "tools_used"   : List[str],
        "error"        : str | None,
    }
    """
    agent = build_agent(api_key, model_id, tools, temperature)

    # Build context string from recent history
    context_turns = history[-6:]
    history_text = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in context_turns
    )
    full_prompt = f"{history_text}\nUser: {query}" if history_text else query

    tools_used: List[str] = []

    class _ToolTracker(BaseCallbackHandler):
        def on_tool_start(self, serialized, input_str, **kw):
            name = serialized.get("name", "unknown")
            if name not in tools_used:
                tools_used.append(name)

    tracker = _ToolTracker()
    all_callbacks = [tracker] + (callbacks or [])

    t0 = time.perf_counter()
    try:
        result = agent.invoke(
            {"messages": [HumanMessage(content=full_prompt)]},
            config={"callbacks": all_callbacks},
        )

        messages = result.get("messages", [])

        # Also pick up tool names from ToolMessages in the graph output
        for m in messages:
            if isinstance(m, ToolMessage) and m.name and m.name not in tools_used:
                tools_used.append(m.name)

        response = _extract_clean_response(messages)
        error = None

    except Exception as exc:
        logger.error("Agent error: %s", exc)
        response = f"⚠️ An error occurred: {exc}"
        error = str(exc)

    elapsed = round(time.perf_counter() - t0, 2)

    return {
        "response":    response,
        "elapsed_sec": elapsed,
        "tools_used":  tools_used,
        "error":       error,
    }