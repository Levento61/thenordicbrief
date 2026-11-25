#!/usr/bin/env python3
"""Bygger The Nordic Brief: content/ -> docs/ (statisk sajt för GitHub Pages).

Användning:
    python3 build.py            # bygger riktiga inlägg
    python3 build.py --demo     # tar även med exempelinlägg (endast förhandsvisning)
"""
import datetime as dt
import email.utils
import html
import json
import re
import shutil
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import markdown
import yaml

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
OUT = ROOT / "docs"
SITE_URL = "https://nordicbrief.se"
SITE_NAME = "The Nordic Brief"
TAGLINE = "Sverige, fotboll och marknader – varje dag."  # sidtitel, metabeskrivning och flöde (sökord)
SLOGAN = "Nyheter som de var förr – snabba, korta och utan brus."  # syns under logotypen

SECTIONS = {
    "sverige": {"name": "Sverige", "desc": "Rikstäckande nyheter från hela Sverige."},
    "fotboll": {"name": "Fotboll", "desc": "Allt om europeisk fotboll – ligor, cuper och transfers."},
    "ekonomi": {"name": "Ekonomi", "desc": "Global ekonomi, börs, krypto och valuta – inrikes och utrikes."},
}

MONTHS = ["januari", "februari", "mars", "april", "maj", "juni", "juli",
          "augusti", "september", "oktober", "november", "december"]

e = html.escape


def sv_date(d: dt.date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def slugify(s: str) -> str:
    s = s.lower()
    for a, b in (("å", "a"), ("ä", "a"), ("ö", "o"), ("é", "e"), ("ü", "u")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:80]


def load_posts(demo: bool):
    dirs = [CONTENT / "posts"] + ([CONTENT / "_demo"] if demo else [])
    posts = []
    for d in dirs:
        for f in sorted(d.glob("*.md")):
            raw = f.read_text(encoding="utf-8")
            m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
            if not m:
                print(f"VARNING: saknar frontmatter: {f}")
                continue
            meta = yaml.safe_load(m.group(1)) or {}
            body = m.group(2)
            if meta.get("section") not in SECTIONS:
                print(f"VARNING: okänd sektion i {f}")
                continue
            date = meta["date"]
            if isinstance(date, str):
                date = dt.datetime.fromisoformat(date)
            if isinstance(date, dt.date) and not isinstance(date, dt.datetime):
                date = dt.datetime.combine(date, dt.time(7, 0))
            slug = meta.get("slug") or slugify(meta["title"])
            posts.append({
                "title": meta["title"],
                "summary": meta.get("summary", ""),
                "section": meta["section"],
                "date": date,
                "sources": meta.get("sources", []) or [],
                "featured": bool(meta.get("featured")),
                "chart": meta.get("chart"),
                "updated": meta.get("updated"),
                "slug": slug,
                "url": f"/{meta['section']}/{date:%Y/%m/%d}/{slug}/",
                "og": f"/og/{meta['section']}-{date:%Y%m%d}-{slug}.jpg",
                "body_md": body,
                "html": markdown.markdown(body, extensions=["extra", "sane_lists"]),
            })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def load_markets(demo=False):
    """Marknadsläget skrivs av scripts/fetch_markets.py. Saknar content/markets.json dess format
    (t.ex. om någon redigerat för hand) används skriptets egen kopia data/markets-lastgood.json."""
    files = ([CONTENT / "_demo" / "markets.json"] if demo else []) + [CONTENT / "markets.json", ROOT / "data" / "markets-lastgood.json"]
    for f in files:
        try:
            m = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if demo or any(it.get("key") for g in m.get("groups", []) for it in g.get("items", [])):
            if f.parent.name == "data":
                shutil.copy(f, CONTENT / "markets.json")
            return m
    return None


EDITION = {}
TZ = ZoneInfo("Europe/Stockholm")
LOGO_URL = SITE_URL + "/assets/logo.png"
PUBLISHER = {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL + "/",
             "logo": {"@type": "ImageObject", "url": LOGO_URL, "width": 512, "height": 512}}


def aware(d):
    """Svensk tid med rätt tidszon (vinter- och sommartid)."""
    if isinstance(d, str):
        d = dt.datetime.fromisoformat(d)
    if isinstance(d, dt.date) and not isinstance(d, dt.datetime):
        d = dt.datetime.combine(d, dt.time(7, 0))
    return d.replace(tzinfo=TZ) if d.tzinfo is None else d


def iso(d):
    return aware(d).isoformat()


def meta_desc(text, limit=155):
    """Kortar metabeskrivningen vid ett ordslut så att Google inte klipper mitt i en mening."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:–-")
    return cut + "…"


def edition_line():
    if not EDITION.get("updated"):
        return sv_date(dt.date.today()).capitalize()
    u = dt.datetime.fromisoformat(str(EDITION["updated"]))
    label = EDITION.get("label", "")
    return f"{sv_date(u.date()).capitalize()} · {e(label)}{' · ' if label else ''}uppdaterad {u:%H.%M}"


def layout(title, body, description=TAGLINE, path="/", og_type="website", extra_head="", og_image="/og/default.jpg"):
    full_title = f"{title} – {SITE_NAME}" if title != SITE_NAME else f"{SITE_NAME} – {TAGLINE}"
    nav = "".join(
        f'<a href="/{k}/" class="{"active" if path.startswith("/" + k) else ""}">{v["name"]}</a>'
        for k, v in SECTIONS.items()
    )
    year = dt.date.today().year
    return f"""<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(meta_desc(description))}">
