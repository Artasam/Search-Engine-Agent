"""
youtube/transcript.py
---------------------
Cloud-safe transcript fetching for ANY YouTube video.

WHY ALL STRATEGIES FAIL ON STREAMLIT CLOUD
-------------------------------------------
Streamlit Cloud runs on AWS/GCP. YouTube permanently blocks ALL requests
from known cloud-provider IP ranges. This kills:
  - yt-dlp          → "Sign in to confirm you're not a bot"
  - youtube-transcript-api (direct) → "IPBlocked / RequestBlocked"

THE CORRECT SOLUTION FOR CLOUD DEPLOYMENTS
-------------------------------------------
Tier 1 : ytta v1.x + Webshare free proxy
         Residential IPs bypass YouTube's cloud ban.
         FREE signup: https://proxy.webshare.io (no credit card)
         Add to Streamlit secrets:
           WEBSHARE_PROXY_USERNAME = "xxxx"
           WEBSHARE_PROXY_PASSWORD = "xxxx"

Tier 2 : ytta v1.x direct
         Works on local machines and non-cloud VPS.
         Fails silently on Streamlit Cloud (expected).

Tier 3 : yt-dlp direct
         Same — works locally, blocked on cloud.

Tier 4 : YouTube Data API v3 — video description as context
         NEVER IP-blocked (it's a public Google API).
         Gives the LLM title + description + tags for a meaningful summary.
         FREE — 10,000 units/day.  Get key:
           https://console.cloud.google.com → YouTube Data API v3
         Add to Streamlit secrets:
           YOUTUBE_API_KEY = "AIza..."

MINIMUM SETUP FOR STREAMLIT CLOUD (pick one):
  Option A — Add WEBSHARE_PROXY_USERNAME + WEBSHARE_PROXY_PASSWORD
             Full transcript → best summaries and Q&A
  Option B — Add YOUTUBE_API_KEY only
             Description-based context → good summaries, limited Q&A
  Option C — Add both
             Best coverage: transcript when available, description as fallback
"""

import re
import os
import json
import time
import random
import tempfile
import urllib.request
import urllib.parse
from typing import Optional

import streamlit as st
from utils.logger import get_logger

logger = get_logger(__name__)

TRANSCRIPT_CHAR_LIMIT = 12_000


# ─────────────────────────────────────────────────────────────────────────────
# Secret resolution
# ─────────────────────────────────────────────────────────────────────────────

def _secret(key: str) -> str:
    """Read from st.secrets first, then os.environ."""
    try:
        val = st.secrets.get(key, "")
        if val:
            return str(val).strip()
    except Exception:
        pass
    return os.environ.get(key, "").strip()


# ─────────────────────────────────────────────────────────────────────────────
# Text cleaning
# ─────────────────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    text = re.sub(r"\[.*?\]", "",  text)
    text = re.sub(r"<[^>]+>", "",  text)
    text = re.sub(r"&amp;",   "&", text)
    text = re.sub(r"&nbsp;",  " ", text)
    text = re.sub(r"&#39;",   "'", text)
    text = re.sub(r"&quot;",  '"', text)
    text = re.sub(r"\s{2,}",  " ", text)
    return text.strip()


def _best_transcript(tlist) -> Optional[str]:
    """
    Given a list of transcript objects from ytta, pick the best one
    (English manual > English auto > any manual > any) and return clean text.
    """
    def _score(t) -> int:
        s = 100 if getattr(t, "language_code", "").startswith("en") else 0
        return s + (10 if not getattr(t, "is_generated", True) else 0)

    for t in sorted(tlist, key=_score, reverse=True):
        try:
            raw = " ".join(seg.text for seg in t.fetch())
            if raw.strip():
                logger.info(
                    "Transcript [lang=%s generated=%s]: %d chars",
                    getattr(t, "language_code", "?"),
                    getattr(t, "is_generated", "?"),
                    len(raw),
                )
                return _clean(raw)[:TRANSCRIPT_CHAR_LIMIT]
        except Exception:
            continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Tier 1 : ytta v1.x + Webshare residential proxy  (cloud-safe)
# ─────────────────────────────────────────────────────────────────────────────

