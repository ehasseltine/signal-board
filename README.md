# Signal Board

Signal Board is a daily AI-powered news analysis engine that reads and synthesizes articles from 300+ news sources, powered by Claude. Built by Elise Hasseltine, Signal Board identifies structural forces across the news landscape, connects disparate stories, and delivers a human-readable narrative on what's really happening.

Live site: https://signal-board.org/today/

## How It Works

Signal Board runs a four-stage data pipeline every day at 7 AM UTC:

### 1. Ingest (Stage 1: Fetch + Classify)
- `actions/ingest.py` fetches the latest articles from 300+ RSS feeds listed in `data/feeds.csv`
- Each article is tagged by domain, media type (news, opinion, analysis), and tier (national, regional, niche)
- Results stored in `data/articles.json`
- Runs in parallel using ThreadPoolExecutor

### 2. Analyze (Stage 2: Cluster + Spectrum + Cooperation)
- `actions/analyze.py` reads the raw articles and clusters them by **structural force** (not keyword overlap)
- Example: articles about tariffs, AI job loss, and immigration policy may all reflect the same structural force—"labor market transformation"
- For each cluster, the engine analyzes how different source tiers (national vs. niche) frame the issue
- Produces `data/daily/{date}.json` with structured force/perspective data
- Designed to surface cross-domain connections that most newsrooms miss

### 3. Synthesize (Stage 3: Editorial Narrative)
- `actions/synthesize.py` reads the full day's analysis and generates editorial narrative using Claude Sonnet
- Creates two outputs per day:
  - **Global editorial**: headline, subheadline, 4-6 paragraph synthesis of the entire day
  - **Per-story synthesis**: focused analysis for the top 3 stories (becomes Daily Thread, Daily Gap, and Meanwhile on the frontend)
- Typical cost: $0.17–0.50/day

### 4. Build (Stage 4: Generate Static Site)
- GitHub Actions runs `npm run build`, which:
  1. Executes `scripts/prebuild.sh` to sync daily JSON from `data/daily/` to `public/data/daily/`
  2. Builds the Astro static site with `astro build`
  3. Runs `scripts/validate.js` to verify the output contains expected HTML
- Output pushed to GitHub Pages at `docs/`
- Live site updates immediately after build completes

## Manual Builds and Testing

### Trigger the Pipeline Manually

In GitHub Actions, open the "Daily Pipeline" workflow and click **Run workflow** to kick off stages 1–3 (ingest, analyze, synthesize) on demand. This is useful for testing code changes or catching up after an outage.

The "Generate Today Page" workflow is triggered automatically after the Daily Pipeline succeeds, but can also be run manually for rebuilds.

### Local Development

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:3000)
npm run dev

# Build locally (requires data/daily/latest.json to exist)
npm run build

# Preview built site
npm preview
```

Before running `npm run build` locally, ensure the pipeline has generated data:
1. Run GitHub Actions manually to populate `data/daily/latest.json`, OR
2. Manually copy recent JSON files from a successful workflow run

### Data Sync Troubleshooting

The most common build failure is stale or missing data in `public/data/daily/`. The `scripts/prebuild.sh` script automates this sync, but if it fails:

```bash
# Manual sync (before npm run build)
mkdir -p public/data/daily
cp data/daily/latest.json public/data/daily/
cp data/daily/2*.json public/data/daily/ 2>/dev/null || true
npm run build
```

## Configuration

### API Key

The Anthropic API key is stored as a GitHub Actions secret: `ANTHROPIC_API_KEY`

Access it in workflows via:
```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

To rotate the key:
1. Generate a new key at https://console.anthropic.com/
2. Update the GitHub secret in repository settings
3. Commit and push to trigger the next scheduled run

### Add a New Source

Edit `data/feeds.csv` and append a row:

```csv
name,url,tier,region,media_type,description,why
Your Publication,https://example.com/rss,national,us,news,Description here,Why include it
```

Fields:
- **name**: Publication name (must be unique)
- **url**: RSS feed URL (must be valid and accessible)
- **tier**: `national`, `regional`, or `niche` (used for perspective weighting)
- **region**: `us`, `global`, or specific country code
- **media_type**: `news`, `opinion`, or `analysis`
- **description**: 1-2 sentence description of the publication
- **why**: Why Signal Board should track this source (e.g., "represents tech industry perspective")

The next pipeline run will automatically fetch from the new source.

### Customize the Analysis

Each Python action accepts command-line arguments for testing:

```bash
# Test ingest with specific date
cd actions
python ingest.py --dry-run  # fetch but don't write
python ingest.py --stats    # print domain stats

# Test analyze for a specific date
python analyze.py --date 2026-03-28

# Test synthesize for a specific date
python synthesize.py --date 2026-03-28
```

## File Structure

