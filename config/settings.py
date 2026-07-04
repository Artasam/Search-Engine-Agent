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
    ModelInfo(
        id                = "openai/gpt-oss-20b",
        label             = "GPT-OSS 20B",
        context_k         = 128,
        tpm_limit         = 6_000,
        safe_input_tokens = 3_300,    # 6000 * 0.55
        best_for          = ["Speed", "Chat", "High-throughput"],
    ),
    ModelInfo(
        id                = "openai/gpt-oss-120b",
        label             = "GPT-OSS 120B (best overall)",
        context_k         = 128,
        tpm_limit         = 6_000,
        safe_input_tokens = 3_300,
        best_for          = ["Reasoning", "Research", "Agents", "Coding", "Math"],
    ),
    ModelInfo(
        id                = "qwen/qwen3.6-27b",
        label             = "Qwen3.6 27B",
        context_k         = 128,
        tpm_limit         = 30_000,
        safe_input_tokens = 16_500,
        best_for          = ["Multimodal", "Long ctx", "File/image input"],
    ),
    ModelInfo(
        id                = "openai/gpt-oss-safeguard-20b",
        label             = "GPT-OSS Safeguard 20B",
        context_k         = 128,
        tpm_limit         = 6_000,
        safe_input_tokens = 3_300,
        best_for          = ["Content moderation", "Policy classification"],
    ),
]

DEFAULT_MODEL_ID = GROQ_MODELS[0].id

# Quick lookup: model_id → ModelInfo
MODEL_LOOKUP: dict = {m.id: m for m in GROQ_MODELS}

# Fallback safe budget for any unknown model (conservative)
DEFAULT_SAFE_INPUT_TOKENS = 3_000