# Signal Board

## What this is

Signal Board is a daily news analysis system that reads 275 sources, classifies articles across 10 structural domains using AI, clusters them into stories by structural force, and publishes a daily synthesis showing how the forces reshaping the world are connected. It lives at elisehasseltine.com/signal-board.

This is Elise Hasseltine's personal project. She builds it because the current information architecture degrades people's ability to think well together, and she believes building the alternative is worth doing.

## The thesis

Tech oligarchs are capturing America's information ecosystem through three interlocking strategies: buying media companies outright, building financial dependency with the newsrooms that are supposed to hold them accountable, and controlling the platforms where most people get their information. Ownership, influence, and distribution work as a single system. Signal Board exists to counter that system.

Signal Board is the structural inverse of media capture:
- **Democratic sourcing** (275 outlets, 10 tiers, 79 local-regional + 31 state/ethnic media) means no single owner shapes the picture.
- **Independent AI classification** that asks "where are people being decent" means the analysis isn't beholden to the companies it covers.
- **Direct-to-reader delivery** with no algorithmic intermediary means the information architecture itself refuses to be captured.

## The philosophy

The conviction underneath everything: humans are inherently cooperative, not inherently selfish, and the information systems through which most people encounter the world produce a systematically distorted picture of who we are. Signal Board exists to correct that distortion.

Every day's analysis is guided by seven questions:
1. Who is thinking well together here, and who has been cut out?
2. What is the information architecture underneath this, and is it carrying knowledge to the people who need it?
3. Where does this connect to something I've read in a different domain?
4. What does this look like for someone living inside it?
5. What would the honest version of this conversation sound like?
6. If I could only tell someone one thing from this source, what would change how they see the world?
7. Where in this story are people being decent, and why is that not the headline?

## Architecture

### Current state (Astro SSG + GitHub Pages)
- **Framework:** Astro 5.0.0, static site generation
- **Hosting:** GitHub Pages served from `docs/` folder
- **Frontend:** Astro pages + components, TypeScript story selection logic, CSS custom properties
- **Data:** JSON files committed to git (`data/articles.json`, `data/daily/latest.json`)
- **Pipeline:** GitHub Actions cron (7 AM UTC daily) → `ingest.py` → `ai_classify.py` → `analyze.py` → `synthesize.py` → JSON → Astro build → `docs/`
- **AI classification:** Claude Haiku (`claude-haiku-4-5-20251001`), batched 10-15 articles per call, 4 concurrent threads
- **AI synthesis:** Claude Sonnet, two passes (global editorial + per-story narratives)

### Daily pipeline flow
```
7 AM UTC: ingest.yml triggers
  ├── ingest.py     → data/articles.json (RSS fetch + AI classify)
  ├── analyze.py    → data/daily/{date}.json (cluster + spectrum + cooperation)
  ├── synthesize.py → data/daily/{date}.json (editorial narrative, 2 passes)
  └── copies data to docs/data/daily/

After ingest.yml succeeds: generate_today.yml triggers
  ├── syncs data/daily/ → public/data/daily/
  ├── npx astro build → docs/
  └── commits and pushes built HTML
```

### Two workflows
- `.github/workflows/ingest.yml` — Daily pipeline (Python: ingest → analyze → synthesize)
- `.github/workflows/generate_today.yml` — Site build (Node: sync data → Astro build → commit)

## Design system (V2)

### Color palette
- Navy: #1B2A4B (primary dark, 30%)
- Cream: #F5EFDF (primary light, 60%)
- Red: #D94032 (Thread accent, 10%)
- Yellow: #FFD23F (watch-for cards, editorial wash)
- Teal: #3BCEAC (Gap accent)
- Green: #0EAD69 (Meanwhile accent)
- Teal wash: #E4F7F1 (Gap section background)
- Ink: var(--ink) for text on cream backgrounds

### Accessible text variants (WCAG AA on cream)
- --red-accessible: #A82A1E
- --green-accessible: #07743F
- --teal-accessible: #1A7A64
- --yellow-accessible: #8B7500

### Color distribution
60% cream, 30% navy, 10% accent colors. Each section has its own accent world:
- Thread (red): navy background with red accents
- Gap (teal): navy header strip → teal wash body
- Meanwhile (green): teal wash background with green accents

### Fonts
- **Abril Fatface:** Masthead title, CTA. Display weight, decorative.
- **Outfit:** Section headlines, stat labels, framing row labels. Weight 800.
- **Lora:** Body text, synthesis paragraphs, framing content. Serif, readable.
- **Caveat:** Handwritten annotations on stats. Informal, personal.
- **Inter:** UI elements, nav, source labels, small text. Clean sans-serif.

### Section structure
Each daily page has three content sections plus framing:
1. **The Daily Thread** — story with widest cross-tier coverage (red accent)
2. **The Daily Gap** — story where framing diverges most (teal accent)
3. **Meanwhile: Who Showed Up Today** — cooperation stories (green accent)

Sections are separated by angled SVG dividers with background color transitions.

## Source base

275 sources across 10 tiers: national (28), international (40), specialist (38), local-regional (79 + 31 state/ethnic media), analysis/think tank (18), podcast (12), explainer (9), newsletter (7), government (5), research (3), solutions journalism (5).

Sources are defined in `data/feeds.csv`. The pipeline reads this file on every run.

## Pipeline details

### ingest.py (Stage 1)
- Reads `data/feeds.csv`
- Fetches each RSS feed (max 25 articles per feed, 8 parallel workers)
- Calls `ai_classify.py` for batched Claude Haiku classification
- Deduplicates by URL hash
- Outputs `data/articles.json`
- Falls back to keyword tagging from `domains.py` if no API key