<link rel="canonical" href="{SITE_URL}{path}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(meta_desc(description, 200))}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{SITE_URL}{path}">
<meta property="og:locale" content="sv_SE">
<meta property="og:image" content="{SITE_URL}{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0f1216" media="(prefers-color-scheme: dark)">
<link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="/feed.xml">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
{extra_head}
</head>
<body>
<header class="masthead">
  <div class="topbar wrap">
    <span class="today">{edition_line()}</span>
    <div class="lang"><span class="lang-label">Language</span><div class="gtranslate_wrapper"></div></div>
  </div>
  <div class="brand wrap">
    <a href="/" class="logo" aria-label="{SITE_NAME} – startsida">
      <span class="logo-mark" aria-hidden="true"></span>
      <span class="logo-text">The Nordic <b>Brief</b></span>
    </a>
    <p class="tagline">{SLOGAN}</p>
  </div>
  <nav class="sections wrap" aria-label="Sektioner">{nav}</nav>
  <div class="principle"><div class="wrap"><p>Bara text, precis som förr. <a href="/om/#utan-bilder">Läs varför vi kör minimalistiskt →</a></p></div></div>
</header>
<main class="wrap">
{body}
</main>
<footer class="footer">
  <div class="wrap footer-grid">
    <div>
      <p class="logo-text small">The Nordic <b>Brief</b></p>
      <p>Dagliga sammanfattningar av det viktigaste inom Sverige, europeisk fotboll och global ekonomi. Varje text länkar till originalkällorna.</p>
    </div>
    <div>
      <p><a href="/om/">Om The Nordic Brief</a></p>
      <p><a href="/om/#sa-arbetar-vi">Så arbetar vi</a></p>
      <p><a href="/rattelser/">Rättelser</a></p>
      <p><a href="/feed.xml">RSS-flöde</a></p>
    </div>
    <div class="fineprint">
      <p>Innehållet sammanställs med hjälp av AI och granskas mot källorna före publicering. Kursuppgifter är fördröjda och utgör inte investeringsråd.</p>
      <p>© {year} {SITE_NAME}</p>
    </div>
  </div>
</footer>
<script>
window.gtranslateSettings = {{"default_language":"sv","languages":["sv","en"],"wrapper_selector":".gtranslate_wrapper","native_language_names":true}};
</script>
<script src="https://cdn.gtranslate.net/widgets/latest/ln.js" defer></script>
</body>
</html>"""


def card(p, size="normal"):
    sec = SECTIONS[p["section"]]["name"]
    summary = f'<p class="summary">{e(p["summary"])}</p>' if p["summary"] else ""
    return f"""<article class="card card-{size} sec-{p['section']}">
  <p class="kicker"><a href="/{p['section']}/">{sec}</a> · <time datetime="{p['date'].isoformat()}">{sv_date(p['date'].date())} {p['date']:%H.%M}</time></p>
  <h3><a href="{p['url']}">{e(p['title'])}</a></h3>
  {summary}
