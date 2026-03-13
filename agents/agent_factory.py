"""
agents/agent_factory.py
-----------------------
Builds a ReAct agent compatible with your installed packages:

    langchain          1.2.11
    langchain-core     1.2.18
    langgraph          1.1.0
    langgraph-prebuilt 1.0.8
    langchain-groq     1.1.2
"""

from typing import List

from langchain_core.tools import BaseTool
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from config.settings import MAX_ITERATIONS, MAX_EXECUTION_TIME

# ── System prompt ─────────────────────────────────────────────────────────────
# Prevents the model from leaking raw tool-call XML / JSON in its final reply.
# Without this, some Groq models return <web_search>{"query":"..."}</function>
# instead of executing the tool and summarising the result.
SYSTEM_PROMPT = """You are a helpful AI research assistant with access to search tools.

STRICT RULES:
1. NEVER output raw tool call syntax like <web_search>...</web_search> or JSON function calls in your final answer.
2. Always USE the tools silently, then write a clean, human-readable answer based on the results.
3. If a tool returns results, summarise them clearly in plain English.
4. Always end with a complete, helpful Final Answer — never leave the response as a tool invocation.
5. Be concise but thorough. Cite sources when available.
"""


def build_agent(
    api_key: str,
    model_id: str,
    tools: List[BaseTool],
    temperature: float = 0.0,
    streaming: bool = True,
):
    """
    Build and return a LangGraph ReAct agent (compiled StateGraph).

    Parameters
    ----------
    api_key     : Groq API key
    model_id    : Groq model identifier string
    tools       : list of LangChain BaseTool instances
    temperature : LLM temperature (0 = deterministic)
    streaming   : enable token streaming
    """
    llm = ChatGroq(
        groq_api_key=api_key,
        model_name=model_id,
        streaming=streaming,
        temperature=temperature,
    )

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

    return agent