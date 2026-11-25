# The Nordic Brief

Daglig nyhetssajt: Sverige, europeisk fotboll och global ekonomi. https://thenordicbrief.com

- `content/posts/` – artiklar (Markdown med frontmatter)
- `content/markets.json` – Marknadsläget
- `content/_demo/` – exempelinnehåll, används bara med `--demo`
- `build.py` – bygger sajten till `docs/` (serveras av GitHub Pages)
- `EDITORIAL.md` – redaktionell instruktion för agentlaget
- `logs/` – publiceringslogg

Bygga: `pip install markdown pyyaml && python3 build.py`
