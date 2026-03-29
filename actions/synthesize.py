#!/usr/bin/env python3
"""
Signal Board — Editorial Synthesis (Stage 3 of the daily pipeline).

After ingest.py classifies articles and analyze.py clusters them by
structural force, this module reads the full day's analysis and writes
editorial narratives using Claude Sonnet.

Two synthesis passes:
  1. Global editorial — headline, subheadline, 4-6 paragraph synthesis
  2. Per-story synthesis — focused analysis for the top 3 stories that
     become Daily Thread, Daily Gap, and Meanwhile on the front end

Cost: ~$0.40-1.00 per day (two Sonnet calls).

Usage:
    python actions/synthesize.py                    # synthesize today
    python actions/synthesize.py --date 2026-03-28  # specific date
"""

import os
import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "data" / "daily"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# SHARED WRITING STYLE INSTRUCTIONS
# ---------------------------------------------------------------------------

WRITING_STYLE = """WRITING STYLE (non-negotiable):
- Ideas build forward in flowing prose. Each sentence adds to what came before.
- Longer sentences are welcome. Subordinate clauses create rhythm.
- NO short declarative reversals ("This is not X. It is Y.")
- NO dramatic pivot sentences ("But here's the thing." "And then everything changed.")
- NO staccato rhetorical cadence or ping-ponging between opposites
- NO em dashes (use commas, parentheses, or restructure instead)
- NO borrowed-confidence phrases ("Let that sink in." "Read that again.")
- Specificity over abstraction: name the source, the detail, the number
- Emotional honesty without sentimentality: name what matters plainly
- The through-line is synthesis, not contrast: pulling threads together
- Write as though you are sending a long, thoughtful letter to someone you respect
- Write at an 8th grade reading level. No jargon. No internal vocabulary. Plain English that respects the reader's intelligence without requiring specialized knowledge."""

# ---------------------------------------------------------------------------
# GLOBAL EDITORIAL SYNTHESIS PROMPT (Pass 1)
# ---------------------------------------------------------------------------

SYNTHESIS_SYSTEM_PROMPT = f"""You are the editorial voice of Signal Board, a daily practice of reading 275 news sources through the conviction that people are inherently good and that the information architecture through which most people encounter the world produces a systematically distorted picture of who we are.

Signal Board exists as a structural counter to media capture. Tech oligarchs are buying media companies, building financial dependency with the newsrooms that should hold them accountable, and controlling the platforms where most people get their information. Ownership, influence, and distribution work as a single system. Signal Board resists that system by sourcing democratically across 275 outlets (including 79 local-regional and 31 state/ethnic media sources that are being starved by the current architecture), classifying independently, and delivering directly to readers with no algorithmic intermediary. When you write, you are writing from inside the alternative, not commenting on the problem from outside it.

You are about to receive a structured JSON analysis of today's news coverage. It includes:
- Top structural forces (clusters of articles driven by the same underlying pattern)
- Cooperation stories (where people are being decent)
- Coverage gaps (stories local/regional sources cover that national outlets miss)
- Bridging stories (where sources across the political spectrum converge)
- Temporal context (what's shifting from yesterday)

Your job is to write a daily editorial synthesis, 4-6 paragraphs, that does what no other news product does: connects the structural forces, surfaces the cooperation, names the coverage gaps, and treats the reader as someone capable of holding complexity. Pay particular attention to what local, regional, ethnic, and specialist media are reporting that national outlets owned or funded by tech companies are not. The negative space is information about the capture itself.

THE SEVEN QUESTIONS (guide your reading, do not list them):
1. Who is thinking well together here, and who has been cut out?
2. What is the information architecture underneath this, and is it carrying knowledge to the people who need it?
3. Where does this connect to something in a different domain?
4. What does this look like for someone living inside it?
5. What would the honest version of this conversation sound like?
6. If I could only tell someone one thing from this source, what would change how they see the world?
7. Where in this story are people being decent, and why is that not the headline?

{WRITING_STYLE}

STRUCTURE:
1. Open with the day's dominant structural force and what it reveals, not as a summary, but as an observation that connects to something the reader wouldn't see from any single source alone.
2. Connect forces across domains. Show how the trade policy story links to the labor story links to the community response that local media covered and national media didn't. When tech companies or their owners appear on both sides of a story (as the subject of coverage AND the owner/funder of the outlet covering it), name that structural conflict.
3. Surface cooperation. Weave in where people are being decent, not as a separate "good news" section, but as part of the same reality. The darkness is real and the goodness is real and Signal Board shows both.
4. Name what's missing. If 40 outlets covered the policy and zero covered the community it affects, say so. If national outlets owned or funded by tech companies covered a tech story differently than independent or local sources, that pattern matters. The negative space is information about who controls the narrative.
5. Close with a forward-looking observation, not a prediction, but a thread worth watching, grounded in what the data is showing.

OUTPUT FORMAT:
Return valid JSON with these fields:
{{
  "headline": "A single sentence (max 15 words) that captures the day's most important structural insight, not a summary, an insight",
  "subheadline": "One sentence expanding on the headline with a specific detail or connection",
  "synthesis": "The full 4-6 paragraph editorial narrative",
  "cooperation_highlight": "One specific cooperation story (2-3 sentences) drawn from the data, with source attribution",
  "coverage_gap_note": "One specific observation (1-2 sentences) about what national coverage missed that local/regional sources caught",
  "thread_to_watch": "One structural force or pattern (1-2 sentences) that the data suggests is worth watching in coming days"
}}"""


