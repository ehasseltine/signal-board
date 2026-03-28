#!/usr/bin/env python3
"""
Signal Board — Daily narrative analysis generator.

Runs after the daily RSS ingest and produces a JSON analysis file
that the frontend consumes for the "Today" tab.

The analysis identifies narrative divergence (domain pairs with diverse
sources covering the same intersection), collision threads (patterns of
domain pairs), emerging signals (anomalies), and source spectrum breakdowns.

Usage:
    python actions/analyze.py                    # analyze today
    python actions/analyze.py --date 2026-03-25  # analyze specific date
"""

import json
import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

from domains import get_domain_labels

# Pair explanations (mapping sorted domain+domain -> human-readable explanation)
PAIR_EXPLANATIONS = {
    'ai+climate': 'AI solutions and energy costs for AI training',
    'ai+economics': 'AI boom driving market movements and investment',
    'ai+governance': 'Governments regulating and attempting to shape AI development',
    'ai+information': 'AI changing media production and information ecosystems',
    'ai+labor': 'AI and automation reshaping work and employment',
    'ai+legal': 'Courts and regulation wrestling with AI liability and rights',
    'ai+security': 'AI as both military tool and national security concern',
    'climate+economics': 'Costs and investments in climate transition',
    'climate+domestic_politics': 'Climate as political dividing line',
    'climate+geopolitics': 'Climate diplomacy and environmental agreements',
    'climate+governance': 'Climate policy and environmental regulation',
    'climate+information': 'Climate science and media coverage of environmental change',
    'climate+labor': 'Green jobs and worker transition in climate action',
    'climate+legal': 'Environmental law and climate litigation',
    'climate+security': 'Climate as security and geopolitical issue',
    'domestic_politics+economics': 'Economic issues driving political divisions',
    'domestic_politics+geopolitics': 'Foreign policy in domestic political debate',
    'domestic_politics+governance': 'Political conflict over governance direction',
    'domestic_politics+information': 'Media coverage of political campaigns and conflict',
    'domestic_politics+legal': 'Courts and judges in political battles',
    'domestic_politics+security': 'Military and defense issues in political campaigns',
    'economics+geopolitics': 'Trade and economic competition between powers',
    'economics+governance': 'Economic policy, fiscal spending, and trade policy',
    'economics+information': 'Tech industry economics and media business models',
    'economics+labor': 'Employment and wage dynamics shaping economic outcomes',
    'economics+legal': 'Antitrust, merger review, and financial regulation',
    'economics+security': 'Military spending and defense as economic activity',
    'geopolitics+governance': 'International diplomacy and governance coordination',
    'geopolitics+information': 'International news coverage and soft power',
    'geopolitics+legal': 'International law, courts, and treaties',
    'geopolitics+security': 'Military tensions and power dynamics between nations',
    'governance+information': 'Media regulation and press freedom issues',
    'governance+labor': 'Government policy regulating workers and employment',
    'governance+legal': 'Government actions running into the courts',
    'governance+security': 'Military strategy and defense policy',
    'information+labor': 'Media coverage of labor movements and worker organizing',
    'information+legal': 'Free speech, media law, and section 230',
    'information+security': 'War coverage and narrative control',
    'labor+legal': 'Employment law, rights, and workplace litigation',
    'labor+security': 'Military staffing and defense workforce implications',
}

# Paths
ROOT = Path(__file__).resolve().parent.parent
ARTICLES_FILE = ROOT / "data" / "articles.json"
DAILY_DIR = ROOT / "data" / "daily"


def load_articles() -> list[dict]:
    """Load articles from articles.json."""
    if not ARTICLES_FILE.exists():
        print(f"ERROR: {ARTICLES_FILE} not found")
        return []

    with open(ARTICLES_FILE, "r") as f:
        data = json.load(f)
        return data.get("articles", [])


def load_daily_history(days: int = 7) -> dict:
    """Load recent daily analysis files to compute rolling averages."""
    history = {}

    if not DAILY_DIR.exists():
        return history

    for daily_file in sorted(DAILY_DIR.glob("*.json")):
        if daily_file.name in ("latest.json",):
            continue
        try:
            with open(daily_file, "r") as f:
                data = json.load(f)
                date_str = data.get("date")
                if date_str:
                    history[date_str] = data
        except (json.JSONDecodeError, IOError):
            pass

    return history


