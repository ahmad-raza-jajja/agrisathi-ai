import pytest

from tests import fake_gemini
from utils import config, llm


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(config, "ENABLE_EXTERNAL_DATA", True)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)


CROP = dict(problem="Leaves turning yellow and water is limited", crop="Wheat", location="Bahawalpur",
            farm_size="5 acres", water="Limited", language="English")
FOOD = dict(problem="approximately 300 kg tomatoes and low market demand", crop="Tomato", location="Multan",
            farm_size="", water="Moderate", language="English")


def test_knowledge_base_has_10_docs_and_retrieves_by_crop():
    from rag.retriever import Retriever
    r = Retriever()
    assert len({x["file"] for x in r.records}) == 10
    assert r.search("yellow leaves whitefly curl", crop="Cotton")[0]["file"].startswith("07_cotton")
    assert r.search("surplus tomatoes storage processing selling", crop="Tomato")[0]["file"].startswith("04_food")
    assert r.search("quantum spaceship engine", min_score=0.2) == []


def test_crop_pipeline_end_to_end(monkeypatch):
    fake_gemini.install(monkeypatch)
    from agents.pipeline import run_blocking
    plan, trace = run_blocking(CROP)
    assert set(trace["orchestrator"]["agents"]) == {"agriculture", "water", "climate"}
    ids = {c["id"] for c in trace["evidence"]}
    assert len(plan["priority_actions"]) == 6 and plan["sources"]
    for item in plan["possible_factors"] + plan["priority_actions"]:
        assert all(s in ids for s in item["source_ids"])  # fabricated "FAKE#99" must be stripped
    assert any("not a confirmed diagnosis" in w for w in plan["warnings"])
    assert trace["tools"]["weather"]["ok"] and trace["tools"]["wapor"]["ok"]


def test_food_pipeline_no_buyer_claims(monkeypatch):
    fake_gemini.install(monkeypatch)
    from agents.pipeline import run_blocking
    plan, trace = run_blocking(FOOD)
    assert trace["orchestrator"]["agents"] == ["food_rescue"]
    assert any("not contacted any buyer" in w for w in plan["warnings"])


def test_urdu_output_and_disclaimer(monkeypatch):
    fake_gemini.install(monkeypatch)
    from agents.pipeline import run_blocking
    plan, _ = run_blocking({**FOOD, "language": "Urdu"})
    assert plan["language"] == "Urdu" and "ٹماٹر" in plan["problem_summary"]
    assert any("زرعی" in w for w in plan["warnings"])


def test_external_data_failure_does_not_break(monkeypatch):
    fake_gemini.install(monkeypatch)
    import requests
    orig = requests.get
    monkeypatch.setattr(requests, "get", lambda url, **k: (_ for _ in ()).throw(requests.ConnectionError()) if "fao" in url or "open-meteo" in url else orig(url, **k))
    monkeypatch.setattr("tools.data_tools.KNOWN_PLACES", {})
    from agents.pipeline import run_blocking
    plan, trace = run_blocking(CROP)
    assert not trace["tools"]["weather"]["ok"] and plan["priority_actions"]


def test_model_not_found_triggers_auto_discovery(monkeypatch):
    calls = fake_gemini.install(monkeypatch, mode="all404")
    out = llm.generate("You are the Orchestrator x", "Wheat tomato kg")
    assert llm.LAST_MODEL == "gemini-9.9-flash" and calls[-1] == "gemini-9.9-flash"
    assert "gemini-9.9-pro" not in calls and "gemini-9.9-flash-tts" not in calls  # only usable Flash text models


def test_bad_key_fails_fast_with_clear_message(monkeypatch):
    calls = fake_gemini.install(monkeypatch, mode="badkey")
    with pytest.raises(llm.LLMError, match="invalid or expired"):
        llm.generate("s", "u")
    assert len(calls) == 1


def test_rate_limit_everywhere_raises_not_fakes(monkeypatch):
    fake_gemini.install(monkeypatch, mode="rate429")
    from agents.pipeline import run_blocking
    with pytest.raises(llm.LLMError):
        run_blocking(CROP)


def test_invalid_json_twice_raises(monkeypatch):
    fake_gemini.install(monkeypatch, mode="notjson")
    with pytest.raises(llm.LLMError, match="invalid JSON"):
        llm.generate_json("s", "u")


def test_missing_key_raises(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    with pytest.raises(llm.LLMError, match="GEMINI_API_KEY"):
        llm.generate("s", "u")


def test_json_parser_variants():
    assert llm.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm.parse_json('noise {"a": 2} noise') == {"a": 2}
    assert llm.parse_json("[1,2]") is None
