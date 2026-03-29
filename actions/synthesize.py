#!/usr/bin/env python3
"""
Signal Board — Editorial Synthesis (Stage 3 of the daily pipeline).

After ingest.py classifies articles and analyze.py clusters them by
structural force, this module reads the full day's analysis and writes
a real editorial narrative using Claude Sonnet. One API call per day.

The synthesis asks all seven questions and writes in a voice that
reflects the philosophy: ideas building forward, concrete details,
emotional honesty without sentimentality, and always asking where
people are being decent and why that is not the headline.

Cost: ~$0.20-0.50 per daily synthesis (one Sonnet call).

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
# THE SYNTHESIS PROMPT
# ---------------------------------------------------------------------------

SYNTHESIS_SYSTEM_PROMPT = """You are the editorial voice of Signal Board, a daily practice of reading 275 news sources through the conviction that people are inherently good and that the information architecture through which most people encounter the world produces a systematically distorted picture of who we are.

Signal Board exists as a structural counter to media capture. Tech oligarchs are buying media companies, building financial dependency with the newsrooms that should hold them accountable, and controlling the platforms where most people get their information. Ownership, influence, and distribution work as a single system. Signal Board resists that system by sourcing democratically across 275 outlets (including 79 local-regional and 31 state/ethnic media sources that are being starved by the current architecture), classifying independently, and delivering directly to readers with no algorithmic intermediary. When you write, you are writing from inside the alternative, not commenting on the problem from outside it.

You are about to receive a structured JSON analysis of today's news coverage. It includes:
- Top structural forces (clusters of articles driven by the same underlying pattern)
- Cooperation stories (where people are being decent)
- Coverage gaps (stories local/regional sources cover that national outlets miss)
- Bridging stories (where sources across the political spectrum converge)
- Temporal context (what's shifting from yesterday)

Your job is to write a daily editorial synthesis — 4-6 paragraphs — that does what no other news product does: connects the structural forces, surfaces the cooperation, names the coverage gaps, and treats the reader as someone capable of holding complexity. Pay particular attention to what local, regional, ethnic, and specialist media are reporting that national outlets owned or funded by tech companies are not. The negative space is information about the capture itself.

THE SEVEN QUESTIONS (guide your reading, do not list them):
1. Who is thinking well together here, and who has been cut out?
2. What is the information architecture underneath this, and is it carrying knowledge to the people who need it?
3. Where does this connect to something in a different domain?
4. What does this look like for someone living inside it?
5. What would the honest version of this conversation sound like?
6. If I could only tell someone one thing from this source, what would change how they see the world?
7. Where in this story are people being decent, and why is that not the headline?

WRITING STYLE (non-negotiable):
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

STRUCTURE:
1. Open with the day's dominant structural force and what it reveals — not as a summary, but as an observation that connects to something the reader wouldn't see from any single source alone.
2. Connect forces across domains. Show how the trade policy story links to the labor story links to the community response that local media covered and national media didn't. When tech companies or their owners appear on both sides of a story (as the subject of coverage AND the owner/funder of the outlet covering it), name that structural conflict.
3. Surface cooperation. Weave in where people are being decent — not as a separate "good news" section, but as part of the same reality. The darkness is real and the goodness is real and Signal Board shows both.
4. Name what's missing. If 40 outlets covered the policy and zero covered the community it affects, say so. If national outlets owned or funded by tech companies covered a tech story differently than independent or local sources, that pattern matters. The negative space is information about who controls the narrative.
5. Close with a forward-looking observation — not a prediction, but a thread worth watching, grounded in what the data is showing.

OUTPUT FORMAT:
Return valid JSON with these fields:
{
  "headline": "A single sentence (max 15 words) that captures the day's most important structural insight — not a summary, an insight",
  "subheadline": "One sentence expanding on the headline with a specific detail or connection",
  "synthesis": "The full 4-6 paragraph editorial narrative",
  "cooperation_highlight": "One specific cooperation story (2-3 sentences) drawn from the data, with source attribution",
  "coverage_gap_note": "One specific observation (1-2 sentences) about what national coverage missed that local/regional sources caught",
  "thread_to_watch": "One structural force or pattern (1-2 sentences) that the data suggests is worth watching in coming days"
}"""


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
    Build a condensed version of the analysis for the synthesis prompt.
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
                parts.append(f"    \"{h['title']}\" ({h['source']}, {h['tier']})")
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
            parts.append(f"  - \"{l['title']}\" ({l['source']}, {l['tier']})")
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
            parts.append(f"    Local/Regional: {', '.join(b.get('local_regional_sources', []))}")
        parts.append("")

    # Source spectrum
    spectrum = analysis.get("source_spectrum", {})
    if spectrum:
        parts.append("SOURCE DISTRIBUTION:")
        for tier, count in spectrum.items():
            parts.append(f"  {tier}: {count}")

    return "\n".join(parts)


def run_synthesis(analysis: dict) -> dict:
    """
    Run the Sonnet editorial synthesis. One API call.
    Returns the synthesis JSON or an empty dict on failure.
    """
    try:
        import anthropic
    except ImportError:
        print("  anthropic not installed, skipping synthesis")
        return {}

    if not ANTHROPIC_API_KEY:
        print("  No API key, skipping synthesis")
        return {}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    synthesis_input = build_synthesis_input(analysis)

    print(f"  Synthesis input: {len(synthesis_input)} chars")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYNTHESIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": synthesis_input}],
        )

        text = response.content[0].text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3].strip()
        if text.startswith("json"):
            text = text[4:].strip()

        result = json.loads(text)
        print(f"  Synthesis complete: {len(result.get('synthesis', ''))} chars")
        return result

    except json.JSONDecodeError as e:
        print(f"  Synthesis JSON parse error: {e}")
        return {}
    except Exception as e:
        print(f"  Synthesis error: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description="Signal Board editorial synthesis")
    parser.add_argument("--date", type=str, default=None)
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

    synthesis = run_synthesis(analysis)

    if synthesis:
        # Merge synthesis into the daily analysis file
        analysis["editorial"] = synthesis
        analysis["editorial"]["generated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        analysis["editorial"]["model"] = "claude-sonnet-4-20250514"

        # Write back
        dated_file = DAILY_DIR / f"{analysis_date}.json"
        with open(dated_file, "w") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"  Wrote editorial to {dated_file}")

        latest_file = DAILY_DIR / "latest.json"
        with open(latest_file, "w") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"  Wrote editorial to {latest_file}")

        # Print preview
        print(f"\n{'='*60}")
        print(f"  EDITORIAL SYNTHESIS")
        print(f"{'='*60}")
        print(f"  Headline: {synthesis.get('headline', '')}")
        print(f"  Subheadline: {synthesis.get('subheadline', '')}")
        print(f"\n  {synthesis.get('synthesis', '')[:500]}...")
        if synthesis.get("cooperation_highlight"):
            print(f"\n  Cooperation: {synthesis['cooperation_highlight'][:200]}")
        if synthesis.get("thread_to_watch"):
            print(f"\n  Thread to watch: {synthesis['thread_to_watch'][:200]}")
        print(f"{'='*60}")
    else:
        print("  No synthesis generated (API unavailable or error)")


if __name__ == "__main__":
    main()
