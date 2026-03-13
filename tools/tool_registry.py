"""
tools/tool_registry.py
----------------------
Single registry that assembles the full tool-set.
Callers just import `get_tools()` — they never touch individual factories.
"""

from typing import List, Dict
from langchain.tools import BaseTool

from .arxiv_tool import build_arxiv_tool
from .wikipedia_tool import build_wikipedia_tool
from .duckduckgo_tool import build_duckduckgo_tool


# Mapping: display name → factory function
_TOOL_FACTORIES: Dict[str, callable] = {
    "🌐 Web Search":  build_duckduckgo_tool,
    "📚 Wikipedia":   build_wikipedia_tool,
    "🔬 Arxiv":       build_arxiv_tool,
}


def get_all_tool_names() -> List[str]:
    """Return display names of every available tool."""
    return list(_TOOL_FACTORIES.keys())


def get_tools(selected_names: List[str] | None = None) -> List[BaseTool]:
    """
    Build and return tools for the given display names.
    If *selected_names* is None, all tools are returned.
    """
    names = selected_names if selected_names is not None else get_all_tool_names()
    return [_TOOL_FACTORIES[name]() for name in names if name in _TOOL_FACTORIES]
