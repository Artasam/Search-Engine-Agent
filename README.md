# 🧠 Search-Engine-Agent

> A multi-source AI research assistant built with **Groq LLMs**, **LangChain Agents**, and **Streamlit**.  
> Ask anything — the agent searches the live web, Wikipedia, and Arxiv in real time and reasons through the results before answering.

---

## 📸 Features

- 🌐 **Multi-source search** — DuckDuckGo (live web), Wikipedia, Arxiv — all togglable
- 🤖 **4 Groq models** — Llama 3 (8B / 70B), Mixtral 8×7B, Gemma 2 — switchable mid-session
- 💭 **Live agent thoughts** — watch every reasoning step stream in real time
- 📊 **Session analytics** — query count, avg latency, per-tool usage frequency
- 🔤 **Token estimation** — live ~token counter shown in sidebar and metrics bar
- 💾 **Chat export** — download full conversation as JSON or Markdown
- 🎛️ **Temperature control** — tune creativity vs determinism via a sidebar slider
- 🔑 **3-tier API key fallback** — sidebar input → `st.secrets` → environment variable
- 🎨 **Premium dark UI** — JetBrains Mono + neon-green terminal aesthetic

---

## 🗂 Project Structure

```
Search-Engine-Agent/
│
├── main.py                     ← Entry point, runs the app
├── requirements.txt            ← All dependencies
├── .env.example                ← API key template
├── .gitignore                  ← Keeps secrets out of git
├── README.md                   ← You are here
│
├── .streamlit/
│   ├── secrets.toml            ← API key for Streamlit Cloud (never commit)
│   └── config.toml             ← Dark theme + server settings
│
├── config/
│   ├── __init__.py
│   └── settings.py             ← All constants, model catalogue, defaults
│
├── tools/
│   ├── __init__.py
│   ├── arxiv_tool.py           ← Arxiv search tool factory
│   ├── wikipedia_tool.py       ← Wikipedia search tool factory
│   ├── duckduckgo_tool.py      ← DuckDuckGo search tool factory
│   └── tool_registry.py        ← Central registry → get_tools(names)
│
├── agents/
│   ├── __init__.py
│   ├── agent_factory.py        ← Builds the LangChain agent
│   └── search_agent.py         ← Runs the agent, returns structured result
│
├── utils/
│   ├── __init__.py
│   ├── logger.py               ← Consistent logging across modules
│   ├── history_manager.py      ← Chat history CRUD + export helpers
│   └── token_counter.py        ← Lightweight token estimator
│
└── ui/
    ├── __init__.py
    ├── theme.py                ← Custom CSS injection
    ├── sidebar.py              ← Settings, stats, export buttons
    ├── chat_interface.py       ← Message rendering + chat input
    └── metrics_panel.py        ← Top metrics bar
```

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/Search-Engine-Agent.git
cd Search-Engine-Agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your API key

```bash
cp .env.example .env
```

Open `.env` and add your key:

```
GROQ_API_KEY=gsk_your_key_here
```

> Get a **free** Groq API key at [console.groq.com](https://console.groq.com)

### 4. Run the app

```bash
streamlit run main.py
```

---

## ☁️ Deploy on Streamlit Cloud

1. Push your repo to GitHub — `.gitignore` ensures secrets are never committed
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your repo and set `main.py` as the entry point
4. Go to **App settings → Secrets** and paste:

```toml
GROQ_API_KEY = "gsk_your_key_here"
```

5. Click **Deploy** — no sidebar input needed, key is injected automatically

---

## 🔑 API Key Resolution Order

The app finds your key automatically using this priority chain:

```
1. Sidebar text input     (typed by user at runtime)
        ↓
2. st.secrets             (Streamlit Cloud → secrets.toml)
        ↓
3. Environment variable   (local .env file)
```

---

## 🤖 Supported Models

| Model | Context Window | Best For |
|-------|---------------|----------|
| Llama 3 · 8B | 8k tokens | Speed, quick summaries |
| Llama 3 · 70B | 8k tokens | Deep reasoning, research |
| Mixtral 8×7B | 32k tokens | Long documents, coding |
| Gemma 2 · 9B | 8k tokens | Instruction following |

---

## 🛠 Adding a New Tool

1. Create `tools/my_tool.py` with a factory function:

```python
from langchain.tools import BaseTool

def build_my_tool() -> BaseTool:
    ...
```

2. Register it in `tools/tool_registry.py`:

```python
from .my_tool import build_my_tool

_TOOL_FACTORIES["🆕 My Tool"] = build_my_tool
```

The sidebar picks it up automatically — no other changes needed.

---

## ⚙️ Configuration

All tuneable values live in `config/settings.py`:

```python
ARXIV_TOP_K          = 3    # results per Arxiv query
WIKIPEDIA_TOP_K      = 2    # results per Wikipedia query
MAX_ITERATIONS       = 6    # agent ReAct loop limit
MAX_EXECUTION_TIME   = 60   # seconds before timeout
MAX_HISTORY_MESSAGES = 50   # rolling window kept in session
```

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM Provider | [Groq](https://groq.com) |
| Agent Framework | [LangChain](https://langchain.com) |
| UI | [Streamlit](https://streamlit.io) |
| Web Search | DuckDuckGo Search |
| Knowledge Search | Wikipedia API |
| Research Search | Arxiv API |

---

## 📄 License

MIT — free to use, modify, and distribute. Attribution appreciated.