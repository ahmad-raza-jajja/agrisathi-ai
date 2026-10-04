"""FAO WaPOR v3 (optional context). PRD: external data must never break the core workflow.

WaPOR v3 is served from the FAO GISMGR catalog API (no token needed per FAO docs). For the MVP we only
check that the catalog is reachable and list a few available water-productivity datasets, so the plan can
mention WaPOR as an optional follow-up data source. We do NOT invent water-productivity numbers.
"""
import requests

from utils import config
from utils.logging import get_logger

log = get_logger("wapor")
CATALOG = "https://data.apps.fao.org/gismgr/api/v2/catalog/workspaces/WAPOR-3/mapsets"


def get_wapor_context() -> dict:
    if not config.ENABLE_EXTERNAL_DATA:
        return {"ok": False, "reason": "External data disabled"}
    try:
        r = requests.get(CATALOG, params={"overview": "true"}, timeout=config.HTTP_TIMEOUT)
        r.raise_for_status()
        resp = r.json().get("response", [])
        items = resp if isinstance(resp, list) else resp.get("items", [])
        names = [i.get("caption") or i.get("code") for i in items[:5] if isinstance(i, dict)]
        return {
            "ok": True,
            "source": "FAO WaPOR v3 catalog (data.apps.fao.org)",
            "datasets": [n for n in names if n],
            "summary": "FAO WaPOR v3 water-productivity datasets are reachable; field-level values are not "
                       "pulled in this MVP.",
        }
    except Exception as e:
        log.warning("WaPOR unavailable: %s", e)
        return {"ok": False, "reason": f"WaPOR unavailable ({type(e).__name__})"}