def filter_articles_by_date(articles: list[dict], date_str: str) -> list[dict]:
    """Filter articles to those published on a specific date."""
    return [a for a in articles if a.get("date") == date_str]


def get_domain_pairs(domains: list[str]) -> list[tuple]:
    """Get all unique pairs from a list of domains, sorted for consistency."""
    if len(domains) < 2:
        return []

    pairs = []
    for i, d1 in enumerate(domains):
        for d2 in domains[i+1:]:
            # Normalize pair order for consistent matching
            pair = tuple(sorted([d1, d2]))
            pairs.append(pair)
    return pairs


def normalize_pair(d1: str, d2: str) -> str:
    """Normalize a pair of domains to key format: 'dom1+dom2' (sorted)."""
    return "+".join(sorted([d1, d2]))


def analyze_narrative_divergence(articles: list[dict]) -> list[dict]:
    """
    Find domain pairs where 3+ different sources have articles.
    Returns list of divergence objects.
    """
    domain_labels = get_domain_labels()

    # Map (domain_pair) -> {source -> [articles]}
    pair_sources = defaultdict(lambda: defaultdict(list))

    for article in articles:
        domains = article.get("domains", [])
        pairs = get_domain_pairs(domains)

        for pair in pairs:
            source = article.get("source")
            pair_sources[pair][source].append(article)

    divergences = []

    for pair in sorted(pair_sources.keys()):
        sources = pair_sources[pair]
        source_count = len(sources)

        # Only report pairs with 3+ sources
        if source_count < 3:
            continue

        d1, d2 = pair
        pair_key = normalize_pair(d1, d2)
        label = f"{domain_labels.get(d1, d1)} + {domain_labels.get(d2, d2)}"
        theme = PAIR_EXPLANATIONS.get(pair_key, f"{d1} and {d2} intersection")

        # Collect sample articles (up to 5 per pair)
        sample_articles = []
        for source in list(sources.keys())[:5]:
            for article in sources[source][:1]:
                sample_articles.append({
                    "title": article.get("title", "")[:100],
                    "source": article.get("source"),
                    "url": article.get("url"),
                    "paywall": article.get("paywall", False),
                    "connection": f"Covers both {d1} and {d2}",
                })

        divergences.append({
            "topic": label,
            "theme": theme,
            "source_count": source_count,
            "articles": sample_articles,
        })

    # Sort by source count (most diverse first)
    divergences.sort(key=lambda x: x["source_count"], reverse=True)

    return divergences


def analyze_collision_threads(
    articles: list[dict],
    history: dict,
    analysis_date: str
) -> list[dict]:
    """
    For each domain pair, count total articles (all-time) and today's.
    Compare to rolling 7-day average to determine trend.
    """
    domain_labels = get_domain_labels()

    # Load all articles to compute all-time counts
    all_articles = load_articles()

    # Map (domain_pair) -> count (all time)
    pair_all_time = defaultdict(int)

    for article in all_articles:
        domains = article.get("domains", [])
        pairs = get_domain_pairs(domains)
        for pair in pairs:
            pair_all_time[pair] += 1

    # Count today's articles per pair
    pair_today = defaultdict(int)
    for article in articles:
        domains = article.get("domains", [])
        pairs = get_domain_pairs(domains)
        for pair in pairs:
            pair_today[pair] += 1

    # Compute rolling 7-day averages from history
    pair_rolling_avg = defaultdict(float)
    history_dates = sorted(history.keys())[-6:]  # Last 6 days (+ today = 7)

    if history_dates:
        for date_key in history_dates:
            daily_analysis = history.get(date_key, {})
            for thread in daily_analysis.get("collision_threads", []):
                pair_str = thread.get("pair")
                if pair_str and isinstance(pair_str, list):
                    normalized = tuple(sorted(pair_str))
                    pair_rolling_avg[normalized] += thread.get("today_count", 0)

        # Average over the days we have
        for pair in pair_rolling_avg:
            pair_rolling_avg[pair] /= len(history_dates)

    threads = []

    for pair in sorted(pair_all_time.keys()):
        d1, d2 = pair
        count_all = pair_all_time[pair]
        count_today = pair_today[pair]

        pair_key = normalize_pair(d1, d2)
        label = f"{domain_labels.get(d1, d1)} + {domain_labels.get(d2, d2)}"
        explanation = PAIR_EXPLANATIONS.get(pair_key, f"{d1} and {d2} intersection")

        # Determine trend
        avg = pair_rolling_avg.get(pair, 0)
        if avg == 0:
            trend = "new" if count_today > 0 else "stable"
        elif count_today > avg * 1.25:
            trend = "rising"
        elif count_today < avg * 0.75:
            trend = "falling"
        else:
            trend = "stable"

        # Collect sample articles for this pair
        sample_articles = []
        for article in articles:
            if len(sample_articles) >= 3:
                break
            if pair[0] in article.get("domains", []) and pair[1] in article.get("domains", []):
                sample_articles.append({
                    "title": article.get("title", "")[:80],
                    "source": article.get("source"),
                    "url": article.get("url"),
                })

        threads.append({
            "pair": list(pair),
            "label": label,
            "explanation": explanation,
            "count": count_all,
            "today_count": count_today,
            "trend": trend,
            "sample_articles": sample_articles,
        })

    # Sort by today's count (most active first)
    threads.sort(key=lambda x: x["today_count"], reverse=True)

    return threads


