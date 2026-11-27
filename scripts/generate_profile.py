#!/usr/bin/env python3
"""Generate monochrome SVG profile assets; stable for a given IST calendar day."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib, json, urllib.request, urllib.error, html

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(timezone.utc).astimezone(IST).date()
SEED = TODAY.isoformat()


def hash_int(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest(), 16)


def fetch_json(url, timeout=4):
    req = urllib.request.Request(url, headers={"User-Agent": "DEVprasad7-profile-generator/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def write(name, content):
    (ASSETS / name).write_text(content, encoding="utf-8")


def header_svg():
    phrases = ["PYTHON DEVELOPER", "AI / ML EXPLORER", "DATA ENGINEERING", "SOFTWARE BUILDER"]
    anims = []
    for i, phrase in enumerate(phrases):
        begin = i * 4.8
        anims.append(f'<text x="54" y="178" class="role" opacity="0">{phrase}<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.08;0.72;1" dur="4.8s" begin="{begin}s" repeatCount="indefinite"/></text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="310" viewBox="0 0 1000 310">
<rect width="1000" height="310" fill="#050505" rx="16"/><rect x="18" y="18" width="964" height="274" rx="12" fill="none" stroke="#333"/>
<text x="54" y="52" fill="#8d8d8d" font-family="JetBrains Mono,monospace" font-size="14" letter-spacing="2">PORTFOLIO / DEVPRASAD7 / INDIA</text>
<text x="54" y="132" fill="#fff" font-family="Space Grotesk,Arial,sans-serif" font-size="72" font-weight="700" letter-spacing="-3">PRASAD MASKAR</text>
{''.join(anims)}
<rect x="54" y="202" width="9" height="24" fill="#eee"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>
<text x="54" y="258" fill="#aaa" font-family="JetBrains Mono,monospace" font-size="14">I build, learn, debug, and build again.</text>
<text x="944" y="258" text-anchor="end" fill="#777" font-family="JetBrains Mono,monospace" font-size="12">SCROLL ↓</text></svg>'''


def pokemon_list():
    try:
        payload = fetch_json("https://pokeapi.co/api/v2/pokemon?limit=1025", timeout=6)
        # API's resource URLs include each species ID, avoiding a separate lookup per Pokémon.
        entries = [(p["name"], int(p["url"].rstrip("/").split("/")[-1])) for p in payload["results"]]
        return entries
    except Exception as exc:
        print(f"PokéAPI unavailable; using fallback list: {exc}")
        fallback = ["pikachu", "eevee", "bulbasaur", "charmander", "squirtle", "snorlax", "gengar", "lucario", "ditto", "psyduck", "dragonite", "mew", "togepi", "jigglypuff", "machop", "mudkip", "rowlet", "piplup", "spheal", "scorbunny"]
        ids = [25,133,1,4,7,143,94,448,132,54,149,151,175,39,66,258,722,393,363,813]
        return list(zip(fallback, ids))


def daily_pokemon():
    entries = pokemon_list()
    ordered = sorted(entries, key=lambda pair: hashlib.sha256((SEED + pair[0]).encode()).hexdigest())
    chosen_entries = ordered[:10]
    chosen = [entry[0] for entry in chosen_entries]
    featured = chosen[hash_int(SEED + "-star") % len(chosen)]
    return chosen, featured, dict(entries)


def event_for_today():
    cfg = json.loads((DATA / "festivals.json").read_text(encoding="utf-8"))
    key = TODAY.strftime("%m-%d")
    return cfg.get("fixed_date_events", {}).get(key)


def behavior_for_day(event):
    if event:
        return event["behavior"], event["name"]
    month = TODAY.month
    season = "monsoon" if month in (6, 7, 8, 9) else "summer" if month in (3, 4, 5) else "winter"
    weekday = TODAY.weekday()
    weekly = {0:"slow_walk", 4:"celebrate", 5:"relax", 6:"nap"}
    behavior = weekly.get(weekday, {"summer":"seek_shade", "monsoon":"rain_watch", "winter":"cozy_idle"}[season])
    return behavior, season.title()


def pokemon_svg():
    chosen, star, id_map = daily_pokemon()
    event = event_for_today()
    behavior, label = behavior_for_day(event)
    tiles = []
    for idx, name in enumerate(chosen):
        x = 34 + idx * 93
        is_star = name == star
        title = name.replace("-", " ").title()
        sprite = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{id_map.get(name)}.png" if id_map.get(name) else ""
        # GitHub's SVG renderer may not load remote raster images reliably; name cards remain useful without them.
        if is_star and sprite:
            tiles.append(f'<g><rect x="{x}" y="110" width="82" height="102" rx="9" fill="#171717" stroke="#777"/><image href="{sprite}" x="{x+9}" y="119" width="64" height="64"/><text x="{x+41}" y="195" fill="#fff" font-size="10" text-anchor="middle" font-family="monospace">{html.escape(title[:13])}</text><text x="{x+41}" y="205" fill="#aaa" font-size="7" text-anchor="middle" font-family="monospace">TODAY ★</text></g>')
        else:
            tiles.append(f'<g><rect x="{x}" y="110" width="82" height="102" rx="9" fill="#0c0c0c" stroke="#333"/><text x="{x+41}" y="157" fill="#bbb" font-size="10" text-anchor="middle" font-family="monospace">#{idx+1:02}</text><text x="{x+41}" y="180" fill="#fff" font-size="10" text-anchor="middle" font-family="monospace">{html.escape(title[:13])}</text></g>')
    # Animate featured tile only; subtle monochrome bob. Festival mode is shown as metadata.
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="280" viewBox="0 0 1000 280"><rect width="1000" height="280" rx="16" fill="#050505" stroke="#333"/>
<text x="30" y="38" fill="#888" font-family="monospace" font-size="12" letter-spacing="2">DAILY POKÉDEX / {TODAY.strftime('%d %b %Y').upper()}</text><text x="970" y="38" fill="#888" text-anchor="end" font-family="monospace" font-size="12">10 SPECIES</text>
<text x="30" y="72" fill="#fff" font-family="monospace" font-size="20">FEATURED: {html.escape(star.upper())}</text><text x="30" y="94" fill="#aaa" font-family="monospace" font-size="11">MODE: {html.escape(label.upper())} / {html.escape(behavior.upper())}</text>
{''.join(tiles)}<text x="30" y="248" fill="#777" font-family="monospace" font-size="10">Daily rotation is date-seeded · festival dates can be maintained in data/festivals.json</text></svg>'''


def quote_svg():
    quotes = json.loads((DATA / "quotes.json").read_text(encoding="utf-8"))
    quote = quotes[hash_int(SEED + "-quote") % len(quotes)]
    text = html.escape(quote["text"])
    tag = html.escape(quote["tag"])
    # Split quote into lines, using approximate 50-char wrapping.
    words, lines, line = text.split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > 54:
            lines.append(line); line = word
        else:
            line = (line + " " + word).strip()
    if line: lines.append(line)
    line_svg = ''.join(f'<text x="44" y="{118+i*34}" fill="#eee" font-family="Space Grotesk,Arial,sans-serif" font-size="23">{l}</text>' for i,l in enumerate(lines[:3]))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="220" viewBox="0 0 1000 220"><rect width="1000" height="220" rx="16" fill="#050505" stroke="#333"/><text x="44" y="40" fill="#888" font-family="monospace" font-size="12" letter-spacing="2">THOUGHT OF THE DAY / {TODAY.strftime('%d %b').upper()}</text><text x="956" y="40" text-anchor="end" fill="#888" font-family="monospace" font-size="12">{tag}</text>{line_svg}<text x="44" y="192" fill="#777" font-family="monospace" font-size="11">ORIGINAL PROFILE NOTE · DATE-SEEDED ROTATION</text></svg>'''



def stats_svg():
    labels = [("PYTHON", "automation · backend · data"), ("AI / ML", "experiments · applied learning"), ("WEB", "React · Next.js · Streamlit"), ("SQL", "MySQL · SQLite")]
    chunks = []
    for i,(title,desc) in enumerate(labels):
        y=92+i*43
        chunks.append(f'<text x="46" y="{y}" fill="#eee" font-family="monospace" font-size="15">{title}</text><text x="954" y="{y}" fill="#888" text-anchor="end" font-family="monospace" font-size="12">{desc}</text><line x1="44" y1="{y+13}" x2="956" y2="{y+13}" stroke="#222"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="260" viewBox="0 0 1000 260"><rect width="1000" height="260" rx="16" fill="#050505" stroke="#333"/><text x="44" y="44" fill="#888" font-family="monospace" font-size="12" letter-spacing="2">CURRENT INTERESTS / NOT A SKILL RANKING</text>{"".join(chunks)}</svg>'


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    write("header.svg", header_svg())
    write("pokemon.svg", pokemon_svg())
    write("quote.svg", quote_svg())
    write("stats.svg", stats_svg())
    print(f"Generated profile SVGs for {TODAY} (IST)")

if __name__ == "__main__":
    main()
