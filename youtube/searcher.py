"""
youtube/searcher.py
-------------------
Searches YouTube for the most relevant video matching a user query.

Fallback chain (tries each in order until one works):
  1. ddgs.text()  with backend="google"   — most reliable
  2. ddgs.text()  with backend="auto"     — let DDGS pick
  3. ddgs.videos() native YouTube search  — direct video results
  4. youtube-search-python               — pure scrape, no API key

Returns a structured VideoResult dataclass with everything the UI needs.
NO YouTube Data API key required.
"""

import re
import time
from dataclasses import dataclass
from typing import Optional, List

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


def _extract_video_id(url: str) -> Optional[str]:
    """Pull the 11-char video ID from any YouTube URL format."""
    if not url:
        return None
    patterns = [
        r"youtube\.com/watch\?v=([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
        r"youtube\.com/v/([A-Za-z0-9_-]{11})",
        r"[?&]v=([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            vid = match.group(1)
            # Sanity check — must be exactly 11 chars
            if len(vid) == 11:
                return vid
    return None


def _parse_result(r: dict) -> Optional[VideoResult]:
    """Convert a raw DDGS result dict into a VideoResult if it has a valid video ID."""
    url   = r.get("href") or r.get("url") or r.get("link") or ""
    vid   = _extract_video_id(url)
    if not vid:
        return None

    title       = r.get("title") or r.get("name") or "Untitled Video"
    body        = r.get("body") or r.get("description") or r.get("snippet") or ""
    channel     = ""

    # Clean " - YouTube" suffix from title
    if " - YouTube" in title:
        title = title.split(" - YouTube")[0].strip()

    # Try to extract channel name from body
    if " · " in body:
        channel = body.split(" · ")[0].strip()
    elif "YouTube · " in body:
        channel = body.split("YouTube · ")[-1].split("\n")[0].strip()

    return VideoResult(
        video_id    = vid,
        title       = title.strip(),
        url         = url,
        channel     = channel,
        description = body[:300],
        thumbnail   = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
    )


# ── Strategy 1: DDGS text search with google backend ─────────────────────────

def _search_via_ddgs_google(query: str, max_results: int) -> Optional[VideoResult]:
    """Use DDGS text search with Google backend scoped to youtube.com."""
    try:
        from ddgs import DDGS
        search_q = f"site:youtube.com/watch {query}"
        logger.info("DDGS google backend: %s", search_q)
        with DDGS() as ddgs:
            results = list(ddgs.text(
                search_q,
                max_results=max_results,
                backend="google",
            ))
        for r in results:
            v = _parse_result(r)
            if v:
                logger.info("Found via DDGS google: %s", v.video_id)
                return v
    except Exception as exc:
        logger.warning("DDGS google backend failed: %s", exc)
    return None


# ── Strategy 2: DDGS text search with auto backend ───────────────────────────

def _search_via_ddgs_auto(query: str, max_results: int) -> Optional[VideoResult]:
    """Use DDGS text search with auto backend."""
    try:
        from ddgs import DDGS
        search_q = f"youtube.com/watch {query} tutorial"
        logger.info("DDGS auto backend: %s", search_q)
        with DDGS() as ddgs:
            results = list(ddgs.text(
                search_q,
                max_results=max_results,
            ))
        for r in results:
            v = _parse_result(r)
            if v:
                logger.info("Found via DDGS auto: %s", v.video_id)
                return v
    except Exception as exc:
        logger.warning("DDGS auto backend failed: %s", exc)
    return None


# ── Strategy 3: DDGS native videos() search ──────────────────────────────────

def _search_via_ddgs_videos(query: str, max_results: int) -> Optional[VideoResult]:
    """Use DDGS native video search endpoint."""
    try:
        from ddgs import DDGS
        logger.info("DDGS videos(): %s", query)
        with DDGS() as ddgs:
            results = list(ddgs.videos(
                query,
                max_results=max_results,
            ))
        for r in results:
            # DDGS videos() returns: content (url), title, description, publisher
            url = r.get("content") or r.get("url") or ""
            vid = _extract_video_id(url)
            if not vid:
                # Try embed_url field
                vid = _extract_video_id(r.get("embed_url", ""))
            if not vid:
                continue

            title   = r.get("title", "Untitled Video")
            channel = r.get("publisher") or r.get("uploader") or ""
            desc    = r.get("description") or ""

            if " - YouTube" in title:
                title = title.split(" - YouTube")[0].strip()

            logger.info("Found via DDGS videos: %s", vid)
            return VideoResult(
                video_id    = vid,
                title       = title.strip(),
                url         = f"https://www.youtube.com/watch?v={vid}",
                channel     = channel,
                description = desc[:300],
                thumbnail   = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
            )
    except Exception as exc:
        logger.warning("DDGS videos() failed: %s", exc)
    return None


# ── Strategy 4: youtube-search-python scrape ─────────────────────────────────

def _search_via_ytsearch(query: str) -> Optional[VideoResult]:
    """
    Use youtube-search-python (youtubesearchpython) as final fallback.
    Install: pip install youtube-search-python
    """
    try:
        from youtubesearchpython import VideosSearch
        logger.info("youtube-search-python: %s", query)
        vs      = VideosSearch(query, limit=3)
        results = vs.result().get("result", [])
        for r in results:
            vid = r.get("id") or _extract_video_id(r.get("link", ""))
            if not vid:
                continue
            title   = r.get("title", "Untitled")
            channel = r.get("channel", {}).get("name", "")
            desc    = r.get("descriptionSnippet", [{}])
            desc_text = desc[0].get("text", "") if isinstance(desc, list) and desc else ""
            logger.info("Found via ytsearch: %s", vid)
            return VideoResult(
                video_id    = vid,
                title       = title,
                url         = f"https://www.youtube.com/watch?v={vid}",
                channel     = channel,
                description = desc_text[:300],
                thumbnail   = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
            )
    except ImportError:
        logger.warning("youtube-search-python not installed. Run: pip install youtube-search-python")
    except Exception as exc:
        logger.warning("youtube-search-python failed: %s", exc)
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def search_youtube(query: str, max_results: int = 6) -> Optional[VideoResult]:
    """
    Search YouTube and return the best VideoResult.
    Tries four strategies in order — returns first success, or None.

    Parameters
    ----------
    query       : user search query (natural language)
    max_results : results to scan per strategy

    Returns VideoResult or None if all strategies fail.
    """
    strategies = [
        lambda: _search_via_ddgs_google(query, max_results),
        lambda: _search_via_ddgs_videos(query, max_results),
        lambda: _search_via_ddgs_auto(query, max_results),
        lambda: _search_via_ytsearch(query),
    ]

    for i, strategy in enumerate(strategies, 1):
        try:
            result = strategy()
            if result:
                return result
        except Exception as exc:
            logger.warning("Strategy %d raised: %s", i, exc)
        # Small back-off between attempts to avoid rate limiting
        if i < len(strategies):
            time.sleep(0.5)

    logger.error("All YouTube search strategies exhausted for: %s", query)
    return None