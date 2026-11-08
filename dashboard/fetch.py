"""Data sources: weather + sun times (Open-Meteo), family calendar (iCal), chores (text file)."""
import datetime as dt
import json
import os
import urllib.request
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/London")

# East Coventry (approximate). Change if you move the dashboard.
LAT, LON = 52.41, -1.47

# WMO weather codes -> (glyph, short label)
WMO = {
    0: ("☀", "Clear"), 1: ("☀", "Mostly clear"), 2: ("☁", "Partly cloudy"), 3: ("☁", "Overcast"),
    45: ("☁", "Fog"), 48: ("☁", "Freezing fog"),
    51: ("☂", "Light drizzle"), 53: ("☂", "Drizzle"), 55: ("☂", "Heavy drizzle"),
    56: ("☂", "Freezing drizzle"), 57: ("☂", "Freezing drizzle"),
    61: ("☂", "Light rain"), 63: ("☂", "Rain"), 65: ("☂", "Heavy rain"),
    66: ("☂", "Freezing rain"), 67: ("☂", "Freezing rain"),
    71: ("❄", "Light snow"), 73: ("❄", "Snow"), 75: ("❄", "Heavy snow"), 77: ("❄", "Snow grains"),
    80: ("☂", "Showers"), 81: ("☂", "Showers"), 82: ("☂", "Heavy showers"),
    85: ("❄", "Snow showers"), 86: ("❄", "Snow showers"),
    95: ("⚡", "Thunderstorm"), 96: ("⚡", "Thunder + hail"), 99: ("⚡", "Thunder + hail"),
}


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "family-kindle-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,weather_code,wind_speed_10m"
        "&hourly=precipitation_probability"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max,sunrise,sunset"
        "&timezone=Europe%2FLondon&forecast_days=4&wind_speed_unit=mph"
    )
    d = json.loads(_get(url))
    cur, daily, hourly = d["current"], d["daily"], d["hourly"]
    now = dt.datetime.now(TZ)

    # Rain chance for the next 12 hours, in 3-hour steps (useful for school run / pickup)
    rain_next = []
    for t, p in zip(hourly["time"], hourly["precipitation_probability"]):
        ts = dt.datetime.fromisoformat(t).replace(tzinfo=TZ)
        if now <= ts <= now + dt.timedelta(hours=12) and ts.hour % 3 == 0:
            rain_next.append((ts.strftime("%H:%M"), p))

    days = []
    for i in range(len(daily["time"])):
        code = daily["weather_code"][i]
        days.append({
            "date": dt.date.fromisoformat(daily["time"][i]),
            "glyph": WMO.get(code, ("?", "?"))[0],
            "label": WMO.get(code, ("?", "Unknown"))[1],
            "hi": round(daily["temperature_2m_max"][i]),
            "lo": round(daily["temperature_2m_min"][i]),
            "rain": daily["precipitation_probability_max"][i],
        })
    code = cur["weather_code"]
    return {
        "now_temp": round(cur["temperature_2m"]),
        "now_glyph": WMO.get(code, ("?", "?"))[0],
        "now_label": WMO.get(code, ("?", "Unknown"))[1],
        "wind": round(cur["wind_speed_10m"]),
        "sunrise": daily["sunrise"][0][-5:],
        "sunset": daily["sunset"][0][-5:],
        "rain_next": rain_next[:4],
        "days": days,
    }


def calendar(ics_url, days_ahead=2):
    """Events for today and tomorrow from a shared iCloud calendar link."""
    import icalendar
    import recurring_ical_events

    ics_url = ics_url.replace("webcal://", "https://")
    cal = icalendar.Calendar.from_ical(_get(ics_url, timeout=30))
    today = dt.datetime.now(TZ).date()
    out = {today + dt.timedelta(days=i): [] for i in range(days_ahead)}
    start = dt.datetime.combine(today, dt.time.min, TZ)
    end = start + dt.timedelta(days=days_ahead)
    for ev in recurring_ical_events.of(cal).between(start, end):
        s = ev["DTSTART"].dt
        all_day = not isinstance(s, dt.datetime)
        if all_day:
            e = ev.get("DTEND").dt if ev.get("DTEND") else s + dt.timedelta(days=1)
            for k in out:  # multi-day all-day events show on each day they cover
                if s <= k < e:
                    out[k].append({"time": "", "title": str(ev.get("SUMMARY", "")).strip()})
        else:
            s = s.astimezone(TZ)
            if s.date() in out:
                out[s.date()].append({"time": s.strftime("%H:%M"), "title": str(ev.get("SUMMARY", "")).strip()})
    for k in out:
        out[k].sort(key=lambda x: (x["time"] != "", x["time"]))  # all-day first
    return out


def chores(path):
    """One chore per line. Lines starting with # are ignored. Written by the iPhone Shortcut."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        lines = [l.strip().lstrip("-•*◦☐").strip() for l in f]
    items = [l for l in lines if l and not l.startswith("#")]
    if items and items[0].lower() == "chores":  # Apple Notes includes the note title as the first line
        items = items[1:]
    return items


def kid_fact(path, day):
    with open(path, encoding="utf-8") as f:
        facts = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    if not facts:
        return ""
    import random
    random.Random(2026).shuffle(facts)  # fixed shuffle: mixes animals/food/countries, same order every day
    return facts[day.toordinal() % len(facts)]