def analyze_emerging_signals(
    articles: list[dict],
    history: dict,
    collision_threads: list[dict]
) -> list[dict]:
    """
    Identify domain pairs where today's count is significantly above
    the rolling average, or domains with unusual activity.
    """
    signals = []

    for thread in collision_threads:
        pair = tuple(sorted(thread["pair"]))
        count_today = thread["today_count"]
        pair_key = normalize_pair(thread["pair"][0], thread["pair"][1])

        # Estimate all-time average (rough: total / days of data)
        history_dates = sorted(history.keys())
        if history_dates and count_today > 0:
            # If trend is "rising" and count is notable, flag as emerging
            if thread["trend"] == "rising" and count_today >= 5:
                label = thread["label"]
                percent_change = "significant"
                if thread.get("count", 1) > 0:
                    pct = ((count_today - (thread["count"] / (len(history_dates) + 1)))
                           / (thread["count"] / (len(history_dates) + 1)) * 100)
                    if pct > 0:
                        percent_change = f"+{int(pct)}%"

                signals.append({
                    "description": f"{label} collision intensity elevated ({count_today} articles today)",
                    "type": "trend",
                    "pair": thread["pair"],
                })

    # Add domain-level anomalies
    domain_counts = defaultdict(int)
    for article in articles:
        for domain in article.get("domains", []):
            domain_counts[domain] += 1

    domain_labels = get_domain_labels()
    for domain_key, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True):
        if count >= 20:  # Threshold for "high activity" domain
            signals.append({
                "description": f"High activity in {domain_labels.get(domain_key, domain_key)}: {count} articles",
                "type": "domain_spike",
            })

    return signals


def analyze_source_spectrum(articles: list[dict]) -> dict:
    """Count articles by source tier."""
    spectrum = {
        "national": sum(1 for a in articles if a.get("tier") == "national"),
        "international": sum(1 for a in articles if a.get("tier") == "international"),
        "specialist": sum(1 for a in articles if a.get("tier") in ("specialist", "domain")),
        "explainer": sum(1 for a in articles if a.get("tier") == "explainer"),
        "community": sum(1 for a in articles if a.get("tier") in ("community", "lived")),
        "analysis": sum(1 for a in articles if a.get("tier") == "analysis"),
    }
    return spectrum


def generate_daily_analysis(
    articles: list[dict],
    analysis_date: str,
    history: dict
) -> dict:
    """
    Generate a complete daily analysis JSON.

    Args:
        articles: Articles for the specific date
        analysis_date: Date string (YYYY-MM-DD)
        history: Dictionary of previous daily analyses

    Returns:
        Analysis dictionary ready for JSON serialization
    """
    domain_labels = get_domain_labels()
    unique_sources = set(a.get("source") for a in articles)

    # Analyze each component
    narrative_divergence = analyze_narrative_divergence(articles)
    collision_threads = analyze_collision_threads(articles, history, analysis_date)
    emerging_signals = analyze_emerging_signals(articles, history, collision_threads)
    source_spectrum = analyze_source_spectrum(articles)

    # Count cross-domain articles
    cross_domain_count = sum(1 for a in articles if a.get("cross_domain", False))

    # Determine top domain
    domain_counts = defaultdict(int)
    for article in articles:
        for domain in article.get("domains", []):
            domain_counts[domain] += 1

    top_domain = ""
    if domain_counts:
        top_domain_key = max(domain_counts.items(), key=lambda x: x[1])[0]
        top_domain = domain_labels.get(top_domain_key, top_domain_key)

    analysis = {
        "date": analysis_date,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_stories": len(articles),
            "sources_reporting": len(unique_sources),
            "cross_domain": cross_domain_count,
            "top_domain": top_domain,
        },
        "narrative_divergence": narrative_divergence[:10],  # Top 10
        "collision_threads": collision_threads[:15],  # Top 15
        "source_spectrum": source_spectrum,
        "emerging_signals": emerging_signals[:5],  # Top 5
    }

    return analysis


