"""
ui/youtube_panel.py
-------------------
Renders the full YouTube Learning Panel:
  1. Video embed (iframe)
  2. AI-generated summary (collapsible)
  3. Dedicated Q&A chat about the video

This panel is shown below the main chat whenever a video is loaded
into st.session_state["yt_video"].
"""

import streamlit as st
from typing import Optional

from youtube import (
    VideoResult, get_transcript,
    summarize_transcript, answer_video_question,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Session state keys
_KEY_VIDEO      = "yt_video"         # VideoResult | None
_KEY_TRANSCRIPT = "yt_transcript"    # str | None
_KEY_SUMMARY    = "yt_summary"       # str | None
_KEY_QA_HISTORY = "yt_qa_history"    # list[dict]
_KEY_LOADING    = "yt_loading"       # bool


def init_youtube_state() -> None:
    """Initialise all YouTube session state keys."""
    defaults = {
        _KEY_VIDEO:      None,
        _KEY_TRANSCRIPT: None,
        _KEY_SUMMARY:    None,
        _KEY_QA_HISTORY: [],
        _KEY_LOADING:    False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def set_video(video: VideoResult) -> None:
    """Load a new video — clears transcript/summary/Q&A history."""
    st.session_state[_KEY_VIDEO]      = video
    st.session_state[_KEY_TRANSCRIPT] = None
    st.session_state[_KEY_SUMMARY]    = None
    st.session_state[_KEY_QA_HISTORY] = []


def clear_video() -> None:
    """Remove the current video and reset all related state."""
    for k in (_KEY_VIDEO, _KEY_TRANSCRIPT, _KEY_SUMMARY):
        st.session_state[k] = None
    st.session_state[_KEY_QA_HISTORY] = []


def get_active_video() -> Optional[VideoResult]:
    return st.session_state.get(_KEY_VIDEO)


def render_youtube_panel(api_key: str, model_id: str) -> None:
    """
    Render the full YouTube Learning Panel.
    Call this from main.py after render_messages().
    Does nothing if no video is currently loaded.
    """
    video: Optional[VideoResult] = st.session_state.get(_KEY_VIDEO)
    if video is None:
        return

    st.markdown("---")

    # ── Panel header ─────────────────────────────────────────────────────────
    st.markdown(
        '<div class="yt-panel-header">'
        '<span class="yt-badge">▶ YOUTUBE LEARNING MODE</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    col_video, col_info = st.columns([3, 2], gap="large")

    with col_video:
        # ── Embedded video ────────────────────────────────────────────────────
        st.markdown(
            f'<div class="yt-embed-wrapper">'
            f'<iframe src="{video.embed_url}" '
            f'width="100%" height="315" frameborder="0" '
            f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
            f'gyroscope; picture-in-picture" allowfullscreen>'
            f'</iframe></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<a href="{video.watch_url}" target="_blank" class="yt-open-link">'
            f'↗ Open on YouTube</a>',
            unsafe_allow_html=True,
        )

    with col_info:
        # ── Video metadata ────────────────────────────────────────────────────
        st.markdown(
            f'<div class="yt-meta">'
            f'<div class="yt-title">{video.title}</div>'
            f'{"<div class=yt-channel>" + video.channel + "</div>" if video.channel else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )

        if video.description:
            st.caption(video.description[:200] + "…" if len(video.description) > 200 else video.description)

        # ── Load transcript + summary buttons ────────────────────────────────
        transcript = st.session_state.get(_KEY_TRANSCRIPT)

        if transcript is None:
            if st.button("📄 Load Transcript & Generate Summary", use_container_width=True, key="yt_load_btn"):
                with st.spinner("Fetching transcript…"):
                    transcript = get_transcript(video.video_id)
                    st.session_state[_KEY_TRANSCRIPT] = transcript

                if transcript:
                    with st.spinner("Generating AI summary…"):
                        summary = summarize_transcript(
                            transcript  = transcript,
                            video_title = video.title,
                            api_key     = api_key,
                            model_id    = model_id,
                        )
                        st.session_state[_KEY_SUMMARY] = summary
                    st.rerun()
                else:
                    st.warning("⚠️ No transcript available for this video.")

        else:
            st.success("✅ Transcript loaded", icon="📄")

        # Clear video button
        if st.button("✕ Close Video", use_container_width=True, key="yt_close_btn"):
            clear_video()
            st.rerun()

    # ── AI Summary  ── prominent card, always above Q&A ──────────────────────
    summary = st.session_state.get(_KEY_SUMMARY)
    if summary:
        st.markdown(
            '<div class="yt-summary-card">'
            '<div class="yt-summary-title">🤖 AI-Generated Summary</div>'
            '<div class="yt-summary-body">'
            + summary.replace("\n", "<br>") +
            '</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # ── Video Q&A Chat ── below summary ───────────────────────────────────────
    transcript = st.session_state.get(_KEY_TRANSCRIPT)
    if transcript:
        st.markdown(
            '<div class="yt-qa-header">💬 Ask About This Video</div>',
            unsafe_allow_html=True,
        )

        # Show Q&A history
        qa_history = st.session_state.get(_KEY_QA_HISTORY, [])
        for msg in qa_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # ── Inline input row ──────────────────────────────────────────────────
        q_col, btn_col = st.columns([5, 1], gap="small")
        with q_col:
            qa_prompt = st.text_input(
                label            = "video_question",
                placeholder      = "Ask a question about this video…",
                label_visibility = "collapsed",
                key              = "yt_qa_input",
            )
        with btn_col:
            ask_clicked = st.button("Ask ↵", key="yt_ask_btn", use_container_width=True)

        if ask_clicked and qa_prompt and qa_prompt.strip():
            with st.chat_message("user"):
                st.markdown(qa_prompt)
            qa_history.append({"role": "user", "content": qa_prompt})

            with st.chat_message("assistant"):
                with st.spinner("Analysing video content…"):
                    answer = answer_video_question(
                        question     = qa_prompt,
                        transcript   = transcript,
                        video_title  = video.title,
                        api_key      = api_key,
                        model_id     = model_id,
                        chat_history = qa_history[:-1],
                    )
                st.markdown(answer)

            qa_history.append({"role": "assistant", "content": answer})
            st.session_state[_KEY_QA_HISTORY] = qa_history
            st.rerun()

        if qa_history:
            if st.button("🗑 Clear Q&A History", key="yt_clear_qa"):
                st.session_state[_KEY_QA_HISTORY] = []
                st.rerun()