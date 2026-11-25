#!/usr/bin/env python3
"""Bygger The Nordic Brief: content/ -> docs/ (statisk sajt för GitHub Pages).

Användning:
    python3 build.py            # bygger riktiga inlägg
    python3 build.py --demo     # tar även med exempelinlägg (endast förhandsvisning)
"""
import datetime as dt
import html
import json
import re
import shutil
import sys
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
OUT = ROOT / "docs"
SITE_URL = "https://nordicbrief.se"
SITE_NAME = "The Nordic Brief"
TAGLINE = "Sverige, fotboll och marknader – varje dag."

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
                "html": markdown.markdown(body, extensions=["extra", "sane_lists"]),
            })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def load_markets(demo=False):
    for f in ([CONTENT / "_demo" / "markets.json"] if demo else []) + [CONTENT / "markets.json"]:
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
    return None


EDITION = {}


def edition_line():
    if not EDITION.get("updated"):
        return sv_date(dt.date.today()).capitalize()
    u = dt.datetime.fromisoformat(str(EDITION["updated"]))
    label = EDITION.get("label", "")
    return f"{sv_date(u.date()).capitalize()} · {e(label)}{' · ' if label else ''}uppdaterad {u:%H.%M}"


def layout(title, body, description=TAGLINE, path="/", og_type="website", extra_head=""):
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
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{SITE_URL}{path}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{SITE_URL}{path}">
<meta property="og:locale" content="sv_SE">
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
    <p class="tagline">{TAGLINE}</p>
  </div>
  <nav class="sections wrap" aria-label="Sektioner">{nav}</nav>
  <div class="principle"><div class="wrap"><p>Inga bilder, inget brus – bara nyheterna. <a href="/om/#utan-bilder">Därför kör vi minimalistiskt →</a></p></div></div>
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
  <p class="kicker"><a href="/{p['section']}/">{sec}</a> · <time datetime="{p['date']:%Y-%m-%d}">{sv_date(p['date'].date())}</time></p>
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
    if not m:
        return ""
    groups = []
    for g in m.get("groups", []):
        rows = []
        for it in g.get("items", []):
            ch = it.get("change_pct")
            cls, chs = "", ""
            if isinstance(ch, (int, float)):
                cls = "up" if ch > 0 else "down" if ch < 0 else ""
                chs = f"{ch:+.2f} %".replace(".", ",")
            rows.append(f'<li><span class="m-name">{e(it["name"])}</span>'
                        f'<span class="m-val">{e(str(it["value"]))}</span>'
                        f'<span class="m-ch {cls}">{chs}</span></li>')
        groups.append(f'<div class="m-group"><h4>{e(g["title"])}</h4><ul>{"".join(rows)}</ul></div>')
    return f"""<section class="markets" aria-label="Marknadsläget">
  <div class="markets-head"><h2>Marknadsläget</h2><p class="asof">{e(m.get('as_of', ''))}</p></div>
  <div class="m-groups">{"".join(groups)}</div>
  <p class="m-src">Källa: {e(m.get('source', ''))}. Fördröjda uppgifter, inte investeringsråd.</p>
</section>"""


def build_index(posts, markets):
    if not posts:
        body = '<section class="empty"><h1>Snart här</h1><p>Första upplagan publiceras inom kort.</p></section>'
        return layout(SITE_NAME, body)
    lead = next((p for p in posts if p["featured"]), posts[0])
    rest = [p for p in posts if p is not lead]
    top = rest[:4]
    cols = []
    for k, v in SECTIONS.items():
        shown = [lead] + top
        items = [p for p in posts if p["section"] == k and p not in shown][:5]
        if not items:
            continue
        lis = "".join(
            f'<li><a href="{p["url"]}">{e(p["title"])}</a><time>{sv_date(p["date"].date())}</time></li>'
            for p in items)
        cols.append(f'<section class="col sec-{k}"><h2><a href="/{k}/">{v["name"]}</a></h2><ul>{lis}</ul>'
                    f'<a class="more" href="/{k}/">Mer {v["name"].lower()} →</a></section>')
    body = f"""<div class="front">
  <div class="lead-area">
    {card(lead, 'lead')}
    <div class="top-grid">{''.join(card(p) for p in top)}</div>
  </div>
  <aside class="side">{markets_box(markets)}</aside>
</div>
<div class="columns">{''.join(cols)}</div>"""
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
        "datePublished": p["date"].isoformat(), "inLanguage": "sv-SE",
        "mainEntityOfPage": SITE_URL + p["url"],
        "publisher": {"@type": "Organization", "name": SITE_NAME},
        "articleSection": sec,
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
    return layout(p["title"], body, p["summary"] or TAGLINE, p["url"], "article", extra)


