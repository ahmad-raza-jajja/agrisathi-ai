"""Test double for the network: fakes Gemini (generateContent + model list), Open-Meteo and WaPOR.
Used only by tests / screenshot verification - never imported by the app."""
import json
import re

import requests


class Resp:
    def __init__(self, code=200, data=None, text=""):
        self.status_code, self._data = code, data
        self.text = text or json.dumps(data or {})

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


def _gem(text):
    return Resp(200, {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]})


def _answer(system, user):
    ids = re.findall(r"^\[([\w#]+)\]", user, flags=re.M)
    cid = ids[:1]
    if system.startswith("You are the Orchestrator"):
        food = "tomato" in user.lower() and "kg" in user.lower()
        return {"intent": "food_surplus" if food else "crop_problem",
                "agents": ["food_rescue"] if food else ["agriculture", "water", "climate"],
                "english_problem": "Farmer has surplus tomatoes and low demand" if food else "Leaves are turning yellow with limited water",
                "search_keywords": ["tomato", "surplus", "storage"] if food else ["yellow", "leaves", "nutrient", "irrigation"],
                "missing_info": [] if food else ["Which leaves turn yellow first?"], "reason": "test"}
    if system.startswith("You are the Agriculture Agent"):
        return {"possible_factors": [{"factor": "Nitrogen shortage", "why": "Old leaves yellow first", "source_ids": cid}],
                "recommended_checks": ["Check old vs young leaves"], "actions": [{"action": "Inspect field pattern", "reason": "Narrows causes", "source_ids": cid}],
                "information_needed": ["Last fertiliser date"]}
    if system.startswith("You are the Water Agent"):
        return {"water_context": "Limited water", "actions": [{"action": "Irrigate at critical stages first", "reason": "Best use of scarce water", "source_ids": cid}],
                "information_needed": ["Next canal turn"]}
    if system.startswith("You are the Climate Agent"):
        return {"climate_context": "Dry week ahead", "risks": ["Heat"], "actions": [{"action": "Irrigate by soil dryness", "reason": "No rain forecast", "source_ids": cid}]}
    if system.startswith("You are the Food Rescue Agent"):
        return {"options": [{"action": "Sort and grade tomatoes", "reason": "Quality decides option", "source_ids": cid}], "information_needed": ["Ripeness"]}
    if system.startswith("You are the Action Planner"):
        urdu = "OUTPUT LANGUAGE: Urdu" in user
        food = "food_surplus" in user
        return {"problem_summary": "ٹماٹر کی اضافی پیداوار اور کم طلب" if urdu else ("300 kg tomato surplus with low demand" if food else "Wheat leaves yellowing with limited water in Bahawalpur"),
                "possible_factors": [] if food else [{"factor": "Possible nitrogen shortage", "why": "Pattern of old leaves", "source_ids": cid + ["FAKE#99"]}],
                "priority_actions": [{"priority": i, "action": f"Action number {i}", "reason": f"Reason {i}", "source_ids": cid} for i in range(1, 7)],
                "information_needed": ["Date of last irrigation"], "warnings": ["Check local prices"], "evidence_sufficient": bool(cid)}
    return {}


def install(monkeypatch=None, mode="ok", log=None):
    """mode: ok | all404 | badkey | rate429 | notjson"""
    calls = log if log is not None else []

    def post(url, params=None, json=None, timeout=None, **kw):  # noqa: A002
        model = url.split("/models/")[1].split(":")[0]
        calls.append(model)
        if mode == "badkey":
            return Resp(400, text='{"error":{"message":"API key not valid. Please pass a valid API key.","status":"INVALID_ARGUMENT"}}')
        if mode == "all404" and model != "gemini-9.9-flash":
            return Resp(404, text="model not found")
        if mode == "rate429":
            return Resp(429, text="quota")
        if mode == "notjson":
            return _gem("this is not json")
        system = json["systemInstruction"]["parts"][0]["text"]
        user = json["contents"][0]["parts"][0]["text"]
        return _gem(__import__("json").dumps(_answer(system, user), ensure_ascii=False))

    def get(url, params=None, timeout=None, **kw):
        if "generativelanguage" in url:
            return Resp(200, {"models": [{"name": "models/gemini-9.9-flash", "supportedGenerationMethods": ["generateContent"]},
                                         {"name": "models/gemini-9.9-flash-tts", "supportedGenerationMethods": ["generateContent"]},
                                         {"name": "models/gemini-9.9-pro", "supportedGenerationMethods": ["generateContent"]}]})
        if "open-meteo" in url:
            days = [f"2026-10-{d:02d}" for d in range(1, 15)]
            return Resp(200, {"daily": {"time": days, "temperature_2m_max": [36 + (i % 3) for i in range(14)],
                                        "temperature_2m_min": [24] * 14, "precipitation_sum": [0.1] * 7 + [0] * 7}})
        if "fao.org" in url:
            return Resp(200, {"response": [{"caption": "Transpiration (National - Dekadal - 100m)"}]})
        raise requests.ConnectionError("blocked in test")

    if monkeypatch is not None:
        monkeypatch.setattr(requests, "post", post)
        monkeypatch.setattr(requests, "get", get)
    else:
        requests.post, requests.get = post, get
    return calls
