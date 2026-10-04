"""Shared helpers: prompt loading, input formatting, and strict normalisation of LLM JSON."""
import json
from typing import List

from utils import config
from utils.llm import generate_json


def load_prompt(name: str) -> str:
    return (config.PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def call_agent(prompt_name: str, user_msg: str) -> dict:
    return generate_json(load_prompt(prompt_name), user_msg)


def format_inputs(inp: dict) -> str:
    return (f"Problem (farmer's words): {inp.get('problem') or 'not given'}\n"
            f"Crop: {inp.get('crop') or 'not given'}\n"
            f"Location: {inp.get('location') or 'not given'}\n"
            f"Farm size: {inp.get('farm_size') or 'not given'}\n"
            f"Water availability: {inp.get('water') or 'not given'}")


def format_evidence(chunks: List[dict]) -> str:
    if not chunks:
        return "EVIDENCE: none found in the knowledge base for this problem."
    return "EVIDENCE:\n" + "\n".join(f"[{c['id']}] ({c['title']}) {c['text']}" for c in chunks)


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, default=str)


# ---------- normalisation (LLM output is never trusted blindly) ----------
def s(x) -> str:
    return str(x).strip() if x is not None else ""


def str_list(x, limit=8) -> List[str]:
    if isinstance(x, str):
        x = [x]
    return [s(i) for i in (x or []) if s(i)][:limit] if isinstance(x, list) else []


def cited_items(x, main_key: str, limit=8) -> List[dict]:
    """List of {main_key, why/reason, source_ids} dicts with safe types."""
    out = []
    for it in (x if isinstance(x, list) else []):
        if isinstance(it, str):
            it = {main_key: it}
        if not isinstance(it, dict) or not s(it.get(main_key)):
            continue
        d = dict(it)
        d[main_key] = s(it.get(main_key))
        for k in ("why", "reason"):
            if k in d:
                d[k] = s(d[k])
        d["source_ids"] = [s(i) for i in (it.get("source_ids") or []) if s(i)] if isinstance(it.get("source_ids"), list) else []
        out.append(d)
    return out[:limit]
