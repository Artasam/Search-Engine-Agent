"""
youtube/searcher.py
-------------------
Intelligent YouTube video search with LLM-powered query refinement
and relevance scoring.

Root cause of irrelevant videos
---------------------------------
Old code: search_youtube(raw_user_prompt)
  → "What are Langchain Components By CampusX?"
  → DDGS returns most-popular video in the cluster
  → "LangChain Models Video 3" (totally different topic)

Fix applied
-----------
1. LLM Query Refinement  (new)
   Before searching, an LLM call extracts the precise search intent:
   "Langchain Components tutorial CampusX" — specific, clean, unambiguous.
   Falls back to keyword extraction (no LLM) if api_key not provided.

2. Multi-candidate retrieval  (improved)
   Fetch up to 8 results from each strategy instead of stopping at 1.

3. Relevance scoring  (new)
   Every candidate is scored against the refined query using:
     - Title word overlap with query keywords
     - Exact phrase matches
     - Channel name match when user mentioned a channel
     - Penalise clearly off-topic keywords found in title
   The HIGHEST scoring video is returned, not the first result found.

4. Context-aware search  (new, called from main.py)
   search_youtube(query, agent_answer=...) passes the agent's own answer
   as additional context so the LLM can build a maximally relevant query.
"""

import re
import time
import random
from dataclasses import dataclass
from typing import Optional, List, Tuple

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VideoResult:
    """All metadata for a single YouTube video."""
    video_id:    str
    title:       str
    url:         str
    channel:     str
    description: str
    thumbnail:   str

    @property
    def embed_url(self) -> str:
        return (
            f"https://www.youtube.com/embed/{self.video_id}"
            f"?rel=0&modestbranding=1&autoplay=0"
        )

    @property
    def watch_url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_video_id(url: str) -> Optional[str]:
    if not url:
        return None
    for pattern in [
        r"youtube\.com/watch\?v=([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
        r"youtube\.com/v/([A-Za-z0-9_-]{11})",
        r"[?&]v=([A-Za-z0-9_-]{11})",
    ]:
        m = re.search(pattern, url)
        if m and len(m.group(1)) == 11:
            return m.group(1)
    return None


def _clean_title(title: str) -> str:
    if " - YouTube" in title:
        title = title.split(" - YouTube")[0]
    return title.strip()