# ---------------------------------------------------------------------------
# PER-STORY SYNTHESIS PROMPT (Pass 2)
# ---------------------------------------------------------------------------

STORY_SYNTHESIS_SYSTEM_PROMPT = f"""You are the editorial voice of Signal Board. You are about to receive data about three specific stories from today's news coverage, each one selected for a distinct editorial role:

1. THE DAILY THREAD — the story with the widest cross-tier coverage, showing how outlets from different worlds converge on the same structural force
2. THE DAILY GAP — the story where framing diverges most sharply between outlet types, revealing what the gap between those frames tells us
3. MEANWHILE — the cooperation and civic participation stories that local and specialist outlets cover while the national cycle ignores them

For each story, you will write focused editorial analysis that gives readers genuine insight, not a data summary but a narrative that helps them understand what this story means, how different outlets are shaping it, why it matters to their life, and what to watch for next.

{WRITING_STYLE}

FOR EACH STORY, PRODUCE:

**synthesis** (2-3 paragraphs, 200-400 words): A narrative analysis of this specific story. What does it reveal when you read it across multiple outlets? What structural pattern is at work? What would someone living inside this story's forces experience? Name specific outlets and what they reported. Connect details across sources to show something the reader could not see from any single article alone.

**cross_spectrum** (1 paragraph, 80-150 words): How different outlet types frame this story, and what the framing reveals. Do not just list which outlets covered it. Describe the difference in how national outlets frame it versus international outlets versus local/regional outlets, and explain what that gap means. If certain outlet types ignored the story entirely, name that absence.

**why_this_matters** (2-3 sentences): Ground this story in personal relevance. What does it mean for someone going about their day? Avoid abstraction. Be specific about whose life this touches and how.

**watch_for** (2-3 sentences): What should a reader pay attention to in the coming days? Not a prediction, but a thread worth tracking, grounded in what the data shows is building or shifting.

OUTPUT FORMAT:
Return valid JSON with this structure:
{{
  "stories": [
    {{
      "role": "thread",
      "structural_force": "the force tag of the story",
      "synthesis": "2-3 paragraph narrative analysis",
      "cross_spectrum": "How outlets framed it differently and what that reveals",
      "why_this_matters": "Personal relevance, specific and grounded",
      "watch_for": "What to track in coming days"
    }},
    {{
      "role": "gap",
      "structural_force": "...",
      "synthesis": "...",
      "cross_spectrum": "...",
      "why_this_matters": "...",
      "watch_for": "..."
    }},
    {{
      "role": "meanwhile",
      "structural_force": "cooperation",
      "synthesis": "...",
      "cross_spectrum": "...",
      "why_this_matters": "...",
      "watch_for": "..."
    }}
  ]
}}"""


def load_daily_analysis(analysis_date: str) -> dict:
    """Load the day's analysis JSON."""
    dated_file = DAILY_DIR / f"{analysis_date}.json"
    if dated_file.exists():
        with open(dated_file, "r") as f:
            return json.load(f)

    latest_file = DAILY_DIR / "latest.json"
    if latest_file.exists():
        with open(latest_file, "r") as f:
            data = json.load(f)
            if data.get("date") == analysis_date:
                return data

    return {}


