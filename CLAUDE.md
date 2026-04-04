# CLAUDE.md — Signal Board

## What This Project Is

Signal Board is a daily editorial data dashboard that reads 300 news sources across borders, languages, political orientations, and institutional types, identifies cross-domain story connections, and publishes a daily analysis at signal-board.org. It exists as a structural counter to platform-mediated information systems.

The site is built by Elise Hasseltine, who is the sole creator, editorial director, and operator. Elise has no coding background. All technical execution happens through Claude. Elise makes editorial decisions, defines section purpose, and reviews output quality.

## What Signal Board Is Trying to Accomplish

Signal Board is not a news aggregator. It's a daily practice that builds structural literacy over time. A reader who follows it for a month should start seeing that the tariff story connects to the labor story connects to the AI governance story connects to what's happening in their community — not because they were told it does, but because the structure of the output trained them to look for those connections on their own.

Five things the output must accomplish:

1. **Build the framework that doesn't exist yet.** Connect dots across domains that no single outlet connects. Train readers to see structural patterns, not just events.

2. **Make the information environment visible.** Show people how events are reported, not just what happened. A reader should finish the Gap section understanding how their reality is shaped by which outlet they read.

3. **Treat cooperation as signal, not consolation.** Meanwhile is not a feel-good section. It's the measured share of civic infrastructure that persists whether national media covers it or not. The percentage metric does real work.

4. **Be usable by someone who won't read the underlying sources.** Every section should end with something concrete — check this, watch for this, this is what it means for your specific situation. Synthesis that doesn't land in someone's actual life is just sophisticated expert knowledge that isn't reaching anyone.

5. **Demonstrate the practice it's arguing for.** The output should feel like you can see someone thinking clearly across a huge volume of information — not performing authority, not simplifying for effect, but doing the actual work of synthesis in a way that invites the reader into the process.

## The Three Sections

### The Daily Thread
**Answers:** What structural force connected the most coverage today, and what does reading across sources reveal that reading any one of them wouldn't?

**Selection logic:** Identify which structural force had the highest cross-tier article count. Tier diversity matters more than raw volume — a force appearing across national, international, regional, and partisan sources is more interesting than one with 30 articles all from national outlets.

**Output:** Editorial synthesis naming specific outlets, what each emphasized, what each made invisible. Framing rows with 15-30 word descriptions per outlet. Pattern summary. Concrete personal stakes. Forward-looking callout scoped to THIS section's topic.

### The Daily Gap
**Answers:** Where did outlets covering the same event construct incompatible versions of reality for their audiences?

**Selection logic (CURRENT — NEEDS FIX):** Currently clusters by shared structural force label, which groups different stories that share a thematic tag. This produces thematic surveys, not framing analysis.

**Selection logic (TARGET):** After force tagging, a second-pass clustering identifies shared events within force clusters (same actors, same timeframe, same triggering action). Framing variance across outlets covering that shared event is the selection metric. High framing variance on a shared event = the Gap story.

**Output:** Comparison of how multiple outlets framed the same event. Not "here are different events under the same theme." Multiple outlets per framing perspective, not one.

### Meanwhile — Who Showed Up Today
**Answers:** Where are people showing up for each other?

**Selection logic:** Filter for cooperation-tagged articles. Surface stories from sources and tiers that Thread and Gap didn't feature. The percentage of total coverage is a meaningful metric, not decoration.

**Output:** Specific cooperation stories with named sources. Category breakdown. Concrete personal stakes. No filler language about how "these stories matter."

## Technical Architecture

### Pipeline (runs daily at 7 UTC via GitHub Actions)

1. **`actions/ingest.py`** — Fetches articles from 300 RSS feeds (`data/feeds.csv`). Claude Haiku classifies each by domain, structural force, cooperation signal. Output: `data/articles.json`

2. **`actions/analyze.py`** — Clusters by structural force, computes tier distribution, identifies cooperation stories, detects framing divergence. Reads source metadata from `data/sources.json`. Output: `data/daily/{date}.json`

3. **`actions/synthesize.py`** — One Claude Sonnet call per day. Reads analysis JSON, produces editorial synthesis. Includes 3-day cross-day continuity. Output: merged into daily JSON.

4. **Astro build** — `generate_today.yml` workflow. Pre-build sync (`scripts/prebuild.sh`), Astro build, post-build validation (`scripts/validate.js`, 13 checks). Output to `docs/` for GitHub Pages.

### Key Files

```
data/feeds.csv              — 300 RSS feed URLs
data/sources.json           — Canonical source metadata (single source of truth)
data/daily/{date}.json      — Daily analysis output
data/daily/latest.json      — Most recent daily file
actions/ingest.py           — Fetch + classify
actions/analyze.py          — Cluster + analyze
actions/synthesize.py       — Editorial synthesis prompt + execution
src/pages/today/index.astro — Today page template
src/pages/archive/[date].astro — Archive page template
src/pages/archive/index.astro  — Archive index
src/pages/about/index.astro    — About page
src/layouts/BaseLayout.astro   — Site-wide layout
src/styles/global.css          — Global CSS
scripts/prebuild.sh            — Pre-build data sync (MUST run before every build)
scripts/validate.js            — Post-build validation
.github/workflows/ingest.yml          — Daily pipeline
.github/workflows/generate_today.yml  — Astro build + deploy
.github/workflows/substack_draft.yml  — DISABLED, do not re-enable
```