def _via_ytta_webshare(video_id: str) -> Optional[str]:
    """
    youtube-transcript-api >= 1.0 with WebshareProxyConfig.
    Webshare free-tier residential proxies are NOT on YouTube's cloud blocklist.

    Requires in Streamlit secrets:
        WEBSHARE_PROXY_USERNAME = "..."
        WEBSHARE_PROXY_PASSWORD = "..."
    Free signup (no credit card): https://proxy.webshare.io
    """
    username = _secret("WEBSHARE_PROXY_USERNAME")
    password = _secret("WEBSHARE_PROXY_PASSWORD")
    if not username or not password:
        logger.debug("Tier 1 skipped: Webshare credentials not set in secrets")
        return None

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api.proxies import WebshareProxyConfig
    except ImportError as exc:
        logger.debug("ytta or WebshareProxyConfig not available: %s", exc)
        return None

    try:
        proxy_config = WebshareProxyConfig(
            proxy_username=username,
            proxy_password=password,
        )
        api   = YouTubeTranscriptApi(proxy_config=proxy_config)
        tlist = list(api.list(video_id))
        result = _best_transcript(tlist)
        if result:
            logger.info("Tier 1 success (ytta+Webshare) for %s", video_id)
        return result
    except Exception as exc:
        logger.warning("Tier 1 ytta+Webshare failed for %s: %s", video_id, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2 : ytta v1.x direct  (works locally, fails on cloud)
# ─────────────────────────────────────────────────────────────────────────────

def _via_ytta_direct(video_id: str) -> Optional[str]:
    """
    Direct ytta v1.x — no proxy.
    Works on local machines and non-cloud VPS.
    Expected to fail on Streamlit Cloud (IP blocked) — fails silently.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        if not hasattr(api, "list"):
            return None
        tlist  = list(api.list(video_id))
        result = _best_transcript(tlist)
        if result:
            logger.info("Tier 2 success (ytta direct) for %s", video_id)
        return result
    except Exception as exc:
        # Expected on Streamlit Cloud — log at debug only
        logger.debug("Tier 2 ytta direct failed for %s (likely cloud IP ban): %s",
                     video_id, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Tier 3 : yt-dlp  (works locally, fails on cloud)
# ─────────────────────────────────────────────────────────────────────────────

def _via_ytdlp(video_id: str) -> Optional[str]:
    """
    yt-dlp subtitle download.
    Works locally. On Streamlit Cloud this raises "Sign in to confirm
    you're not a bot" — caught and logged at debug only.
    """
    try:
        import yt_dlp
    except ImportError:
        return None

    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts = {
            "skip_download":      True,
            "writesubtitles":     True,
            "writeautomaticsub":  True,
            "subtitleslangs":     ["all"],
            "subtitlesformat":    "json3/vtt/best",
            "outtmpl":            f"{tmpdir}/%(id)s.%(ext)s",
            "quiet":              True,
            "no_warnings":        True,
            "sleep_interval":     1,
            "max_sleep_interval": 3,
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadError as exc:
            logger.debug("Tier 3 yt-dlp failed for %s (likely cloud IP ban): %s",
                         video_id, exc)
            return None
        except Exception as exc:
            logger.debug("Tier 3 yt-dlp unexpected error for %s: %s", video_id, exc)
            return None

        import os
        all_files = os.listdir(tmpdir)

        def _score(fname: str) -> int:
            s = 0
            if ".en." in fname:           s += 100
            if fname.endswith(".json3"):  s += 10
            elif fname.endswith(".vtt"):  s += 5
            if ".a." not in fname:        s += 20
            return s

        for fname in sorted(all_files, key=_score, reverse=True):
            fpath = os.path.join(tmpdir, fname)
            if fname.endswith(".json3"):
                try:
                    import json as _json
                    with open(fpath, encoding="utf-8") as f:
                        data = _json.load(f)
                    segs = [
                        seg.get("utf8", "").strip()
                        for ev in data.get("events", [])
                        for seg in ev.get("segs", [])
                        if seg.get("utf8", "").strip() not in ("", "\n")
                    ]
                    raw = " ".join(segs)
                    if raw.strip():
                        logger.info("Tier 3 success (yt-dlp json3) for %s", video_id)
                        return _clean(raw)[:TRANSCRIPT_CHAR_LIMIT]
                except Exception:
                    continue
            elif fname.endswith(".vtt"):
                try:
                    with open(fpath, encoding="utf-8") as f:
                        vtt = f.read()
                    lines = [
                        l.strip() for l in vtt.splitlines()
                        if l.strip()
                        and not l.startswith("WEBVTT")
                        and "-->" not in l
                        and not re.match(r"^\d{2}:\d{2}", l)
                        and not re.match(r"^\d+$", l)
                    ]
                    raw = " ".join(lines)
                    if raw.strip():
                        logger.info("Tier 3 success (yt-dlp vtt) for %s", video_id)
                        return _clean(raw)[:TRANSCRIPT_CHAR_LIMIT]
                except Exception:
                    continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Tier 4 : YouTube Data API v3 — description fallback  (never IP-blocked)
# ─────────────────────────────────────────────────────────────────────────────

def _via_youtube_api_description(video_id: str) -> Optional[str]:
    """
    Fetch video metadata via YouTube Data API v3 (public endpoint, never
    blocked by YouTube regardless of server IP).

    Returns title + channel + tags + full description — enough for the LLM
    to produce a meaningful summary and answer basic questions.

    Requires YOUTUBE_API_KEY in Streamlit secrets or environment.
    Free quota: 10,000 units/day.  1 unit per call.
    Get key: https://console.cloud.google.com → YouTube Data API v3
    """
    api_key = _secret("YOUTUBE_API_KEY")
    if not api_key:
        logger.warning(
            "Tier 4 skipped: YOUTUBE_API_KEY not set. "
            "Add it to Streamlit secrets for cloud deployments."
        )
        return None

    url = (
        "https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet&id={video_id}&key={api_key}"
    )
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("Tier 4 YouTube API request failed for %s: %s", video_id, exc)
        return None

    items = data.get("items", [])
    if not items:
        logger.warning("Tier 4 YouTube API: video %s not found", video_id)
        return None

    snippet = items[0].get("snippet", {})
    title   = snippet.get("title", "")
    channel = snippet.get("channelTitle", "")
    desc    = snippet.get("description", "")
    tags    = ", ".join(snippet.get("tags", [])[:15])

    combined = (
        f"Video Title: {title}\n"
        f"Channel: {channel}\n"
        + (f"Tags: {tags}\n" if tags else "")
        + f"\nDescription:\n{desc}"
    ).strip()

    if combined:
        logger.info(
            "Tier 4 success (YouTube API description) for %s: %d chars",
            video_id, len(combined),
        )
        return _clean(combined)[:TRANSCRIPT_CHAR_LIMIT]

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_transcript(video_id: str, languages: list = None) -> Optional[str]:
    """
    Fetch transcript for *video_id* using a cloud-safe 4-tier chain.

    Tier 1 — ytta + Webshare proxy    CLOUD-SAFE  needs WEBSHARE_* secrets
    Tier 2 — ytta direct              LOCAL ONLY  fails silently on cloud
    Tier 3 — yt-dlp direct            LOCAL ONLY  fails silently on cloud
    Tier 4 — YouTube Data API desc    CLOUD-SAFE  needs YOUTUBE_API_KEY secret

    For Streamlit Cloud: add at least YOUTUBE_API_KEY to secrets.
    For full transcripts on cloud: also add WEBSHARE_PROXY_USERNAME/PASSWORD.
    """
    logger.info("Fetching transcript for video: %s", video_id)

    result = _via_ytta_webshare(video_id)
    if result:
        return result

    result = _via_ytta_direct(video_id)
    if result:
        return result

    result = _via_ytdlp(video_id)
    if result:
        return result

    result = _via_youtube_api_description(video_id)
    if result:
        logger.warning(
            "No captions found for %s — using video description as context. "
            "Add WEBSHARE_PROXY_USERNAME/PASSWORD to secrets for full transcripts.",
            video_id,
        )
        return result

    logger.error(
        "All transcript tiers exhausted for %s. "
        "On Streamlit Cloud, add YOUTUBE_API_KEY (and optionally WEBSHARE_PROXY_*) "
        "to your app secrets: https://share.streamlit.io → App settings → Secrets",
        video_id,
    )
    return None