def _to_result(vid: str, title: str, channel: str,
               desc: str, url: str = "") -> VideoResult:
    return VideoResult(
        video_id    = vid,
        title       = _clean_title(title),
        url         = url or f"https://www.youtube.com/watch?v={vid}",
        channel     = channel,
        description = desc[:300],
        thumbnail   = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — LLM Query Refinement
# ─────────────────────────────────────────────────────────────────────────────

_REFINE_SYSTEM = """You are a YouTube search query expert.
Given a user's question and (optionally) an AI answer about that topic,
produce ONE concise YouTube search query (5-8 words max) that will find
the most relevant educational video.

Rules:
- Be SPECIFIC to the exact topic asked (e.g. "components" not "overview")
- Keep any channel name the user mentioned
- Add "tutorial" or "explained" if it's a how-to question
- Remove question words (what, how, why, etc.)
- Output ONLY the search query — no explanation, no quotes, no punctuation

Examples:
  User: "What are Langchain Components By CampusX?"
  Output: Langchain components explained CampusX

  User: "How does attention mechanism work in transformers?"
  Output: attention mechanism transformers explained

  User: "Tell me about neural networks"
  Output: neural networks tutorial beginner"""


def _refine_query_with_llm(
    user_query: str,
    agent_answer: str,
    api_key: str,
    model_id: str,
) -> str:
    """
    Use the Groq LLM to extract a precise YouTube search query from the
    user's natural-language question and the agent's answer context.

    Returns the refined query string, or falls back to keyword extraction.
    """
    if not api_key:
        return _refine_query_keywords(user_query)

    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatGroq(
            groq_api_key = api_key,
            model_name   = model_id,
            temperature  = 0.0,
            max_tokens   = 30,
        )

        context = f"User question: {user_query}"
        if agent_answer and len(agent_answer) > 20:
            # Take just the first sentence of the answer as context
            first_sentence = agent_answer.split(".")[0][:200]
            context += f"\nTopic summary: {first_sentence}"

        response = llm.invoke([
            SystemMessage(content=_REFINE_SYSTEM),
            HumanMessage(content=context),
        ])

        refined = response.content.strip().strip('"\'')
        # Sanity check — must be a short string, not a paragraph
        if refined and len(refined.split()) <= 12 and len(refined) < 100:
            logger.info("LLM refined query: '%s' → '%s'", user_query, refined)
            return refined

    except Exception as exc:
        logger.debug("LLM query refinement failed: %s", exc)

    return _refine_query_keywords(user_query)


def _refine_query_keywords(query: str) -> str:
    """
    Lightweight keyword extraction — no LLM required.
    Removes question words and filler, keeps the meaningful terms.
    """
    # Remove question words and filler phrases
    stopwords = {
        "what", "are", "is", "how", "does", "do", "why", "when", "where",
        "who", "which", "can", "could", "would", "should", "tell", "me",
        "about", "explain", "give", "a", "an", "the", "of", "in", "on",
        "for", "to", "and", "or", "with", "by", "please", "its", "it",
        "some", "any", "all", "let", "talk", "discuss",
    }
    words = re.sub(r"[?!.,;:]", "", query.lower()).split()
    keywords = [w for w in words if w not in stopwords and len(w) > 1]

    if not keywords:
        return query

    refined = " ".join(keywords[:6])
    logger.info("Keyword refined query: '%s' → '%s'", query, refined)
    return refined


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Relevance Scoring
# ─────────────────────────────────────────────────────────────────────────────

def _score_relevance(video: VideoResult, query_keywords: List[str],
                     original_query: str) -> float:
    """
    Score a video's relevance to the query on a 0–100 scale.

    Scoring dimensions:
      +5  per query keyword found in title (case-insensitive)
      +15 bonus if ALL keywords found in title
      +10 if channel name mentioned in original query matches
      +8  per keyword found in description
      -20 penalty per title word that directly contradicts the query
           (e.g. user asked "components", title says "models")

    Higher = more relevant.
    """
    title_lower = video.title.lower()
    desc_lower  = video.description.lower()
    orig_lower  = original_query.lower()

    score = 0.0

    # Keyword coverage in title
    matched = 0
    for kw in query_keywords:
        if kw.lower() in title_lower:
            score += 5
            matched += 1

    # Bonus: all keywords present
    if matched == len(query_keywords) and query_keywords:
        score += 15

    # Keyword coverage in description
    for kw in query_keywords:
        if kw.lower() in desc_lower:
            score += 8

    # Channel match: if user explicitly mentioned a channel name
    channel_patterns = re.findall(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?\b", original_query)
    for cp in channel_patterns:
        if cp.lower() in video.channel.lower() or cp.lower() in title_lower:
            score += 10

    # Contradiction penalty: detect topic-mismatch keywords
    # Build a set of "what the user asked for" vs "what the title says"
    # Focus on nouns that differ between query and title
    query_nouns = set(query_keywords)
    title_words = set(re.sub(r"[^a-z0-9 ]", "", title_lower).split())

    # If query has a specific noun that the title replaces with a different noun
    # from the same domain — penalise
    topic_groups = [
        {"components", "architecture", "structure"},
        {"models", "llm", "gpt", "llama"},
        {"agents", "agent", "tool"},
        {"chains", "chain", "pipeline"},
        {"memory", "context", "history"},
        {"embeddings", "embedding", "vectors", "vector"},
        {"prompts", "prompt", "prompting"},
        {"retrieval", "rag", "search"},
    ]
    for group in topic_groups:
        query_hits = query_nouns & group
        title_hits = title_words & group
        if query_hits and title_hits and not (query_hits & title_hits):
            # Title mentions a DIFFERENT concept from the same domain
            score -= 20

    return score


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Multi-candidate retrieval strategies
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_ddgs_videos(query: str, max_results: int) -> List[VideoResult]:
    """DDGS native videos() — returns up to max_results candidates."""
    results = []
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            raw = list(ddgs.videos(query, max_results=max_results))
        for r in raw:
            url = r.get("content") or r.get("url") or ""
            vid = _extract_video_id(url) or _extract_video_id(r.get("embed_url", ""))
            if not vid:
                continue
            results.append(_to_result(
                vid     = vid,
                title   = r.get("title", ""),
                channel = r.get("publisher") or r.get("uploader") or "",
                desc    = r.get("description") or "",
                url     = f"https://www.youtube.com/watch?v={vid}",
            ))
    except Exception as exc:
        logger.debug("ddgs.videos() failed: %s", exc)
    return results


def _fetch_ddgs_text(query: str, max_results: int,
                     backend: str = "auto") -> List[VideoResult]:
    """DDGS text search scoped to youtube.com/watch."""
    results = []
    try:
        from ddgs import DDGS
        search_q = f"site:youtube.com/watch {query}"
        kwargs = {"max_results": max_results}
        if backend != "auto":
            kwargs["backend"] = backend
        with DDGS() as ddgs:
            raw = list(ddgs.text(search_q, **kwargs))
        for r in raw:
            url = r.get("href") or r.get("url") or ""
            vid = _extract_video_id(url)
            if not vid:
                continue
            title = r.get("title") or ""
            body  = r.get("body") or r.get("description") or ""
            ch    = body.split(" · ")[0].strip() if " · " in body else ""
            results.append(_to_result(vid=vid, title=title,
                                      channel=ch, desc=body, url=url))
    except Exception as exc:
        logger.debug("ddgs.text() backend=%s failed: %s", backend, exc)
    return results


def _fetch_ytsearch(query: str, max_results: int) -> List[VideoResult]:
    """youtube-search-python — pure scrape fallback."""
    results = []
    try:
        from youtubesearchpython import VideosSearch
        vs  = VideosSearch(query, limit=max_results)
        raw = vs.result().get("result", [])
        for r in raw:
            vid = r.get("id") or _extract_video_id(r.get("link", ""))
            if not vid:
                continue
            desc_runs = r.get("descriptionSnippet") or []
            desc = desc_runs[0].get("text", "") if desc_runs else ""
            results.append(_to_result(
                vid     = vid,
                title   = r.get("title", ""),
                channel = r.get("channel", {}).get("name", ""),
                desc    = desc,
            ))
    except Exception as exc:
        logger.debug("youtube-search-python failed: %s", exc)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def search_youtube(
    query: str,
    agent_answer: str = "",
    api_key:  str = "",
    model_id: str = "llama-3.1-8b-instant",
    max_results: int = 8,
) -> Optional[VideoResult]:
    """
    Search YouTube intelligently and return the MOST RELEVANT video.

    Parameters
    ----------
    query        : raw user question / prompt
    agent_answer : the agent's text answer (used as context for query refinement)
    api_key      : Groq API key (enables LLM-based query refinement)
    model_id     : Groq model for query refinement
    max_results  : candidates to fetch per strategy

    Process
    -------
    1. Refine the query using LLM (or keyword extraction)
    2. Collect up to max_results candidates from each strategy
    3. Score every candidate for relevance to the original query
    4. Return the highest-scoring video
    """
    logger.info("YouTube search for: '%s'", query)

    # ── Step 1: Refine query ─────────────────────────────────────────────────
    refined = _refine_query_with_llm(query, agent_answer, api_key, model_id)

    # ── Step 2: Collect candidates from all strategies ───────────────────────
    all_candidates: List[VideoResult] = []

    # Primary: DDGS videos with refined query
    candidates = _fetch_ddgs_videos(refined, max_results)
    logger.info("ddgs.videos(%s): %d candidates", refined, len(candidates))
    all_candidates.extend(candidates)

    # If fewer than 3 candidates, try with original query too
    if len(all_candidates) < 3:
        candidates2 = _fetch_ddgs_videos(query, max_results)
        logger.info("ddgs.videos(original): %d candidates", len(candidates2))
        all_candidates.extend(candidates2)

    # Secondary: DDGS text auto
    if len(all_candidates) < 5:
        candidates3 = _fetch_ddgs_text(refined, max_results, backend="auto")
        logger.info("ddgs.text(auto): %d candidates", len(candidates3))
        all_candidates.extend(candidates3)

    # Tertiary: DDGS text google
    if len(all_candidates) < 5:
        candidates4 = _fetch_ddgs_text(refined, max_results, backend="google")
        logger.info("ddgs.text(google): %d candidates", len(candidates4))
        all_candidates.extend(candidates4)

    # Final fallback: youtube-search-python
    if len(all_candidates) < 3:
        candidates5 = _fetch_ytsearch(refined, max_results)
        logger.info("ytsearch: %d candidates", len(candidates5))
        all_candidates.extend(candidates5)

    if not all_candidates:
        logger.error("No candidates found for: %s", query)
        return None

    # Deduplicate by video_id
    seen:   set = set()
    unique: List[VideoResult] = []
    for v in all_candidates:
        if v.video_id not in seen:
            seen.add(v.video_id)
            unique.append(v)

    logger.info("Total unique candidates: %d", len(unique))

    # ── Step 3: Score and rank all candidates ────────────────────────────────
    query_keywords = _refine_query_keywords(query).split()

    scored: List[Tuple[float, VideoResult]] = []
    for v in unique:
        score = _score_relevance(v, query_keywords, query)
        scored.append((score, v))
        logger.debug("  [%.1f] %s", score, v.title)

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score, best_video = scored[0]
    logger.info(
        "Best match [score=%.1f]: '%s' (id=%s)",
        best_score, best_video.title, best_video.video_id,
    )

    return best_video