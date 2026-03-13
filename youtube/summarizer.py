"""
youtube/summarizer.py
---------------------
AI-powered video summary and Q&A using Groq LLMs.

Token-budget problem this version solves
-----------------------------------------
Groq free-tier TPM limits vary per model:
  llama-3.1-8b-instant     →  6 000 TPM
  llama-3.3-70b-versatile  →  6 000 TPM
  llama-4-scout-17b        → 30 000 TPM
  qwen3-32b                →  6 000 TPM

A raw transcript can be 10 000+ tokens, which blows the per-minute
limit and returns HTTP 413.  This module fixes that by:

  1. _token_budget(model_id)
       Looks up the model's safe_input_tokens from settings.MODEL_LOOKUP.
       Falls back to DEFAULT_SAFE_INPUT_TOKENS for any unknown model.

  2. _truncate(transcript, max_tokens)
       Converts the token budget to a character limit (1 token ≈ 4 chars),
       then takes the first 60 % and last 20 % of that limit so the
       summary covers both the intro and conclusion of the video.

  3. _call_with_retry(llm, messages, transcript, max_tokens)
       On HTTP 413 / rate_limit_exceeded, halves the transcript and retries
       up to MAX_SHRINK_ATTEMPTS times before giving up.
"""

import re
import time
from typing import List

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage

from config.settings import MODEL_LOOKUP, DEFAULT_SAFE_INPUT_TOKENS
from utils.logger import get_logger

logger = get_logger(__name__)

# How many times to halve the transcript on 413 before giving up
MAX_SHRINK_ATTEMPTS = 4

# Approximate chars-per-token for English/multilingual text
CHARS_PER_TOKEN = 4


# ─────────────────────────────────────────────────────────────────────────────
# Token budget helpers
# ─────────────────────────────────────────────────────────────────────────────

def _token_budget(model_id: str) -> int:
    """
    Return the safe input token budget for *model_id*.
    Uses MODEL_LOOKUP from settings; falls back to DEFAULT_SAFE_INPUT_TOKENS.
    """
    model = MODEL_LOOKUP.get(model_id)
    if model:
        return model.safe_input_tokens
    logger.warning(
        "Model '%s' not in MODEL_LOOKUP — using default budget of %d tokens",
        model_id, DEFAULT_SAFE_INPUT_TOKENS,
    )
    return DEFAULT_SAFE_INPUT_TOKENS


def _char_limit(token_budget: int) -> int:
    """Convert token budget to a character limit (1 token ≈ 4 chars)."""
    return token_budget * CHARS_PER_TOKEN


def _truncate(transcript: str, max_chars: int) -> str:
    """
    Intelligently truncate a transcript to *max_chars*.

    Strategy: keep first 60 % (intro / definitions) + last 20 % (conclusion).
    This gives the LLM a better picture than just chopping at the end.
    """
    if len(transcript) <= max_chars:
        return transcript

    head_chars = int(max_chars * 0.60)
    tail_chars = int(max_chars * 0.20)

    head = transcript[:head_chars]
    tail = transcript[-tail_chars:] if tail_chars > 0 else ""

    skipped = len(transcript) - head_chars - tail_chars
    bridge = f"\n\n[... {skipped:,} characters omitted for length ...]\n\n"

    truncated = head + bridge + tail
    logger.debug(
        "Transcript truncated: %d → %d chars (head=%d tail=%d skipped=%d)",
        len(transcript), len(truncated), head_chars, tail_chars, skipped,
    )
    return truncated


def _is_413(exc: Exception) -> bool:
    """Return True if the exception is a Groq 413 / token limit error."""
    msg = str(exc).lower()
    return (
        "413" in msg
        or "request too large" in msg
        or "rate_limit_exceeded" in msg
        or "tokens per minute" in msg
        or "tpm" in msg
    )


# ─────────────────────────────────────────────────────────────────────────────
# Retry-on-413 wrapper
# ─────────────────────────────────────────────────────────────────────────────

def _call_with_retry(
    llm: ChatGroq,
    system_prompt: str,
    user_prompt_prefix: str,   # everything before the transcript
    transcript: str,
    user_prompt_suffix: str,   # everything after the transcript
    max_chars: int,
) -> str:
    """
    Call the LLM with automatic 413 recovery:
      - On 413: halve the transcript and retry up to MAX_SHRINK_ATTEMPTS times.
      - Between retries: sleep 1 s to let the TPM window refresh slightly.
    """
    current_transcript = _truncate(transcript, max_chars)
    current_max        = max_chars

    for attempt in range(1, MAX_SHRINK_ATTEMPTS + 2):   # +1 for the initial attempt
        user_content = (
            user_prompt_prefix
            + current_transcript
            + user_prompt_suffix
        )
        messages: List[BaseMessage] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]

        try:
            response = llm.invoke(messages)
            return response.content.strip()

        except Exception as exc:
            if _is_413(exc) and attempt <= MAX_SHRINK_ATTEMPTS:
                current_max = current_max // 2
                current_transcript = _truncate(transcript, current_max)
                logger.warning(
                    "413 on attempt %d — shrinking transcript to %d chars and retrying",
                    attempt, current_max,
                )
                time.sleep(1.0)   # let the 1-minute TPM window recover a little
                continue
            # Non-413 error or exhausted retries
            raise

    raise RuntimeError("Exhausted all retry attempts after repeated 413 errors")


# ─────────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────────