</article>"""


def chart_svg(c):
    """Linjediagram som inline-SVG. c = {title, values, labels?, unit?, source?}"""
    vals = [float(v) for v in c.get("values", []) if v is not None]
    if len(vals) < 2:
        return ""
    W, H, pl, pr, pt, pb = 680, 260, 56, 16, 16, 30
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.08 or 1
    lo, hi = lo - pad, hi + pad
    x = lambda i: pl + i * (W - pl - pr) / (len(vals) - 1)
    y = lambda v: pt + (hi - v) * (H - pt - pb) / (hi - lo)
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))
    area = f"{pl},{H - pb} {pts} {x(len(vals) - 1):.1f},{H - pb}"
    fmt = lambda v: (f"{v:,.0f}" if abs(v) >= 100 else f"{v:,.2f}").replace(",", " ").replace(".", ",")
    grid = ""
    for k in range(4):
        gv = lo + (hi - lo) * k / 3
        gy = y(gv)
        grid += (f'<line x1="{pl}" x2="{W - pr}" y1="{gy:.1f}" y2="{gy:.1f}" class="g"/>'
                 f'<text x="{pl - 8}" y="{gy + 4:.1f}" text-anchor="end">{fmt(gv)}</text>')
    labels = c.get("labels") or []
    xl = ""
    if len(labels) == len(vals):
        for i in sorted({0, len(vals) // 2, len(vals) - 1}):
            anchor = "start" if i == 0 else "end" if i == len(vals) - 1 else "middle"
            xl += f'<text x="{x(i):.1f}" y="{H - 8}" text-anchor="{anchor}">{e(str(labels[i]))}</text>'
    ch = (vals[-1] - vals[0]) / vals[0] * 100 if vals[0] else 0
    cls = "up" if ch > 0 else "down" if ch < 0 else ""
    last = f'{fmt(vals[-1])}{(" " + e(c["unit"])) if c.get("unit") else ""}'
    src = f'<figcaption>Källa: {e(c["source"])}</figcaption>' if c.get("source") else ""
    return f"""<figure class="chart">
  <div class="chart-head"><span class="chart-title">{e(c.get('title', ''))}</span>
  <span class="chart-last">{last} <b class="{cls}">{f"{ch:+.1f}".replace(".", ",")} %</b></span></div>
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="{e(c.get('title', 'Diagram'))}">
    {grid}<polygon points="{area}" class="a"/><polyline points="{pts}" class="l"/>
    <circle cx="{x(len(vals) - 1):.1f}" cy="{y(vals[-1]):.1f}" r="4" class="d"/>{xl}
  </svg>{src}
</figure>"""


def markets_box(m):
    """Marknadsläget. Datan skrivs av scripts/fetch_markets.py (GitHub Actions var 15:e minut);
    assets/markets-live.js hämtar /data/markets.json i läsarens webbläsare och uppdaterar rutan."""
    if not m:
        return ""
    groups = []
    for g in m.get("groups", []):
        rows = []
        for it in g.get("items", []):
            ch = it.get("change_pct")
            cls, chs = "", ""
            if isinstance(ch, (int, float)):
                cls = "up" if ch > 0 else "down" if ch < 0 else "flat"
                chs = f"{ch:+.2f} %".replace(".", ",").replace("-", "−")
            key = it.get("key", "")
            rows.append(f'<li data-key="{e(key)}"><span class="m-name">{e(it["name"])}</span>'
                        f'<span class="m-val">{e(str(it["value"]))}</span>'
                        f'<span class="m-ch {cls}">{chs}</span></li>')
        groups.append(f'<div class="m-group"><h4>{e(g["title"])}</h4><ul>{"".join(rows)}</ul></div>')
    return f"""<section class="markets" aria-label="Marknadsläget">
  <div class="markets-head"><h2>Marknadsläget</h2><p class="asof">{e(m.get('as_of', ''))}</p></div>
  <div class="m-groups">{"".join(groups)}</div>
  <p class="m-src">Källa: <span class="m-srcs">{e(m.get('source', ''))}</span>. Uppdateras var 15:e minut, kan vara fördröjd. Inte investeringsråd.</p>
