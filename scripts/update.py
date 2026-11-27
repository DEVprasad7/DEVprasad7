#!/usr/bin/env python3
"""
Generates the living parts of the profile README:
  assets/header.svg   typewriter header + season-aware particles (rain / heat / leaves / mist)
  assets/pokemon.svg  10 random Pokemon of the day; one "star" acts out a mood (fly / sneak / jump...)
  assets/quote.svg    quote of the day, typewriter style
  assets/stats.svg    monochrome GitHub stats (repos, stars, followers, languages)

Runs daily in GitHub Actions. Standard library only.
Date logic uses IST so the change happens at midnight in India.
"""
import base64, datetime as dt, html, itertools, json, os, random, textwrap, urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

TODAY = dt.datetime.now(ZoneInfo("Asia/Kolkata")).date()
RNG = random.Random(TODAY.toordinal())  # same day -> same result, new day -> new result

FONT = "'JetBrains Mono','Fira Code','SF Mono',Consolas,'Courier New',monospace"
CW = 0.6  # monospace glyph width in em
_ids = itertools.count(1)
esc = html.escape


# ───────────────────────── calendar: seasons + Indian festivals ─────────────────────────
def season(d: dt.date):
    m = d.month
    if m in (3, 4, 5):   return "summer"
    if m in (6, 7, 8, 9): return "monsoon"
    if m in (10, 11):    return "autumn"
    return "winter"

SEASON_LABEL = {"summer": "summer", "monsoon": "monsoon", "autumn": "post-monsoon", "winter": "winter"}

# (month, day): (name, greeting, glyph, mood)
FIXED = {
    (1, 1):   ("New Year", "Happy New Year. Ship something new.", "🎆", "jump"),
    (1, 14):  ("Makar Sankranti", "Tilgul ghya, god god bola!", "🪁", "fly"),
    (1, 26):  ("Republic Day", "Happy Republic Day. Jai Hind!", "🇮🇳", "fly"),
    (8, 15):  ("Independence Day", "Happy Independence Day. Jai Hind!", "🇮🇳", "fly"),
    (9, 5):   ("Teachers' Day", "Thank a teacher today.", "📚", "dance"),
    (10, 2):  ("Gandhi Jayanti", "Simple living, high thinking.", "🕊️", "float"),
    (11, 14): ("Children's Day", "Stay curious like a kid.", "🎈", "jump"),
    (12, 25): ("Christmas", "Merry Christmas!", "🎄", "dance"),
    (12, 31): ("New Year's Eve", "Last commit of the year.", "🎆", "spin"),
}

# Moveable festivals: (start, end, name, greeting, glyph, mood)
# ⚠ Dates change every year (lunar calendar). Double-check and add new years yourself.
D = dt.date
MOVEABLE = [
    (D(2026, 3, 4),   D(2026, 3, 4),   "Holi", "Happy Holi! Bura na mano, Holi hai!", "🎨", "dance"),
    (D(2026, 9, 14),  D(2026, 9, 24),  "Ganesh Chaturthi", "Ganpati Bappa Morya!", "🌺", "dance"),
    (D(2026, 11, 6),  D(2026, 11, 10), "Diwali", "Shubh Deepavali!", "🪔", "jump"),
    (D(2027, 3, 22),  D(2027, 3, 22),  "Holi", "Happy Holi! Bura na mano, Holi hai!", "🎨", "dance"),
    (D(2027, 10, 27), D(2027, 10, 31), "Diwali", "Shubh Deepavali!", "🪔", "jump"),
]

def all_events():
    ev = list(MOVEABLE)
    for y in (TODAY.year, TODAY.year + 1):
        for (m, d), (n, g, gl, mo) in FIXED.items():
            ev.append((D(y, m, d), D(y, m, d), n, g, gl, mo))
        pd = D.fromordinal(D(y, 1, 1).toordinal() + 255)  # 256th day = Programmers' Day
        ev.append((pd, pd, "Programmers' Day", "Hello, World. Happy Programmers' Day!", "💻", "dance"))
    return sorted(ev)

def active_and_next():
    ev = all_events()
    active = next((e for e in ev if e[0] <= TODAY <= e[1]), None)
    upcoming = next((e for e in ev if e[0] > TODAY), None)
    return active, upcoming


