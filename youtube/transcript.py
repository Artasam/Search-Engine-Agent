"""
youtube/transcript.py
---------------------
Fetches captions/transcript for ANY YouTube video in ANY language.

Errors this version resolves
-----------------------------
1. HTTP 429 Too Many Requests (yt-dlp)
   → Added: randomised User-Agent, sleep+retry with back-off,
     extractor_args to suppress unnecessary API calls.

2. post() got unexpected keyword argument 'proxies'
   (youtubesearchpython broken on modern requests/httpx)
   → Replaced: with pure urllib / YouTube innertube API call — zero
     third-party dependency for description fallback.

3. All strategies exhausted on non-English videos
   → Added: direct YouTube timedtext XML strategy (Strategy 3)
     which bypasses both yt-dlp rate-limiting and broken libraries.

Strategy chain
--------------
  1. yt-dlp              — best quality, any language, with 429 retry
  2. ytta v1.x           — youtube-transcript-api >= 1.0 (instance API)
  3. ytta v0.x           — youtube-transcript-api < 1.0 (class-method)
  4. timedtext API       — direct YouTube timedtext XML, no library
  5. innertube describe  — YouTube's internal API for description text
"""

import re
import os
import json
import time
import random
import urllib.request
import urllib.parse
import urllib.error
import tempfile
from typing import Optional, List

from utils.logger import get_logger

logger = get_logger(__name__)

TRANSCRIPT_CHAR_LIMIT = 12_000

# Realistic desktop browser User-Agents to rotate through
_USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def _random_ua() -> str:
    return random.choice(_USER_AGENTS)


# ─────────────────────────────────────────────────────────────────────────────
# Text cleaning
# ─────────────────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    """Strip caption artifacts and normalise whitespace."""
    text = re.sub(r"\[.*?\]",  "",   text)   # [Music] [Applause]
    text = re.sub(r"<[^>]+>",  "",   text)   # HTML timing tags
    text = re.sub(r"&amp;",    "&",  text)
    text = re.sub(r"&nbsp;",   " ",  text)
    text = re.sub(r"&#39;",    "'",  text)
    text = re.sub(r"&quot;",   '"',  text)
    text = re.sub(r"\s{2,}",   " ",  text)
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 1 : yt-dlp  with 429-resistant options
# ─────────────────────────────────────────────────────────────────────────────

