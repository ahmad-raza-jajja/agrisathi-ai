"""Action Planner: merges everything into one prioritised plan and enforces the safety guardrails."""
from agents.base import call_agent, cited_items, dump, format_evidence, format_inputs, s, str_list

LANGS = {"English": "English", "Urdu": "Urdu (اردو, in Urdu script)", "Roman Urdu": "Roman Urdu (Urdu written in English letters)"}
DISCLAIMER = {
    "English": "AgriSathi AI is decision support, not a replacement for a qualified agricultural officer. Confirm important steps (especially sprays) with your local extension office.",
    "Urdu": "ایگری ساتھی اے آئی فیصلہ سازی میں مدد دیتا ہے، یہ کسی ماہرِ زراعت کا متبادل نہیں۔ اہم اقدامات (خاص طور پر سپرے) سے پہلے اپنے مقامی زرعی توسیعی دفتر سے تصدیق کر لیں۔",
    "Roman Urdu": "AgriSathi AI faisla karne me madad deta hai, ye kisi zarai mahir ka mutadil nahi. Aham iqdamat (khas taur par spray) se pehle apne muqami zarai daftar se tasdeeq kar lein.",
}
NOT_DIAGNOSIS = {
    "English": "These are possible factors, not a confirmed diagnosis.",
    "Urdu": "یہ ممکنہ وجوہات ہیں، حتمی تشخیص نہیں۔",
    "Roman Urdu": "Ye mumkina wajuhat hain, qatai tashkhees nahi.",
}
NO_EVIDENCE = {
    "English": "The current knowledge base does not contain sufficient evidence for this problem. Treat the points below as general guidance and ask a local expert.",
    "Urdu": "موجودہ علمی ذخیرے میں اس مسئلے کے لیے کافی شواہد موجود نہیں۔ نیچے دی گئی باتیں عمومی رہنمائی سمجھیں اور مقامی ماہر سے پوچھیں۔",
    "Roman Urdu": "Maujooda knowledge base me is masle ke liye kafi saboot nahi hain. Neeche ki baatein aam rehnumai samjhein aur muqami mahir se poochein.",
}
NO_BUYERS = {
    "English": "AgriSathi has not contacted any buyer. Check current prices and buyers yourself.",
    "Urdu": "ایگری ساتھی نے کسی خریدار سے رابطہ نہیں کیا۔ موجودہ قیمتیں اور خریدار خود چیک کریں۔",
    "Roman Urdu": "AgriSathi ne kisi buyer se rabta nahi kiya. Maujooda qeematein aur buyers khud check karein.",
}


def run(inp, orch, results, tools, evidence, language="English") -> dict:
    valid_ids = {c["id"] for c in evidence}
    ctx = (f"OUTPUT LANGUAGE: {LANGS.get(language, 'English')}\n\n{format_inputs(inp)}\n\n"
           f"Problem in English: {orch['english_problem']}\nINTENT: {orch['intent']}\n"
           f"Missing details noticed by the orchestrator: {orch['missing_info']}\n\n"
           f"SPECIALIST AGENT RESULTS:\n{dump(results)}\n\n"
           f"TOOLS:\n{dump({k: v.get('summary', v.get('reason')) for k, v in tools.items()})}\n\n"
           f"{format_evidence(evidence)}")
    raw = call_agent("action_planner", ctx)

    def clean(items):
        for it in items:
            it["source_ids"] = [x for x in it["source_ids"] if x in valid_ids]  # never show a source we did not retrieve
        return items

    actions = clean(cited_items(raw.get("priority_actions"), "action", 6))
    for i, a in enumerate(actions, 1):
        try:
            a["priority"] = int(a.get("priority", i))
        except (TypeError, ValueError):
            a["priority"] = i
    plan = {
        "problem_summary": s(raw.get("problem_summary")) or s(inp.get("problem")),
        "possible_factors": clean(cited_items(raw.get("possible_factors"), "factor", 5)),
        "priority_actions": sorted(actions, key=lambda a: a["priority"]),
        "information_needed": str_list(raw.get("information_needed"), 6),
        "warnings": str_list(raw.get("warnings"), 5),
        "evidence_sufficient": bool(raw.get("evidence_sufficient", True)) and bool(evidence),
    }
    if not plan["priority_actions"]:
        raise ValueError("Planner returned no actions")
    lang = language if language in DISCLAIMER else "English"
    if not plan["evidence_sufficient"]:
        plan["warnings"].insert(0, NO_EVIDENCE[lang])
    if orch["intent"] == "crop_problem":
        plan["warnings"].append(NOT_DIAGNOSIS[lang])
    if orch["intent"] == "food_surplus" or "food_rescue" in orch["agents"]:
        plan["warnings"].append(NO_BUYERS[lang])
    plan["warnings"].append(DISCLAIMER[lang])
    cited = {x for k in ("possible_factors", "priority_actions") for it in plan[k] for x in it["source_ids"]}
    plan["sources"] = [c for c in evidence if c["id"] in cited]
    plan["sources_note"] = "" if plan["sources"] else "retrieved"
    if not plan["sources"]:
        plan["sources"] = evidence[:3]
    plan["language"] = lang
    return plan
