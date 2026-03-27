# Signal Board

A project to track how interconnected global forces appear in the news, and to surface the connections between them that most coverage misses.

Built by Elise Hasseltine as research infrastructure for the Center for Tomorrow.

## Domains tracked

AI, Labor, Governance, Information, Economics, Climate

## How it works

1. Python script fetches RSS feeds from 35 sources daily
2. Articles auto-tagged by domain using keyword matching
3. Cross-domain articles highlighted as structural signals
4. GitHub Action runs ingest daily
5. Static dashboard on GitHub Pages

## Running locally

pip install feedparser && python actions/ingest.py

Then open docs/index.html in a browser.
