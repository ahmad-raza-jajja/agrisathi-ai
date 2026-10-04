"""Central configuration. Order of precedence: environment variable -> .env -> Streamlit secrets -> default."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "data" / "documents"
PROMPTS_DIR = ROOT / "prompts"


def _get(name: str, default: str = "") -> str:
    v = os.getenv(name)
    if v:
        return v.strip()
    try:  # Streamlit Community Cloud secrets
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return default


# ---- LLM: Gemini free tier (REST) ----
GEMINI_API_KEY = _get("GEMINI_API_KEY")
# Tried in order. If all fail, the app asks the API which Flash models the key can use and tries those.
GEMINI_MODELS = [
    m.strip()
    for m in _get("GEMINI_MODELS", "gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.8-flash,gemini-3.1-flash-lite").split(",")
    if m.strip()
]
LLM_TIMEOUT = int(_get("LLM_TIMEOUT", "60"))
LLM_TEMPERATURE = float(_get("LLM_TEMPERATURE", "1.0"))  # Gemini 3 models work best at default 1.0
LLM_MAX_TOKENS = int(_get("LLM_MAX_TOKENS", "8192"))

# ---- RAG ----
EMBEDDINGS_BACKEND = _get("EMBEDDINGS_BACKEND", "tfidf").lower()  # tfidf | st
ST_MODEL = _get("ST_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
CHUNK_WORDS = int(_get("CHUNK_WORDS", "150"))
CHUNK_OVERLAP = int(_get("CHUNK_OVERLAP", "25"))
TOP_K = int(_get("TOP_K", "4"))
MIN_SCORE = float(_get("MIN_SCORE", "0.06"))

# ---- External open data (optional) ----
ENABLE_EXTERNAL_DATA = _get("ENABLE_EXTERNAL_DATA", "true").lower() == "true"
HTTP_TIMEOUT = int(_get("HTTP_TIMEOUT", "8"))

# ---- App ----
COOLDOWN_SECONDS = int(_get("COOLDOWN_SECONDS", "8"))  # per-session spam guard
