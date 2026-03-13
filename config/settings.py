"""
config/settings.py
------------------
Centralised, single-source-of-truth for every tuneable parameter.
Import from here everywhere; never hard-code values in other modules.
"""

from dataclasses import dataclass, field
from typing import List


# ── App metadata ─────────────────────────────────────────────────────────────
APP_TITLE    = "Search-Engine-Agent"
APP_SUBTITLE = "Multi-source AI research assistant powered by Groq + LangChain"
APP_VERSION  = "2.0.0"
APP_ICON     = "🔍"
APP_LAYOUT   = "wide"

# ── Tool defaults ─────────────────────────────────────────────────────────────
ARXIV_TOP_K         = 3
ARXIV_CHARS_MAX     = 500
WIKIPEDIA_TOP_K     = 2
WIKIPEDIA_CHARS_MAX = 500

# ── Agent ─────────────────────────────────────────────────────────────────────
MAX_ITERATIONS     = 6
MAX_EXECUTION_TIME = 60   # seconds

# ── Chat history ──────────────────────────────────────────────────────────────
MAX_HISTORY_MESSAGES = 50
DEFAULT_SYSTEM_MSG   = (
    "Hi! I'm your AI research assistant. I can search the web, Wikipedia, "
    "and Arxiv to answer your questions. What would you like to explore?"
)

# ── Model catalogue ───────────────────────────────────────────────────────────
# TPM limits are Groq free-tier on_demand values (as of 2025-2026).
# tpm_limit  : tokens-per-minute cap enforced by Groq
# safe_input_tokens : conservative budget we send per request
#   = tpm_limit * 0.55  (leaves 45 % headroom for system prompt +
#     response tokens + any burst the LLM uses for reasoning)
#
# Source: https://console.groq.com/settings/limits
@dataclass
class ModelInfo:
    id:               str
    label:            str
    context_k:        int              # context window (thousands of tokens)
    tpm_limit:        int              # Groq free-tier TPM cap
    safe_input_tokens: int             # max input tokens we budget per call
    best_for:         List[str] = field(default_factory=list)


GROQ_MODELS: List[ModelInfo] = [
    # llama-3.1-8b-instant  — TPM 6 000  (tightest limit)
    ModelInfo(
        id                = "llama-3.1-8b-instant",
        label             = "Llama 3.1 · 8B  (fastest)",
        context_k         = 128,
        tpm_limit         = 6_000,
        safe_input_tokens = 3_300,    # 6000 * 0.55
        best_for          = ["Speed", "Chat"],
    ),
    # llama-3.3-70b-versatile — TPM 6 000
    ModelInfo(
        id                = "llama-3.3-70b-versatile",
        label             = "Llama 3.3 · 70B (best)",
        context_k         = 128,
        tpm_limit         = 6_000,
        safe_input_tokens = 3_300,
        best_for          = ["Reasoning", "Research", "Agents"],
    ),
    # llama-4-scout — TPM 30 000
    ModelInfo(
        id                = "meta-llama/llama-4-scout-17b-16e-instruct",
        label             = "Llama 4 Scout · 17B (preview)",
        context_k         = 128,
        tpm_limit         = 30_000,
        safe_input_tokens = 16_500,   # 30000 * 0.55
        best_for          = ["Multimodal", "Long ctx"],
    ),
    # qwen3-32b — TPM 6 000
    ModelInfo(
        id                = "qwen/qwen3-32b",
        label             = "Qwen 3 · 32B (reasoning)",
        context_k         = 128,
        tpm_limit         = 6_000,
        safe_input_tokens = 3_300,
        best_for          = ["Math", "Coding", "Reasoning"],
    ),
]

DEFAULT_MODEL_ID = GROQ_MODELS[0].id

# Quick lookup: model_id → ModelInfo
MODEL_LOOKUP: dict = {m.id: m for m in GROQ_MODELS}

# Fallback safe budget for any unknown model (conservative)
DEFAULT_SAFE_INPUT_TOKENS = 3_000