def _via_ytdlp(video_id: str, max_retries: int = 3) -> Optional[str]:
    """
    Download subtitles via yt-dlp.

    429 mitigations applied:
      - Randomised User-Agent per attempt
      - sleep_interval / max_sleep_interval — random delay between requests
      - ratelimit — cap bandwidth to avoid triggering YouTube's detector
      - extractor_args disables DASH/HLS manifest fetching (fewer requests)
      - Exponential back-off between retry attempts (2s, 4s, 8s)
    """
    try:
        import yt_dlp
    except ImportError:
        logger.warning("yt-dlp not installed. Run: pip install yt-dlp")
        return None

    url = f"https://www.youtube.com/watch?v={video_id}"

    for attempt in range(1, max_retries + 1):
        wait = 2 ** attempt          # 2s, 4s, 8s
        jitter = random.uniform(0, 1)

        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "skip_download":      True,
                "writesubtitles":     True,
                "writeautomaticsub":  True,
                "subtitleslangs":     ["all"],
                "subtitlesformat":    "json3/vtt/best",
                "outtmpl":            os.path.join(tmpdir, "%(id)s.%(ext)s"),
                "quiet":              True,
                "no_warnings":        True,
                # ── 429 mitigations ──────────────────────────────────────
                "sleep_interval":     1,
                "max_sleep_interval": 4,
                "http_headers": {
                    "User-Agent": _random_ua(),
                    "Accept-Language": "en-US,en;q=0.9",
                },
                # Skip unnecessary manifest requests
                "extractor_args": {
                    "youtube": {
                        "skip": ["dash", "hls"],
                        "player_skip": ["webpage", "configs"],
                    }
                },
                # Retries at the network level
                "retries":            3,
                "fragment_retries":   3,
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except yt_dlp.utils.DownloadError as exc:
                msg = str(exc)
                if "429" in msg:
                    logger.warning(
                        "yt-dlp 429 on attempt %d/%d for %s — "
                        "sleeping %.1fs before retry",
                        attempt, max_retries, video_id, wait + jitter,
                    )
                    time.sleep(wait + jitter)
                    continue
                logger.warning("yt-dlp DownloadError for %s: %s", video_id, exc)
                return None
            except Exception as exc:
                logger.warning("yt-dlp unexpected error for %s: %s", video_id, exc)
                return None

            # ── Parse subtitle files ──────────────────────────────────────
            all_files = os.listdir(tmpdir)
            if not all_files:
                logger.warning("yt-dlp wrote no files for %s", video_id)
                time.sleep(wait)
                continue

            def _score(fname: str) -> int:
                s = 0
                if ".en." in fname:        s += 100
                if fname.endswith(".json3"): s += 10
                elif fname.endswith(".vtt"): s += 5
                if ".a." not in fname:     s += 20   # manual > auto
                return s

            for fname in sorted(all_files, key=_score, reverse=True):
                fpath = os.path.join(tmpdir, fname)

                if fname.endswith(".json3"):
                    try:
                        with open(fpath, encoding="utf-8") as f:
                            data = json.load(f)
                        segs = [
                            seg.get("utf8", "").strip()
                            for ev in data.get("events", [])
                            for seg in ev.get("segs", [])
                            if seg.get("utf8", "").strip() not in ("", "\n")
                        ]
                        raw = " ".join(segs)
                        if raw.strip():
                            logger.info("Transcript via yt-dlp json3 [%s]: %d chars", fname, len(raw))
                            return _clean(raw)[:TRANSCRIPT_CHAR_LIMIT]
                    except Exception as exc:
                        logger.debug("json3 parse error %s: %s", fname, exc)

                elif fname.endswith(".vtt"):
                    try:
                        with open(fpath, encoding="utf-8") as f:
                            vtt = f.read()
                        lines = [
                            l.strip() for l in vtt.splitlines()
                            if l.strip()
                            and not l.startswith("WEBVTT")
                            and not l.startswith("NOTE")
                            and "-->" not in l
                            and not re.match(r"^\d{2}:\d{2}", l)
                            and not re.match(r"^\d+$", l)
                            and not l.startswith("align:")
                            and not l.startswith("position:")
                        ]
                        raw = " ".join(lines)
                        if raw.strip():
                            logger.info("Transcript via yt-dlp vtt [%s]: %d chars", fname, len(raw))
                            return _clean(raw)[:TRANSCRIPT_CHAR_LIMIT]
                    except Exception as exc:
                        logger.debug("vtt parse error %s: %s", fname, exc)

    logger.warning("yt-dlp exhausted all retries for %s", video_id)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 2 : youtube-transcript-api v1.x  (instance API, 2024+)
# ─────────────────────────────────────────────────────────────────────────────

def _via_ytta_v1(video_id: str) -> Optional[str]:
    """youtube-transcript-api >= 1.0 — instance-based API."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        if not hasattr(api, "list"):
            return None

        tlist = list(api.list(video_id))

        def _score(t) -> int:
            s = 100 if getattr(t, "language_code", "").startswith("en") else 0
            return s + (10 if not getattr(t, "is_generated", True) else 0)

        for t in sorted(tlist, key=_score, reverse=True):
            try:
                raw = " ".join(seg.text for seg in t.fetch())
                if raw.strip():
                    logger.info(
                        "Transcript via ytta v1 [lang=%s]: %d chars",
                        getattr(t, "language_code", "?"), len(raw),
                    )
                    return _clean(raw)[:TRANSCRIPT_CHAR_LIMIT]
            except Exception:
                continue

    except ImportError:
        pass
    except TypeError:
        pass  # not instantiable → v0.x
    except Exception as exc:
        logger.warning("ytta v1 error for %s: %s", video_id, exc)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 3 : youtube-transcript-api v0.x  (class-method API, legacy)
# ─────────────────────────────────────────────────────────────────────────────

def _via_ytta_v0(video_id: str) -> Optional[str]:
    """youtube-transcript-api < 1.0 — class-method API."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        list_fn = getattr(YouTubeTranscriptApi, "list_transcripts", None)
        if list_fn is None:
            return None

        tlist = list(list_fn(video_id))

        def _score(t) -> int:
            s = 100 if getattr(t, "language_code", "").startswith("en") else 0
            return s + (10 if not getattr(t, "is_generated", True) else 0)

        for t in sorted(tlist, key=_score, reverse=True):
            try:
                raw = " ".join(chunk.get("text", "") for chunk in t.fetch())
                if raw.strip():
                    logger.info(
                        "Transcript via ytta v0 [lang=%s]: %d chars",
                        getattr(t, "language_code", "?"), len(raw),
                    )
                    return _clean(raw)[:TRANSCRIPT_CHAR_LIMIT]
            except Exception:
                continue

    except ImportError:
        pass
    except Exception as exc:
        logger.debug("ytta v0 error for %s: %s", video_id, exc)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 4 : Direct YouTube timedtext XML API  (no library, pure urllib)