# ───────────────────────── SVG helpers ─────────────────────────
def typed(text, x, y, size, begin, speed=0.05, weight=400, opacity=1.0):
    """Typewriter text. Returns (svg, end_time). Uses a stepped clip-path reveal."""
    n = len(text)
    w = n * CW * size
    cid = f"c{next(_ids)}"
    steps = ";".join(f"{w * i / n:.1f}" for i in range(n + 1))
    dur = max(n * speed, 0.1)
    svg = (
        f'<clipPath id="{cid}"><rect x="{x}" y="{y - size}" height="{size * 1.6:.0f}" width="0">'
        f'<animate attributeName="width" values="{steps}" dur="{dur:.2f}s" begin="{begin:.2f}s" '
        f'calcMode="discrete" fill="freeze"/></rect></clipPath>'
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="#fff" '
        f'fill-opacity="{opacity}" textLength="{w:.1f}" lengthAdjust="spacing" '
        f'clip-path="url(#{cid})" xml:space="preserve">{esc(text)}</text>'
    )
    return svg, begin + dur

def cursor(x, y, size, begin):
    return (
        f'<rect x="{x:.1f}" y="{y - size * 0.85:.1f}" width="{CW * size:.1f}" height="{size:.1f}" fill="#fff" opacity="0">'
        f'<animate attributeName="opacity" values="0;1" dur="1s" begin="{begin:.2f}s" '
        f'repeatCount="indefinite" calcMode="discrete"/></rect>'
    )

def wrap_svg(w, h, body, css=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">'
        f'<style>{css}</style>'
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="#000" stroke="#fff" stroke-opacity=".35"/>'
        f'{body}</svg>'
    )

def window_dots():
    return "".join(f'<circle cx="{22 + i * 16}" cy="20" r="4.5" fill="none" stroke="#fff" stroke-opacity=".5"/>' for i in range(3))


# ───────────────────────── seasonal particles ─────────────────────────
def particles(kind, w, h):
    r = random.Random(TODAY.toordinal() * 7)
    out = []
    x0 = w * 0.45  # keep the left (text) side clean
    if kind == "monsoon":
        for _ in range(38):
            x, d, b = r.uniform(x0, w), r.uniform(0.9, 1.8), -r.uniform(0, 2)
            out.append(
                f'<g><line x1="0" y1="0" x2="-4" y2="14" stroke="#fff" stroke-opacity="{r.uniform(.2, .5):.2f}"/>'
                f'<animateTransform attributeName="transform" type="translate" from="{x:.0f} -20" to="{x - 40:.0f} {h + 10}" '
                f'dur="{d:.2f}s" begin="{b:.2f}s" repeatCount="indefinite"/></g>')
    elif kind == "summer":
        out.append(f'<circle cx="{w - 90}" cy="70" r="34" fill="none" stroke="#fff" stroke-opacity=".6"/>')
        out.append(f'<circle cx="{w - 90}" cy="70" r="46" fill="none" stroke="#fff" stroke-opacity=".2" stroke-dasharray="2 6">'
                   f'<animateTransform attributeName="transform" type="rotate" from="0 {w - 90} 70" to="360 {w - 90} 70" dur="40s" repeatCount="indefinite"/></circle>')
        for _ in range(16):  # heat shimmer rising
            x, d, b = r.uniform(x0, w - 150), r.uniform(5, 9), -r.uniform(0, 8)
            out.append(
                f'<circle r="1.3" fill="#fff" fill-opacity=".4"><animateTransform attributeName="transform" type="translate" '
                f'from="{x:.0f} {h}" to="{x + 10:.0f} -10" dur="{d:.1f}s" begin="{b:.1f}s" repeatCount="indefinite"/></circle>')
    elif kind == "autumn":
        for _ in range(16):  # drifting leaves
            x, d, b = r.uniform(x0, w), r.uniform(6, 11), -r.uniform(0, 10)
            out.append(
                f'<g><rect x="-4" y="-2" width="8" height="4" rx="2" fill="#fff" fill-opacity=".45">'
                f'<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="{d / 2:.1f}s" repeatCount="indefinite"/></rect>'
                f'<animateTransform attributeName="transform" type="translate" values="{x:.0f} -10;{x - 30:.0f} {h / 2:.0f};{x + 10:.0f} {h + 10}" '
                f'dur="{d:.1f}s" begin="{b:.1f}s" repeatCount="indefinite"/></g>')
    else:  # winter: slow mist / snow dust
        for _ in range(34):
            x, d, b = r.uniform(x0, w), r.uniform(8, 16), -r.uniform(0, 16)
            out.append(
                f'<circle r="{r.uniform(.8, 2):.1f}" fill="#fff" fill-opacity="{r.uniform(.2, .5):.2f}">'
                f'<animateTransform attributeName="transform" type="translate" values="{x:.0f} -10;{x + 14:.0f} {h / 2:.0f};{x - 6:.0f} {h + 10}" '
                f'dur="{d:.1f}s" begin="{b:.1f}s" repeatCount="indefinite"/></circle>')
    return "<g>" + "".join(out) + "</g>"


