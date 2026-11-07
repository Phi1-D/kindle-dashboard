"""Draws the dashboard as a 600x800 greyscale PNG for a Kindle 7th gen (KT2)."""
import datetime as dt
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 600, 800
M = 24  # side margin
BLACK, DARK, MID, LIGHT, WHITE = 0, 60, 130, 215, 255

FONT_DIR = os.environ.get("FONT_DIR", "/usr/share/fonts/truetype/dejavu")


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def text_w(d, s, f):
    return d.textlength(s, font=f)


def fit(d, s, f, max_w):
    """Truncate with an ellipsis so the text fits max_w pixels."""
    if text_w(d, s, f) <= max_w:
        return s
    while s and text_w(d, s + "…", f) > max_w:
        s = s[:-1]
    return s.rstrip() + "…"


def wrap(d, s, f, max_w, max_lines):
    words, lines, cur = s.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if text_w(d, trial, f) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = fit(d, lines[-1] + " …", f, max_w)
    return lines


def section_title(d, y, label):
    f = font(17, bold=True)
    d.text((M, y), label.upper(), font=f, fill=DARK)
    x = M + text_w(d, label.upper(), f) + 10
    d.line([(x, y + 11), (W - M, y + 11)], fill=LIGHT, width=2)
    return y + 30


def christmas_countdown(today):
    xmas = dt.date(today.year, 12, 25)
    if today > xmas:
        xmas = dt.date(today.year + 1, 12, 25)
    n = (xmas - today).days
    if n == 0:
        return "Happy Christmas!"
    if n == 1:
        return "1 sleep till Christmas!"
    return f"{n} sleeps till Christmas"



