# Signal Board

A project to track how interconnected global forces — AI, labor, governance, economics, climate, and information systems — appear in the news, and to surface the connections between them that most coverage misses.

Built by [Elise Hasseltine](https://www.elisehasseltine.com/).

## What it does

Signal Board pulls articles daily from RSS feeds across major policy, technology, and journalism outlets. Each article is tagged by domain — not to sort it into a box, but to make visible when a story lives in multiple domains at once. Those cross-domain articles are the ones that matter most, because they reveal structural patterns that single-beat coverage can't see.

## Domains tracked

- **AI** — artificial intelligence policy, deployment, research, and industry
- **Labor** — workforce, employment, automation, worker protections
- **Governance** — democratic institutions, regulation, public administration
- **Information** — media systems, journalism, platform dynamics, public knowledge
- **Economics** — markets, inequality, trade, fiscal policy, economic transformation
- **Climate** — environment, energy, sustainability, adaptation

## How it works

1. A Python script (`actions/ingest.py`) fetches RSS feeds listed in `feeds.csv`
2. Articles are auto-tagged by domain using keyword matching
3. Results are stored in `data/articles.json`
4. A GitHub Action runs the ingest daily
5. A static dashboard (`docs/index.html`) visualizes the data on GitHub Pages

## Running locally

```bash
pip install feedparser requests
python actions/ingest.py
```

Then open `docs/index.html` in a browser.

## Architecture

```
signal-board/
├── actions/
│   ├── ingest.py          # RSS fetch + parse + tag
│   └── domains.py         # Domain definitions and keywords
├── data/
│   ├── articles.json      # All ingested articles
│   └── feeds.csv          # RSS feed sources
├── docs/
│   └── index.html         # Dashboard (GitHub Pages)
└── .github/
    └── workflows/
        └── ingest.yml     # Daily automated ingest
```

## Philosophy

The thing humans do that matters most is think well together, and the current information architecture is degrading that capacity. This tool exists to make the structural patterns visible — not by telling anyone what to think, but by showing what's connected to what.
