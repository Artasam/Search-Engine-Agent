"""
ui/theme.py
-----------
Premium dark AI-assistant theme.
Cyan / neon accent palette with glow effects, glassmorphism cards,
animated borders, and polished hover states.
"""

import streamlit as st


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

/* HIDE STREAMLIT CHROME */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
button[data-testid="baseButton-header"],
section[data-testid="stSidebar"] > div > div > button,
.st-emotion-cache-1rtdyuf,
.st-emotion-cache-pkbazv,
#MainMenu,
header[data-testid="stHeader"],
footer { display: none !important; }

/* DESIGN TOKENS */
:root {
  --bg:           #080b12;
  --bg2:          #0d1117;
  --surface:      #0f1520;
  --surface2:     #141c2e;
  --border:       #1e2d45;
  --cyan:         #00e5ff;
  --cyan-dim:     #00e5ff18;
  --cyan-mid:     #00e5ff55;
  --cyan-glow:    0 0 12px #00e5ff55, 0 0 30px #00e5ff22;
  --cyan-glow-sm: 0 0 8px #00e5ff44;
  --purple:       #7c6af7;
  --purple-dim:   #7c6af720;
  --text:         #dceeff;
  --text-muted:   #4a6080;
  --text-dim:     #2a4060;
  --radius-sm:    8px;
  --radius:       12px;
  --radius-lg:    16px;
  --font:         'Inter', sans-serif;
  --mono:         'JetBrains Mono', monospace;
  --ease:         all 0.2s cubic-bezier(0.4,0,0.2,1);
}

/* GLOBAL */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main .block-container {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: var(--font) !important;
}
.main .block-container {
  padding-top: 2rem !important;
  padding-bottom: 4rem !important;
  max-width: 880px !important;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
  box-shadow: 4px 0 32px #00000077 !important;
}
[data-testid="stSidebar"] > div { padding: 1.5rem 1rem !important; }
[data-testid="stSidebar"] * { font-family: var(--font) !important; }
[data-testid="stSidebar"] .stMarkdown strong {
  color: var(--text-muted) !important;
  font-size: 10px !important;
  font-family: var(--mono) !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
}

/* TITLE */
[data-testid="stMarkdownContainer"] h1, h1 {
  font-family: var(--font) !important;
  font-weight: 600 !important;
  font-size: 1.9rem !important;
  color: var(--text) !important;
  letter-spacing: -0.02em !important;
}

/* CHAT MESSAGES */
[data-testid="stChatMessage"] {
  border-radius: var(--radius) !important;
  border: 1px solid var(--border) !important;
  padding: 16px 20px !important;
  margin-bottom: 12px !important;
  transition: var(--ease) !important;
  position: relative !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
  background: linear-gradient(135deg, #12162a, #0f1420) !important;
  border-left: 3px solid var(--purple) !important;
  box-shadow: inset 0 0 30px var(--purple-dim), 0 2px 12px #00000044 !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
  background: linear-gradient(135deg, #081520, #0a1218) !important;
  border-left: 3px solid var(--cyan) !important;
  box-shadow: inset 0 0 30px var(--cyan-dim), 0 2px 12px #00000044 !important;
}
[data-testid="stChatMessage"]:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 24px #00000055 !important;
}

/* CHAT INPUT */
[data-testid="stChatInput"] {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  transition: var(--ease) !important;
}
[data-testid="stChatInput"]:focus-within {
  border-color: var(--cyan) !important;
  box-shadow: var(--cyan-glow-sm) !important;
}
[data-testid="stChatInput"] textarea {
  background: transparent !important;
  border: none !important;
  color: var(--text) !important;
  font-family: var(--mono) !important;
  font-size: 14px !important;
  caret-color: var(--cyan) !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--text-muted) !important; }

/* BUTTONS */
.stButton > button {
  background: transparent !important;
  border: 1px solid var(--border) !important;
  color: var(--text-muted) !important;
  border-radius: var(--radius-sm) !important;
  font-family: var(--mono) !important;
  font-size: 11px !important;
  letter-spacing: 0.05em !important;
  transition: var(--ease) !important;
}
.stButton > button:hover {
  background: var(--cyan-dim) !important;
  border-color: var(--cyan) !important;
  color: var(--cyan) !important;
  box-shadow: var(--cyan-glow-sm) !important;
  transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* DOWNLOAD BUTTONS */
[data-testid="stDownloadButton"] > button {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-muted) !important;
  border-radius: var(--radius-sm) !important;
  font-family: var(--mono) !important;
  font-size: 11px !important;
  transition: var(--ease) !important;
}
[data-testid="stDownloadButton"] > button:hover {
  border-color: var(--cyan) !important;
  color: var(--cyan) !important;
  background: var(--cyan-dim) !important;
  box-shadow: var(--cyan-glow-sm) !important;
}