# ───────────────────────── header.svg ─────────────────────────
def build_header():
    w, h = 840, 230
    s = season(TODAY)
    body = window_dots() + particles(s, w, h)
    parts, t = [], 0.4
    for text, x, y, size, wt, op in [
        ("prasad@india:~$ whoami", 28, 62, 14, 400, .55),
        ("Prasad Maskar", 28, 120, 46, 700, 1),
        ("developer · learner · builder", 28, 156, 16, 400, .85),
        (f"[ {SEASON_LABEL[s]} · {TODAY.strftime('%d %b %Y').lower()} ]", 28, 200, 12, 400, .5),
    ]:
        svg, t_end = typed(text, x, y, size, t, 0.05 if size < 40 else 0.09, wt, op)
        parts.append(svg)
        last = (x + len(text) * CW * size, y, size)
        t = t_end + 0.25
    body += "".join(parts) + cursor(last[0] + 3, last[1], last[2], t)
    (OUT / "header.svg").write_text(wrap_svg(w, h, body), encoding="utf-8")


# ───────────────────────── pokemon.svg ─────────────────────────
def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-bot"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()

def fetch_pokemon(pid):
    try:
        data = json.loads(http_get(f"https://pokeapi.co/api/v2/pokemon/{pid}"))
        img = base64.b64encode(http_get(data["sprites"]["front_default"])).decode()
        return {"id": pid, "name": data["name"], "types": [t["type"]["name"] for t in data["types"]], "img": img}
    except Exception as e:  # offline / API hiccup: still render something
        print(f"pokemon {pid} failed: {e}")
        return {"id": pid, "name": f"#{pid}", "types": [], "img": None}

def pick_mood(star, fest):
    if fest:
        return fest[5]
    t = star["types"]
    if "flying" in t: return "fly"
    if "ghost" in t or "dark" in t: return "sneak"
    if any(x in t for x in ("fire", "electric", "fighting")): return "jump"
    if any(x in t for x in ("water", "psychic", "fairy")): return "float"
    return RNG.choice(["jump", "dance", "spin", "sneak", "float"])

MOOD_SPEED = {"fly": 9, "sneak": 24, "jump": 12, "dance": 14, "spin": 11, "float": 16}
MOOD_NOTE = {"fly": "flying around", "sneak": "sneaking around...", "jump": "jumping around",
             "dance": "dancing", "spin": "twirling", "float": "floating by"}

POKE_CSS = """
.mover{animation:walk var(--d,12s) linear infinite alternate}
@keyframes walk{from{transform:translateX(0)}to{transform:translateX(560px)}}
.m{transform-box:fill-box;transform-origin:50% 100%}
.fly{animation:fly 2.4s ease-in-out infinite}
@keyframes fly{0%,100%{transform:translateY(-30px) rotate(-4deg)}50%{transform:translateY(-52px) rotate(4deg)}}
.jump{animation:jump .9s cubic-bezier(.3,.7,.4,1) infinite}
@keyframes jump{0%,100%{transform:translateY(0) scaleY(.92)}50%{transform:translateY(-55px) scaleY(1.05)}}
.sneak{animation:sneak 1.6s ease-in-out infinite;opacity:.55}
@keyframes sneak{0%,100%{transform:scaleY(1)}50%{transform:scaleY(.85)}}
.dance{animation:dance .7s ease-in-out infinite alternate}
@keyframes dance{from{transform:rotate(-10deg) translateY(0)}to{transform:rotate(10deg) translateY(-12px)}}
.spin{animation:spin 1.6s ease-in-out infinite;transform-origin:50% 50%}
@keyframes spin{0%,100%{transform:scaleX(1)}50%{transform:scaleX(-1)}}
.float{animation:float 3s ease-in-out infinite}
@keyframes float{0%,100%{transform:translateY(-8px)}50%{transform:translateY(-26px)}}
image{image-rendering:pixelated}
"""

