"""Build the dashboard image.

Usage:
  python dashboard/main.py              # live data (needs ICAL_URL env var)
  python dashboard/main.py --sample     # dummy data, for checking the layout
"""
import datetime as dt
import os
import sys
import json
import traceback

sys.path.insert(0, os.path.dirname(__file__))
import fetch  # noqa: E402
from render import render  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "public")


def sample_data(now):
    today = now.date()
    tmw = today + dt.timedelta(days=1)
    days = []
    for i, (g, l, hi, lo, r) in enumerate([("☁", "Partly cloudy", 11, 5, 20), ("☂", "Rain", 10, 6, 80),
                                            ("☁", "Overcast", 9, 4, 30), ("☀", "Clear", 8, 1, 5)]):
        days.append({"date": today + dt.timedelta(days=i), "glyph": g, "label": l, "hi": hi, "lo": lo, "rain": r})
    return {
        "now": now,
        "weather": {"now_temp": 9, "now_glyph": "☁", "now_label": "Partly cloudy", "wind": 12,
                    "sunrise": "07:16", "sunset": "16:22",
                    "rain_next": [("15:00", 20), ("18:00", 55), ("21:00", 40), ("00:00", 10)], "days": days},
        "calendar": {
            today: [{"time": "", "title": "Bins: blue (recycling)"},
                    {"time": "", "title": "School dinners"},
                    {"time": "", "title": "Mufti day"},
                    {"time": "10:00", "title": "Swimming lessons"},
                    {"time": "14:30", "title": "Birthday party – soft play"},
                    {"time": "18:00", "title": "Dinner at Nan's"}],
            tmw: [{"time": "", "title": "PE kit – Year 4"},
                  {"time": "", "title": "Packed lunch"},
                  {"time": "", "title": "Library books back"},
                  {"time": "09:30", "title": "Dog to groomer"},
                  {"time": "16:00", "title": "Football training"}],
            today + dt.timedelta(days=2): [{"time": "", "title": "School dinners"},
                                           {"time": "19:00", "title": "Parents' evening"}],
        },
        "chores": ["Empty dishwasher", "Feed the dog", "Tidy bedrooms", "Hoover lounge", "Water plants"],
        "fact": "An octopus has three hearts and blue blood.",
    }


def live_data(now):
    data = {"now": now}
    errors = []
    try:
        data["weather"] = fetch.weather()
    except Exception:
        errors.append("weather")
        traceback.print_exc()
        raise  # weather is the core of the dashboard; fail the run so the last good image stays up
    url = os.environ.get("ICAL_URL", "").strip()
    if not url:
        data["calendar"] = {now.date(): [{"time": "", "title": "Calendar not connected yet"}]}
    else:
      try:
        data["calendar"] = fetch.calendar(url, days_ahead=3)
      except Exception:
        errors.append("calendar")
        traceback.print_exc()
        data["calendar"] = {now.date(): [{"time": "", "title": "Calendar unavailable - will retry"}]}
    data["chores"] = fetch.chores(os.path.join(ROOT, "chores.txt"))
    data["fact"] = fetch.kid_fact(os.path.join(ROOT, "dashboard", "facts.txt"), now.date())
    return data


def to_json(data):
    """Data for the colour kitchen page (dates as ISO strings)."""
    w = dict(data["weather"])
    w["days"] = [dict(d, date=d["date"].isoformat()) for d in w["days"]]
    return {
        "generated": data["now"].isoformat(timespec="minutes"),
        "weather": w,
        "calendar": [{"date": d.isoformat(), "events": ev} for d, ev in data["calendar"].items()],
        "chores": data["chores"],
        "fact": data["fact"],
        "build": os.environ.get("GITHUB_SHA", "")[:7],
    }


if __name__ == "__main__":
    now = dt.datetime.now(fetch.TZ)
    try:
        data = sample_data(now) if "--sample" in sys.argv else live_data(now)
    except Exception:
        # Weather still unreachable after retries: publish nothing, so the screens keep the last good version.
        print("::warning::Weather service unreachable after retries; keeping the last published dashboard.")
        sys.exit(0)
    os.makedirs(OUT_DIR, exist_ok=True)
    # Kindle shows today + tomorrow; the kitchen page gets everything
    kindle = dict(data, calendar=dict(list(data["calendar"].items())[:2]))
    out = render(kindle, os.path.join(OUT_DIR, "dash.png"))
    with open(os.path.join(OUT_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(to_json(data), f, ensure_ascii=False)
    print("Wrote", out, "and data.json")
