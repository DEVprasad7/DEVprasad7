#!/usr/bin/env python3
"""Refresh README daily Pokémon + quote + seasonal theme. Uses Mumbai/India time."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib, json, html, urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA, ASSETS = ROOT / "data", ROOT / "assets"
IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(timezone.utc).astimezone(IST).date()
SEED = TODAY.isoformat()
README = ROOT / "README.md"
START, END = "<!-- DAILY_POKEDEX_START -->", "<!-- DAILY_POKEDEX_END -->"
FALLBACK = [("pikachu",25),("eevee",133),("bulbasaur",1),("charmander",4),("squirtle",7),("snorlax",143),("gengar",94),("lucario",448),("ditto",132),("psyduck",54),("dragonite",149),("mew",151),("togepi",175),("jigglypuff",39),("machop",66),("mudkip",258),("rowlet",722),("piplup",393),("spheal",363),("scorbunny",813)]
def h(value): return int(hashlib.sha256(value.encode()).hexdigest(),16)
def fetch(url, timeout=8):
    req=urllib.request.Request(url,headers={"User-Agent":"DEVprasad7-README-generator"})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode())
def choose_season():
    seasons=json.loads((DATA/"seasons.json").read_text())
    month=TODAY.month
    for key,cfg in seasons.items():
        if month in cfg["months"]: return key,cfg
    return "winter",seasons["winter"]
def pokemon_pool():
    try:
        results=fetch("https://pokeapi.co/api/v2/pokemon?limit=1025")["results"]
        return [(p["name"],int(p["url"].strip("/").split("/")[-1])) for p in results]
    except Exception as e:
        print("PokéAPI unavailable; using fallback list:",e)
        return FALLBACK
def daily_pokemon():
    pool=sorted(pokemon_pool(),key=lambda p:hashlib.sha256((SEED+"|"+p[0]).encode()).hexdigest())
    # Pick nine date-stable entries, then guarantee the featured Pokémon comes
    # from the older animated-sprite catalog (IDs <= 649).
    featured_pool=[entry for entry in pool if entry[1] <= 649]
    featured=featured_pool[h(SEED+"|featured")%len(featured_pool)] if featured_pool else pool[0]
    selected=pool[:]
    selected=[entry for entry in selected if entry[0] != featured[0]][:9]
    selected.append(featured)
    selected=sorted(selected,key=lambda p:hashlib.sha256((SEED+"|display|"+p[0]).encode()).hexdigest())
    return selected,featured
def quote_of_day():
    q=json.loads((DATA/"quotes.json").read_text())
    return q[h(SEED+"|quote")%len(q)]
def sprite_url(pid):
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pid}.png"
def animated_sprite_url(pid):
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/animated/{pid}.gif"
def pokedex_html(selected,featured,season,cfg,mode):
    date_label=TODAY.strftime("%d %b %Y").upper()
    featured_name,featured_id=featured
    cards=[]
    for idx,(pname,pid) in enumerate(selected,1):
        is_feature=(pname==featured_name)
        title=pname.replace("-"," ").title()
        src=animated_sprite_url(pid) if is_feature else sprite_url(pid)
        fallback=sprite_url(pid)
        marker='<br/><sub>★ FEATURED · TRY GIF</sub>' if is_feature else ''
        cards.append(f'''<td align="center" width="20%" style="border:1px solid #333;border-radius:10px;padding:7px;background:#101010;">
<a href="https://www.pokemon.com/us/pokedex/{pname}"><img src="{src}" alt="{title} sprite" width="72" height="72" /></a><br/><sub>#{idx:02d}</sub><br/><strong>{html.escape(title)}</strong>{marker}</td>''')
    rows=[]
    for i in range(0,len(cards),5): rows.append("<tr>"+"".join(cards[i:i+5])+"</tr>")
    return f'''<div align="center">
<table width="100%"><tr><td align="left"><sub>DAILY POKÉDEX / {date_label} · INDIA (IST)</sub></td><td align="right"><sub>10 SPECIES · {cfg['label']} MODE</sub></td></tr></table>
<h3 align="left">FEATURED: {html.escape(featured_name.replace('-',' ').title())}</h3>
<p align="left"><code>BEHAVIOUR: {html.escape(mode.upper())}</code></p>
<table width="100%" cellpadding="4" cellspacing="8">{''.join(rows)}</table>
<p align="left"><sub>Date-seeded lineup · Pokémon sprites served directly from PokéAPI sprite repository · {season.upper()} theme</sub></p>
</div>'''
def make_header():
    roles=["PYTHON DEVELOPER","AI / ML EXPLORER","DATA ENGINEERING","SOFTWARE BUILDER"]
    anim=[]
    for i,role in enumerate(roles):
        anim.append(f'<text x="62" y="178" fill="#fff" font-family="JetBrains Mono,monospace" font-size="25" opacity="0">{role}<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.12;0.78;1" dur="4.6s" begin="{i*4.6}s" repeatCount="indefinite"/></text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="320" viewBox="0 0 1000 320">
<rect width="1000" height="320" rx="18" fill="#070707"/><rect x="16" y="16" width="968" height="288" rx="14" fill="none" stroke="#333"/>
<text x="62" y="58" fill="#888" font-family="JetBrains Mono,monospace" font-size="14" letter-spacing="2">PORTFOLIO / DEVPRASAD7 / INDIA</text>
<text x="62" y="136" fill="#fff" font-family="Space Grotesk,Arial,sans-serif" font-size="68" font-weight="700" letter-spacing="-2">PRASAD MASKAR</text>
{''.join(anim)}
<rect x="62" y="198" width="8" height="25" fill="#fff"><animate attributeName="opacity" values="1;0;1" dur="0.9s" repeatCount="indefinite"/></rect>
<text x="62" y="262" fill="#aaa" font-family="JetBrains Mono,monospace" font-size="14">I build, learn, debug, and build again.</text>
<text x="938" y="262" text-anchor="end" fill="#777" font-family="JetBrains Mono,monospace" font-size="12">SCROLL ↓</text></svg>'''
def make_quote_svg():
    q=quote_of_day(); lines=[]; line=""
    for word in q["text"].split():
        if len(line)+len(word)+1>52: lines.append(line); line=word
        else: line=(line+" "+word).strip()
    if line: lines.append(line)
    rendered="".join(f'<text x="46" y="{116+i*36}" fill="#eee" font-family="Space Grotesk,Arial,sans-serif" font-size="23">{html.escape(l)}</text>' for i,l in enumerate(lines[:3]))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="230" viewBox="0 0 1000 230"><rect width="1000" height="230" rx="16" fill="#050505" stroke="#333"/><text x="46" y="40" fill="#888" font-family="monospace" font-size="12" letter-spacing="2">THOUGHT OF THE DAY / {TODAY.strftime('%d %b').upper()}</text><text x="954"" y="40" text-anchor="end" fill="#888" font-family="monospace" font-size="12">{html.escape(q['tag'])}</text>{rendered}<text x="46" y="198" fill="#777" font-family="monospace" font-size="11">DAILY ROTATION · CURATED QUOTES</text></svg>'''.replace('x="954""','x="954"')
def replace_section(section):
    text=README.read_text(encoding="utf-8")
    if START not in text or END not in text: raise RuntimeError("README daily Pokédex markers missing")
    start=text.index(START)+len(START); end=text.index(END)
    README.write_text(text[:start]+"\n"+section+"\n"+text[end:],encoding="utf-8")
def main():
    ASSETS.mkdir(exist_ok=True)
    season,cfg=choose_season()
    mode=cfg["behavior"][h(SEED+"|seasonal_behavior")%len(cfg["behavior"])]
    selected,featured=daily_pokemon()
    (ASSETS/"header.svg").write_text(make_header(),encoding="utf-8")
    (ASSETS/"quote.svg").write_text(make_quote_svg(),encoding="utf-8")
    replace_section(pokedex_html(selected,featured,season,cfg,mode))
    print(f"Profile README updated for {TODAY} IST · {season} · {mode}")
if __name__=="__main__": main()