</section>
<script src="/assets/markets-live.js" defer></script>"""


def latest_box(posts, n=12):
    lis = "".join(
        f'<li class="sec-{p["section"]}"><time datetime="{p["date"].isoformat()}">{p["date"]:%H.%M}</time>'
        f'<span class="l-sec">{SECTIONS[p["section"]]["name"]}</span><a href="{p["url"]}">{e(p["title"])}</a></li>'
        for p in posts[:n])
    return f'<section class="latest" aria-label="Senaste"><h2>Senaste</h2><ol>{lis}</ol></section>'


def build_index(posts, markets):
    if not posts:
        body = '<section class="empty"><h1>Snart här</h1><p>Första upplagan publiceras inom kort.</p></section>'
        return layout(SITE_NAME, body)
    lead = next((p for p in posts if p["featured"]), posts[0])
    rest = [p for p in posts if p is not lead]
    top = rest[:6]
    cols = []
    for k, v in SECTIONS.items():
        shown = [lead] + top
        items = [p for p in posts if p["section"] == k and p not in shown][:8]
        if not items:
            continue
        lis = "".join(
            f'<li><a href="{p["url"]}">{e(p["title"])}</a><time datetime="{p["date"].isoformat()}">{sv_date(p["date"].date())} {p["date"]:%H.%M}</time></li>'
            for p in items)
        cols.append(f'<section class="col sec-{k}"><h2><a href="/{k}/">{v["name"]}</a></h2><ul>{lis}</ul>'
                    f'<a class="more" href="/{k}/">Mer {v["name"]} →</a></section>')
    site_ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/", "inLanguage": "sv-SE"},
        PUBLISHER]}
    body = f"""<h1 class="sr-only">{SITE_NAME} – nyheter om Sverige, fotboll och marknader</h1>
<script type="application/ld+json">{json.dumps(site_ld, ensure_ascii=False)}</script>
<div class="front">
  <div class="lead-area">
    {card(lead, 'lead')}
    <div class="top-grid">{''.join(card(p) for p in top)}</div>
    <div class="columns">{''.join(cols)}</div>
  </div>
  <aside class="side">{markets_box(markets)}{latest_box(posts)}</aside>
</div>"""
    return layout(SITE_NAME, body)


def build_section(key, posts):
    v = SECTIONS[key]
    items = [p for p in posts if p["section"] == key]
    cards = "".join(card(p) for p in items) or "<p>Inga artiklar ännu.</p>"
    body = f"""<header class="sec-head sec-{key}"><h1>{v['name']}</h1><p>{v['desc']}</p></header>
<div class="list-grid">{cards}</div>"""
    return layout(v["name"], body, v["desc"], f"/{key}/")


def build_post(p, posts):
    sec = SECTIONS[p["section"]]["name"]
    srcs = "".join(
        f'<li><a href="{e(s["url"])}" rel="nofollow noopener" target="_blank">{e(s["name"])}</a></li>'
        for s in p["sources"] if s.get("url"))
    sources = f'<aside class="sources"><h2>Källor</h2><ul>{srcs}</ul></aside>' if srcs else ""
    related = [q for q in posts if q["section"] == p["section"] and q is not p][:3]
    rel = (f'<section class="related"><h2>Mer från {sec}</h2><div class="list-grid">'
           f'{"".join(card(q) for q in related)}</div></section>') if related else ""
    ld = {
        "@context": "https://schema.org", "@type": "NewsArticle",
        "headline": p["title"], "description": p["summary"],
        "datePublished": iso(p["date"]), "inLanguage": "sv-SE",
        "dateModified": iso(p.get("updated") or p["date"]),
        "mainEntityOfPage": SITE_URL + p["url"],
        "author": {"@type": "Organization", "name": SITE_NAME + "-redaktionen", "url": SITE_URL + "/om/"},
        "publisher": PUBLISHER,
        "articleSection": sec,
        "image": [SITE_URL + p["og"]],
    }
    extra = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
    body = f"""<article class="post sec-{p['section']}">
  <p class="kicker"><a href="/{p['section']}/">{sec}</a> · <time datetime="{p['date'].isoformat()}">{sv_date(p['date'].date())} {p['date']:%H.%M}</time>{(' · Uppdaterad ' + dt.datetime.fromisoformat(str(p['updated'])).strftime('%H.%M')) if p.get('updated') else ''}</p>
  <h1>{e(p['title'])}</h1>
  <p class="dek">{e(p['summary'])}</p>
  {chart_svg(p['chart']) if p.get('chart') else ''}
  <div class="body">{p['html']}</div>
  {sources}