def draw_day(d, y, label, events, limit):
    """Draw one day's events: all-day items as compact pills, timed items as rows.
    Stops before `limit` and adds '+N more' if anything didn't fit. Returns new y."""
    d.text((M, y), label, font=font(17, bold=True), fill=MID)
    y += 24
    if not events:
        d.text((M + 8, y), "Nothing on", font=font(18), fill=MID)
        return y + 26

    all_day = [e for e in events if not e["time"]]
    timed = [e for e in events if e["time"]]
    hidden = 0
    pill_f, PH, GAP = font(16, bold=True), 28, 6

    # All-day pills, wrapping across the width
    x = M
    for ev in all_day:
        t = fit(d, ev["title"], pill_f, W - 2 * M - 20)
        pw = text_w(d, t, pill_f) + 20
        if x + pw > W - M:  # wrap to next line
            x, y = M, y + PH + GAP
        if y + PH > limit - 22:
            hidden += 1
            continue
        d.rounded_rectangle([x, y, x + pw, y + PH], radius=PH // 2, outline=BLACK, width=2)
        d.text((x + 10, y + 4), t, font=pill_f, fill=BLACK)
        x += pw + GAP
    if all_day:
        y += PH + GAP + 2

    # Timed rows
    ev_f, time_f = font(19), font(19, bold=True)
    for ev in timed:
        if y + 26 > limit - 22:
            hidden += 1
            continue
        d.text((M + 4, y), ev["time"], font=time_f, fill=BLACK)
        d.text((M + 80, y), fit(d, ev["title"], ev_f, W - 2 * M - 80), font=ev_f, fill=BLACK)
        y += 26

    if hidden:
        d.text((M + 4, y), f"+{hidden} more", font=font(15), fill=MID)
        y += 20
    return y

def render(data, out_path):
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    now = data["now"]
    today = now.date()

    # ---- Header bar ----
    d.rectangle([0, 0, W, 58], fill=BLACK)
    d.text((M, 12), now.strftime("%A %-d %B"), font=font(28, bold=True), fill=WHITE)
    upd = f"Updated {now:%H:%M}"
    f = font(15)
    d.text((W - M - text_w(d, upd, f), 22), upd, font=f, fill=LIGHT)

    # ---- Weather now ----
    w = data["weather"]
    y = 72
    d.text((M, y - 4), w["now_glyph"], font=font(78), fill=BLACK)
    d.text((M + 96, y - 6), f"{w['now_temp']}°", font=font(72, bold=True), fill=BLACK)
    d.text((M + 96, y + 78), fit(d, w["now_label"], font(20), 230), font=font(20), fill=DARK)
    today_fc = w["days"][0]
    d.text((M + 96, y + 104), f"High {today_fc['hi']}°  Low {today_fc['lo']}°  Wind {w['wind']} mph",
           font=font(16), fill=DARK)

    # Sunrise / sunset (right column)
    rx = 410
    d.text((rx, y + 2), "Sunrise", font=font(15), fill=MID)
    d.text((rx, y + 20), "☀↑ " + w["sunrise"], font=font(26, bold=True), fill=BLACK)
    d.text((rx, y + 58), "Sunset", font=font(15), fill=MID)
    d.text((rx, y + 76), "☀↓ " + w["sunset"], font=font(26, bold=True), fill=BLACK)

    # Rain chance next 12h
    y = 210
    if w["rain_next"]:
        d.text((M, y), "Rain chance", font=font(15, bold=True), fill=DARK)
        x = M + 110
        for t, p in w["rain_next"]:
            d.text((x, y), f"{t} {p}%", font=font(15), fill=BLACK if p >= 50 else DARK)
            x += 112

    # 3-day forecast
    y = 240
    col = (W - 2 * M) // 3
    for i, day in enumerate(w["days"][1:4]):
        x = M + i * col
        d.rounded_rectangle([x + 2, y, x + col - 6, y + 74], radius=10, outline=LIGHT, width=2)
        d.text((x + 14, y + 6), day["date"].strftime("%a"), font=font(18, bold=True), fill=BLACK)
        d.text((x + 14, y + 32), day["glyph"], font=font(30), fill=BLACK)
        d.text((x + 56, y + 32), f"{day['hi']}°/{day['lo']}°", font=font(18), fill=BLACK)
        d.text((x + 56, y + 54), f"rain {day['rain']}%", font=font(13), fill=DARK)

    # ---- Bottom strips (laid out first so the calendar can take all remaining space) ----
    kid_top = H - 74
    chores = data["chores"]
    chores_y = kid_top - 34 if chores else None
    cal_bottom = (chores_y if chores else kid_top) - 8

    # ---- Calendar ----
    y = section_title(d, 334, "Family calendar")
    days = list(data["calendar"].items())
    for i, (day, events) in enumerate(days):
        # Today gets priority; leave at least ~80px for each later day
        limit = cal_bottom - 80 * (len(days) - 1 - i)
        label = "Today" if day == today else ("Tomorrow" if day == today + dt.timedelta(days=1) else day.strftime("%A"))
        y = draw_day(d, y, label, events, limit) + 4

    # ---- Chores: one compact line ----
    if chores:
        d.line([(M, chores_y - 6), (W - M, chores_y - 6)], fill=LIGHT, width=2)
        f_lab, f = font(17, bold=True), font(17)
        d.text((M, chores_y), "Chores", font=f_lab, fill=DARK)
        x0 = M + text_w(d, "Chores", f_lab) + 12
        d.text((x0, chores_y), fit(d, "  ·  ".join(chores), f, W - M - x0), font=f, fill=BLACK)

    # ---- Kids strip ----
    d.rounded_rectangle([M - 6, kid_top, W - M + 6, H - 8], radius=12, fill=LIGHT)
    d.text((M + 6, kid_top + 6), "★ " + christmas_countdown(today), font=font(21, bold=True), fill=BLACK)
    if data.get("fact"):
        d.text((M + 6, kid_top + 36), fit(d, data["fact"], font(17), W - 2 * M - 12), font=font(17), fill=BLACK)

    img.save(out_path, "PNG", optimize=True)
    return out_path
