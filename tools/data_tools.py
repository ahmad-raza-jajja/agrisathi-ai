"""Open-Meteo weather tools (free, no API key). Every function fails soft and returns {"ok": False,...}."""
import requests

from utils import config
from utils.logging import get_logger

log = get_logger("data_tools")

# Offline coordinates for common Pakistani locations so weather works even if geocoding fails.
KNOWN_PLACES = {
    "bahawalpur": (29.3956, 71.6836), "multan": (30.1575, 71.5249), "lahore": (31.5204, 74.3587),
    "faisalabad": (31.4504, 73.1350), "karachi": (24.8607, 67.0011), "islamabad": (33.6844, 73.0479),
    "rawalpindi": (33.5651, 73.0169), "peshawar": (34.0151, 71.5249), "quetta": (30.1798, 66.9750),
    "sukkur": (27.7052, 68.8574), "hyderabad": (25.3960, 68.3578), "sargodha": (32.0836, 72.6711),
    "rahim yar khan": (28.4202, 70.2952), "dera ghazi khan": (30.0489, 70.6455),
    "sahiwal": (30.6682, 73.1114), "gujranwala": (32.1877, 74.1945), "mardan": (34.1986, 72.0404),
}


def geocode(place: str):
    if not place:
        return None
    key = place.strip().lower().split(",")[0].strip()
    if key in KNOWN_PLACES:
        return KNOWN_PLACES[key]
    if not config.ENABLE_EXTERNAL_DATA:
        return None
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": key, "count": 1, "country_code": "PK"},
            timeout=config.HTTP_TIMEOUT,
        )
        res = r.json().get("results")
        if res:
            return res[0]["latitude"], res[0]["longitude"]
    except Exception as e:
        log.warning("geocode failed: %s", e)
    return None


def get_weather(location: str) -> dict:
    """7-day forecast + last 7 days summary for the location."""
    if not config.ENABLE_EXTERNAL_DATA:
        return {"ok": False, "reason": "External data disabled"}
    coords = geocode(location)
    if not coords:
        return {"ok": False, "reason": f"Could not locate '{location}'"}
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": coords[0], "longitude": coords[1], "timezone": "auto",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "past_days": 7, "forecast_days": 7,
            },
            timeout=config.HTTP_TIMEOUT,
        )
        r.raise_for_status()
        d = r.json()["daily"]
        n_past = 7
        tmax, tmin, rain = d["temperature_2m_max"], d["temperature_2m_min"], d["precipitation_sum"]
        fut_rain, past_rain = sum(x or 0 for x in rain[n_past:]), sum(x or 0 for x in rain[:n_past])
        return {
            "ok": True, "source": "Open-Meteo (open-meteo.com)", "location": location,
            "coords": coords,
            "past7_rain_mm": round(past_rain, 1), "next7_rain_mm": round(fut_rain, 1),
            "next7_tmax_c": max(x for x in tmax[n_past:] if x is not None),
            "next7_tmin_c": min(x for x in tmin[n_past:] if x is not None),
            "forecast": [
                {"date": d["time"][i], "tmax": tmax[i], "tmin": tmin[i], "rain": rain[i] or 0}
                for i in range(n_past, len(d["time"]))
            ],
            "summary": (
                f"Last 7 days rain: {past_rain:.1f} mm. Next 7 days forecast: rain {fut_rain:.1f} mm, "
                f"max temp {max(x for x in tmax[n_past:] if x is not None):.0f}°C, "
                f"min temp {min(x for x in tmin[n_past:] if x is not None):.0f}°C."
            ),
        }
    except Exception as e:
        log.warning("weather failed: %s", e)
        return {"ok": False, "reason": f"Weather service unavailable ({type(e).__name__})"}
