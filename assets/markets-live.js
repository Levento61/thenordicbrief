/* Marknadsläget – hämtar /data/markets.json (skrivs av GitHub Actions var 15:e minut,
   se scripts/fetch_markets.py) och uppdaterar rutan utan omladdning. Svarar inte filen
   ligger värdena från senaste bygget kvar, så rutan blir aldrig tom. */
(function () {
  var box = document.querySelector(".markets");
  if (!box) return;
  var nf = new Intl.NumberFormat("sv-SE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  function apply(d) {
    if (!d || !d.groups) return;
    d.groups.forEach(function (g) {
      (g.items || []).forEach(function (it) {
        var li = box.querySelector('[data-key="' + it.key + '"]');
        if (!li || !it.value) return;
        li.querySelector(".m-val").textContent = it.value;
        var c = li.querySelector(".m-ch"), ch = it.change_pct;
        c.className = "m-ch";
        c.textContent = "";
        if (typeof ch === "number" && isFinite(ch)) {
          c.classList.add(ch > 0 ? "up" : ch < 0 ? "down" : "flat");
          c.textContent = (ch > 0 ? "+" : ch < 0 ? "−" : "") + nf.format(Math.abs(ch)) + " %";
        }
        li.title = (it.source || "") + (it.stale ? " (senast kända värde)" : "");
      });
    });
    var a = box.querySelector(".asof"); if (a && d.as_of) a.textContent = d.as_of;
    var s = box.querySelector(".m-srcs"); if (s && d.source) s.textContent = d.source;
  }

  var last = 0;
  function refresh() {
    if (Date.now() - last < 60 * 1000) return;
    last = Date.now();
    fetch("/data/markets.json?t=" + Math.floor(Date.now() / 60000), { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(apply)
      .catch(function () { /* behåll värdena som redan visas */ });
  }

  refresh();
  setInterval(function () { if (!document.hidden) refresh(); }, 5 * 60 * 1000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) refresh(); });
})();
