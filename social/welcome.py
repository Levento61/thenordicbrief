#!/usr/bin/env python3
"""Profilbild och välkomstkarusell för Instagram."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from make_cards import font, logo, wrap, W, H, INK, MUTED, RULE, SITE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "social" / "cards" / "valkommen"
OUT.mkdir(parents=True, exist_ok=True)
BLUE, GREEN, PINK, GREY = "#1d5bd6", "#178a4c", "#c2185b", "#9aa2ad"


def profile_picture():
    s = 1080
    im = Image.new("RGB", (s, s), INK)
    d = ImageDraw.Draw(im)
    bw, bh, gap = 560, 84, 66
    x0 = (s - bw) // 2
    y0 = (s - (3 * bh + 2 * gap)) // 2
    for i, c in enumerate([BLUE, GREEN, PINK]):
        y = y0 + i * (bh + gap)
        d.rounded_rectangle([x0, y, x0 + bw, y + bh], radius=bh // 2, fill=c)
    im.save(ROOT / "social" / "profilbild.png")


def slide1():
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    logo(d, 80, 90, 1.1, color="#ffffff")
    big = font("Fraunces-ExtraBold", 120)
    y = 380
    for ln in ["Välkommen", "till The", "Nordic Brief"]:
        d.text((80, y), ln, font=big, fill="#ffffff")
        y += 136
    y += 40
    for i, c in enumerate([BLUE, GREEN, PINK]):
        d.rounded_rectangle([80 + i * 110, y, 80 + i * 110 + 90, y + 14], radius=7, fill=c)
    f = font("Inter-Regular", 40)
    y += 70
    for ln in wrap(d, "Nyheterna du behöver – korta, källgranskade och utan brus.", f, W - 160, 3):
        d.text((80, y), ln, font=f, fill="#d4d8de")
        y += 56
    d.text((80, H - 120), "Svep för att läsa  »", font=font("Inter-Regular", 30), fill=GREY)
    return im


def page_footer(d, n, total, dark=False):
    col = "#2a2f37" if dark else RULE
    d.line([(80, H - 140), (W - 80, H - 140)], fill=col, width=2)
    logo(d, 80, H - 105, 0.85, color="#ffffff" if dark else INK)
    f2 = font("Inter-Regular", 26)
    pt = f"{n}/{total}"
    d.text((W / 2 - d.textlength(pt, font=f2) / 2, H - 94), pt, font=f2, fill=MUTED)
    f = font("Inter-SemiBold", 30)
    d.text((W - 80 - d.textlength("nordicbrief.se", font=f), H - 96), "nordicbrief.se", font=f,
           fill=GREY if dark else MUTED)


def slide2():
    im = Image.new("RGB", (W, H), "#ffffff")
    d = ImageDraw.Draw(im)
    d.text((80, 100), "VAD VI BEVAKAR", font=font("Inter-Bold", 32), fill=MUTED)
    d.text((80, 150), "Tre områden.", font=font("Fraunces-ExtraBold", 96), fill=INK)
    d.text((80, 260), "Varje dag.", font=font("Fraunces-ExtraBold", 96), fill=INK)
    rows = [(BLUE, "Sverige", "Rikstäckande nyheter – politik, samhälle och det som påverkar dig."),
            (GREEN, "Fotboll", "All europeisk fotboll – ligor, cuper, landslag och transfers."),
            (PINK, "Ekonomi", "Börs, räntor, krypto och valuta – inrikes och utrikes.")]
    y = 450
    for c, t, desc in rows:
        d.rectangle([80, y, 94, y + 200], fill=c)
        d.text((126, y), t, font=font("Fraunces-ExtraBold", 60), fill=c)
        yy = y + 84
        for ln in wrap(d, desc, font("Inter-Regular", 36), W - 206, 3):
            d.text((126, yy), ln, font=font("Inter-Regular", 36), fill="#2d333d")
            yy += 50
        y += 250
    page_footer(d, 2, 4)
    return im


def slide3():
    im = Image.new("RGB", (W, H), "#ffffff")
    d = ImageDraw.Draw(im)
    d.text((80, 100), "SÅ FUNKAR DET", font=font("Inter-Bold", 32), fill=MUTED)
    d.text((80, 150), "Fyra upplagor", font=font("Fraunces-ExtraBold", 96), fill=INK)
    d.text((80, 260), "om dagen.", font=font("Fraunces-ExtraBold", 96), fill=INK)
    times = [("08.00", "Morgon", "Allt du missat under natten"),
             ("13.00", "Lunch", "Förmiddagens utveckling"),
             ("18.00", "Kväll", "Dagens läge och börsens stängning"),
             ("10.30 · 15 · 21", "Snabbkoll", "Stora nyheter direkt när de händer")]
    y = 440
    for t, n, desc in times:
        d.text((80, y), t, font=font("Fraunces-ExtraBold", 72), fill=INK)
        d.text((380, y + 4), n, font=font("Inter-Bold", 38), fill=INK)
        d.text((380, y + 56), desc, font=font("Inter-Regular", 32), fill=MUTED)
        y += 150
        d.line([(80, y - 28), (W - 80, y - 28)], fill=RULE, width=2)
    page_footer(d, 3, 4)
    return im


def slide4():
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    d.text((80, 100), "VÅRT LÖFTE", font=font("Inter-Bold", 32), fill="#ff9ec2")
    big = font("Fraunces-ExtraBold", 104)
    y = 170
    for ln in ["Inga bilder.", "Inget brus.", "Bara nyheterna."]:
        d.text((80, y), ln, font=big, fill="#ffffff")
        y += 120
    y += 50
    pts = ["Korta sammanfattningar med egna ord", "Varje nyhet granskas mot källorna",
           "Länk till originalkällan i varje artikel"]
    f = font("Inter-Regular", 38)
    for p in pts:
        d.rounded_rectangle([80, y + 14, 98, y + 32], radius=9, fill="#6fd39b")
        d.text((124, y), p, font=f, fill="#e6e9ee")
        y += 70
    y += 60
    d.text((80, y), "Följ oss för dagens viktigaste.", font=font("Inter-Bold", 42), fill="#ffffff")
    d.text((80, y + 62), "Allt finns på nordicbrief.se – länk i bion.", font=font("Inter-Regular", 36), fill=GREY)
    page_footer(d, 4, 4, dark=True)
    return im


profile_picture()
urls = []
for i, f in enumerate([slide1, slide2, slide3, slide4], start=1):
    p = OUT / f"{i:02d}.jpg"
    f().convert("RGB").save(p, "JPEG", quality=92, optimize=True)
    urls.append(f"{SITE}/social/valkommen/{p.name}")
(OUT / "urls.txt").write_text("\n".join(urls), encoding="utf-8")
print("\n".join(urls))
