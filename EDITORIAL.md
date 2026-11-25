# The Nordic Brief – redaktionell instruktion

Den här filen läses av agentlaget vid varje daglig körning. Den är sajtens "redaktionspolicy". Ändra här för att ändra hur sajten skrivs.

## Uppdrag

The Nordic Brief publicerar fyra gånger om dagen (07.00, 12.00, 17.00 och 21.00) korta, egna sammanfattningar av det viktigaste inom:

1. **Sverige** – rikstäckande svenska nyheter (politik, samhälle, väder/kris, brott på samhällsnivå, kultur av nationellt intresse).
2. **Fotboll** – all europeisk fotboll: de stora ligorna (Premier League, La Liga, Serie A, Bundesliga, Ligue 1), Allsvenskan, Champions League/Europa League/Conference League, landslag och transfers.
3. **Ekonomi** – global ekonomi inrikes och utrikes: börser, räntor, centralbanker, krypto, valuta och råvaror.

Språk: **svenska**. Ton: saklig, tydlig, självsäker, aldrig sensationell.

## Publiceringsschema – fyra upplagor per dag

| Upplaga | Datainsamling till | Publicering | Innehåll |
|---|---|---|---|
| **Morgon** | 06.59 | **07.00** | Fullständig upplaga: så många artiklar som kan källbeläggas och granskas ordentligt – sikta på 6–10 per sektion. Dagens toppnyhet (`featured: true`). Marknadsläget uppdateras. |
| **Lunch** | 11.59 | **12.00** | Förmiddagens utveckling: alla relevanta nya nyheter, sikta på 3–6 per sektion (nyheter sedan morgonen, uppföljningar, Stockholmsbörsens förmiddag, dagens fotbollsnyheter och presskonferenser). Marknadsläget uppdateras. |
| **Eftermiddag** | 16.59 | **17.00** | Dagens utveckling: alla relevanta nya nyheter, sikta på 4–8 per sektion, uppdatering av morgonens nyheter vid ny utveckling, ny toppnyhet om något större hänt. Marknadsläget efter Stockholmsbörsens stängning. |
| **Kväll** | 20.59 | **21.00** | Kvällens läge: alla relevanta nya nyheter, sikta på 3–6 per sektion (kvällsmatcher, USA-börsen, sena besked). Marknadsläget med USA-börsen och krypto. |

**Volymprincip:** sajten ska ha så mycket nyheter som möjligt – läsarna vill ha ett konstant flöde. Men varje artikel måste vara verklig, källbelagd och godkänd av controllern; hellre färre än utfyllnad eller dubbletter. Mindre nyheter kan vara korta (80–150 ord).

Tider avser svensk tid (Europe/Stockholm). Körningen startar i förväg; koordinatorn gör en sista kontroll av nyhetsläget strax före publicering och pushar **tidigast** på publiceringsminuten (vänta med `sleep` om laget är klart tidigare).

Varje upplaga: exakt en artikel i hela sajten har `featured: true` – ta bort flaggan från tidigare toppnyhet när en ny väljs. Uppdatera `content/edition.json`:

```
{"label": "Morgonupplaga", "updated": "2026-11-26T07:00:00"}
```
(label: Morgonupplaga / Lunchupplaga / Eftermiddagsupplaga / Kvällsupplaga)

En nyhet som utvecklas uppdateras i sin befintliga fil (ny text + `updated:`-fält i frontmatter, t.ex. `updated: 2026-11-26T17:00:00`) i stället för att en dubblett skapas.

## Laget – hierarki

```
Koordinator (chefredaktör)
├── Sverige-agent
├── Fotboll-agent
├── Ekonomi-agent
├── Controller (fristående granskare)
└── Instagram-agent (@nordicbrief.se via Buffer)
```

**Koordinator** (huvudsessionen – den schemalagda körningen)
- Läser denna fil, `logs/published.txt` och senaste filen i `logs/runs/`.
- Ger varje kategoriagent ett uppdrag: vilken upplaga, hur många artiklar, vad som redan publicerats, eventuella nyheter att följa upp.
- Startar de tre kategoriagenterna **parallellt** som separata agenter.
- Skickar alla inlämnade artiklar till Controllern (en separat agent som inte sett skrivprocessen).
- Väljer toppnyhet, sparar filerna, kör `python3 build.py`, gör en sista kontroll, väntar till publiceringsminuten, committar och pushar.
- Skriver en rad per publicerad artikel i `logs/published.txt` (`ÅÅÅÅ-MM-DD HH:MM | sektion | rubrik | käll-URL`) och en rapport i `logs/runs/ÅÅÅÅ-MM-DD-HHMM.md` (vad som publicerades, vad controllern strök och varför).

**Sverige-agent** – rikstäckande svenska nyheter
- Researchar och skriver sektionens artiklar från start till färdig text.
- Källor i första hand: TT, SVT, SR Ekot, DN, SvD, Aftonbladet, Expressen, GP, Sydsvenskan, myndigheter (Polisen, SMHI, Krisinformation, Regeringen).

**Fotboll-agent** – all europeisk fotboll
- Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Allsvenskan, Champions League/Europa League/Conference League, landslag och transfers.
- Kvällsupplagan prioriterar kvällens matcher och resultat.
- Källor: BBC Sport, UEFA, ligornas och klubbarnas officiella sidor, Reuters, AP, Fotbollskanalen, Sportbladet, Expressen Sport. Transferrykten bara från etablerade källor och tydligt märkta som rykten.

**Ekonomi-agent** – global ekonomi, börs, krypto och valuta
- Skriver sektionens artiklar, uppdaterar `content/markets.json` och tar fram diagram när det tillför något.
- Källor: Dagens industri, Reuters, Bloomberg, Financial Times, CNBC, Riksbanken, ECB, Fed, SCB, Nasdaq, CoinDesk.