</article>
{rel}"""
    return layout(p["title"], body, p["summary"] or TAGLINE, p["url"], "article", extra, og_image=p["og"])


def build_about():
    body = """<article class="post">
  <h1>Om The Nordic Brief</h1>
  <div class="body">
  <p>The Nordic Brief samlar varje dag det viktigaste inom tre områden: rikstäckande svenska nyheter, europeisk fotboll och global ekonomi – börs, krypto, räntor och valuta. Sajten uppdateras fyra gånger om dagen: 07.00, 12.00, 17.00 och 21.00.</p>
  <p>Vi skriver korta, egna sammanfattningar och länkar alltid till originalkällorna, så att du snabbt får överblick och kan läsa vidare där nyheten publicerades först.</p>
  <h2 id="sa-arbetar-vi">Så arbetar vi</h2>
  <p>The Nordic Brief produceras med AI, i ett redaktionellt flöde med tydliga roller och regler:</p>
  <ol>
    <li><strong>Research och skrivande.</strong> Tre AI-redaktörer – en för Sverige, en för fotboll och en för ekonomi – söker efter de senaste nyheterna hos etablerade källor som TT, SVT, Sveriges Radio, DN, SvD, Reuters, AP, BBC, UEFA, Dagens industri och myndigheter. De skriver varje text med egna ord och anger sina källor.</li>
    <li><strong>Fristående granskning.</strong> En separat granskare, som inte deltagit i skrivandet, kontrollerar varje artikel mot källorna: namn, siffror, datum, citat och resultat. Den kontrollerar också att inget är kopierat. Det som inte går att belägga stryks – hellre en nyhet mindre än ett fel.</li>
    <li><strong>Publicering.</strong> Bara granskade texter publiceras. Varje artikel visar sina källor längst ner.</li>
  </ol>
  <p>Vi namnger inte misstänkta eller brottsoffer som inte är offentliga personer, vi skriver politiskt neutralt och vi ger aldrig investeringsråd. Transferrykten publiceras bara från etablerade källor och märks tydligt som rykten.</p>
  <h2 id="marknadslaget">Marknadsläget</h2>
  <p>Marknadsläget uppdateras automatiskt var 15:e minut. Kurserna hämtas från TradingView, med Yahoo Finance, CoinGecko och ECB som reserv; styrräntan kommer direkt från Riksbanken. Svarar ingen källa visas det senast kända värdet. Förändringen avser senaste handelsdag (för krypto senaste 24 timmarna). Kursuppgifter kan vara fördröjda och är inte investeringsråd.</p>
  <h2 id="rattelser">Rättelser</h2>
  <p>Fel som upptäcks rättas i artikeln, med en notering om vad som ändrats och när. Alla rättelser samlas på sidan <a href="/rattelser/">Rättelser</a>. Hittar du ett fel? Hör av dig så rättar vi.</p>
  <h2 id="utan-bilder">Varför inga bilder?</h2>
  <p>The Nordic Brief är medvetet minimalistisk. Vi använder inga foton – sidan laddar snabbt, fungerar även med svag uppkoppling och låter nyheten stå i centrum. Där en bild faktiskt tillför något, till exempel börs- och kursutveckling, visar vi diagram byggda på data.</p>
  </div>
