#!/usr/bin/env python3
"""Skapar Instagram-kort (1080x1350) för en upplaga av The Nordic Brief.

Användning:
    python3 social/make_cards.py --edition morgon --posts content/posts/a.md content/posts/b.md ...
    python3 social/make_cards.py --edition morgon --auto 3      # tar de 3 senaste (toppnyheten först)
    lägg till --markets för att även göra ett Marknadsläget-kort

Bilderna sparas i social/cards/ÅÅÅÅ-MM-DD-<upplaga>/; build.py kopierar dem till docs/social/
så att de blir publikt nåbara på https://nordicbrief.se/social/... efter build + push (krävs för att Buffer ska kunna hämta dem).
En caption-fil (caption.txt) och en lista med bild-URL:er (urls.txt) skrivs i samma mapp.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "social" / "fonts"
SITE = "https://nordicbrief.se"
W, H = 1080, 1350
INK, PAPER, MUTED, RULE = "#111418", "#ffffff", "#5b616b", "#e2e4e8"
SEC = {
    "sverige": ("Sverige", "#1d5bd6"),
    "fotboll": ("Fotboll", "#178a4c"),
    "ekonomi": ("Ekonomi", "#c2185b"),
}
EDITIONS = {"morgon": "Morgonens", "lunch": "Lunchens", "eftermiddag": "Eftermiddagens", "kvall": "Kvällens"}
MONTHS = ["jan", "feb", "mars", "april", "maj", "juni", "juli", "aug", "sep", "okt", "nov", "dec"]


def font(name, size):
    return ImageFont.truetype(str(FONTS / f"{name}.ttf"), size)


def wrap(draw, text, fnt, width, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while draw.textlength(lines[-1] + "…", font=fnt) > width and " " in lines[-1]:
            lines[-1] = lines[-1].rsplit(" ", 1)[0]
        lines[-1] += "…"
    return lines


def fit_lines(draw, text, name, sizes, width, max_lines):
    for s in sizes:
        f = font(name, s)
        lines = wrap(draw, text, f, width, 99)
        if len(lines) <= max_lines:
            return f, lines, s
    f = font(name, sizes[-1])
    return f, wrap(draw, text, f, width, max_lines), sizes[-1]


def logo(draw, x, y, scale=1.0, color=INK):
    s = int(46 * scale)
    draw.rounded_rectangle([x, y, x + s, y + s], radius=int(10 * scale), fill=INK if color == INK else "#ffffff")
    bar = INK if color != INK else None
    for i, c in enumerate(["#1d5bd6", "#178a4c", "#c2185b"]):
        by = y + int((11 + i * 10) * scale)
        draw.rounded_rectangle([x + int(10 * scale), by, x + s - int(10 * scale), by + int(5 * scale)],
                               radius=int(2 * scale), fill=c)
    f1, f2 = font("Fraunces-SemiBold", int(40 * scale)), font("Fraunces-ExtraBold", int(40 * scale))
    tx = x + s + int(16 * scale)
    ty = y + int(1 * scale)
    draw.text((tx, ty), "The Nordic ", font=f1, fill=color)
    draw.text((tx + draw.textlength("The Nordic ", font=f1), ty), "Brief", font=f2, fill=color)


def footer(draw, page=None, total=None):
    draw.line([(80, H - 140), (W - 80, H - 140)], fill=RULE, width=2)
    logo(draw, 80, H - 105, 0.85)
    f = font("Inter-SemiBold", 30)
    t = "nordicbrief.se"
    draw.text((W - 80 - draw.textlength(t, font=f), H - 96), t, font=f, fill=MUTED)
    if page and total:
        f2 = font("Inter-Regular", 26)
        pt = f"{page}/{total}"
        draw.text((W / 2 - draw.textlength(pt, font=f2) / 2, H - 94), pt, font=f2, fill=MUTED)


def cover_card(edition, date, posts):
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    logo(d, 80, 90, 1.1, color="#ffffff")
    fk = font("Inter-SemiBold", 34)
    d.text((80, 260), f"{date.day} {MONTHS[date.month - 1]} {date.year}".upper(), font=fk, fill="#9aa2ad")
    big = font("Fraunces-ExtraBold", 108)
    y = 320
    for line in [EDITIONS.get(edition, "Dagens"), f"{len(posts)} viktigaste"]:
        d.text((80, y), line, font=big, fill="#ffffff")
        y += 122
    y += 50
    for p in posts:
        name, col = SEC[p["section"]]
        d.rectangle([80, y + 8, 92, y + 48], fill=col)
        d.text((116, y), name.upper(), font=font("Inter-Bold", 26), fill=col if col != "#1d5bd6" else "#6f9bff")
        ft = font("Inter-SemiBold", 36)
        lines = wrap(d, p["title"], ft, W - 196, 2)
        ty = y + 38
        for ln in lines:
            d.text((116, ty), ln, font=ft, fill="#ffffff")
            ty += 46
        y = ty + 34
    f = font("Inter-Regular", 30)
    t = "Svep för att läsa  »"
    d.text((80, H - 120), t, font=f, fill="#9aa2ad")
    return im


def story_card(p, page, total):
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    name, col = SEC[p["section"]]
    d.rectangle([0, 0, W, 18], fill=col)
    d.text((80, 100), name.upper(), font=font("Inter-Bold", 32), fill=col)
    fh, lines, size = fit_lines(d, p["title"], "Fraunces-ExtraBold", [92, 84, 76, 68, 62], W - 160, 6)
    y = 170
    lh = int(size * 1.12)
    for ln in lines:
        d.text((80, y), ln, font=fh, fill=INK)
        y += lh
    y += 40
    d.line([(80, y), (240, y)], fill=col, width=6)
    y += 44
    fs = font("Inter-Regular", 40)
    room = int((H - 200 - y) / 56)
    for ln in wrap(d, p.get("summary", ""), fs, W - 160, max(2, min(7, room))):
        d.text((80, y), ln, font=fs, fill="#2d333d")
        y += 56
    d.text((80, H - 200), "Läs hela texten på nordicbrief.se  »", font=font("Inter-SemiBold", 30), fill=col)
    footer(d, page, total)
    return im


def markets_card(m, page, total):
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    d.text((80, 100), "MARKNADSLÄGET", font=font("Inter-Bold", 32), fill="#ff9ec2")
    d.text((80, 150), m.get("as_of", ""), font=font("Inter-Regular", 30), fill="#9aa2ad")
    y = 230
    fn, fv = font("Inter-SemiBold", 40), font("Inter-Regular", 40)
    for g in m.get("groups", []):
        d.text((80, y), g["title"].upper(), font=font("Inter-Bold", 24), fill="#ff9ec2")
        y += 44
        for it in g.get("items", []):
            if y > H - 260:
                break
            d.text((80, y), it["name"], font=fn, fill="#ffffff")
            val = str(it["value"])
            ch = it.get("change_pct")
            chs = f"{ch:+.2f} %".replace(".", ",") if isinstance(ch, (int, float)) else ""
            cc = "#6fd39b" if isinstance(ch, (int, float)) and ch > 0 else "#ff8a80" if isinstance(ch, (int, float)) and ch < 0 else "#9aa2ad"
            d.text((W - 80 - 230 - d.textlength(val, font=fv), y), val, font=fv, fill="#ffffff")
            d.text((W - 80 - d.textlength(chs, font=fn), y), chs, font=fn, fill=cc)
            y += 62
        y += 18
    d.text((80, H - 190), f"Källa: {m.get('source', '')}. Ej investeringsråd.", font=font("Inter-Regular", 24), fill="#9aa2ad")
    d.line([(80, H - 140), (W - 80, H - 140)], fill="#2a2f37", width=2)
    logo(d, 80, H - 105, 0.85, color="#ffffff")
    f = font("Inter-SemiBold", 30)
    d.text((W - 80 - d.textlength("nordicbrief.se", font=f), H - 96), "nordicbrief.se", font=f, fill="#9aa2ad")
    return im


def load(path):
    raw = Path(path).read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
    meta = yaml.safe_load(m.group(1))
    return {"title": meta["title"], "summary": meta.get("summary", ""), "section": meta["section"],
            "featured": bool(meta.get("featured")), "date": str(meta.get("date"))}


def caption(edition, posts):
    head = {"morgon": "☀️ Morgonens viktigaste", "lunch": "🍽️ Lunchens nyheter", "eftermiddag": "📰 Eftermiddagens läge", "kvall": "🌙 Kvällens nyheter"}.get(edition, "Dagens nyheter")
    lines = [head, ""]
    for p in posts:
        lines.append(f"▪️ {SEC[p['section']][0]}: {p['title']}")
    lines += ["", "Kort, källgranskat och utan brus. Läs mer på nordicbrief.se – länk i bion.", "",
              "#nyheter #sverige #fotboll #ekonomi #börsen #krypto #nordicbrief"]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edition", required=True, choices=list(EDITIONS))
    ap.add_argument("--posts", nargs="*", default=[])
    ap.add_argument("--auto", type=int, default=0)
    ap.add_argument("--markets", action="store_true")
    ap.add_argument("--date", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    files = a.posts
    if a.auto:
        allp = sorted((ROOT / "content" / "posts").glob("*.md"), reverse=True)
        loaded = [(f, load(f)) for f in allp]
        loaded.sort(key=lambda x: (not x[1]["featured"], ), reverse=False)
        files = [str(f) for f, _ in loaded[:a.auto]]
    posts = [load(f) for f in files]
    if not posts:
        sys.exit("Inga artiklar valda")
    date = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    out = Path(a.out) if a.out else ROOT / "social" / "cards" / f"{date.isoformat()}-{a.edition}"
    out.mkdir(parents=True, exist_ok=True)
    cards = [cover_card(a.edition, date, posts)]
    extra = 1 if a.markets else 0
    total = len(posts) + 1 + extra
    for i, p in enumerate(posts, start=2):
        cards.append(story_card(p, i, total))
    if a.markets:
        mf = ROOT / "content" / "markets.json"
        if mf.exists():
            cards.append(markets_card(json.loads(mf.read_text(encoding="utf-8")), total, total))
    urls = []
    for i, im in enumerate(cards, start=1):
        fn = out / f"{i:02d}.jpg"
        im.convert("RGB").save(fn, "JPEG", quality=92, optimize=True)
        urls.append(f"{SITE}/social/{out.name}/{fn.name}")
    (out / "caption.txt").write_text(caption(a.edition, posts), encoding="utf-8")
    (out / "urls.txt").write_text("\n".join(urls), encoding="utf-8")
    print("\n".join(urls))


if __name__ == "__main__":
    main()
