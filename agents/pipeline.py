"""End-to-end workflow, yielding progress events for the UI.

Farmer Problem -> Orchestrator -> RAG + tools -> Specialist agents (parallel) -> Action Planner -> Plan
Events: {"step": str, "state": "start"|"done", "detail": str}  and finally {"step": "result", "plan", "trace"}.
Raises LLMError if the AI model cannot be reached (nothing is faked).
"""
import time
from concurrent.futures import ThreadPoolExecutor

from agents import action_planner, orchestrator, specialists
from rag.retriever import get_retriever
from tools.data_tools import get_weather
from tools.wapor import get_wapor_context
from utils import llm
from utils.llm import LLMError
from utils.logging import get_logger

log = get_logger("pipeline")
STEPS = ["Understanding Problem", "Selecting Agents", "Searching Knowledge",
         "Checking Context", "Agents Analysing", "Creating Action Plan"]


def run_pipeline(inp: dict):
    inp = {k: (v.strip() if isinstance(v, str) else v) for k, v in inp.items()}
    language = inp.pop("language", "English")
    t0 = time.time()
    trace = {"input": inp, "errors": [], "models": set()}

    yield {"step": STEPS[0], "state": "start", "detail": "Reading your problem"}
    orch = orchestrator.run(inp)
    trace["orchestrator"] = orch
    trace["models"].add(llm.LAST_MODEL)
    yield {"step": STEPS[0], "state": "done", "detail": orch["english_problem"]}

    yield {"step": STEPS[1], "state": "start", "detail": ""}
    yield {"step": STEPS[1], "state": "done",
           "detail": f"Intent: {orch['intent'].replace('_', ' ')} · agents: {', '.join(orch['agents'])}"}

    yield {"step": STEPS[2], "state": "start", "detail": "Searching trusted documents"}
    retriever = get_retriever()
    per_agent, evidence, seen = {}, [], set()
    for name in orch["agents"]:
        q = f"{inp.get('crop', '')} {orch['english_problem']} {' '.join(orch['search_keywords'])} {specialists.FOCUS[name]}"
        hits = retriever.search(q, crop=inp.get("crop", ""))
        per_agent[name] = hits
        for c in hits:
            if c["id"] not in seen:
                seen.add(c["id"])
                evidence.append(c)
    evidence = sorted(evidence, key=lambda c: -c["score"])[:10]
    yield {"step": STEPS[2], "state": "done", "detail": f"{len(evidence)} relevant passages found"}

    yield {"step": STEPS[3], "state": "start", "detail": "Checking weather and water data"}
    tools = {}
    want = []
    if {"climate", "water"} & set(orch["agents"]):
        want.append(("weather", lambda: get_weather(inp.get("location", ""))))
    if "water" in orch["agents"]:
        want.append(("wapor", get_wapor_context))
    if want:
        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = {n: ex.submit(f) for n, f in want}
            tools = {n: f.result() for n, f in futs.items()}
    ok = [n for n, t in tools.items() if t.get("ok")]
    yield {"step": STEPS[3], "state": "done",
           "detail": ("Used: " + ", ".join(ok)) if ok else "No optional data needed or available"}

    yield {"step": STEPS[4], "state": "start", "detail": "Specialist agents are working"}
    results, errors = {}, []

    def work(name):
        return name, specialists.RUNNERS[name](inp, orch, per_agent[name], tools)

    with ThreadPoolExecutor(max_workers=len(orch["agents"])) as ex:
        futs = [ex.submit(work, n) for n in orch["agents"]]
        for f in futs:
            try:
                name, res = f.result()
                results[name] = res
            except Exception as e:
                log.warning("agent failed: %s", e)
                errors.append(str(e))
    trace["errors"] = errors
    if not results:
        raise LLMError(errors[0] if errors else "All specialist agents failed")
    trace["models"].add(llm.LAST_MODEL)
    yield {"step": STEPS[4], "state": "done", "detail": f"{len(results)} of {len(orch['agents'])} agents finished"}

    yield {"step": STEPS[5], "state": "start", "detail": "Combining everything into one plan"}
    try:
        plan = action_planner.run(inp, orch, results, tools, evidence, language)
    except ValueError as e:
        raise LLMError(str(e))
    trace["models"].add(llm.LAST_MODEL)
    trace["models"].discard("")
    trace.update({"agent_results": results, "tools": tools, "evidence": evidence,
                  "seconds": round(time.time() - t0, 1), "models": sorted(trace["models"])})
    yield {"step": STEPS[5], "state": "done", "detail": f"{len(plan['priority_actions'])} actions"}
    yield {"step": "result", "plan": plan, "trace": trace}


def run_blocking(inp: dict):
    last = None
    for ev in run_pipeline(inp):
        last = ev
    return last["plan"], last["trace"]
