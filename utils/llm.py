"""Gemini REST client (free tier). Online only: failures raise LLMError, they are never faked.

Resilience: tries each configured model in order, retries transient errors (429/5xx/timeouts) once,
and if every configured model fails it asks the API which Flash models this key can use and tries those.
"""
import json
import re
import time
from typing import List, Optional, Tuple

import requests

from utils import config
from utils.logging import get_logger

log = get_logger("llm")
BASE = "https://generativelanguage.googleapis.com/v1beta"

LAST_MODEL = ""  # model that produced the most recent answer
LAST_ERROR = ""


class LLMError(Exception):
    """Raised when no model could produce a usable answer."""


def llm_available() -> bool:
    return bool(config.GEMINI_API_KEY)


def list_models() -> List[str]:
    """Flash-family models this key can call with generateContent (stable before preview, newest first)."""
    try:
        r = requests.get(f"{BASE}/models", params={"key": config.GEMINI_API_KEY, "pageSize": 200},
                         timeout=config.LLM_TIMEOUT)
        names = [m["name"].split("/", 1)[1] for m in r.json().get("models", [])
                 if "generateContent" in m.get("supportedGenerationMethods", [])]
    except Exception as e:
        log.warning("model discovery failed: %s", e)
        return []
    bad = ("tts", "live", "image", "audio", "embedding", "transcribe", "translate", "robotics", "computer",
           "pro", "thinking", "exp", "gemma", "learnlm", "aqa")
    good = [n for n in names if n.startswith("gemini-") and "flash" in n and not any(b in n for b in bad)]

    def version(n):
        m = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        return float(m.group(1)) if m else 0.0

    return sorted(good, key=lambda n: ("preview" in n, -version(n), "lite" in n))


def _call(model: str, body: dict) -> Tuple[str, str, str]:
    """-> (status, text, error). status: ok | transient | badkey | hard"""
    try:
        r = requests.post(f"{BASE}/models/{model}:generateContent", params={"key": config.GEMINI_API_KEY},
                          json=body, timeout=config.LLM_TIMEOUT)
    except (requests.Timeout, requests.ConnectionError) as e:
        return "transient", "", f"{type(e).__name__}"
    except Exception as e:
        return "hard", "", f"{type(e).__name__}: {e}"
    if r.status_code == 429 or r.status_code >= 500:
        return "transient", "", f"HTTP {r.status_code} (rate limit or server busy)"
    if r.status_code != 200:
        txt = r.text[:300]
        if re.search(r"API_KEY_INVALID|API key not valid|API key expired|API key.*invalid", txt, re.I):
            return "badkey", "", "The Gemini API key is invalid or expired"
        return "hard", "", f"HTTP {r.status_code}: {txt}"
    try:
        cand = r.json()["candidates"][0]
        parts = cand.get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    except Exception:
        return "hard", "", "Unexpected response format"
    if not text:
        return "hard", "", f"Empty answer (finish reason: {cand.get('finishReason', 'unknown')})"
    return "ok", text, ""


def generate(system: str, user: str, json_mode: bool = False) -> str:
    global LAST_MODEL, LAST_ERROR
    if not llm_available():
        raise LLMError("GEMINI_API_KEY is not set. Add it in .env (local) or in the Streamlit Cloud secrets.")
    gen_cfg = {"temperature": config.LLM_TEMPERATURE, "maxOutputTokens": config.LLM_MAX_TOKENS}
    if json_mode:
        gen_cfg["responseMimeType"] = "application/json"
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": gen_cfg}

    candidates, seen, hard_failed, errors = list(config.GEMINI_MODELS), set(config.GEMINI_MODELS), set(), []
    discovered, retried = False, False
    while True:
        transient = []
        for model in candidates:
            if model in hard_failed:
                continue
            status, text, err = _call(model, body)
            if status == "ok":
                LAST_MODEL, LAST_ERROR = model, ""
                return text
            log.warning("%s -> %s", model, err)
            errors.append(f"{model}: {err}")
            if status == "badkey":
                LAST_ERROR = err
                raise LLMError(err)
            if status == "transient":
                transient.append(model)
            else:
                hard_failed.add(model)
        if transient and not retried:
            retried = True
            time.sleep(4)
            candidates = transient
            continue
        if not discovered:
            discovered = True
            extra = [m for m in list_models() if m not in seen]
            if extra:
                log.info("Auto-discovered models: %s", extra)
                seen.update(extra)
                candidates = extra
                continue
        break
    LAST_ERROR = " | ".join(errors[-4:])
    raise LLMError("No Gemini model answered. " + LAST_ERROR)


def parse_json(text: str) -> Optional[dict]:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(0))
                return obj if isinstance(obj, dict) else None
            except Exception:
                return None
    return None


def generate_json(system: str, user: str) -> dict:
    msg = user
    for attempt in range(2):
        obj = parse_json(generate(system, msg, json_mode=True))
        if obj is not None:
            return obj
        msg = user + "\n\nYour previous reply was not valid JSON. Reply with ONE valid JSON object only."
    raise LLMError("The model returned invalid JSON twice.")
