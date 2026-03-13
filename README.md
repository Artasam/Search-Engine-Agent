# 🔍 Search-Engine-Agent

<div align="center">

**A premium AI research assistant that searches the web, explains topics, and teaches through YouTube — powered by Groq LLMs and LangChain agents.**

[![Streamlit](https://img.shields.io/badge/Streamlit-1.55-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![LangChain](https://img.shields.io/badge/LangChain-1.2-1C3C3C?style=flat&logo=chainlink&logoColor=white)](https://langchain.com)
[![Groq](https://img.shields.io/badge/Groq-LLM-F55036?style=flat)](https://groq.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://search-engine-agent-ak.streamlit.app)

</div>

> 🌐 **Live App:** [search-engine-agent-ak.streamlit.app](https://search-engine-agent-ak.streamlit.app)

---

## ✨ What It Does

Ask any question → the agent searches the web, Wikipedia, and Arxiv to give you a grounded answer — then automatically finds a relevant YouTube video, embeds it, generates an AI summary, and lets you ask follow-up questions about the video content. All inside one sleek dark-themed interface.

```
Your Question
    │
    ├─► AI Agent  ──► DuckDuckGo · Wikipedia · Arxiv  ──► Text Answer
    │
    └─► YouTube Search  ──► Embed Video
                               │
                               ├─► Transcript Extraction (5-strategy fallback)
                               ├─► AI-Generated Summary
                               └─► Video Q&A Chat
```

---

## 🚀 Features

### 🤖 AI Research Agent
| Feature | Details |
|---|---|
| **Multi-source search** | DuckDuckGo (live web), Wikipedia, Arxiv — all togglable per session |
| **4 Groq LLMs** | Llama 3.1 8B · Llama 3.3 70B · Llama 4 Scout 17B · Qwen3 32B |
| **ReAct agent loop** | LangGraph `create_react_agent` with up to 6 reasoning iterations |
| **Temperature control** | Fine-tune creativity vs. determinism via sidebar slider |
| **Session analytics** | Query count, avg latency, tool usage frequency in real time |
| **Chat export** | Download full history as JSON or Markdown |
| **Tool selection** | Enable/disable any tool without restarting |

### 🎬 YouTube Learning Mode
| Feature | Details |
|---|---|
| **Auto video search** | Finds the most relevant YouTube video for every query automatically |
| **Embedded player** | Watch directly in the app — no tab switching |
| **Transcript extraction** | 5-strategy fallback: yt-dlp → ytta v1 → ytta v0 → timedtext XML → innertube API |
| **Any language** | Works on English, Hindi, Urdu, Spanish, Arabic and more — AI always responds in English |
| **AI-generated summary** | Structured Overview / Key Points / Conclusion in under 60 seconds |
| **Video Q&A chat** | Ask follow-up questions answered from the transcript with full conversation memory |
| **Token-safe summarisation** | Per-model TPM budget, smart head+tail truncation, auto-retry on 413 |

### 🎨 UI & Theme
- Premium dark theme with **cyan / neon accent** palette
- Glow effects, glassmorphism cards, animated status dot
- `Inter` + `JetBrains Mono` typography
- Prominent AI summary card with cyan border and glow
- Thin 4px custom scrollbar with hover effect

---

## 🗂 Project Structure

```
Search-Engine-Agent/
│
├── main.py                      # Entry point — orchestration only
│
├── config/
│   ├── __init__.py
│   └── settings.py              # All constants, model catalogue, TPM budgets
│
├── tools/
│   ├── __init__.py
│   ├── arxiv_tool.py            # ArxivQueryRun wrapper
│   ├── wikipedia_tool.py        # WikipediaQueryRun wrapper
│   ├── duckduckgo_tool.py       # DuckDuckGoSearchRun wrapper
│   └── tool_registry.py        # Central registry — get_tools(names)
│
├── agents/
│   ├── __init__.py
│   ├── agent_factory.py         # build_agent() via LangGraph create_react_agent
│   └── search_agent.py         # run_agent() → structured result dict
│
├── youtube/                     # YouTube Learning Mode package
│   ├── __init__.py
│   ├── searcher.py              # 4-strategy YouTube search (no API key needed)
│   ├── transcript.py           # 5-strategy transcript extraction, any language
│   └── summarizer.py           # AI summary + video Q&A with token budgeting
│
├── utils/
│   ├── __init__.py
│   ├── logger.py               # Consistent logging across all modules
│   ├── history_manager.py      # Session-state chat CRUD + export
│   └── token_counter.py        # Lightweight token estimator
│
├── ui/
│   ├── __init__.py
│   ├── theme.py                # Full CSS injection — cyan/neon dark theme
│   ├── sidebar.py              # Settings, stats, YouTube toggle, export
│   ├── chat_interface.py       # Message rendering + main chat input
│   ├── metrics_panel.py        # Top metrics bar
│   └── youtube_panel.py        # Embedded video, summary card, Q&A chat
│
├── .streamlit/
│   ├── config.toml             # Dark base theme, minimal toolbar
│   └── secrets.toml            # GROQ_API_KEY (never commit)
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-username/search-engine-agent.git
cd search-engine-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Groq API key
cp .env.example .env
# Edit .env → GROQ_API_KEY=gsk_...

# 4. Run
streamlit run main.py
```

Get a **free** Groq API key at [console.groq.com](https://console.groq.com).

### Streamlit Cloud Deployment

1. Push your repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Add your key under **App settings → Secrets**:
   ```toml
   GROQ_API_KEY = "gsk_..."
   ```

---

## 🤖 Supported Models

| Model | TPM Limit | Safe Input | Best For |
|---|---|---|---|
| `llama-3.1-8b-instant` | 6,000 | 3,300 tokens | Speed, chat, quick summaries |
| `llama-3.3-70b-versatile` | 6,000 | 3,300 tokens | Deep reasoning, research, agents |
| `meta-llama/llama-4-scout-17b-16e-instruct` | 30,000 | 16,500 tokens | Long context, multilingual, transcripts |
| `qwen/qwen3-32b` | 6,000 | 3,300 tokens | Math, coding, structured reasoning |

> **Tip:** Use **Llama 4 Scout** when summarising long video transcripts — its 30K TPM limit handles them without truncation.

---

## 🎬 YouTube Transcript Extraction — Strategy Chain

The transcript system tries 5 strategies in order, stopping at the first success:

```
1. yt-dlp            subtitleslangs=["all"], json3/vtt, 429 retry + back-off
2. ytta v1.x         YouTubeTranscriptApi().list() — instance API (2024+)
3. ytta v0.x         YouTubeTranscriptApi.list_transcripts() — legacy API
4. timedtext XML     Direct YouTube timedtext endpoint via built-in urllib only
5. innertube API     YouTube's internal /youtubei/v1/next — description fallback
```

All languages are supported. The LLM always responds in English regardless of transcript language.

---

## 📦 Dependencies

```
streamlit              # UI framework
langchain              # Agent orchestration
langchain-groq         # Groq LLM integration
langchain-community    # Tool wrappers
langgraph              # ReAct agent runtime
python-dotenv          # .env loading

ddgs                   # DuckDuckGo search
arxiv                  # Arxiv paper search
wikipedia              # Wikipedia API wrapper

yt-dlp                 # Primary transcript extraction
youtube-transcript-api # Secondary transcript extraction (v0.x + v1.x)
youtube-search-python  # YouTube search fallback

pandas
plotly
```

---

## 🔧 Configuration

All tuneable values live in **`config/settings.py`** — never scattered:

```python
ARXIV_TOP_K          = 3      # results per Arxiv query
WIKIPEDIA_TOP_K      = 2      # results per Wikipedia query
MAX_ITERATIONS       = 6      # ReAct loop limit
MAX_EXECUTION_TIME   = 60     # seconds before agent timeout
MAX_HISTORY_MESSAGES = 50     # rolling chat window in session
```

---

## 🧩 Adding a New Search Tool

1. Create `tools/my_tool.py` with a `build_my_tool() -> BaseTool` function.
2. Register it in `tools/tool_registry.py`:
   ```python
   from .my_tool import build_my_tool
   _TOOL_FACTORIES["🆕 My Tool"] = build_my_tool
   ```
The sidebar picks it up automatically — no other changes needed.

---

## 🔑 API Key Resolution Order

```
1. Sidebar text input    — typed by user at runtime
2. st.secrets            — Streamlit Cloud → App settings → Secrets
3. Environment variable  — local .env file or shell export
```

---

## 📄 License

MIT — use freely, attribution appreciated.