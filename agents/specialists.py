"""Specialist agents. Each takes the farmer input, orchestrator output, its own retrieved evidence and tool data,
and returns a normalised dict. Prompts live in prompts/*.md."""
from agents.base import call_agent, cited_items, dump, format_evidence, format_inputs, s, str_list

FOCUS = {
    "agriculture": "symptoms causes nutrient deficiency disease pest management field checks",
    "water": "irrigation scheduling limited water critical growth stages water saving",
    "climate": "weather rain heat forecast irrigation spraying decisions",
    "food_rescue": "post harvest storage processing selling surplus waste reduction donation",
}


def _msg(inp, orch, evidence, extra=""):
    return (f"{format_inputs(inp)}\n\nProblem in English: {orch['english_problem']}\n\n"
            f"{extra}{format_evidence(evidence)}")


def agriculture(inp, orch, evidence, tools):
    r = call_agent("agriculture_agent", _msg(inp, orch, evidence))
    return {"possible_factors": cited_items(r.get("possible_factors"), "factor", 5),
            "recommended_checks": str_list(r.get("recommended_checks"), 6),
            "actions": cited_items(r.get("actions"), "action", 6),
            "information_needed": str_list(r.get("information_needed"), 5)}


def water(inp, orch, evidence, tools):
    tool_txt = "TOOLS:\n" + dump({k: v.get("summary", v.get("reason")) for k, v in tools.items()}) + "\n\n"
    r = call_agent("water_agent", _msg(inp, orch, evidence, tool_txt))
    return {"water_context": s(r.get("water_context")),
            "actions": cited_items(r.get("actions"), "action", 6),
            "information_needed": str_list(r.get("information_needed"), 5)}


def climate(inp, orch, evidence, tools):
    w = tools.get("weather", {})
    wtxt = "WEATHER TOOL OUTPUT:\n" + dump({k: v for k, v in w.items() if k != "forecast"}
                                           | ({"forecast": w["forecast"]} if w.get("ok") else {})) + "\n\n"
    r = call_agent("climate_agent", _msg(inp, orch, evidence, wtxt))
    return {"climate_context": s(r.get("climate_context")),
            "risks": str_list(r.get("risks"), 5),
            "actions": cited_items(r.get("actions"), "action", 5)}


def food_rescue(inp, orch, evidence, tools):
    r = call_agent("food_rescue_agent", _msg(inp, orch, evidence))
    return {"actions": cited_items(r.get("options"), "action", 7),
            "information_needed": str_list(r.get("information_needed"), 5)}


RUNNERS = {"agriculture": agriculture, "water": water, "climate": climate, "food_rescue": food_rescue}
