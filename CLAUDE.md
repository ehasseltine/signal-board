# Signal Board

## What this is

Signal Board is a daily news analysis system that reads 275 sources, classifies articles across 10 structural domains using AI, clusters them into mega-stories by structural force, and publishes a daily synthesis showing how the forces reshaping the world are connected. It lives at elisehasseltine.com/signal-board.

This is Elise Hasseltine's personal project. It is not a portfolio piece, a pitch for any organization, or a proof of concept. She builds it because the current information architecture degrades people's ability to think well together, and she believes building the alternative is worth doing.

## The philosophy

The conviction underneath everything: humans are inherently cooperative, not inherently selfish, and the information systems through which most people encounter the world produce a systematically distorted picture of who we are. Signal Board exists to correct that distortion by reading broadly, connecting what fragmented coverage keeps separate, and surfacing evidence of the cooperative reality the architecture hides.

Every day's analysis is guided by seven questions:
1. Who is thinking well together here, and who has been cut out?
2. What is the information architecture underneath this, and is it carrying knowledge to the people who need it?
3. Where does this connect to something I've read in a different domain?
4. What does this look like for someone living inside it?
5. What would the honest version of this conversation sound like?
6. If I could only tell someone one thing from this source, what would change how they see the world?
7. Where in this story are people being decent, and why is that not the headline?

The seventh question is what makes Signal Board different from everything else. No existing product asks it.

## Architecture

### Current state (prototype)
- **Hosting:** GitHub Pages served from `docs/` folder
- **Frontend:** Static HTML files (11 pages), vanilla JS, no framework
- **Data:** JSON files committed to git (`data/articles.json`, `data/daily/latest.json`)
- **Pipeline:** GitHub Actions cron (7 AM UTC daily) → `ingest.py` → `ai_classify.py` → `analyze.py` → JSON → `docs/data/`
- **AI:** Claude Haiku (`claude-haiku-4-5-20251001`) for article domain classification, batched 10-15 articles per call, 4 concurrent threads
- **Visualization:** D3.js force-directed graph ("The Constellation")
- **Bias data:** AllSides (CC BY-NC 4.0), 215/275 sources matched

### Known architectural debt
The static HTML + JSON-in-git approach was right for getting live fast. It is now the primary bottleneck. Every new feature requires editing raw HTML across 11 files. There is no component reuse, no templating, no real data layer. Migration plan:
- **Next:** Astro (content-first, ships minimal JS, great for SEO), 4 pages: Today, Constellation, Sources, About
- **After:** SQLite/Turso for the article corpus (data compounding, historical queries, temporal intelligence)
- **Goal:** Data that builds on itself, learns from itself, gets more valuable every day it runs

## Source base

275 sources across 10 tiers: national (28), international (40), specialist (38), local-regional (79 + 31 new state/ethnic media), analysis/think tank (18), podcast (12), explainer (9), newsletter (7), government (5), research (3), solutions journalism (5).

Sources are defined in `data/feeds.csv`. The pipeline reads this file on every run.

Tier colors: national=#6652FF, international=#1976D2, specialist=#00C2A8, local-regional=#FF5400

## Design system

- Background: #0f0f14 (dark)
- Accent: #6652FF (purple, same as Center for Tomorrow branding)
- Fonts: Space Grotesk (headings), Inter (body)
- Layout: 1200px max-width, responsive

## Pipeline details

### ingest.py
- Reads `data/feeds.csv`
- Fetches each RSS feed (max 25 articles per feed)
- Calls `ai_classify.py` for batched Claude Haiku classification
- Deduplicates by URL hash
- Outputs `data/articles.json`
- Falls back to keyword tagging from `domains.py` if no API key

### ai_classify.py
- Batches 10-15 articles per API call
- 4 concurrent threads via ThreadPoolExecutor
- Classifies by structural force, not keyword overlap
- Returns: domains (multi-select from 10), connection sentence, force_tag, cooperation (bool), cooperation_type
- The seventh question is embedded in the prompt: "Where in this story are people being decent?"
- Cost: ~$0.50/day for ~1,000 articles

### analyze.py
- Filters to today's articles
- Clusters by force_tag (Jaccard similarity merging)
- Generates mega-story synthesis with source perspective breakdown
- NEW: `analyze_cooperation_stories()` surfaces where people are being decent, grouped by cooperation type and structural force, with coverage gap detection
- Outputs `data/daily/{date}.json` and `data/daily/latest.json`

### synthesize.py
- Stage 3 of the pipeline (runs after analyze.py)
- Single Claude Sonnet call that reads the full day's analysis
- Writes editorial narrative asking all seven questions in Elise's voice
- Returns: headline, subheadline, synthesis (4-6 paragraphs), cooperation_highlight, coverage_gap_note, thread_to_watch
- Merges output into `data/daily/{date}.json` under the `editorial` key
- Cost: ~$0.20-0.50/day

## Domains

ai, labor, governance, information, economics, climate, security, geopolitics, domestic_politics, legal

## Writing style (non-negotiable)

All prose on the site follows Elise's writing style. The key rules:
- No short declarative reversals ("This is not X. It is Y.")
- No dramatic pivot sentences
- No staccato rhetorical cadence
- No em dashes
- Ideas build forward in flowing prose
- Longer sentences are fine
- Direct, high-caliber writing — a thoughtful person thinking clearly
- Flag violations proactively before Elise has to catch them

## Working conventions

- Push back on technical decisions. Elise is not a web developer. If the architecture is wrong, say so.
- Frame everything around curiosity, warmth, intellectual energy, honesty, and transparency.
- Never use "community" as a source tier label. It's "local-regional" or describe what sources actually do.
- When adding sources, validate RSS feeds before committing them.
- This is a learning project built in public. The framework changes as the source base grows and the thinking evolves. That is the point.

## Key files

- `data/feeds.csv` — all 275 source definitions
- `data/articles.json` — full article corpus
- `data/daily/latest.json` — today's analysis
- `actions/ingest.py` — RSS fetcher + AI classification orchestrator
- `actions/ai_classify.py` — Claude Haiku batched classifier (with cooperation dimension)
- `actions/analyze.py` — daily structural analysis + cooperation analysis
- `actions/synthesize.py` — Claude Sonnet editorial narrative synthesis
- `actions/domains.py` — keyword fallback classification + tier definitions
- `docs/today/index.html` — main daily analysis page
- `docs/sources/index.html` — source directory
- `docs/about/index.html` — philosophy and methodology
- `.github/workflows/ingest.yml` — daily pipeline automation

## GitHub

- Repo: ehasseltine/signal-board
- Secrets: ANTHROPIC_API_KEY (for Claude Haiku classification)
- Pages: served from docs/ folder on main branch
- Bot commits daily data as "Signal Board Bot"
