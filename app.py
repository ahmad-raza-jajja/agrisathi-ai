"""AgriSathi AI - Streamlit app.   Run: python -m streamlit run app.py"""
import time
from html import escape as esc

import streamlit as st

from agents.pipeline import STEPS, run_pipeline
from utils import config, llm
from utils.llm import LLMError, llm_available
from utils.logging import get_logger

log = get_logger("app")

st.set_page_config(page_title="AgriSathi AI – Farming Copilot", page_icon="🌾", layout="wide",
                   initial_sidebar_state="collapsed")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Naskh+Arabic:wght@400;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, textarea, label { font-family: 'Inter', sans-serif; }
#MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; height: 0; }
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1250px; }

.hero { background: linear-gradient(120deg,#14532d 0%,#15803d 55%,#65a30d 100%); border-radius: 22px;
        padding: 30px 36px; color: #fff; margin-bottom: 22px; position: relative; overflow: hidden;
        box-shadow: 0 10px 30px rgba(21,128,61,.25); }
.hero:after { content: "🌾"; position: absolute; right: 28px; bottom: -22px; font-size: 130px; opacity: .13; }
.hero h1 { margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -.5px; color: #fff; }
.hero p { margin: 6px 0 14px; font-size: 1.05rem; opacity: .93; color: #fff; }
.pill { display: inline-block; background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.28);
        padding: 4px 12px; border-radius: 999px; font-size: .78rem; font-weight: 600; margin: 0 6px 6px 0; color: #fff; }

.panel { background: #fff; border: 1px solid #dfeadb; border-radius: 18px; padding: 6px 4px; }
.sec { display: flex; align-items: center; gap: 10px; margin: 26px 0 10px; font-weight: 700; font-size: 1.12rem; color: #14532d; }
.sec .dot { width: 8px; height: 22px; border-radius: 4px; background: #16a34a; }
.card { background: #fff; border: 1px solid #e3ece0; border-radius: 14px; padding: 14px 18px; margin: 8px 0;
        color: #1f2937; box-shadow: 0 1px 2px rgba(0,0,0,.03); line-height: 1.55; }
.card b { color: #111827; }
.summary { background: linear-gradient(180deg,#f0fdf4,#ffffff); border-left: 5px solid #16a34a; font-size: 1.04rem; }
.act { display: flex; gap: 14px; align-items: flex-start; }
.num { flex: 0 0 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
       font-weight: 800; color: #fff; background: #16a34a; }
.num.p1 { background: #dc2626; } .num.p2 { background: #ea580c; } .num.p3 { background: #d97706; }
.tag { display: inline-block; font-size: .7rem; font-weight: 700; padding: 2px 9px; border-radius: 999px; margin-left: 8px;
       vertical-align: middle; }
.tag.t1 { background: #fee2e2; color: #b91c1c; } .tag.t2 { background: #fef3c7; color: #b45309; }
.tag.t3 { background: #dcfce7; color: #166534; }
.why { color: #4b5563; font-size: .93rem; margin-top: 2px; }
.src { display: inline-block; background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; border-radius: 8px;
       padding: 1px 8px; font-size: .72rem; margin: 6px 6px 0 0; font-weight: 600; }
.warn { background: #fffbeb; border: 1px solid #fde68a; color: #78350f; border-radius: 12px; padding: 10px 14px;
        margin: 6px 0; font-size: .93rem; }
.warn.strong { background: #fef2f2; border-color: #fecaca; color: #7f1d1d; }
.chk { padding: 6px 2px; color: #1f2937; }
.chip { display: inline-block; background: #fff; border: 1px solid #dfeadb; border-radius: 12px; padding: 8px 14px;
        margin: 0 8px 8px 0; font-size: .85rem; color: #374151; }
.chip b { display: block; font-size: 1rem; color: #14532d; }
.step { display: flex; gap: 10px; align-items: center; padding: 7px 4px; color: #374151; font-size: .96rem; }
.step small { color: #6b7280; }
.step .ic { width: 24px; text-align: center; }
.step.pend { opacity: .45; } .step.run { font-weight: 600; color: #14532d; }
.spin { display:inline-block; animation: sp 1s linear infinite; } @keyframes sp { to { transform: rotate(360deg); } }
.rtl { direction: rtl; text-align: right; font-family: 'Noto Naskh Arabic','Inter',serif; font-size: 1.08rem; }
.rtl .act { flex-direction: row-reverse; } .rtl .sec { flex-direction: row-reverse; }
.empty { text-align: center; padding: 56px 20px; color: #5b6b5a; background: #fff; border: 2px dashed #cfe2ca; border-radius: 18px; }
.empty .big { font-size: 3rem; }
div[data-testid="stForm"] { border: 1px solid #dfeadb; border-radius: 18px; background: #fff; padding: 18px 20px; }
.stButton > button, div[data-testid="stFormSubmitButton"] > button { border-radius: 12px; font-weight: 700; padding: .65rem 1rem; }
@media (max-width: 760px) { .hero { padding: 22px 20px; } .hero h1 { font-size: 1.6rem; } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

CROPS = ["Wheat", "Rice", "Cotton", "Sugarcane", "Maize", "Tomato", "Potato", "Onion", "Other"]
WATER = ["Very limited", "Limited", "Moderate", "Sufficient"]
LANGUAGES = ["English", "Urdu", "Roman Urdu"]
LABELS = {
    "English": dict(summary="Problem Summary", factors="Possible Factors", actions="Priority Actions",
                    info="Information Needed", warn="Warnings", src="Evidence & Sources",
                    t1="Do first", t2="Next", t3="Then", retrieved="Closest passages from the knowledge base:"),
    "Urdu": dict(summary="مسئلے کا خلاصہ", factors="ممکنہ وجوہات", actions="ترجیحی اقدامات",
                 info="مزید معلومات درکار", warn="انتباہات", src="شواہد اور ذرائع",
                 t1="پہلے کریں", t2="اس کے بعد", t3="پھر", retrieved="علمی ذخیرے سے قریب ترین حوالے:"),
    "Roman Urdu": dict(summary="Masle ka khulasa", factors="Mumkina wajuhat", actions="Tarjihi iqdamat",
                       info="Mazeed maloomat darkar", warn="Ihtiyat", src="Saboot aur zaraye",
                       t1="Pehle karein", t2="Is ke baad", t3="Phir",
                       retrieved="Knowledge base se qareeb tareen hawale:"),
}

# ---------------------------------------------------------------- header
st.markdown(
    """<div class="hero"><h1>🌾 AgriSathi AI</h1>
    <p>From farm problems to evidence-backed actions — your agentic AI copilot for smarter farming.</p>
    <span class="pill">🤖 Multi-agent AI</span><span class="pill">📚 Evidence from trusted documents</span>
    <span class="pill">🌦️ Live weather &amp; FAO WaPOR data</span><span class="pill">🗣️ English · اردو · Roman Urdu</span></div>""",
    unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🌾 AgriSathi AI")
    st.caption("Decision support for small and medium farmers.")
    if llm_available():
        st.success("AI model connected", icon="✅")
    else:
        st.error("AI key missing", icon="🔑")
    st.markdown("**How it works**")
    st.markdown("1. You describe the problem  \n2. An orchestrator picks the right specialist agents  \n"
                "3. Agents search trusted documents and open data  \n4. A planner writes a prioritised, source-backed plan")
    st.info("AgriSathi gives guidance, not a diagnosis. Always confirm important steps — especially sprays — "
            "with your local agriculture extension office.")

if not llm_available():
    st.error("**The AI key is not configured.** Add `GEMINI_API_KEY` in the Streamlit Cloud *Secrets* "
             "(or in a local `.env` file) and reload. A free key is available at aistudio.google.com/apikey.")
    st.stop()

# ---------------------------------------------------------------- layout
left, right = st.columns([1, 1.65], gap="large")

with left:
    with st.form("farm_form", border=False):
        st.markdown("#### Tell us about your farm")
        problem = st.text_area("What is the problem? *", height=130, max_chars=800,
                               placeholder="Describe what you see — in English, اردو or Roman Urdu.\n"
                                           "e.g. Leaves of my crop are turning yellow / I have surplus produce and low prices")
        c1, c2 = st.columns(2)
        crop = c1.selectbox("Crop *", CROPS)
        water = c2.selectbox("Water availability *", WATER, index=1)
        location = st.text_input("Location (district / city) *", max_chars=60, placeholder="e.g. Bahawalpur")
        c3, c4 = st.columns(2)
        farm_size = c3.text_input("Farm size", max_chars=30, placeholder="e.g. 5 acres")
        language = c4.selectbox("Answer language", LANGUAGES)
        submit = st.form_submit_button("🔍  Get my action plan", type="primary", use_container_width=True)
    st.caption("Your answer is based on the details you enter. The more precise you are, the better the plan.")

with right:
    out = st.container()

if submit:
    if len(problem.strip()) < 6 or not location.strip():
        out.warning("Please describe the problem (at least a few words) and enter your location.")
    elif time.time() - st.session_state.get("last_run", 0) < config.COOLDOWN_SECONDS:
        out.info("Please wait a few seconds before sending another request.")
    else:
        st.session_state.last_run = time.time()
        inp = dict(problem=problem, crop=crop, location=location, farm_size=farm_size, water=water,
                   language=language)
        state = {s: ("pend", "") for s in STEPS}
        with out:
            st.markdown("#### 🤖 Your agents are working")
            ph = st.empty()

        def paint():
            rows = []
            for name in STEPS:
                kind, detail = state[name]
                icon = {"done": "✅", "run": '<span class="spin">⏳</span>', "pend": "○"}[kind]
                rows.append(f'<div class="step {kind}"><span class="ic">{icon}</span><span>{esc(name)} '
                            f'<small>{esc(detail)}</small></span></div>')
            ph.markdown('<div class="card">' + "".join(rows) + "</div>", unsafe_allow_html=True)

        paint()
        error = None
        try:
            for ev in run_pipeline(inp):
                if ev["step"] == "result":
                    st.session_state.result = (ev["plan"], ev["trace"])
                    st.session_state.pop("error", None)
                    break
                state[ev["step"]] = ("run" if ev["state"] == "start" else "done", ev["detail"])
                paint()
        except LLMError as e:
            error = ("The AI service could not be reached right now. This is usually a temporary rate limit — "
                     "please try again in a minute.", str(e))
        except Exception as e:  # keep the app alive, show a clean message
            log.exception("pipeline failed")
            error = ("Something went wrong while preparing your plan. Please try again.", f"{type(e).__name__}: {e}")
        if error:
            st.session_state.pop("result", None)
            st.session_state.error = error
        ph.empty()
        st.rerun()


def section(title: str):
    return f'<div class="sec"><span class="dot"></span>{esc(title)}</div>'


def src_chips(ids):
    return "".join(f'<span class="src">📄 {esc(i)}</span>' for i in ids)


def render(plan, trace):
    L = LABELS[plan["language"]]
    rtl = plan["language"] == "Urdu"
    orch = trace["orchestrator"]
    chips = (f'<span class="chip">Intent<b>{esc(orch["intent"].replace("_", " ").title())}</b></span>'
             f'<span class="chip">Agents used<b>{len(trace["agent_results"])}</b></span>'
             f'<span class="chip">Sources<b>{len(plan["sources"])}</b></span>'
             f'<span class="chip">Time<b><bdi>{trace["seconds"]} sec</bdi></b></span>')
    html = [f'<div class="{"rtl" if rtl else ""}">', chips,
            section(L["summary"]), f'<div class="card summary">{esc(plan["problem_summary"])}</div>']

    if not plan["evidence_sufficient"]:
        html.append(f'<div class="warn strong">⚠️ {esc(plan["warnings"][0])}</div>')

    if plan["possible_factors"]:
        html.append(section(L["factors"]))
        for f in plan["possible_factors"]:
            html.append(f'<div class="card"><b>{esc(f["factor"])}</b>'
                        + (f'<div class="why">{esc(f.get("why", ""))}</div>' if f.get("why") else "")
                        + src_chips(f["source_ids"]) + "</div>")

    html.append(section(L["actions"]))
    for i, a in enumerate(plan["priority_actions"], 1):
        k = 1 if i <= 2 else 2 if i <= 4 else 3
        html.append(f'<div class="card act"><div class="num p{min(i, 3) if i <= 3 else 0}">{i}</div><div>'
                    f'<b>{esc(a["action"])}</b><span class="tag t{k}">{esc(L["t" + str(k)])}</span>'
                    + (f'<div class="why">{esc(a.get("reason", ""))}</div>' if a.get("reason") else "")
                    + src_chips(a["source_ids"]) + "</div></div>")

    if plan["information_needed"]:
        html.append(section(L["info"]))
        html.append('<div class="card">' + "".join(f'<div class="chk">☐ {esc(i)}</div>'
                                                   for i in plan["information_needed"]) + "</div>")

    warns = plan["warnings"][1:] if not plan["evidence_sufficient"] else plan["warnings"]
    html.append(section(L["warn"]))
    html += [f'<div class="warn">⚠️ {esc(w)}</div>' for w in warns]
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)

    w = trace["tools"].get("weather", {})
    if w.get("ok"):
        st.markdown(section("🌦️ Weather for " + w["location"].title()), unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rain last 7 days", f'{w["past7_rain_mm"]} mm')
        m2.metric("Rain next 7 days", f'{w["next7_rain_mm"]} mm')
        m3.metric("Max temp", f'{w["next7_tmax_c"]:.0f} °C')
        m4.metric("Min temp", f'{w["next7_tmin_c"]:.0f} °C')
        with st.expander("7-day forecast"):
            st.dataframe([{"Date": d["date"], "Max °C": d["tmax"], "Min °C": d["tmin"], "Rain mm": d["rain"]}
                          for d in w["forecast"]], hide_index=True, use_container_width=True)
        st.caption("Source: Open-Meteo. A forecast for the location, not for a specific field.")

    st.markdown(section(L["src"]), unsafe_allow_html=True)
    if plan["sources_note"]:
        st.caption(L["retrieved"])
    if not plan["sources"]:
        st.write("No supporting documents were found in the current knowledge base for this problem.")
    for s in plan["sources"]:
        with st.expander(f"📄 {s['title']}"):
            st.write(s["text"])
            st.caption(f"{s['id']} · {s['source']} · relevance {s['score']}")

    with st.expander("🧩 How this plan was made"):
        st.write(f"**Understood as:** {orch['english_problem']}")
        st.write("**Agents:** " + ", ".join(orch["agents"]))
        if trace["models"]:
            st.write("**AI model:** " + ", ".join(trace["models"]))
        optional = [f"{n}: {'used' if t.get('ok') else 'unavailable'}" for n, t in trace["tools"].items()]
        if optional:
            st.write("**Optional data:** " + " · ".join(optional))
        if trace["errors"]:
            st.warning(f"{len(trace['errors'])} agent(s) could not finish; the plan uses the rest.")

    st.markdown("<br>", unsafe_allow_html=True)
    fb = st.feedback("thumbs", key=f"fb_{trace['seconds']}")
    if fb is not None:
        st.toast("Thanks for your feedback!")


with right:
    if st.session_state.get("error"):
        msg, detail = st.session_state.error
        with out:
            st.error(msg, icon="⚠️")
            with st.expander("Technical details"):
                st.code(detail)
    elif st.session_state.get("result"):
        with out:
            render(*st.session_state.result)
    elif not submit:
        with out:
            st.markdown('<div class="empty"><div class="big">🌱</div><h3>Your action plan will appear here</h3>'
                        '<p>Describe your crop, water or produce problem on the left and our AI agents will '
                        'prepare a prioritised, evidence-backed plan.</p></div>', unsafe_allow_html=True)