def build_pokemon():
    w, h = 840, 330
    ids = RNG.sample(range(1, 1026), 10)
    mons = [fetch_pokemon(i) for i in ids]
    star = mons[0]
    active, upcoming = active_and_next()
    mood = pick_mood(star, active)

    body = window_dots()
    title, t = typed(f"$ ./pokedex --random 10 --date {TODAY.isoformat()}", 28, 52, 12, 0.3, 0.03, 400, .6)
    body += title

    # stage
    ground = 205
    body += f'<line x1="24" y1="{ground}" x2="{w - 24}" y2="{ground}" stroke="#fff" stroke-opacity=".3" stroke-dasharray="3 5"/>'
    size = 112
    if star["img"]:
        sprite = f'<image x="0" y="{ground - size}" width="{size}" height="{size}" href="data:image/png;base64,{star["img"]}"/>'
    else:
        sprite = f'<text x="{size / 2}" y="{ground - 40}" font-size="40" text-anchor="middle" fill="#fff">?</text>'
    glyph = f'<text x="{size / 2}" y="{ground - size - 4}" font-size="22" text-anchor="middle">{active[4]}</text>' if active else ""
    body += (
        f'<g transform="translate(40 0)"><g class="mover" style="--d:{MOOD_SPEED[mood]}s">'
        f'<g class="m {mood}">{sprite}{glyph}</g></g></g>'
    )

    # greeting (top right)
    if active:
        greet = active[3]
    else:
        greet = f"hi, i'm {star['name']}. i'm {MOOD_NOTE[mood]}."
    gx = w - 28 - len(greet) * CW * 13
    g_svg, _ = typed(greet, gx, 90, 13, 1.2, 0.04, 400, .9)
    body += g_svg

    # status line
    status = f"star of the day: {star['name']} · mood: {mood}"
    if upcoming:
        days = (upcoming[0] - TODAY).days
        status += f" · next: {upcoming[2].lower()} in {days}d"
    s_svg, _ = typed(status, 28, 232, 11, 1.5, 0.025, 400, .55)
    body += s_svg

    # row of 10
    for i, m in enumerate(mons):
        x = 20 + i * 80
        if i == 0:
            body += f'<rect x="{x}" y="244" width="76" height="76" rx="8" fill="none" stroke="#fff" stroke-opacity=".8"/>'
        if m["img"]:
            body += f'<image x="{x + 10}" y="246" width="56" height="56" href="data:image/png;base64,{m["img"]}"/>'
        body += (f'<text x="{x + 38}" y="314" font-size="10" text-anchor="middle" fill="#fff" '
                 f'fill-opacity=".7">{esc(m["name"][:11])}</text>')
    (OUT / "pokemon.svg").write_text(wrap_svg(w, h, body, POKE_CSS), encoding="utf-8")