/* METRIC CARDS */
[data-testid="stMetric"] {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  padding: 14px 18px !important;
  transition: var(--ease) !important;
  position: relative !important;
  overflow: hidden !important;
}
[data-testid="stMetric"]::before {
  content: '';
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 2px;
  background: linear-gradient(90deg, var(--cyan), var(--purple));
  opacity: 0.8;
}
[data-testid="stMetric"]:hover {
  border-color: var(--cyan-mid) !important;
  box-shadow: var(--cyan-glow-sm) !important;
}
[data-testid="stMetricLabel"] {
  color: var(--text-muted) !important;
  font-size: 10px !important;
  font-family: var(--mono) !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
  color: var(--cyan) !important;
  font-family: var(--mono) !important;
  font-size: 1.5rem !important;
  font-weight: 600 !important;
}

/* SELECTBOX */
[data-baseweb="select"] > div {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text) !important;
  transition: var(--ease) !important;
}
[data-baseweb="select"] > div:hover { border-color: var(--cyan-mid) !important; }
[data-baseweb="popover"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
}

/* TEXT INPUT */
[data-testid="stTextInput"] input {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text) !important;
  font-family: var(--mono) !important;
  font-size: 13px !important;
  transition: var(--ease) !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: var(--cyan) !important;
  box-shadow: var(--cyan-glow-sm) !important;
}

/* SLIDER */
[data-testid="stSlider"] div[role="slider"] {
  background: var(--cyan) !important;
  box-shadow: var(--cyan-glow-sm) !important;
}

/* CHECKBOX */
[data-testid="stCheckbox"] label {
  color: var(--text-muted) !important;
  font-size: 13px !important;
  transition: var(--ease) !important;
}
[data-testid="stCheckbox"] label:hover { color: var(--cyan) !important; }

/* PROGRESS */
[data-testid="stProgressBar"] > div {
  background: var(--surface2) !important;
  border-radius: 99px !important;
}
[data-testid="stProgressBar"] > div > div {
  background: linear-gradient(90deg, var(--cyan), var(--purple)) !important;
  border-radius: 99px !important;
}

/* HR DIVIDER */
hr {
  border: none !important;
  border-top: 1px solid var(--border) !important;
  margin: 1.5rem 0 !important;
}

/* CODE */
code {
  font-family: var(--mono) !important;
  font-size: 12px !important;
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px !important;
  padding: 1px 6px !important;
  color: var(--cyan) !important;
}
pre {
  font-family: var(--mono) !important;
  font-size: 12px !important;
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  padding: 14px !important;
}

/* CAPTION */
[data-testid="stCaptionContainer"] {
  color: var(--text-muted) !important;
  font-size: 11px !important;
  font-family: var(--mono) !important;
}

/* CUSTOM CLASSES */
.brand-header {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-dim);
  letter-spacing: 0.2em;
  text-transform: uppercase;
  border-bottom: 1px solid var(--border);
  padding-bottom: 10px;
  margin-bottom: 6px;
}
.accent  { color: var(--cyan); }
.accent2 { color: var(--purple); }

.tool-badge {
  display: inline-flex;
  align-items: center;
  background: var(--cyan-dim);
  border: 1px solid var(--cyan-mid);
  color: var(--cyan);
  border-radius: 99px;
  padding: 2px 10px;
  font-size: 10px;
  font-family: var(--mono);
  margin-right: 4px;
  letter-spacing: 0.04em;
}

.msg-ts {
  font-size: 10px;
  color: var(--text-dim);
  font-family: var(--mono);
  margin-top: 8px;
}

.status-dot {
  display: inline-block;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--cyan);
  box-shadow: 0 0 6px var(--cyan);
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%,100% { opacity: 1; }
  50%      { opacity: 0.3; }
}

/* SCROLLBAR */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: var(--cyan-mid); }

/* SELECTION */
::selection { background: var(--cyan-mid); color: var(--bg); }

/* YOUTUBE LEARNING PANEL */
.yt-panel-header {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
}
.yt-badge {
  background: linear-gradient(90deg, #ff000022, #ff000011);
  border: 1px solid #ff000055;
  color: #ff6060;
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.15em;
  padding: 4px 14px;
  border-radius: 99px;
}
.yt-embed-wrapper {
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid var(--border);
  box-shadow: 0 4px 24px #00000077;
  background: #000;
}
.yt-embed-wrapper iframe {
  display: block;
  border-radius: var(--radius);
}
.yt-open-link {
  display: inline-block;
  margin-top: 8px;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--text-muted);
  text-decoration: none;
  letter-spacing: 0.05em;
  transition: var(--ease);
}
.yt-open-link:hover { color: var(--cyan); }

.yt-meta { margin-bottom: 12px; }
.yt-title {
  font-family: var(--font);
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.4;
  margin-bottom: 4px;
}
.yt-channel {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--cyan);
  letter-spacing: 0.05em;
}
.yt-qa-header {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
  border-top: 1px solid var(--border);
  padding-top: 1rem;
  margin: 1.2rem 0 0.8rem;
}
</style>
"""


def apply_theme() -> None:
    """Inject the full CSS theme. Call once at startup before any other st call."""
    st.markdown(_CSS, unsafe_allow_html=True)