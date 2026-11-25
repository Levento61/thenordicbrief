#!/usr/bin/env python3
"""Hämtar Marknadsläget och skriver content/markets.json + docs/data/markets.json.

Körs av GitHub Actions (.github/workflows/markets.yml) var 15:e minut.
Källordning per rad:
  1. TradingView (scanner)
  2. Yahoo Finance
  3. Extra reserv: CoinGecko (krypto), ECB via Frankfurter (valuta); Riksbanken är primär för styrräntan
  4. Senast kända värde från föregående körning – så att inget fält någonsin blir tomt.
Endast standardbiblioteket.
"""
import datetime as dt
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
CONTENT_FILE = ROOT / "content" / "markets.json"
DOCS_FILE = ROOT / "docs" / "data" / "markets.json"
TZ = ZoneInfo("Europe/Stockholm")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
MONTHS = ["jan", "feb", "mars", "apr", "maj", "juni", "juli", "aug", "sep", "okt", "nov", "dec"]

# key, namn, grupp, decimaler, enhet, TradingView-tickers (i ordning), Yahoo-symbol, extra reserv
ROWS = [
    ("omxs30", "OMXS30", "Index", 2, "", ["OMXSTO:OMXS30"], "^OMX", None),
    ("spx", "S&P 500", "Index", 2, "", ["SP:SPX"], "^GSPC", None),
    ("nasdaq", "Nasdaq", "Index", 2, "", ["NASDAQ:IXIC"], "^IXIC", None),
    ("nyse", "NYSE", "Index", 2, "", ["NYSE:NYA"], "^NYA", None),
    ("btc", "Bitcoin", "Krypto", 0, "USD", ["BITSTAMP:BTCUSD", "COINBASE:BTCUSD"], "BTC-USD", ("cg", "bitcoin")),
    ("eth", "Ethereum", "Krypto", 0, "USD", ["BITSTAMP:ETHUSD", "COINBASE:ETHUSD"], "ETH-USD", ("cg", "ethereum")),
    ("sol", "Solana", "Krypto", 2, "USD", ["COINBASE:SOLUSD", "BINANCE:SOLUSDT"], "SOL-USD", ("cg", "solana")),
    ("eursek", "EUR/SEK", "Valuta", 2, "", ["FX_IDC:EURSEK", "FX:EURSEK"], "EURSEK=X", ("fx", "EUR")),
    ("usdsek", "USD/SEK", "Valuta", 2, "", ["FX_IDC:USDSEK", "FX:USDSEK"], "USDSEK=X", ("fx", "USD")),
    ("jpysek", "JPY/SEK", "Valuta", 4, "", ["FX_IDC:JPYSEK"], "JPYSEK=X", ("fx", "JPY")),
    ("policy", "Styrränta (Riksbanken)", "Räntor & råvaror", 2, "%", [], None, ("riksbank", "SECBREPOEFF")),
    ("gold", "Guld", "Räntor & råvaror", 2, "USD", ["TVC:GOLD", "OANDA:XAUUSD"], "GC=F", None),
    ("brent", "Brent", "Räntor & råvaror", 2, "USD", ["TVC:UKOIL", "ICEEUR:BRN1!"], "BZ=F", None),
    ("natgas", "Naturgas", "Räntor & råvaror", 3, "USD", ["NYMEX:NG1!", "TVC:NATGAS"], "NG=F", None),
]
GROUPS = ["Index", "Krypto", "Valuta", "Räntor & råvaror"]
TV_MARKETS = ["global", "america", "sweden", "crypto", "forex", "futures", "cfd"]

log = []


def http(url, data=None, headers=None, timeout=15):
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def ok(v):
    return isinstance(v, (int, float)) and v == v and v not in (float("inf"), float("-inf"))


def now_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


# ---------- 1. TradingView ----------
def tradingview(tickers):
    out, missing = {}, list(dict.fromkeys(tickers))
    for market in TV_MARKETS:
        if not missing:
            break
        body = json.dumps({"symbols": {"tickers": missing, "query": {"types": []}},
                           "columns": ["close", "change"]}).encode()
        try:
            d = http(f"https://scanner.tradingview.com/{market}/scan", data=body,
                     headers={"Content-Type": "application/json", "Origin": "https://www.tradingview.com",
                              "Referer": "https://www.tradingview.com/"})
        except Exception as ex:  # noqa: BLE001
            log.append(f"TradingView {market}: fel {ex}")
            continue
        got = []
        for row in d.get("data") or []:
            vals = row.get("d") or []
            if len(vals) >= 2 and ok(vals[0]):
                out[row["s"]] = (float(vals[0]), float(vals[1]) if ok(vals[1]) else None)
                got.append(row["s"])
        log.append(f"TradingView {market}: {len(got)} träffar {got}")
        missing = [t for t in missing if t not in out]
    return out