### Costs

- Haiku classification: ~$0.50/day
- Sonnet synthesis: ~$0.40-$1.00/day
- Total: ~$25-$45/month
- Every GitHub Actions workflow run costs real money. Never trigger workflows to test. Verify locally first.

## Working Rules

### Branching and Deployment

- **Never push directly to main.** All changes go to a `staging` branch first.
- **Verify locally before pushing.** Run `npm run build`, check the output visually.
- **Never trigger GitHub Actions workflows until the local build is visually confirmed.**
- **One task per session.** Do not combine unrelated changes.

### Git Access

- Clone to `/tmp/sb-clone` — do not use the mounted workspace `.git` (FUSE deadlocks).
- Configure credentials: `git config --global credential.helper store` with the `signal-board-deploy` token.
- Verify push works before starting: `git push --dry-run origin main`

### Environment Check (do this first every session)

Before ANY work, confirm:
1. `git status` works
2. `git push --dry-run` works
3. `npm run build` works
4. You can visually verify built HTML

If any fail, STOP and report. Do not attempt workarounds.

### Verification

- **Visual verification means looking at the rendered page**, not checking HTML source for strings.
- After deploying, scroll through the entire page top to bottom.
- Check: all sections visible, text readable, colors correct, no invisible text, no broken layout.
- Report what you see at each section, not "it looks good."

### Communication

- **Report findings before implementing fixes.**
- **If something is broken, say so directly.** Do not minimize or bury problems.
- **If you can't do something, say so before attempting.** Do not waste time on workarounds.
- **If you made a mistake, own it.** "My change broke X because Y."
- **Be specific.** "Added og:title to BaseLayout" is good. "Updated meta tags" is not.

## Source Description Rules

All source descriptions live in `data/sources.json`. This is the single source of truth.

- 15-25 words, factual, institutional context only
- Include: what the outlet is (type), who owns/funds it, what it covers, when founded if notable
- NEVER include political lean labels: no "conservative," "liberal," "center-left," "center-right," "left-leaning," "right-leaning," "generally regarded as"
- The About page states: "This is not a bias rating; it is context"

## Writing Style (Synthesis Prompt)

- Voice: Ideas build forward. Each sentence adds context, evidence, or implication. Always forward, never back-and-forth.
- Reading level: 8th grade. Short clear words, direct sentences, confidence to explain complex things simply.
- First person natural: "I," "we read," "Signal Board found"
- Every sentence must earn its place. Zero tolerance for filler.
- No short declarative reversals ("This is not X. It is Y.")
- No dramatic pivot sentences ("But here's the thing")
- No borrowed-confidence phrases ("Let that sink in")
- No filler language ("it's worth noting," "at the end of the day")
- No em dashes anywhere
- No periods in abbreviations (US, UK, UN — not U.S., U.K.)
- Framing descriptions: 15-30 words, start with outlet name + past-tense verb
- Foreign-language content must be translated or excluded, never displayed raw

## Design System

### Section Colors
- Thread: Red #D94032, card bg peach-gold #FFD07B at 25% opacity
- Gap: Teal #3BCEAC, card bg mint #42F0A5
- Meanwhile: Green #0EAD69, card bg bright blue #1789FC

### Core Colors
- Navy #1B2A4B (text, hero)
- Warm cream #FFF8E7 (primary background)
- Yellow/Gold #FFD23F (callout highlights)
- Amber gold #FDB833 (callout cards)

### Fonts
- Outfit (headlines, navigation)
- Lora (body text, editorial)
- Inter (data, metadata)
- Caveat (annotations, human-touch moments)
- Abril Fatface (hero masthead)

### Rules
- Color carries meaning, never decoration
- No neutral gray anywhere
- Five-layer navy-tinted box shadows on cards
- `prefers-reduced-motion` respected throughout

## Known Issues (as of April 2026)

- **Gap section clusters by structural force, not by shared event.** Produces thematic surveys instead of framing analysis. Needs restructure in `analyze.py` and `synthesize.py`.
- **`analyze.py` contains `left_sources`/`right_sources` variables and `SOURCE_CONTEXT` dictionary** with political lean language. Flagged for removal. Navigate by variable name, not line number.
- **Some source descriptions in `sources.json` contain political lean labels** or are missing entirely. Being fixed.
- **"What to watch for" callouts sometimes bleed between sections** — a Thread callout may reference the Gap topic. Prompt scoping issue in `synthesize.py`.
- **Archive pages use a simpler template** than the today page. Parity work needed but lower priority than pipeline fixes.
- **SEO meta tags are minimal.** Needs sitemap verification, dynamic titles/descriptions, Twitter Cards, JSON-LD. Separate task from pipeline work.
- **Substack draft workflow is disabled.** Do not re-enable.

## Author and Attribution

- All author links: https://www.elisehasseltine.com/ (no other URLs)
- No Twitter/X, no LinkedIn in schema or structured data
- Footer: "Signal Board · Created by Elise Hasseltine · Last updated: [date] · No tracking · No ads"
