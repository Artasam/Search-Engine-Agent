"""
tools/duckduckgo_tool.py
------------------------
Factory for DuckDuckGoSearchRun.
"""

from langchain_community.tools import DuckDuckGoSearchRun


def build_duckduckgo_tool() -> DuckDuckGoSearchRun:
    """Return a configured DuckDuckGoSearchRun tool."""
    tool = DuckDuckGoSearchRun(name="web_search")
    tool.description = (
        "Search the live web using DuckDuckGo. "
        "Use for current events, recent news, trending topics, and real-time information."
    )
    return tool