### ai_classify.py
- Batches 10-15 articles per API call, 4 concurrent threads
- Classifies by structural force, not keyword overlap
- Returns: domains (multi-select from 10), connection sentence, force_tag, cooperation (bool), cooperation_type
- The seventh question is embedded in the prompt: "Where in this story are people being decent?"
- Cost: ~$0.50/day for ~1,000 articles

### analyze.py (Stage 2)
- Filters to today's articles
- Clusters by force_tag (Jaccard similarity merging)
- Builds top_stories with tier_framing (how different outlet types frame the same story)
- Analyzes cooperation stories by type (civic participation, institutional reform, etc.)
- Detects coverage gaps between outlet types
- Builds what_connects and narrative_divergence structures
- Outputs `data/daily/{date}.json` and `data/daily/latest.json`

### synthesize.py (Stage 3)
- **Pass 1 (global editorial):** Single Claude Sonnet call reading full day's analysis. Returns: headline, accessible_headline, subheadline, synthesis (4-6 paragraphs), cooperation_highlight, coverage_gap_note, thread_to_watch.
- **Pass 2 (per-story synthesis):** Second Sonnet call with data for the three featured stories. Returns: synthesis, cross_spectrum, why_this_matters, watch_for for each of thread/gap/meanwhile roles.
- Both passes use WRITING_STYLE constant enforcing Elise's voice (no em dashes, no reversals, ideas build forward).
- Merges output into `data/daily/{date}.json` under `editorial` and `story_syntheses` keys.
- Cost: ~$0.40-1.00/day

### Story selection (frontend, storySelection.ts)
- **selectDailyThread():** Picks story with highest (tier_count × 100 + source_count). Merges Pass 2 synthesis if available.
- **selectDailyGap():** Picks from narrative_divergence (different story than Thread). Builds framing comparisons from tier_framing data. Merges Pass 2 synthesis.
- **selectMeanwhile():** Uses cooperation data. Hardened fallback: if Pass 2 is missing, constructs analytical content from cooperation highlights connection text and type breakdowns. Never falls back to raw headlines. Skips highlights without analysis.

## Writing style (non-negotiable)

All prose on the site follows Elise's writing style (see `.claude/skills/elise-writing-style/SKILL.md` for full guide). The key rules:
- No em dashes anywhere (commas, parentheses, or restructure instead)
- No short declarative reversals ("This is not X. It is Y.")
- No dramatic pivot sentences ("But here's the thing.")
- No staccato rhetorical cadence or ping-ponging between opposites
- No borrowed-confidence phrases ("Let that sink in.")
- Ideas build forward in flowing prose, each sentence adding to what came before
- Longer sentences with subordinate clauses are welcome
- Specificity over abstraction: name the source, the detail, the number
- Write at an 8th grade reading level with no jargon
- The through-line is synthesis, not contrast: pulling threads together
- Write as though sending a long, thoughtful letter to someone you respect

These rules apply to: synthesize.py prompts, storySelection.ts fallback templates, and any manually written content.

## Working conventions

- Push back on technical decisions. Elise is not a web developer. If the architecture is wrong, say so.
- Frame everything around curiosity, warmth, intellectual energy, honesty, and transparency.
- Never use "community" as a source tier label. It's "local-regional."
- When adding sources, validate RSS feeds before committing them.
- Never publish bio/about/personal copy without Elise's explicit sign-off. She wants minimal bio (name + website link only).

## Domains

ai, labor, governance, information, economics, climate, security, geopolitics, domestic_politics, legal

## Key files

### Pipeline (actions/)
- `actions/ingest.py` — Stage 1: RSS fetcher + AI classification orchestrator
- `actions/ai_classify.py` — Claude Haiku batched classifier (cooperation dimension)
- `actions/analyze.py` — Stage 2: daily structural analysis + cooperation analysis
- `actions/synthesize.py` — Stage 3: Claude Sonnet editorial narrative (2 passes)
- `actions/domains.py` — keyword fallback classification + tier/domain definitions
- `actions/fetch_bias.py` — AllSides bias rating fetcher (manual utility, not in pipeline)
- `actions/reclassify_today.py` — Re-classification utility (manual, not in pipeline)

### Data
- `data/feeds.csv` — all 275 source definitions (name, URL, tier, region, type, description, why)
- `data/articles.json` — full article corpus
- `data/daily/latest.json` — today's analysis (output of analyze + synthesize)
- `data/bias_ratings.json` — AllSides bias ratings (output of fetch_bias.py)

### Frontend (src/)
- `src/pages/today/index.astro` — main daily page template
- `src/pages/archive/[date].astro` — archive page template
- `src/pages/archive/index.astro` — archive listing
- `src/pages/about/index.astro` — about/methodology page
- `src/lib/storySelection.ts` — story selection logic (Thread, Gap, Meanwhile)
- `src/lib/data.ts` — data loader (reads public/data/daily/latest.json at build time)
- `src/styles/global.css` — complete design system (V2 palette, all components)
- `src/layouts/BaseLayout.astro` — shared HTML template, nav, meta

### Workflows
- `.github/workflows/ingest.yml` — daily pipeline automation (7 AM UTC)
- `.github/workflows/generate_today.yml` — Astro build after pipeline succeeds

## GitHub

- Repo: ehasseltine/signal-board
- Secrets: ANTHROPIC_API_KEY (for Claude Haiku + Sonnet)
- Pages: served from docs/ folder on main branch
- Bot commits daily data as "Signal Board Bot"