def print_summary(analysis: dict):
    """Print a human-readable summary of the analysis."""
    summary = analysis["summary"]
    print("\n========== DAILY NARRATIVE ANALYSIS ==========")
    print(f"Date:               {analysis['date']}")
    print(f"Generated:          {analysis['generated']}")
    print(f"Total stories:      {summary['total_stories']}")
    print(f"Sources reporting:  {summary['sources_reporting']}")
    print(f"Cross-domain:       {summary['cross_domain']}")
    print(f"Top domain:         {summary['top_domain']}")

    if analysis["narrative_divergence"]:
        print(f"\nTop divergences ({len(analysis['narrative_divergence'])} found):")
        for i, div in enumerate(analysis["narrative_divergence"][:3], 1):
            print(f"  {i}. {div['topic']} ({div['source_count']} sources)")

    if analysis["collision_threads"]:
        print(f"\nTop collision threads ({len(analysis['collision_threads'])} found):")
        for i, thread in enumerate(analysis["collision_threads"][:5], 1):
            trend_emoji = {
                "rising": "↑",
                "falling": "↓",
                "stable": "→",
                "new": "★",
            }.get(thread["trend"], "•")
            print(f"  {i}. {thread['label']} {trend_emoji} ({thread['today_count']} today)")

    if analysis["emerging_signals"]:
        print(f"\nEmerging signals ({len(analysis['emerging_signals'])} found):")
        for i, signal in enumerate(analysis["emerging_signals"][:3], 1):
            print(f"  {i}. {signal['description']}")

    print(f"\nSource spectrum:")
    for tier, count in analysis["source_spectrum"].items():
        if count > 0:
            print(f"  {tier:15s}: {count:3d}")

    print("===========================================\n")


def main():
    parser = argparse.ArgumentParser(description="Signal Board daily narrative analysis")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date to analyze (YYYY-MM-DD, default: today)"
    )
    args = parser.parse_args()

    # Determine analysis date
    if args.date:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
            analysis_date = args.date
        except ValueError:
            print(f"ERROR: Invalid date format '{args.date}'. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        analysis_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"Analyzing articles for {analysis_date}")

    # Load data
    all_articles = load_articles()
    if not all_articles:
        print("ERROR: No articles found. Run ingest first.")
        sys.exit(1)

    history = load_daily_history(days=7)

    # Filter to analysis date
    articles = filter_articles_by_date(all_articles, analysis_date)

    if not articles:
        print(f"WARNING: No articles found for {analysis_date}")
        # Create empty analysis
        analysis = {
            "date": analysis_date,
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": {
                "total_stories": 0,
                "sources_reporting": 0,
                "cross_domain": 0,
                "top_domain": "",
            },
            "narrative_divergence": [],
            "collision_threads": [],
            "source_spectrum": {
                "national": 0,
                "international": 0,
                "specialist": 0,
                "explainer": 0,
                "community": 0,
                "analysis": 0,
            },
            "emerging_signals": [],
        }
    else:
        # Generate analysis
        analysis = generate_daily_analysis(articles, analysis_date, history)

    # Create output directory
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    # Write dated file
    dated_file = DAILY_DIR / f"{analysis_date}.json"
    with open(dated_file, "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"Wrote {dated_file}")

    # Write latest.json
    latest_file = DAILY_DIR / "latest.json"
    with open(latest_file, "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"Wrote {latest_file}")

    # Print summary
    print_summary(analysis)


if __name__ == "__main__":
    main()