def build_synthesis_input(analysis: dict) -> str:
    """
    Build a condensed version of the analysis for the global synthesis prompt.
    We don't send the entire JSON (too large, too much noise). We send
    the most important signals.
    """
    parts = []

    # Summary stats
    s = analysis.get("summary", {})
    parts.append(f"DATE: {analysis.get('date', 'unknown')}")
    parts.append(f"TOTAL ARTICLES: {s.get('total_stories', 0)} from {s.get('sources_reporting', 0)} sources")
    parts.append(f"CROSS-DOMAIN: {s.get('cross_domain', 0)} ({s.get('cross_domain_pct', 0)}%)")
    parts.append(f"TOP DOMAIN: {s.get('top_domain', 'unknown')}")
    parts.append("")

    # Temporal context
    tc = analysis.get("temporal_context", {})
    if tc.get("has_yesterday"):
        parts.append(f"VOLUME CHANGE: {tc.get('volume_change_pct', 0)}% vs yesterday")
        surges = tc.get("surges", [])
        if surges:
            parts.append("SURGING: " + ", ".join(
                f"{s['label']} (+{s['change_pct']}%)" for s in surges
            ))
        drops = tc.get("drops", [])
        if drops:
            parts.append("DROPPING: " + ", ".join(
                f"{d['label']} ({d['change_pct']}%)" for d in drops
            ))
        new_forces = tc.get("new_forces", [])
        if new_forces:
            parts.append("NEW FORCES TODAY:")
            for nf in new_forces[:5]:
                parts.append(f"  - {nf['force']} ({nf['count']} articles, domains: {', '.join(nf['domains'])})")
                if nf.get("insight"):
                    parts.append(f"    Insight: {nf['insight']}")
        parts.append("")

    # Top stories (structural forces)
    stories = analysis.get("top_stories", [])
    if stories:
        parts.append("TOP STRUCTURAL FORCES:")
        for i, st in enumerate(stories[:7], 1):
            parts.append(f"\n  {i}. FORCE: {st.get('structural_force', 'unknown')}")
            parts.append(f"     Headline: {st.get('headline', '')}")
            parts.append(f"     Sources: {st.get('source_count', 0)} | Articles: {st.get('article_count', 0)}")
            parts.append(f"     Domains: {', '.join(st.get('domains', []))}")
            parts.append(f"     Tiers: {', '.join(st.get('tiers', []))}")
            # Connections (the gold)
            for conn in st.get("connections", [])[:2]:
                parts.append(f"     Connection: {conn['text']} (via {conn['source']})")
            # Tier framing
            tf = st.get("tier_framing", {})
            for tier_name, info in tf.items():
                sample = info.get("sample", {})
                parts.append(f"     {tier_name}: \"{sample.get('title', '')}\" ({sample.get('source', '')})")
        parts.append("")

    # Cooperation stories
    coop = analysis.get("cooperation", {})
    if coop and coop.get("total_cooperation_stories", 0) > 0:
        parts.append(f"COOPERATION ({coop['total_cooperation_stories']} stories, {coop['cooperation_rate']}% of coverage):")
        for ct in coop.get("by_type", [])[:6]:
            sample = ct.get("sample", {})
            parts.append(f"  - {ct['type']} ({ct['count']} articles): \"{sample.get('title', '')}\" ({sample.get('source', '')})")
        highlights = coop.get("highlights", [])
        if highlights:
            parts.append("  HIGHLIGHTS (from local/regional/specialist sources):")
            for h in highlights[:4]:
                parts.append(f"    \"{h['title']}\" ({h['source']}, {h.get('tier', 'unknown')})")
                if h.get("connection"):
                    parts.append(f"    Connection: {h['connection']}")
        coverage_gap = coop.get("coverage_gap", [])
        if coverage_gap:
            parts.append("  COOPERATION GAPS (forces with no decency signals):")
            for gap in coverage_gap[:3]:
                parts.append(f"    {gap['force']} ({gap['article_count']} articles, zero cooperation)")
        parts.append("")

    # Local/regional exclusive stories
    local = analysis.get("local_regional_exclusive", [])
    if local:
        parts.append("STORIES NATIONAL MEDIA MISSED:")
        for l in local[:5]:
            parts.append(f"  - \"{l['title']}\" ({l['source']}, {l.get('tier', 'unknown')})")
            if l.get("connection"):
                parts.append(f"    Connection: {l['connection']}")
        parts.append("")

    # Bridging stories
    bridges = analysis.get("what_connects", [])
    if bridges:
        parts.append("BRIDGING STORIES (across political spectrum):")
        for b in bridges[:3]:
            parts.append(f"  - {b['headline']} (force: {b.get('structural_force', 'unknown')})")
            parts.append(f"    Left: {', '.join(b.get('left_sources', []))}")
            parts.append(f"    Right: {', '.join(b.get('right_sources', []))}")
            parts.append(f"    International: {', '.join(b.get('international_sources', []))}")
            parts.append(f"    Local/Regional: {', '.join(b.get('local_regional_sources', b.get('community_sources', [])))}")
        parts.append("")

    # Source spectrum
    spectrum = analysis.get("source_spectrum", {})
    if spectrum:
        parts.append("SOURCE DISTRIBUTION:")
        for tier, count in spectrum.items():
            parts.append(f"  {tier}: {count}")

    return "\n".join(parts)


