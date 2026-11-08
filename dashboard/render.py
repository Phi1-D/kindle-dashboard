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


def days_to_christmas(today):
    xmas = dt.date(today.year, 12, 25)
    if today > xmas:
        xmas = dt.date(today.year + 1, 12, 25)
    return (xmas - today).days


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

    # ---- Weather now (large) ----
    w = data["weather"]
    y = 64
    d.text((M, y), w["now_glyph"], font=font(90), fill=BLACK)
    d.text((M + 112, y - 6), f"{w['now_temp']}°", font=font(88, bold=True), fill=BLACK)
    d.text((M + 114, y + 96), fit(d, w["now_label"], font(24), 270), font=font(24), fill=BLACK)
    today_fc = w["days"][0]
    d.text((M, y + 132), f"High {today_fc['hi']}°   Low {today_fc['lo']}°   Wind {w['wind']} mph",
           font=font(21, bold=True), fill=DARK)

    # Sunrise / sunset (right column)
    rx = 420
    d.text((rx, y + 2), "Sunrise", font=font(18), fill=DARK)
    d.text((rx, y + 24), w["sunrise"], font=font(34, bold=True), fill=BLACK)
    d.text((rx, y + 68), "Sunset", font=font(18), fill=DARK)
    d.text((rx, y + 90), w["sunset"], font=font(34, bold=True), fill=BLACK)

    # Rain chance next 12h
    y = 230
    if w["rain_next"]:
        d.text((M, y), "Rain", font=font(20, bold=True), fill=DARK)
        x = M + 66
        for t, p in w["rain_next"][:3]:
            d.text((x, y), f"{t} {p}%", font=font(20, bold=p >= 50), fill=BLACK)
            x += 160

    # 3-day forecast
    y = 264
    col = (W - 2 * M) // 3
    for i, day in enumerate(w["days"][1:4]):
        x = M + i * col
        d.rounded_rectangle([x + 2, y, x + col - 6, y + 96], radius=12, outline=MID, width=2)
        d.text((x + 14, y + 8), day["date"].strftime("%a"), font=font(23, bold=True), fill=BLACK)
        d.text((x + 12, y + 42), day["glyph"], font=font(40), fill=BLACK)
        d.text((x + 66, y + 38), f"{day['hi']}°/{day['lo']}°", font=font(25, bold=True), fill=BLACK)
        d.text((x + 66, y + 68), f"rain {day['rain']}%", font=font(18), fill=BLACK)

    # ---- Kids boxes at the bottom: countdown | fact ----
    kid_top = H - 98
    cal_bottom = kid_top - 10

    # ---- Calendar ----
    y = section_title(d, 374, "Family calendar")
    days = list(data["calendar"].items())
    for i, (day, events) in enumerate(days):
        # Today gets priority; leave at least ~80px for each later day
        limit = cal_bottom - 80 * (len(days) - 1 - i)
        label = "Today" if day == today else ("Tomorrow" if day == today + dt.timedelta(days=1) else day.strftime("%A"))
        y = draw_day(d, y, label, events, limit) + 4

    # Countdown: black box, white text
    xw = 222
    d.rounded_rectangle([M - 6, kid_top, M - 6 + xw, H - 8], radius=12, fill=BLACK)
    n = days_to_christmas(today)
    if n == 0:
        l1, l2 = "Happy", "Christmas!"
    else:
        l1, l2 = f"★ {n} sleep{'s' if n != 1 else ''}", "till Christmas"
    d.text((M + 8, kid_top + 12), l1, font=font(30, bold=True), fill=WHITE)
    d.text((M + 8, kid_top + 52), l2, font=font(21), fill=WHITE)

    # Fact: light grey box
    fx = M - 6 + xw + 10
    d.rounded_rectangle([fx, kid_top, W - M + 6, H - 8], radius=12, fill=LIGHT)
    d.text((fx + 12, kid_top + 8), "DID YOU KNOW?", font=font(14, bold=True), fill=DARK)
    if data.get("fact"):
        ly = kid_top + 30
        for ln in wrap(d, data["fact"], font(18), W - M + 6 - fx - 24, 3):
            d.text((fx + 12, ly), ln, font=font(18), fill=BLACK)
            ly += 22

    img.save(out_path, "PNG", optimize=True)
    return out_path