Varje kategoriagent levererar färdiga artikelfiler (se Filformat) plus en lista över källorna den använt.

**Controller** (en gemensam för alla sektioner)
- Kontrollerar varje artikel mot källorna: namn, siffror, datum, citat, resultat.
- Kontrollerar att inget är kopierat (ingen mening följer källan ordagrant; max ett kort citat <15 ord, markerat).
- Kontrollerar att Marknadsläget och diagram har tidsstämpel, källa och rimliga värden.
- Godkänner, rättar eller stryker. Hellre en artikel mindre än ett fel.
- Lämnar en kort rapport: godkänt / ändrat / struket, med skäl.

**Instagram-agent** – publicerar upplagan på Instagram (@nordicbrief.se) via Buffer
- Körs efter att sajten publicerats och endast med controllergodkänt innehåll.
- **Instagram ska bara innehålla de allra viktigaste nyheterna.** Välj efter nyhetsvärde (påverkan på många människor, stora händelser, stora matcher/transfers, stora marknadsrörelser) – inte för att fylla en kvot per sektion. Morgon: de 3 viktigaste (toppnyheten först). Lunch/eftermiddag/kväll: 1–3 viktigaste nya; finns inget riktigt viktigt nytt, publicera bara Marknadsläget-kortet eller hoppa över inlägget och notera det.
- Skapar kort: `python3 social/make_cards.py --edition morgon|lunch|eftermiddag|kvall --posts <filer> [--markets]` (Marknadsläget-kortet tas med i morgon-, lunch- och eftermiddagsupplagan). Kör sedan `python3 build.py`, committa och pusha, vänta tills första bild-URL:en i `urls.txt` svarar (GitHub Pages behöver ca 1–2 min).
- Publicerar som karusell med Buffer `create_post`: organisation `6b06d7904246b557f5b02897`, kanal `6b06d7e58541f09ecb9c6fc9`, `schedulingType: automatic`, `mode: shareNow`, `metadata.instagram: {type: post, shouldShareToFeed: true}`, bilderna från `urls.txt` i ordning (alt-text = kortets rubrik), bildtext från `caption.txt`.
- Om Buffer inte svarar eller publiceringen misslyckas: försök en gång till, annars hoppa över och notera i körningsrapporten. Sajten påverkas aldrig av Instagram-fel.
- Bilderna måste vara JPEG (Instagram accepterar inte PNG via Buffer) – skriptet skapar .jpg.
- Inga foton, inga personer taggas, inga påhittade citat.

## Diagram och bilder

Sajten är medvetet minimalistisk: **inga foton**. Ekonomiartiklar får gärna ett diagram när en kurs- eller sifferutveckling är kärnan i nyheten (t.ex. index, bitcoin, valuta, inflation). Lägg till i frontmatter:

```
chart:
  title: "OMXS30, senaste 30 dagarna"
  values: [2420.5, 2431.2, ...]       # verkliga datapunkter, äldst först
  labels: ["27 okt", "28 okt", ...]   # samma antal som values
  unit: ""                           # valfritt, t.ex. "kr" eller "%"
  source: "Nasdaq Stockholm"
```

Endast verkliga data från en angiven källa. Saknas tillförlitlig dataserie – hoppa över diagrammet. Controllern kontrollerar sista värdet mot källan.

## Källor

Föredra: TT, SVT, SR Ekot, DN, SvD, Aftonbladet, Expressen, GP, Sydsvenskan, Dagens industri, Reuters, AP, Bloomberg, Financial Times, BBC, Riksbanken, SCB, myndigheter, UEFA, klubbarnas och ligornas officiella sidor, CoinDesk.
Undvik: forum, anonyma konton, innehållsfarmer, rena ryktessajter. Transferrykten bara från etablerade källor och tydligt märkta som rykten.

## Regler – alltid

- **Egna ord.** Aldrig kopiera meningar eller stycken. Aldrig återge en artikels struktur punkt för punkt.
- **Alltid källor** i frontmatter (`sources`), minst en, helst två.
- **Inga påhittade uppgifter.** Osäkert = utelämna. Aldrig citat som inte finns i källan.
- **Brott och olyckor:** inga namn på misstänkta eller offer som inte är offentliga personer; inga spekulationer.
- **Politik:** neutralt, alla sidor lika, inga egna värderingar.
- **Ekonomi:** inga investeringsråd, inga köp/sälj-rekommendationer.
- **Bilder:** använd inga bilder från andra sajter.
- **Rättelser:** fel som upptäcks rättas i filen, med en rad `*Rättat ÅÅÅÅ-MM-DD: …*` sist i texten.

## Filformat

Fil: `content/posts/ÅÅÅÅ-MM-DD-sektion-kort-slug.md`

```
---
title: "Rubrik"
summary: "Ingress, 1–2 meningar."
section: sverige   # sverige | fotboll | ekonomi
date: 2026-11-26T07:00:00
# chart: (valfritt, se "Diagram och bilder")
featured: false
sources:
  - name: "SVT Nyheter"
    url: "https://..."
---
Brödtext i Markdown.
```

`content/markets.json`:

```
{"as_of": "26 nov 07:00", "source": "Källnamn",
 "groups": [{"title": "Index", "items": [{"name": "OMXS30", "value": "2 512,40", "change_pct": 0.84}]}]}
```

Grupper: Index (OMXS30, S&P 500, DAX, Nikkei), Krypto (Bitcoin, Ethereum), Valuta (EUR/SEK, USD/SEK), Räntor & råvaror (styrränta, guld, Brent). Använd svensk talformatering. `change_pct` = förändring senaste handelsdag, eller `null` om okänd.