# ───────────────────────── quote.svg ─────────────────────────
QUOTES = [
    ("Talk is cheap. Show me the code.", "Linus Torvalds"),
    ("Premature optimization is the root of all evil.", "Donald Knuth"),
    ("Simplicity is prerequisite for reliability.", "Edsger W. Dijkstra"),
    ("Programs must be written for people to read, and only incidentally for machines to execute.", "Harold Abelson"),
    ("First, solve the problem. Then, write the code.", "John Johnson"),
    ("Make it work, make it right, make it fast.", "Kent Beck"),
    ("The best way to predict the future is to invent it.", "Alan Kay"),
    ("Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "Martin Fowler"),
    ("Dream, dream, dream. Dreams transform into thoughts and thoughts result in action.", "A. P. J. Abdul Kalam"),
    ("Arise, awake, and stop not till the goal is reached.", "Swami Vivekananda"),
    ("Well begun is half done.", "Aristotle"),
    ("A journey of a thousand miles begins with a single step.", "Lao Tzu"),
    ("Fall seven times, stand up eight.", "Japanese proverb"),
    ("Stay hungry, stay foolish.", "Steve Jobs"),
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("Whatever you are, be a good one.", "Abraham Lincoln"),
]

def build_quote():
    text, author = QUOTES[TODAY.toordinal() % len(QUOTES)]
    lines = textwrap.wrap(f"“{text}”", 58)
    size, lh = 18, 30
    w, h = 840, 92 + len(lines) * lh + 44
    body = window_dots()
    t = 0.3
    head, t = typed("$ cat quote_of_the_day.txt", 28, 52, 12, t, 0.03, 400, .55)
    body += head
    t += 0.2
    y = 92
    for ln in lines:
        svg, t = typed(ln, 28, y, size, t, 0.035)
        body += svg
        last = (28 + len(ln) * CW * size, y, size)
        y += lh
    svg, t = typed(f"— {author}", 28, y, 13, t + 0.2, 0.04, 400, .6)
    body += svg
    body += cursor(28 + len(f"— {author}") * CW * 13 + 3, y, 13, t)
    (OUT / "quote.svg").write_text(wrap_svg(w, h, body), encoding="utf-8")


# ───────────────────────── stats.svg (monochrome, from the GitHub API) ─────────────────────────
USER = "DEVprasad7"
EXCLUDE_LANGS = {"Jupyter Notebook"}  # notebooks are huge JSON and skew the percentages

def gh(path):
    headers = {"User-Agent": "profile-readme-bot", "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    req = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def collect_stats(user):
    u = gh(f"/users/{user}")
    own = [r for r in gh(f"/users/{user}/repos?per_page=100&type=owner") if not r["fork"]]
    langs = {}
    for r in own:
        try:
            for k, v in gh(f"/repos/{user}/{r['name']}/languages").items():
                langs[k] = langs.get(k, 0) + v
        except Exception:
            pass
    for k in EXCLUDE_LANGS:
        langs.pop(k, None)
    return {"repos": u["public_repos"], "followers": u["followers"],
            "stars": sum(r["stargazers_count"] for r in own), "since": u["created_at"][:4], "langs": langs}

def render_stats(user, st):
    w, h = 840, 250
    body = window_dots()
    head, _ = typed(f"$ gh stats --user {user.lower()}", 28, 52, 12, 0.3, 0.03, 400, .6)
    body += head
    for i, (num, label) in enumerate([(st["repos"], "public repos"), (st["stars"], "stars earned"),
                                      (st["followers"], "followers"), (st["since"], "on github since")]):
        x = 28 + i * 202
        body += (f'<text x="{x}" y="112" font-size="34" font-weight="700" fill="#fff">{num}</text>'
                 f'<text x="{x}" y="134" font-size="11" fill="#fff" fill-opacity=".55">{label}</text>')
    body += '<text x="28" y="176" font-size="11" fill="#fff" fill-opacity=".55">languages (by code size)</text>'
    total = sum(st["langs"].values()) or 1
    top = [kv for kv in sorted(st["langs"].items(), key=lambda kv: -kv[1]) if kv[1] / total >= 0.01][:6]
    shades = [1, .75, .55, .4, .28, .18]
    x = 28.0
    for (name, val), op in zip(top, shades):
        seg = 784 * val / total
        body += f'<rect x="{x:.1f}" y="186" width="{max(seg - 2, 1):.1f}" height="8" fill="#fff" fill-opacity="{op}"/>'
        x += seg
    for i, ((name, val), op) in enumerate(zip(top, shades)):
        lx = 28 + i * 132
        body += (f'<rect x="{lx}" y="214" width="9" height="9" fill="#fff" fill-opacity="{op}"/>'
                 f'<text x="{lx + 15}" y="223" font-size="11" fill="#fff" fill-opacity=".8">{esc(name[:11])} {val * 100 / total:.0f}%</text>')
    (OUT / "stats.svg").write_text(wrap_svg(w, h, body), encoding="utf-8")

def build_stats():
    try:
        render_stats(USER, collect_stats(USER))
    except Exception as e:  # keep the previous stats.svg if the API is unavailable
        print("stats skipped:", e)


if __name__ == "__main__":
    build_header()
    build_pokemon()
    build_quote()
    build_stats()
    print("done:", TODAY, season(TODAY), active_and_next())