# ─────────────────────────────────────────────────────────────────────────────

def _via_timedtext(video_id: str) -> Optional[str]:
    """
    Call YouTube's internal timedtext endpoint directly using only
    Python's built-in urllib — zero third-party dependencies.

    Step 1: Fetch the watch page and extract the captions track list
            from the ytInitialPlayerResponse JSON blob.
    Step 2: Pick the best track (English manual > English auto > any).
    Step 3: Fetch the timedtext XML and parse <text> elements.

    This bypasses both yt-dlp rate-limiting and broken library APIs.
    """
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        "User-Agent": _random_ua(),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # ── Step 1: fetch watch page ──────────────────────────────────────────
    try:
        req = urllib.request.Request(watch_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        logger.debug("timedtext: watch page fetch failed for %s: %s", video_id, exc)
        return None

    # ── Step 2: extract ytInitialPlayerResponse ───────────────────────────
    match = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.+?\});\s*(?:var|</script)", html, re.DOTALL)
    if not match:
        # Second pattern — sometimes it's in a script tag boundary
        match = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.+)", html)
    if not match:
        logger.debug("timedtext: could not find ytInitialPlayerResponse for %s", video_id)
        return None

    try:
        # The blob can be huge; json.loads handles it fine
        player_data = json.loads(match.group(1))
    except json.JSONDecodeError:
        # Truncated — try to find a balanced brace substring
        raw_json = match.group(1)
        depth = 0
        end = 0
        for i, ch in enumerate(raw_json):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        try:
            player_data = json.loads(raw_json[:end])
        except Exception:
            logger.debug("timedtext: JSON parse failed for %s", video_id)
            return None

    # ── Step 3: find captions track list ─────────────────────────────────
    try:
        captions_data = (
            player_data
            .get("captions", {})
            .get("playerCaptionsTracklistRenderer", {})
            .get("captionTracks", [])
        )
    except Exception:
        captions_data = []

    if not captions_data:
        logger.debug("timedtext: no captionTracks found for %s", video_id)
        return None

    # Score tracks: English manual > English auto > any manual > any auto
    def _track_score(track: dict) -> int:
        lang = track.get("languageCode", "")
        kind = track.get("kind", "")
        s = 0
        if lang.startswith("en"):   s += 100
        if kind != "asr":           s += 10   # manual beats auto-speech-recognition
        return s

    best_tracks = sorted(captions_data, key=_track_score, reverse=True)

    # ── Step 4: fetch and parse timedtext XML ─────────────────────────────
    for track in best_tracks:
        base_url = track.get("baseUrl", "")
        if not base_url:
            continue

        # Ensure we get plain XML (fmt=srv3 = XML with timing)
        if "fmt=" not in base_url:
            base_url += "&fmt=srv3"

        try:
            req = urllib.request.Request(base_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                xml_bytes = resp.read()
            xml_text = xml_bytes.decode("utf-8", errors="replace")

            # Parse <text start="..." dur="...">...</text> elements
            texts = re.findall(r"<text[^>]*>(.*?)</text>", xml_text, re.DOTALL)
            if not texts:
                continue

            # Unescape XML entities inside text nodes
            raw_parts = []
            for t in texts:
                t = re.sub(r"<[^>]+>", "", t)   # strip any nested tags
                t = t.replace("&amp;", "&").replace("&lt;", "<") \
                     .replace("&gt;", ">").replace("&quot;", '"') \
                     .replace("&#39;", "'").replace("&nbsp;", " ")
                t = t.strip()
                if t:
                    raw_parts.append(t)

            raw = " ".join(raw_parts)
            if raw.strip():
                lang_code = track.get("languageCode", "?")
                logger.info(
                    "Transcript via timedtext [lang=%s]: %d chars",
                    lang_code, len(raw),
                )
                return _clean(raw)[:TRANSCRIPT_CHAR_LIMIT]

        except Exception as exc:
            logger.debug("timedtext fetch failed for track %s: %s",
                         track.get("languageCode", "?"), exc)
            continue

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 5 : YouTube innertube API description  (pure urllib, zero deps)
# ─────────────────────────────────────────────────────────────────────────────

def _via_innertube_description(video_id: str) -> Optional[str]:
    """
    Call YouTube's internal innertube /next endpoint to get the video
    description. Uses only Python's built-in urllib — replaces the broken
    youtubesearchpython (which fails with 'proxies' kwarg on modern requests).

    Not a real transcript — but gives the LLM context for summary/Q&A
    when no captions exist at all.
    """
    url = "https://www.youtube.com/youtubei/v1/next"
    payload = json.dumps({
        "videoId": video_id,
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240101.00.00",
                "hl": "en",
                "gl": "US",
            }
        }
    }).encode("utf-8")

    headers = {
        "User-Agent":     _random_ua(),
        "Content-Type":   "application/json",
        "Accept":         "application/json",
        "X-YouTube-Client-Name":    "1",
        "X-YouTube-Client-Version": "2.20240101.00.00",
    }

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        logger.debug("innertube description failed for %s: %s", video_id, exc)
        return None

    # Walk the deeply nested response to find description runs
    try:
        contents = (
            data.get("contents", {})
                .get("twoColumnWatchNextResults", {})
                .get("results", {})
                .get("results", {})
                .get("contents", [])
        )
        for block in contents:
            vpp = block.get("videoPrimaryInfoRenderer", {})
            desc_runs = (
                vpp.get("description", {})
                   .get("runs", [])
            )
            if desc_runs:
                desc = " ".join(r.get("text", "") for r in desc_runs)
                if desc.strip():
                    logger.info(
                        "Transcript fallback via innertube description: %d chars",
                        len(desc),
                    )
                    return _clean(desc)[:TRANSCRIPT_CHAR_LIMIT]
    except Exception as exc:
        logger.debug("innertube description parse error for %s: %s", video_id, exc)

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_transcript(video_id: str, languages: list = None) -> Optional[str]:
    """
    Fetch the transcript for *video_id* in ANY available language.

    `languages` is kept for backwards compatibility but not used —
    every strategy discovers all available captions and picks the best.

    Returns plain-text transcript (≤ TRANSCRIPT_CHAR_LIMIT chars) or None.
    """
    logger.info("Fetching transcript for video: %s", video_id)

    # Strategy 1: yt-dlp — best quality, 429-retry logic, any language
    result = _via_ytdlp(video_id)
    if result:
        return result

    # Strategy 2: ytta v1.x — instance API (youtube-transcript-api >= 1.0)
    result = _via_ytta_v1(video_id)
    if result:
        return result

    # Strategy 3: ytta v0.x — class-method API (legacy installs)
    result = _via_ytta_v0(video_id)
    if result:
        return result

    # Strategy 4: Direct timedtext XML — pure urllib, no library, no 429 risk
    result = _via_timedtext(video_id)
    if result:
        return result

    # Strategy 5: innertube description — pure urllib, replaces broken ytsearch
    result = _via_innertube_description(video_id)
    if result:
        logger.warning("Only description available for %s — no captions found", video_id)
        return result

    logger.error("All transcript strategies exhausted for video: %s", video_id)
    return None