def build_story_synthesis_input(analysis: dict) -> str:
    """
    Build focused input for the per-story synthesis prompt.
    Selects the top 3 stories for Thread, Gap, and Meanwhile,
    and provides deep context for each.
    """
    parts = []
    stories = analysis.get("top_stories", [])
    coop = analysis.get("cooperation", {})
    divergence = analysis.get("narrative_divergence", [])
    bridges = analysis.get("what_connects", [])
    local_exclusive = analysis.get("local_regional_exclusive", [])

    # ── THREAD: highest source_count × tier_count story ──
    if stories:
        scored = sorted(
            stories,
            key=lambda s: (s.get("tier_count", 1) * 100 + s.get("source_count", 0)),
            reverse=True
        )
        thread_story = scored[0]

        parts.append("=" * 60)
        parts.append("STORY 1: THE DAILY THREAD")
        parts.append(f"Role: The story with the widest cross-tier coverage")
        parts.append("=" * 60)
        parts.append(f"Force: {thread_story.get('structural_force', 'unknown')}")
        parts.append(f"Headline: {thread_story.get('headline', '')}")
        parts.append(f"Sources: {thread_story.get('source_count', 0)} across {thread_story.get('tier_count', 0)} tiers")
        parts.append(f"Articles: {thread_story.get('article_count', 0)}")
        parts.append(f"Domains: {', '.join(thread_story.get('domains', []))}")

        # All connections
        for conn in thread_story.get("connections", []):
            parts.append(f"Connection: {conn.get('text', '')} (via {conn.get('source', '')})")

        # All tier framing
        tf = thread_story.get("tier_framing", {})
        if tf:
            parts.append("\nHow different outlet types framed it:")
            for tier_name, info in tf.items():
                sample = info.get("sample", {})
                all_articles = info.get("articles", [])
                parts.append(f"  {tier_name}:")
                parts.append(f"    Lead: \"{sample.get('title', '')}\" ({sample.get('source', '')})")
                for art in all_articles[:3]:
                    parts.append(f"    Also: \"{art.get('title', '')}\" ({art.get('source', '')})")

        # All articles
        articles = thread_story.get("articles", [])
        if articles:
            parts.append(f"\nAll articles ({len(articles)}):")
            for art in articles:
                parts.append(f"  [{art.get('tier', '?')}] \"{art.get('title', '')}\" — {art.get('source', '')}")

        # Matching bridging story (cross-spectrum detail)
        thread_force = thread_story.get("structural_force", "")
        for b in bridges:
            if b.get("structural_force") == thread_force or thread_force in b.get("headline", ""):
                parts.append(f"\nCross-spectrum sources on this story:")
                parts.append(f"  Left: {', '.join(b.get('left_sources', []))}")
                parts.append(f"  Right: {', '.join(b.get('right_sources', []))}")
                parts.append(f"  International: {', '.join(b.get('international_sources', []))}")
                parts.append(f"  Local/Regional: {', '.join(b.get('local_regional_sources', b.get('community_sources', [])))}")
                break

        parts.append("")

    # ── GAP: narrative divergence or second story ──
    gap_story = None
    if divergence:
        # Find a divergence that is NOT the same as the thread
        thread_force = stories[0].get("structural_force", "") if stories else ""
        for nd in divergence:
            if nd.get("structural_force") != thread_force:
                gap_story = nd
                break
        if not gap_story:
            gap_story = divergence[0]

    if gap_story:
        parts.append("=" * 60)
        parts.append("STORY 2: THE DAILY GAP")
        parts.append(f"Role: Where framing diverges most sharply between outlet types")
        parts.append("=" * 60)
        parts.append(f"Force: {gap_story.get('structural_force', 'unknown')}")
        parts.append(f"Theme: {gap_story.get('theme', '')}")
        parts.append(f"Topic area: {gap_story.get('topic', '')}")
        parts.append(f"Sources: {gap_story.get('source_count', 0)}")

        articles = gap_story.get("articles", [])
        if articles:
            parts.append(f"\nArticles covering this story ({len(articles)}):")
            for art in articles:
                line = f"  [{art.get('tier', '?')}] \"{art.get('title', '')}\" — {art.get('source', '')}"
                if art.get("framing"):
                    line += f"\n    Framing: {art['framing']}"
                parts.append(line)
        parts.append("")

    elif len(stories) > 1:
        # Fallback: use second top story
        gap_story_data = scored[1] if len(scored) > 1 else stories[1]
        parts.append("=" * 60)
        parts.append("STORY 2: THE DAILY GAP")
        parts.append(f"Role: Where framing diverges most sharply between outlet types")
        parts.append("=" * 60)
        parts.append(f"Force: {gap_story_data.get('structural_force', 'unknown')}")
        parts.append(f"Headline: {gap_story_data.get('headline', '')}")
        parts.append(f"Sources: {gap_story_data.get('source_count', 0)}")
        parts.append(f"Articles: {gap_story_data.get('article_count', 0)}")
        for conn in gap_story_data.get("connections", [])[:3]:
            parts.append(f"Connection: {conn.get('text', '')}")
        tf = gap_story_data.get("tier_framing", {})
        for tier_name, info in tf.items():
            sample = info.get("sample", {})
            parts.append(f"  {tier_name}: \"{sample.get('title', '')}\" ({sample.get('source', '')})")
        parts.append("")

    # ── MEANWHILE: cooperation stories ──
    parts.append("=" * 60)
    parts.append("STORY 3: MEANWHILE")
    parts.append(f"Role: Who showed up today — cooperation, civic participation, people being decent")
    parts.append("=" * 60)

    if coop:
        parts.append(f"Total cooperation stories: {coop.get('total_cooperation_stories', 0)}")
        parts.append(f"Cooperation rate: {coop.get('cooperation_rate', 0)}% of all coverage")

        by_type = coop.get("by_type", [])
        if by_type:
            parts.append("\nCooperation by type:")
            for ct in by_type[:8]:
                sample = ct.get("sample", {})
                parts.append(f"  {ct['type']} ({ct['count']} articles)")
                if sample:
                    parts.append(f"    Example: \"{sample.get('title', '')}\" ({sample.get('source', '')})")
                for src in ct.get("sources", [])[:4]:
                    parts.append(f"    Source: {src}")

        highlights = coop.get("highlights", [])
        if highlights:
            parts.append(f"\nHighlight stories ({len(highlights)}):")
            for h in highlights[:6]:
                parts.append(f"  \"{h.get('title', '')}\" ({h.get('source', '')}, {h.get('tier', '')})")
                if h.get("connection"):
                    parts.append(f"    {h['connection']}")
                if h.get("cooperation_type"):
                    parts.append(f"    Type: {h['cooperation_type']}")
                if h.get("force_tag"):
                    parts.append(f"    Force: {h['force_tag']}")

        coverage_gap = coop.get("coverage_gap", [])
        if coverage_gap:
            parts.append("\nForces with ZERO cooperation signals:")
            for gap in coverage_gap[:4]:
                parts.append(f"  {gap['force']} ({gap['article_count']} articles)")
                if gap.get("note"):
                    parts.append(f"    {gap['note']}")

    # Local/regional exclusive context
    if local_exclusive:
        parts.append(f"\nStories only local/regional/specialist outlets covered:")
        for l in local_exclusive[:6]:
            parts.append(f"  \"{l.get('title', '')}\" ({l.get('source', '')}, {l.get('tier', '')})")
            if l.get("connection"):
                parts.append(f"    {l['connection']}")
            if l.get("context"):
                parts.append(f"    Context: {l['context']}")

    return "\n".join(parts)