</article>"""
    return layout("Om oss", body, "Om The Nordic Brief, hur innehållet tas fram och granskas.", "/om/")


def build_corrections(posts):
    rows = []
    for p in posts:
        for m in re.finditer(r"\*Rättat ([0-9]{4}-[0-9]{2}-[0-9]{2}):\s*(.+?)\*", p["body_md"]):
            rows.append((m.group(1), p, m.group(2).strip()))
    rows.sort(key=lambda r: r[0], reverse=True)
    if rows:
        lis = "".join(f'<li><time datetime="{d}">{sv_date(dt.date.fromisoformat(d))}</time> · '
                      f'<a href="{p["url"]}">{e(p["title"])}</a><p>{e(t)}</p></li>' for d, p, t in rows)
        lst = f'<ul class="corrections">{lis}</ul>'
    else:
        lst = "<p>Inga rättelser hittills.</p>"
    body = f"""<article class="post"><h1>Rättelser</h1>
  <div class="body"><p>Här samlas alla rättelser i publicerade artiklar, senaste först. Läs mer om <a href="/om/#sa-arbetar-vi">hur vi arbetar</a>.</p></div>
  {lst}
</article>"""
    return layout("Rättelser", body, "Rättelser i artiklar på The Nordic Brief.", "/rattelser/")


def build_news_sitemap(posts):
    """Google News-sitemap: artiklar från de senaste två dygnen."""
    newest = max((p["date"] for p in posts), default=dt.datetime.now())
    recent = [p for p in posts if p["date"] >= newest - dt.timedelta(days=2)]
    items = "".join(f"""<url><loc>{SITE_URL}{p['url']}</loc><news:news><news:publication><news:name>{SITE_NAME}</news:name><news:language>sv</news:language></news:publication><news:publication_date>{iso(p['date'])}</news:publication_date><news:title>{e(p['title'])}</news:title></news:news></url>"""
                    for p in recent)
    return ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            f'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">{items}</urlset>')


OG_FONTS = ROOT / "social" / "fonts"
OG_COLORS = {"sverige": "#1d5bd6", "fotboll": "#178a4c", "ekonomi": "#c2185b"}


def og_image(path: Path, title: str, section=None, date=None):
    """Delningsbild 1200x630 (JPEG) för sociala medier."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), "#ffffff")
    d = ImageDraw.Draw(im)
    f = lambda n, sz: ImageFont.truetype(str(OG_FONTS / f"{n}.ttf"), sz)
    accent = OG_COLORS.get(section, "#111418")
    d.rectangle([0, 0, W, 14], fill=accent)
    # logga
    d.rounded_rectangle([70, 64, 118, 112], 10, fill="#111418")
    for y, c in ((78, "#1d5bd6"), (87, "#178a4c"), (96, "#c2185b")):
        d.rounded_rectangle([81, y, 107, y + 4], 2, fill=c)
    d.text((134, 66), "The Nordic Brief", font=f("Fraunces-SemiBold", 40), fill="#111418")
    kicker = SECTIONS[section]["name"].upper() if section else "SVERIGE · FOTBOLL · EKONOMI"
    if date:
        kicker += f"  ·  {sv_date(date.date()).upper()}"
    d.text((70, 170), kicker, font=f("Inter-SemiBold", 26), fill=accent)
    # rubrik, radbrytning med krympande storlek
    for size in (74, 66, 58, 50, 44):
        fnt = f("Fraunces-ExtraBold", size)
        words, lines, cur = title.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=fnt) <= W - 140:
                cur = t
            else:
                lines.append(cur); cur = w
        lines.append(cur)
        if len(lines) * size * 1.15 <= 330:
            break
    lines = lines[:5]
    y = 220
    for ln in lines:
        d.text((70, y), ln, font=fnt, fill="#111418")
        y += int(size * 1.15)
    d.line([70, H - 70, W - 70, H - 70], fill="#e2e4e8", width=2)
    d.text((70, H - 56), "nordicbrief.se", font=f("Inter-SemiBold", 24), fill="#5b616b")
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=85, optimize=True)
    return True


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_feed(posts):
    items = "".join(f"""<item><title>{e(p['title'])}</title><link>{SITE_URL}{p['url']}</link>
<guid>{SITE_URL}{p['url']}</guid><pubDate>{email.utils.format_datetime(aware(p['date']))}</pubDate>
<description>{e(p['summary'])}</description><category>{SECTIONS[p['section']]['name']}</category></item>"""
                    for p in posts[:40])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>{SITE_NAME}</title><link>{SITE_URL}/</link>
