"""
tools/wikipedia_tool.py
-----------------------
Factory for WikipediaQueryRun.
"""

from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools import WikipediaQueryRun
from config.settings import WIKIPEDIA_TOP_K, WIKIPEDIA_CHARS_MAX


def build_wikipedia_tool() -> WikipediaQueryRun:
    """Return a configured WikipediaQueryRun tool."""
    wrapper = WikipediaAPIWrapper(
        top_k_results=WIKIPEDIA_TOP_K,
        doc_content_chars_max=WIKIPEDIA_CHARS_MAX,
    )
    tool = WikipediaQueryRun(api_wrapper=wrapper)
    tool.description = (
        "Search Wikipedia for factual information, definitions, and encyclopedic content. "
        "Best for concepts, historical events, and well-established topics."
    )
    return tool
