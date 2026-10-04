"""Orchestrator: understands intent (any language) and selects the specialist agents."""
from agents.base import call_agent, format_inputs, s, str_list
from utils import config

VALID = ["agriculture", "water", "climate", "food_rescue"]
INTENTS = {"crop_problem", "water_management", "food_surplus", "climate_risk", "general"}


def run(inp: dict) -> dict:
    raw = call_agent("orchestrator", format_inputs(inp))
    agents = [a for a in str_list(raw.get("agents")) if a in VALID]
    intent = s(raw.get("intent")) if s(raw.get("intent")) in INTENTS else "general"
    if not agents:
        agents = ["food_rescue"] if intent == "food_surplus" else ["agriculture", "water"]
    # Guardrails on the LLM's routing
    if intent == "crop_problem" and "agriculture" not in agents:
        agents.insert(0, "agriculture")
    if "climate" in agents and not (config.ENABLE_EXTERNAL_DATA and inp.get("location")):
        agents.remove("climate")
    problem_en = s(raw.get("english_problem")) or s(inp.get("problem"))
    return {
        "intent": intent,
        "agents": list(dict.fromkeys(agents)),
        "english_problem": problem_en,
        "search_keywords": str_list(raw.get("search_keywords"), 8),
        "missing_info": str_list(raw.get("missing_info"), 4),
        "reason": s(raw.get("reason")),
    }