# ---------- 2. Yahoo Finance ----------
def yahoo(sym):
    for host in ("query1", "query2"):
        try:
            d = http(f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=1d&interval=5m")
            meta = d["chart"]["result"][0]["meta"]
            p = meta.get("regularMarketPrice")
            prev = meta.get("chartPreviousClose") or meta.get("previousClose")
            if ok(p):
                return float(p), ((p / prev - 1) * 100 if ok(prev) and prev else None)
        except Exception as ex:  # noqa: BLE001
            log.append(f"Yahoo {host} {sym}: fel {ex}")
    return None


# ---------- 3. Extra reserver ----------
_cg = None


def coingecko(cid):
    global _cg
    if _cg is None:
        try:
            _cg = http("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana"
                       "&vs_currencies=usd&include_24hr_change=true")
        except Exception as ex:  # noqa: BLE001
            log.append(f"CoinGecko: fel {ex}")
            _cg = {}
    c = _cg.get(cid) or {}
    return (float(c["usd"]), c.get("usd_24h_change")) if ok(c.get("usd")) else None


_fx = None


def frankfurter(cur):
    """SEK per 1 enhet av cur, med förändring mot föregående ECB-dag."""
    global _fx
    if _fx is None:
        _fx = {}
        start = (dt.date.today() - dt.timedelta(days=10)).isoformat()
        for base in ("https://api.frankfurter.dev/v1/", "https://api.frankfurter.app/"):
            try:
                d = http(f"{base}{start}..?from=SEK&to=EUR,USD,JPY")
                days = sorted(d.get("rates", {}))
                _fx = {"last": d["rates"][days[-1]], "prev": d["rates"][days[-2]] if len(days) > 1 else None}
                break
            except Exception as ex:  # noqa: BLE001
                log.append(f"Frankfurter {base}: fel {ex}")
    if not _fx.get("last") or not ok(_fx["last"].get(cur)):
        return None
    v = 1 / _fx["last"][cur]
    pv = 1 / _fx["prev"][cur] if _fx.get("prev") and ok(_fx["prev"].get(cur)) else None
    return v, ((v / pv - 1) * 100 if pv else None)


def riksbank(series):
    for url in (f"https://api.riksbank.se/swea/v1/Observations/Latest/{series}",):
        try:
            d = http(url)
            d = d[0] if isinstance(d, list) else d
            if ok(d.get("value")):
                return float(d["value"]), None
        except Exception as ex:  # noqa: BLE001
            log.append(f"Riksbanken: fel {ex}")
    return None


EXTRA = {"cg": (coingecko, "CoinGecko"), "fx": (frankfurter, "ECB via Frankfurter"), "riksbank": (riksbank, "Riksbanken")}


# ---------- formatering ----------
def fmt_num(v, dec):
    s = f"{v:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s.replace(" ", " ")


def fmt_value(v, dec, unit):
    if unit == "%":
        return fmt_num(v, dec) + " %"
    return fmt_num(v, dec) + (f" {unit}" if unit else "")


def fmt_time(iso):
    t = dt.datetime.fromisoformat(iso).astimezone(TZ)
    return f"{t.day} {MONTHS[t.month - 1]} {t:%H.%M}"


def load_previous():
    for f in (DOCS_FILE, CONTENT_FILE):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            prev = {it["key"]: it for g in d.get("groups", []) for it in g.get("items", []) if it.get("key")}
            if prev:
                return prev
        except Exception:  # noqa: BLE001
            pass
    return {}


def main():
    prev = load_previous()
    tv = tradingview([t for r in ROWS for t in r[5]])
    stamp = now_iso()
    items, used, fresh = {}, [], 0
    for key, name, group, dec, unit, tvs, ysym, extra in ROWS:
        res, src = None, None
        if extra and extra[0] == "riksbank":  # primärkälla för styrräntan
            res, src = riksbank(extra[1]), "Riksbanken"
        for t in tvs:
            if res:
                break
            if t in tv:
                res, src = tv[t], "TradingView"
        if not res and ysym:
            res = yahoo(ysym)
            src = "Yahoo Finance" if res else None
        if not res and extra and extra[0] != "riksbank":
            fn, label = EXTRA[extra[0]]
            res = fn(extra[1])
            src = label if res else None
        if res:
            v, ch = res
            items[key] = {"key": key, "name": name, "value": fmt_value(v, dec, unit), "raw": round(v, 6),
                          "change_pct": round(ch, 2) if ok(ch) else None, "source": src, "as_of": stamp,
                          "stale": False}
            fresh += 1
            used.append(src)
        elif key in prev and prev[key].get("value") not in (None, "", "—"):
            items[key] = dict(prev[key], stale=True)
            used.append(prev[key].get("source", ""))
            log.append(f"{name}: alla källor föll – behåller senast kända värde från {prev[key].get('as_of')}")
        else:
            log.append(f"{name}: INGET VÄRDE (ingen källa och inget tidigare värde)")
    groups = [{"title": g, "items": [items[r[0]] for r in ROWS if r[2] == g and r[0] in items]} for g in GROUPS]
    srcs = list(dict.fromkeys(s for s in used if s))
    out = {
        "updated": stamp,
        "as_of": fmt_time(stamp),
        "source": ", ".join(srcs),
        "groups": groups,
    }
    for f in (CONTENT_FILE, DOCS_FILE):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("\n".join(log))
    print(f"{fresh}/{len(ROWS)} färska värden, {len(items)}/{len(ROWS)} rader ifyllda")
    for g in groups:
        for it in g["items"]:
            print(f"  {it['name']:24} {it['value']:>16} {it['change_pct']}  [{it['source']}{', gammalt' if it.get('stale') else ''}]")
    return 0 if len(items) == len(ROWS) else 1


if __name__ == "__main__":
    sys.exit(main())