def strip_json_fences(text: str) -> str:
    """Strip markdown code fences from JSON response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()
    if text.startswith("json"):
        text = text[4:].strip()
    return text


def run_synthesis(analysis: dict, client) -> dict:
    """
    Pass 1: Global editorial synthesis. One API call.
    Returns the editorial JSON or an empty dict on failure.
    """
    synthesis_input = build_synthesis_input(analysis)
    print(f"  [Pass 1] Global editorial — input: {len(synthesis_input)} chars")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYNTHESIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": synthesis_input}],
        )

        text = strip_json_fences(response.content[0].text)
        result = json.loads(text)
        print(f"  [Pass 1] Complete: {len(result.get('synthesis', ''))} chars")
        return result

    except json.JSONDecodeError as e:
        print(f"  [Pass 1] JSON parse error: {e}")
        return {}
    except Exception as e:
        print(f"  [Pass 1] Error: {e}")
        return {}


def run_story_synthesis(analysis: dict, client) -> list:
    """
    Pass 2: Per-story editorial synthesis. One API call.
    Returns a list of story synthesis dicts or an empty list on failure.
    """
    story_input = build_story_synthesis_input(analysis)
    print(f"  [Pass 2] Per-story synthesis — input: {len(story_input)} chars")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=6000,
            system=STORY_SYNTHESIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": story_input}],
        )

        text = strip_json_fences(response.content[0].text)
        result = json.loads(text)
        stories = result.get("stories", [])
        print(f"  [Pass 2] Complete: {len(stories)} stories synthesized")
        for s in stories:
            synth_len = len(s.get("synthesis", ""))
            print(f"    {s.get('role', '?')}: {synth_len} chars synthesis, "
                  f"{len(s.get('cross_spectrum', ''))} chars cross-spectrum")
        return stories

    except json.JSONDecodeError as e:
        print(f"  [Pass 2] JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"  [Pass 2] Error: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Signal Board editorial synthesis")
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--skip-global", action="store_true",
                       help="Skip global editorial (reuse existing)")
    parser.add_argument("--skip-stories", action="store_true",
                       help="Skip per-story synthesis")
    args = parser.parse_args()

    if args.date:
        analysis_date = args.date
    else:
        analysis_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"Running editorial synthesis for {analysis_date}")

    analysis = load_daily_analysis(analysis_date)
    if not analysis:
        print(f"ERROR: No analysis found for {analysis_date}")
        sys.exit(1)

    # Initialize API client
    try:
        import anthropic
    except ImportError:
        print("  anthropic not installed, skipping synthesis")
        sys.exit(1)

    if not ANTHROPIC_API_KEY:
        print("  No API key, skipping synthesis")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # ── Pass 1: Global editorial ──
    if not args.skip_global:
        synthesis = run_synthesis(analysis, client)
        if synthesis:
            analysis["editorial"] = synthesis
            analysis["editorial"]["generated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            analysis["editorial"]["model"] = "claude-sonnet-4-20250514"
    else:
        print("  [Pass 1] Skipped (--skip-global)")
        synthesis = analysis.get("editorial", {})

    # ── Pass 2: Per-story synthesis ──
    if not args.skip_stories:
        story_syntheses = run_story_synthesis(analysis, client)
        if story_syntheses:
            analysis["story_syntheses"] = story_syntheses
    else:
        print("  [Pass 2] Skipped (--skip-stories)")

    # ── Write results ──
    dated_file = DAILY_DIR / f"{analysis_date}.json"
    with open(dated_file, "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"  Wrote to {dated_file}")

    latest_file = DAILY_DIR / "latest.json"
    with open(latest_file, "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"  Wrote to {latest_file}")

    # ── Print preview ──
    editorial = analysis.get("editorial", {})
    if editorial:
        print(f"\n{'=' * 60}")
        print(f"  GLOBAL EDITORIAL")
        print(f"{'=' * 60}")
        print(f"  Headline: {editorial.get('headline', '')}")
        print(f"  Subheadline: {editorial.get('subheadline', '')}")
        print(f"\n  {editorial.get('synthesis', '')[:500]}...")

    story_syntheses = analysis.get("story_syntheses", [])
    if story_syntheses:
        print(f"\n{'=' * 60}")
        print(f"  PER-STORY SYNTHESES ({len(story_syntheses)} stories)")
        print(f"{'=' * 60}")
        for ss in story_syntheses:
            print(f"\n  [{ss.get('role', '?').upper()}] {ss.get('structural_force', '')}")
            print(f"  Synthesis: {ss.get('synthesis', '')[:300]}...")
            if ss.get("why_this_matters"):
                print(f"  Why it matters: {ss['why_this_matters'][:200]}")

    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
