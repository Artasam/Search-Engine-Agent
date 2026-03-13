"""
tools/arxiv_tool.py
-------------------
Thin factory that builds a configured ArxivQueryRun tool.
Keeps all tool-specific knobs in one place.
"""

from langchain_community.utilities import ArxivAPIWrapper
from langchain_community.tools import ArxivQueryRun
from config.settings import ARXIV_TOP_K, ARXIV_CHARS_MAX


def build_arxiv_tool() -> ArxivQueryRun:
    """Return a ready-to-use ArxivQueryRun tool."""
    wrapper = ArxivAPIWrapper(
        top_k_results=ARXIV_TOP_K,
        doc_content_chars_max=ARXIV_CHARS_MAX,
    )
    tool = ArxivQueryRun(api_wrapper=wrapper)
    tool.description = (
        "Search academic papers on Arxiv. "
        "Use for scientific questions, research papers, and technical topics."
    )
    return tool
