# 🌾 AgriSathi AI — Agentic AI Copilot for Smarter Farming

Farmer problem → **Orchestrator** → **RAG + open data** → **Agriculture / Water / Climate / Food-Rescue agents (parallel)** → **Action Planner** → prioritised, source-backed plan.
Online-only (Gemini free tier). English · اردو · Roman Urdu. Built for Streamlit Community Cloud.

## Run locally
```bash
pip install -r requirements.txt
copy .env.example .env        # Windows  (Mac/Linux: cp)   then paste your free key into .env
python check_gemini.py        # verifies key + shows usable free models
python -m streamlit run app.py
```
Free key: https://aistudio.google.com/apikey

## Deploy on Streamlit Community Cloud
1. Push this folder to a GitHub repo (`.env` and `secrets.toml` are git-ignored — never commit your key).
2. share.streamlit.io → **Create app** → pick the repo, branch `main`, main file `app.py`.
3. **Advanced settings → Secrets**, paste:
   ```toml
   GEMINI_API_KEY = "your-key"
   ```
4. Deploy. Models are auto-selected (`gemini-3.5-flash` → `3.5-flash-lite` → `3.8-flash` → `3.1-flash-lite`); if names change, the app asks the API which Flash models your key can use.

## Project map
| Path | Role |
|---|---|
| `app.py` | Streamlit UI |
| `agents/` | orchestrator, specialists, action planner, pipeline |
| `prompts/` | one prompt file per agent |
| `rag/` | ingest (clean+chunk), TF-IDF/sentence-transformer embeddings, retriever |
| `tools/` | Open-Meteo weather, FAO WaPOR catalog |
| `data/documents/` | knowledge base (10 starter notes) |
| `tests/` | `python -m pytest -q tests` (network is faked in tests only) |

## Safety rules built in
Possible factors, never a diagnosis · only retrieved sources can be shown · "not enough evidence" warning · no buyer/price claims · weather/WaPOR optional · decision support only · input length limits and a per-session cooldown.

## IMPORTANT: knowledge base
`data/documents/*.md` are **starter notes** (summaries of general guidance). Add official FAO / PARC / Agriculture Department PDFs or text to `data/documents/` — the index rebuilds at startup. Optional first lines in text files: `TITLE:` and `SOURCE:`.