def build_about():
    body = """<article class="post">
  <h1>Om The Nordic Brief</h1>
  <div class="body">
  <p>The Nordic Brief samlar varje dag det viktigaste inom tre områden: rikstäckande svenska nyheter, europeisk fotboll och global ekonomi – börs, krypto, räntor och valuta.</p>
  <p>Vi skriver korta, egna sammanfattningar och länkar alltid till originalkällorna, så att du snabbt får överblick och kan läsa vidare där nyheten publicerades först.</p>
  <h2 id="utan-bilder">Varför inga bilder?</h2>
  <p>The Nordic Brief är medvetet minimalistisk. Vi använder inga foton – sidan laddar snabbt, fungerar även med svag uppkoppling och låter nyheten stå i centrum. Där en bild faktiskt tillför något, till exempel börs- och kursutveckling, visar vi diagram byggda på data.</p>
  <h2>Så arbetar vi</h2>
  <p>Innehållet tas fram med hjälp av AI i flera steg: research, skrivande och en separat granskning där varje uppgift kontrolleras mot källorna innan publicering. Hittar du ett fel? Hör av dig så rättar vi.</p>
  <p>Kursuppgifter är fördröjda och ska inte ses som investeringsråd.</p>
  </div>
</article>"""
    return layout("Om oss", body, "Om The Nordic Brief och hur innehållet tas fram.", "/om/")


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_feed(posts):
    items = "".join(f"""<item><title>{e(p['title'])}</title><link>{SITE_URL}{p['url']}</link>
<guid>{SITE_URL}{p['url']}</guid><pubDate>{p['date'].strftime('%a, %d %b %Y %H:%M:%S +0100')}</pubDate>
<description>{e(p['summary'])}</description><category>{SECTIONS[p['section']]['name']}</category></item>"""
                    for p in posts[:40])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>{SITE_NAME}</title><link>{SITE_URL}/</link>
<description>{TAGLINE}</description><language>sv-se</language>{items}</channel></rss>"""


def build_sitemap(posts):
    urls = ["/", "/om/"] + [f"/{k}/" for k in SECTIONS] + [p["url"] for p in posts]
    body = "".join(f"<url><loc>{SITE_URL}{u}</loc></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'


def main():
    demo = "--demo" in sys.argv
    posts = load_posts(demo)
    markets = load_markets(demo)
    ef = CONTENT / "edition.json"
    if ef.exists():
        EDITION.update(json.loads(ef.read_text(encoding="utf-8")))
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    if (ROOT / "static").exists():
        for f in (ROOT / "static").iterdir():
            shutil.copy(f, OUT / f.name)
    write(OUT / "index.html", build_index(posts, markets))
    for k in SECTIONS:
        write(OUT / k / "index.html", build_section(k, posts))
    for p in posts:
        write(OUT / p["url"].strip("/") / "index.html", build_post(p, posts))
    write(OUT / "om" / "index.html", build_about())
    write(OUT / "feed.xml", build_feed(posts))
    write(OUT / "sitemap.xml", build_sitemap(posts))
    write(OUT / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    write(OUT / "CNAME", "nordicbrief.se\n")
    write(OUT / ".nojekyll", "")
    write(OUT / "404.html", layout("Sidan hittades inte",
                                    '<section class="empty"><h1>Sidan hittades inte</h1><p><a href="/">Till startsidan →</a></p></section>',
                                    path="/404.html"))
    print(f"Byggt {len(posts)} inlägg till {OUT}{' (DEMO)' if demo else ''}")


if __name__ == "__main__":
    main()
