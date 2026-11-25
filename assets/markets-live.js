/* Marknadsläget – liveuppdatering av krypto (CoinGecko) och valuta (ECB via Frankfurter) var 15:e minut.
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

  function getJSON(urls) {
    var url = urls[0];
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).catch(function (err) {
      if (urls.length > 1) return getJSON(urls.slice(1));
      throw err;
    });
  }

  function crypto() {
    return getJSON(["https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true"])
      .then(function (d) {
        var ok = set("btc", d.bitcoin && nf(0).format(d.bitcoin.usd) + " USD", d.bitcoin && d.bitcoin.usd_24h_change);
        ok = set("eth", d.ethereum && nf(0).format(d.ethereum.usd) + " USD", d.ethereum && d.ethereum.usd_24h_change) || ok;
        return ok ? new Date() : null;
      }).catch(function () { return null; });
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
      if (r[0]) parts.push("Krypto live " + r[0].toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Stockholm" }).replace(":", ".") + " (CoinGecko, 24 h)");
      if (r[1]) {
        var dt = new Date(r[1] + "T12:00:00Z");
        parts.push("valuta: ECB:s referenskurs " + dt.toLocaleDateString("sv-SE", { day: "numeric", month: "short", timeZone: "Europe/Stockholm" }) + " (Frankfurter)");
      }
      if (parts.length) { note.textContent = parts.join(" · ") + ". Uppdateras var 15:e minut."; note.hidden = false; }
    });
  }

  refresh();
  setInterval(function () { if (!document.hidden) refresh(); }, INTERVAL);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) refresh(); });
})();