<description>{TAGLINE}</description><language>sv-se</language>{items}</channel></rss>"""


def build_sitemap(posts):
    def last(ps):
        return max((aware(q.get("updated") or q["date"]) for q in ps), default=aware(dt.datetime.now())).date().isoformat()
    urls = [("/", last(posts)), ("/om/", None), ("/rattelser/", None)]
    urls += [(f"/{k}/", last([q for q in posts if q["section"] == k])) for k in SECTIONS]
    urls += [(q["url"], aware(q.get("updated") or q["date"]).date().isoformat()) for q in posts]
    body = "".join(f"<url><loc>{SITE_URL}{u}</loc>{f'<lastmod>{m}</lastmod>' if m else ''}</url>" for u, m in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'


def main():
    demo = "--demo" in sys.argv
    posts = load_posts(demo)
    markets = load_markets(demo)
    ef = CONTENT / "edition.json"
    if ef.exists():
        EDITION.update(json.loads(ef.read_text(encoding="utf-8")))
    og_cache = ROOT / ".og-cache"
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    if (ROOT / "social" / "cards").exists():
        shutil.copytree(ROOT / "social" / "cards", OUT / "social")
    if (ROOT / "static").exists():
        for f in (ROOT / "static").iterdir():
            shutil.copy(f, OUT / f.name)
    # Delningsbilder: återanvänd från cache, skapa bara nya
    for p in posts:
        cached = og_cache / Path(p["og"]).name
        key = cached.with_suffix(".txt")
        sig = p["title"] + "|" + p["section"]
        if not (cached.exists() and key.exists() and key.read_text(encoding="utf-8") == sig):
            if og_image(cached, p["title"], p["section"], p["date"]):
                key.write_text(sig, encoding="utf-8")
    default_og = og_cache / "default.jpg"
    if not default_og.exists():
        og_image(default_og, SLOGAN)
    if og_cache.exists():
        (OUT / "og").mkdir(parents=True, exist_ok=True)
        for f in og_cache.glob("*.jpg"):
            shutil.copy(f, OUT / "og" / f.name)
    for p in posts:  # saknas bilden (t.ex. utan Pillow) används standardbilden
        if not (OUT / p["og"].lstrip("/")).exists():
            p["og"] = "/og/default.jpg"
    if (CONTENT / "markets.json").exists():
        (OUT / "data").mkdir(parents=True, exist_ok=True)
        shutil.copy(CONTENT / "markets.json", OUT / "data" / "markets.json")
    write(OUT / "index.html", build_index(posts, markets))
    for k in SECTIONS:
        write(OUT / k / "index.html", build_section(k, posts))
    for p in posts:
        write(OUT / p["url"].strip("/") / "index.html", build_post(p, posts))
    write(OUT / "om" / "index.html", build_about())
    write(OUT / "rattelser" / "index.html", build_corrections(posts))
    write(OUT / "news-sitemap.xml", build_news_sitemap(posts))
    write(OUT / "feed.xml", build_feed(posts))
    write(OUT / "sitemap.xml", build_sitemap(posts))
    write(OUT / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\nSitemap: {SITE_URL}/news-sitemap.xml\n")
    write(OUT / "CNAME", "nordicbrief.se\n")
    write(OUT / ".nojekyll", "")
    write(OUT / "404.html", layout("Sidan hittades inte",
                                    '<section class="empty"><h1>Sidan hittades inte</h1><p><a href="/">Till startsidan →</a></p></section>',
                                    path="/404.html"))
    print(f"Byggt {len(posts)} inlägg till {OUT}{' (DEMO)' if demo else ''}")


if __name__ == "__main__":
    main()
