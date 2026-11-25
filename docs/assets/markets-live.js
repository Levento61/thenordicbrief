/* Marknadsläget – liveuppdatering av krypto (CoinDesk-index; reserv CryptoCompare, CoinGecko, Coinbase, Binance) och valuta (ECB via Frankfurter) var 15:e minut.
   Index, räntor och råvaror kommer fortsatt från upplagornas granskade markets.json. */
(function () {
  var box = document.querySelector(".markets");
  if (!box) return;
  var INTERVAL = 15 * 60 * 1000;
  var nf = function (d) { return new Intl.NumberFormat("sv-SE", { minimumFractionDigits: d, maximumFractionDigits: d }); };
  var note = box.querySelector(".m-live");

  function set(key, value, ch) {
    var li = box.querySelector('[data-live="' + key + '"]');
    if (!li || !value || /NaN|∞/.test(value)) return false;
    li.querySelector(".m-val").textContent = value;
    var c = li.querySelector(".m-ch");
    c.className = "m-ch";
    c.textContent = "";
    if (typeof ch === "number" && isFinite(ch)) {
      c.classList.add(ch > 0 ? "up" : ch < 0 ? "down" : "flat");
      c.textContent = (ch > 0 ? "+" : ch < 0 ? "-" : "") + nf(2).format(Math.abs(ch)) + " %";
    }
    li.classList.add("is-live");
    return true;
  }

  function fetchJSON(url) {
    var ctrl = typeof AbortController === "function" ? new AbortController() : null;
    var t = ctrl ? setTimeout(function () { ctrl.abort(); }, 8000) : null;
    return fetch(url, { cache: "no-store", signal: ctrl ? ctrl.signal : undefined }).then(function (r) {
      if (t) clearTimeout(t);
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }, function (err) { if (t) clearTimeout(t); throw err; });
  }
  function getJSON(urls) {
    return fetchJSON(urls[0]).catch(function (err) {
      if (urls.length > 1) return getJSON(urls.slice(1));
      throw err;
    });
  }

  /* Kryptokällor i prioritetsordning. Varje källa returnerar {btc: [pris, ändring24h], eth: [...]}. */
  var num = function (x) { var n = parseFloat(x); return isFinite(n) ? n : null; };
  var CRYPTO = [
    { name: "CoinDesk-index", get: function () {
      return fetchJSON("https://data-api.coindesk.com/index/cc/v1/latest/tick?market=cadli&instruments=BTC-USD,ETH-USD").then(function (d) {
        var D = (d && d.Data) || {}, f = function (k) { return D[k] ? [num(D[k].VALUE), num(D[k].MOVING_24_HOUR_CHANGE_PERCENTAGE)] : null; };
        return { btc: f("BTC-USD"), eth: f("ETH-USD") };
      });
    } },
    { name: "CoinDesk/CryptoCompare", get: function () {
      return fetchJSON("https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC,ETH&tsyms=USD").then(function (d) {
        var R = (d && d.RAW) || {}, f = function (k) { return R[k] && R[k].USD ? [num(R[k].USD.PRICE), num(R[k].USD.CHANGEPCT24HOUR)] : null; };
        return { btc: f("BTC"), eth: f("ETH") };
      });
    } },
    { name: "data via CoinGecko", get: function () {
      return fetchJSON("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true").then(function (d) {
        var f = function (k) { return d && d[k] ? [num(d[k].usd), num(d[k].usd_24h_change)] : null; };
        return { btc: f("bitcoin"), eth: f("ethereum") };
      });
    } },
    { name: "data via Coinbase", get: function () {
      var one = function (pair) {
        return fetchJSON("https://api.exchange.coinbase.com/products/" + pair + "/stats").then(function (d) {
          var last = num(d.last), open = num(d.open);
          return last ? [last, open ? (last / open - 1) * 100 : null] : null;
        }).catch(function () { return null; });
      };
      return Promise.all([one("BTC-USD"), one("ETH-USD")]).then(function (r) { return { btc: r[0], eth: r[1] }; });
    } },
    { name: "data via Binance (USDT)", get: function () {
      return fetchJSON('https://data-api.binance.vision/api/v3/ticker/24hr?symbols=%5B%22BTCUSDT%22,%22ETHUSDT%22%5D').then(function (arr) {
        var m = {}; (arr || []).forEach(function (x) { m[x.symbol] = [num(x.lastPrice), num(x.priceChangePercent)]; });
        return { btc: m.BTCUSDT || null, eth: m.ETHUSDT || null };
      });
    } }
  ];

  function fmtCrypto(v) { return nf(0).format(v) + " USD"; }
  function crypto() {
    var need = { btc: true, eth: true }, used = [];
    function next(i) {
      if (i >= CRYPTO.length || (!need.btc && !need.eth)) return Promise.resolve();
      return CRYPTO[i].get().catch(function () { return {}; }).then(function (r) {
        var hit = false;
        ["btc", "eth"].forEach(function (k) {
          if (need[k] && r && r[k] && r[k][0] && set(k, fmtCrypto(r[k][0]), r[k][1])) { need[k] = false; hit = true; }
        });
        if (hit) used.push(CRYPTO[i].name);
        return next(i + 1);
      });
    }
    return next(0).then(function () { return used.length ? { at: new Date(), src: used.join(" + ") } : null; });
  }

  function fx() {
    var from = new Date(Date.now() - 10 * 864e5).toISOString().slice(0, 10);
    var q = from + "..?from=EUR&to=SEK,USD";
    return getJSON(["https://api.frankfurter.dev/v1/" + q, "https://api.frankfurter.app/" + q])
      .then(function (d) {
        var days = Object.keys(d.rates || {}).sort();
        if (!days.length) return null;
        var last = d.rates[days[days.length - 1]], prev = days.length > 1 ? d.rates[days[days.length - 2]] : null;
        var eursek = last.SEK, usdsek = last.SEK / last.USD;
        var pct = function (a, b) { return b ? (a / b - 1) * 100 : null; };
        set("eursek", nf(2).format(eursek), prev && pct(eursek, prev.SEK));
        set("usdsek", nf(2).format(usdsek), prev && pct(usdsek, prev.SEK / prev.USD));
        return days[days.length - 1];
      }).catch(function () { return null; });
  }

  var lastRun = 0;
  function refresh() {
    if (Date.now() - lastRun < 60 * 1000) return;
    lastRun = Date.now();
    Promise.all([crypto(), fx()]).then(function (r) {
      if (!note) return;
      var parts = [];
      if (r[0]) parts.push("Krypto live " + r[0].at.toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Stockholm" }).replace(":", ".") + " (" + r[0].src + ", 24 h)");
      if (r[1]) {
        var dt = new Date(r[1] + "T12:00:00Z");
        parts.push("valuta: ECB:s referenskurs " + dt.toLocaleDateString("sv-SE", { day: "numeric", month: "short", timeZone: "Europe/Stockholm" }) + " (via Frankfurter)");
      }
      if (parts.length) { note.textContent = parts.join(" · ") + ". Uppdateras var 15:e minut."; note.hidden = false; }
    });
  }

  refresh();
  setInterval(function () { if (!document.hidden) refresh(); }, INTERVAL);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) refresh(); });
})();
