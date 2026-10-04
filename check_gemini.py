"""Run:  python check_gemini.py   -> checks your key, lists usable free models, makes one real test call."""
from utils import config, llm

print("Key loaded      :", bool(config.GEMINI_API_KEY), f"(length {len(config.GEMINI_API_KEY)})")
print("Configured models:", config.GEMINI_MODELS)
if not config.GEMINI_API_KEY:
    raise SystemExit("-> Put GEMINI_API_KEY=... in .env (same folder as app.py) and run again.")
print("Models your key can use:", llm.list_models() or "none returned (key/network problem?)")
try:
    print("Test reply      :", llm.generate("Reply with one word.", "Say OK"))
    print("Model used      :", llm.LAST_MODEL)
    print("RESULT: Gemini is working.")
except llm.LLMError as e:
    print("RESULT: FAILED ->", e)