_SUMMARY_SYSTEM = """You are an expert multilingual video analyst and educator.
Your job is to produce a concise, well-structured summary of a YouTube video
based on its transcript.

IMPORTANT: The transcript may be in ANY language (Hindi, Urdu, Spanish, Arabic,
French, etc.). Regardless of the transcript language, you MUST always write
your summary in clear English. Translate and summarise — do not reproduce
raw non-English text.

Format your response in clean Markdown with these sections:
## Overview
One or two sentences describing what the video is about.

## Key Points
A bullet list of the 4-6 most important concepts, facts, or takeaways.

## Main Conclusion
One sentence capturing the core message or conclusion of the video.

Be factual, clear, and educational. Do not add information not present in the transcript.
Keep your total response under 400 words."""


_QA_SYSTEM_TEMPLATE = """You are an intelligent multilingual video learning assistant.
The user is watching: "{title}"

The transcript may be in any language. Always answer in clear English —
translate and explain as needed. Be concise and educational.
If the answer is not in the transcript, say so clearly.

VIDEO TRANSCRIPT (may be truncated):
{transcript}"""


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def summarize_transcript(
    transcript: str,
    video_title: str,
    api_key: str,
    model_id: str,
) -> str:
    """
    Generate a structured markdown summary from a video transcript.

    Automatically truncates the transcript to fit within the model's
    Groq TPM limit. Retries with progressively smaller input on 413.

    Parameters
    ----------
    transcript  : raw transcript text (any length, any language)
    video_title : video title for context
    api_key     : Groq API key
    model_id    : Groq model ID (used to look up TPM budget)

    Returns markdown summary string.
    """
    if not transcript or not transcript.strip():
        return "_No transcript available — summary could not be generated._"

    # Reserve tokens: system prompt (~200) + response (~400) + title (~20) + margin
    reserved_tokens  = 700
    budget_tokens    = _token_budget(model_id) - reserved_tokens
    budget_chars     = _char_limit(max(budget_tokens, 500))   # floor at 500

    logger.info(
        "Summarizing for model=%s | budget=%d tokens (%d chars) | "
        "transcript=%d chars",
        model_id, budget_tokens, budget_chars, len(transcript),
    )

    llm = ChatGroq(
        groq_api_key = api_key,
        model_name   = model_id,
        temperature  = 0.3,
        streaming    = False,
    )

    prefix = f"Video title: **{video_title}**\n\nTranscript:\n"
    suffix = "\n\nPlease summarise this video using the format specified."

    try:
        return _call_with_retry(
            llm            = llm,
            system_prompt  = _SUMMARY_SYSTEM,
            user_prompt_prefix = prefix,
            transcript     = transcript,
            user_prompt_suffix = suffix,
            max_chars      = budget_chars,
        )
    except Exception as exc:
        logger.error("Summary generation failed for model=%s: %s", model_id, exc)
        return (
            f"_Summary unavailable — the transcript may be too long for this "
            f"model's rate limit. Try switching to **Llama 4 Scout** (30K TPM) "
            f"in the sidebar, or try again in a minute._\n\n"
            f"_Error: {exc}_"
        )


def answer_video_question(
    question: str,
    transcript: str,
    video_title: str,
    api_key: str,
    model_id: str,
    chat_history: list = None,
) -> str:
    """
    Answer a user question about the video using its transcript.

    Automatically truncates the transcript to leave room for the question,
    chat history, and response within the model's TPM budget.

    Parameters
    ----------
    question     : user's question
    transcript   : video transcript (any length, any language)
    video_title  : video title
    api_key      : Groq API key
    model_id     : Groq model ID
    chat_history : list of prior {"role": ..., "content": ...} messages

    Returns answer string.
    """
    # Estimate tokens used by history + question + system overhead
    history_chars    = sum(len(m.get("content", "")) for m in (chat_history or []))
    question_chars   = len(question)
    overhead_tokens  = 600 + (history_chars + question_chars) // CHARS_PER_TOKEN
    budget_tokens    = _token_budget(model_id) - overhead_tokens
    budget_chars     = _char_limit(max(budget_tokens, 400))

    logger.info(
        "Q&A for model=%s | budget=%d tokens (%d chars) | transcript=%d chars",
        model_id, budget_tokens, budget_chars, len(transcript or ""),
    )

    safe_transcript = _truncate(transcript or "No transcript available.", budget_chars)

    system_content = _QA_SYSTEM_TEMPLATE.format(
        title      = video_title,
        transcript = safe_transcript,
    )

    messages: List[BaseMessage] = [SystemMessage(content=system_content)]

    # Inject prior Q&A turns (last 4 only to save tokens)
    for msg in (chat_history or [])[-4:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=question))

    llm = ChatGroq(
        groq_api_key = api_key,
        model_name   = model_id,
        temperature  = 0.3,
        streaming    = False,
    )

    for attempt in range(1, MAX_SHRINK_ATTEMPTS + 2):
        try:
            response = llm.invoke(messages)
            return response.content.strip()
        except Exception as exc:
            if _is_413(exc) and attempt <= MAX_SHRINK_ATTEMPTS:
                # Rebuild system message with half the transcript
                budget_chars = budget_chars // 2
                safe_transcript = _truncate(
                    transcript or "No transcript available.", budget_chars
                )
                system_content = _QA_SYSTEM_TEMPLATE.format(
                    title      = video_title,
                    transcript = safe_transcript,
                )
                messages[0] = SystemMessage(content=system_content)
                logger.warning(
                    "Q&A 413 on attempt %d — shrinking to %d chars",
                    attempt, budget_chars,
                )
                time.sleep(1.0)
                continue
            logger.error("Q&A failed for model=%s: %s", model_id, exc)
            return (
                f"⚠️ Could not answer — token limit hit. "
                f"Try switching to **Llama 4 Scout** in the sidebar or "
                f"wait a moment and try again.\n\n_Error: {exc}_"
            )