- **actions/** - Python pipeline stages (ingest, analyze, synthesize)
  - `ingest.py` - Fetch articles from RSS feeds
  - `analyze.py` - Cluster by structural force
  - `synthesize.py` - Generate editorial narrative
- **data/** - Raw and processed data
  - `feeds.csv` - Source registry (300+ feeds)
  - `articles.json` - Ingested articles (updated daily)
  - `daily/` - Per-date analysis output (JSON files)
    - `latest.json` - Pointer to today's date
    - `YYYY-MM-DD.json` - Full analysis for each day
- **src/** - Astro page templates and components
  - `pages/today/index.astro` - Main "today" page
  - `pages/archive/[date].astro` - Archive page for past dates
  - `pages/about/index.astro` - About page
  - `pages/index.astro` - Home / redirect
  - `lib/data.ts` - Data loading utilities
  - `lib/storySelection.ts` - Story picking logic
  - `layouts/BaseLayout.astro` - Shared layout
  - `styles/global.css` - Global CSS
- **public/** - Static assets and build-time data
  - `data/daily/` - Synced JSON files (must exist before Astro build)
- **docs/** - Built static site (GitHub Pages output)
- **scripts/** - Build and validation scripts
  - `prebuild.sh` - Sync data from `data/daily/` to `public/data/daily/`
  - `validate.js` - Post-build checks (HTML presence, data validity)
- **.github/workflows/** - GitHub Actions CI/CD
  - `ingest.yml` - Daily Pipeline (cron 7 AM UTC, or manual trigger)
  - `generate_today.yml` - Build & publish (triggered after ingest succeeds)

## Troubleshooting

### Build Fails: "No pipeline data found"

**Cause**: `data/daily/latest.json` does not exist or `public/data/daily/` was not synced before the build.

**Fix**:
1. Check that the Daily Pipeline succeeded (GitHub Actions > Workflows)
2. If it failed, check the error log and fix the issue (see below)
3. Run the Daily Pipeline manually
4. Then run Generate Today Page manually

### Synthesis Returns Invalid JSON

**Cause**: Claude API error or malformed prompt that causes the synthesize.py script to fail.

**Fix**:
1. Check `synthesize.py` error output in the Actions log
2. Verify ANTHROPIC_API_KEY is set and valid
3. Check API usage / rate limits at https://console.anthropic.com/
4. Reduce the number of sources in feeds.csv temporarily to reduce API load
5. Re-run the Daily Pipeline

### API Key Expired or Rate Limited

**Cause**: Your Anthropic API key has been revoked or you've hit the daily/monthly spending limit.

**Fix**:
1. Visit https://console.anthropic.com/ and verify the key is valid
2. Check your usage and billing
3. If expired, generate a new key and update the GitHub secret
4. If rate-limited, wait 24 hours or upgrade your plan
5. Re-run the Daily Pipeline

### Site Not Updated After Push

**Cause**: GitHub Pages cache or delayed deploy.

**Fix**:
1. Verify the `docs/today/index.html` file exists and has today's date
2. Hard-refresh your browser (Cmd+Shift+R or Ctrl+Shift+R)
3. Wait 1-2 minutes for GitHub Pages to deploy
4. Check `https://signal-board.org/today/` in an incognito window

## Rolling Back

To revert to the previous version:

```bash
git revert HEAD
git push origin main
```

This creates a new commit that undoes the last commit without rewriting history. The next Daily Pipeline run will use the reverted code.

If you need to revert to a specific historical commit:

```bash
git log --oneline | head -10  # Find the commit hash
git revert <commit-hash>
git push origin main
```

## Costs

- **Anthropic API** (ingest + analyze + synthesize): ~$0.17–1.50/day depending on article volume and model used
- **GitHub Actions**: Free tier (sufficient for daily runs)
- **GitHub Pages**: Free (built-in)

Total monthly cost: ~$5–45 for API, plus domain hosting.

## Daily Publishing Schedule

Signal Board publishes every day at 7 AM UTC:

```
0 7 * * * (cron expression in ingest.yml)
```

This runs the Daily Pipeline, which injects data into the build. The Generate Today Page workflow then builds and deploys immediately.

To change the schedule, edit `.github/workflows/ingest.yml` and modify the cron expression.

## Architecture Notes

**Why Astro?**
- Static site generation (fast, cacheable)
- Client-side data loading for interactivity
- Zero JavaScript overhead

**Why separate ingest/analyze/synthesize?**
- Each stage is testable independently
- Failures in one stage don't block the others
- Easy to re-run just the synthesis if copy needs tweaking

**Why store data in data/ AND docs/?**
- `data/` is the source of truth (controlled by Python pipeline)
- `docs/` is a fallback for GitHub Pages (in case the pipeline runs but build fails)
- `public/` is synced from `data/` before every Astro build

**Why cluster by structural force?**
- Most news analysis clusters by keywords or topics, which misses cross-domain patterns
- Structural forces (labor market transformation, energy transition, regulatory capture) connect disparate stories
- This is what readers actually want to understand

## Contributing

1. Edit Python actions in `actions/` for pipeline changes
2. Edit Astro pages in `src/pages/` for UI changes
3. Test locally with `npm run dev`
4. Commit and push
5. GitHub Actions will automatically validate the build
6. Live site updates after successful build

For template/layout changes, test thoroughly in dev before pushing—the build validators catch many common issues, but not all.

## License

Signal Board is built by Elise Hasseltine.
