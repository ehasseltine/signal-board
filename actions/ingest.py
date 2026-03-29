#!/usr/bin/env python3
"""
Signal Board — RSS ingest pipeline.

Fetches articles from RSS feeds, auto-tags them by domain,
and stores results in data/articles.json. Designed to run
daily via GitHub Actions or manually from the command line.

Usage:
    python actions/ingest.py              # full ingest
    python actions/ingest.py --dry-run    # fetch but don't write
    python actions/ingest.py --stats      # print domain stats from existing data
"""

import csv
import json
import hashlib
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import mktime

import ssl
import urllib.request

import socket
import feedparser

from domains import tag_article, get_domain_labels

# Set a global socket timeout so no single feed can hang the pipeline
socket.setdefaulttimeout(30)
from ai_classify import classify_batch, get_client

# Allow SSL connections even when certificates are outdated
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

# Sources known to have paywalls (partial or full)
PAYWALLED_SOURCES = {
    "New York Times", "Washington Post", "Wall Street Journal", "Bloomberg",
    "The Atlantic", "Politico", "Business Insider", "CNBC",
    "Foreign Policy", "Foreign Affairs", "The Economist",
    "South China Morning Post", "The Dispatch", "Platformer",
    "Wired", "Ars Technica", "The Information",
    "Financial Times", "Barron's", "The New Yorker",
}

# Paths
ROOT = Path(__file__).resolve().parent.parent
FEEDS_FILE = ROOT / "data" / "feeds.csv"
ARTICLES_FILE = ROOT / "data" / "articles.json"

# Limit how far back we look (avoids massive initial pulls)
MAX_ARTICLES_PER_FEED = 25

# User agent — some feeds block bot-style UAs, use browser-like
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def load_feeds() -> list[dict]:
    """Load feed definitions from CSV."""
    feeds = []
    with open(FEEDS_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            feeds.append({
                "name": row["name"].strip(),
                "url": row["url"].strip(),
                "tier": row["tier"].strip(),
                "region": row["region"].strip(),
                "media_type": row.get("media_type", "news").strip(),
                "description": row.get("description", "").strip(),
                "why": row.get("why", "").strip(),
            })
    return feeds


def load_existing_articles() -> dict:
    """Load existing articles from JSON. Returns dict keyed by article ID."""
    if ARTICLES_FILE.exists():
        with open(ARTICLES_FILE, "r") as f:
            data = json.load(f)
            return {a["id"]: a for a in data.get("articles", [])}
    return {}


def make_article_id(url: str) -> str:
    """Generate a stable ID from article URL."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def parse_date(entry) -> str:
    """Extract and normalize publication date from a feed entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, OverflowError):
            pass
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            dt = datetime.fromtimestamp(mktime(entry.updated_parsed), tz=timezone.utc)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, OverflowError):
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_summary(entry) -> str:
    """Extract best available summary from a feed entry."""
    if hasattr(entry, "summary") and entry.summary:
        # Strip HTML tags naively (good enough for keyword matching)
        import re
        text = re.sub(r"<[^>]+>", " ", entry.summary)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:500]  # cap length
    if hasattr(entry, "description") and entry.description:
        import re
        text = re.sub(r"<[^>]+>", " ", entry.description)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:500]
    return ""


def get_full_text(entry) -> str:
    """Extract the fullest available text from a feed entry (up to 3000 chars)."""
    import re

    text = ""

    # Try content:encoded first (often has full article)
    if hasattr(entry, "content") and entry.content:
        for content_obj in entry.content:
            if hasattr(content_obj, "value") and content_obj.value:
                candidate = re.sub(r"<[^>]+>", " ", content_obj.value)
                candidate = re.sub(r"\s+", " ", candidate).strip()
                if len(candidate) > len(text):
                    text = candidate

    # Try summary
    if not text or len(text) < 100:
        if hasattr(entry, "summary") and entry.summary:
            candidate = re.sub(r"<[^>]+>", " ", entry.summary)
            candidate = re.sub(r"\s+", " ", candidate).strip()
            if len(candidate) > len(text):
                text = candidate

    # Try description
    if not text or len(text) < 100:
        if hasattr(entry, "description") and entry.description:
            candidate = re.sub(r"<[^>]+>", " ", entry.description)
            candidate = re.sub(r"\s+", " ", candidate).strip()
            if len(candidate) > len(text):
                text = candidate

    return text[:3000]


def fetch_feed(feed: dict) -> list[dict]:
    """Fetch and parse a single RSS feed. Returns list of article dicts."""
    articles = []

    try:
        parsed = feedparser.parse(
            feed["url"],
            agent=USER_AGENT,
        )

        if parsed.bozo and not parsed.entries:
            print(f"  WARNING: {feed['name']} — feed error: {parsed.bozo_exception}")
            return []

        for entry in parsed.entries[:MAX_ARTICLES_PER_FEED]:
            url = getattr(entry, "link", None)
            title = getattr(entry, "title", None)

            if not url or not title:
                continue

            article_id = make_article_id(url)
            summary = get_summary(entry)
            full_text = get_full_text(entry)
            domains = tag_article(title, summary)
            pub_date = parse_date(entry)

            articles.append({
                "id": article_id,
                "title": title.strip(),
                "url": url.strip(),
                "summary": summary,
                "text": full_text,
                "source": feed["name"],
                "tier": feed["tier"],
                "region": feed["region"],
                "media_type": feed["media_type"],
                "domains": domains,
                "cross_domain": len(domains) > 1,
                "paywall": feed["name"] in PAYWALLED_SOURCES,
                "date": pub_date,
                "ingested": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })

        print(f"  OK: {feed['name']} — {len(articles)} articles")

    except Exception as e:
        print(f"  ERROR: {feed['name']} — {e}")

    return articles


def compute_stats(articles: list[dict]) -> dict:
    """Compute domain-level statistics from article list."""
    domain_labels = get_domain_labels()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    stats = {
        "total_articles": len(articles),
        "total_sources": len(set(a["source"] for a in articles)),
        "cross_domain_count": sum(1 for a in articles if a.get("cross_domain")),
        "today_count": sum(1 for a in articles if a["date"] == today),
        "domains": {},
        "by_tier": {
            "national": sum(1 for a in articles if a["tier"] == "national"),
            "international": sum(1 for a in articles if a["tier"] == "international"),
            "domain": sum(1 for a in articles if a["tier"] == "domain"),
            "explainer": sum(1 for a in articles if a["tier"] == "explainer"),
            "lived": sum(1 for a in articles if a["tier"] == "lived"),
            "analysis": sum(1 for a in articles if a["tier"] == "analysis"),
        },
    }

    for domain_key, label in domain_labels.items():
        domain_articles = [a for a in articles if domain_key in a.get("domains", [])]
        stats["domains"][domain_key] = {
            "label": label,
            "count": len(domain_articles),
            "today": sum(1 for a in domain_articles if a["date"] == today),
        }

    return stats


def print_stats(articles: list[dict]):
    """Print a readable summary of the current data."""
    stats = compute_stats(articles)
    domain_labels = get_domain_labels()

    print("\n========== SIGNAL BOARD STATS ==========")
    print(f"Total articles:    {stats['total_articles']}")
    print(f"Sources:           {stats['total_sources']}")
    print(f"Cross-domain:      {stats['cross_domain_count']}")
    print(f"Added today:       {stats['today_count']}")
    print(f"\nBy tier:")
    print(f"  National (US):   {stats['by_tier']['national']}")
    print(f"  International:   {stats['by_tier']['international']}")
    print(f"  Domain-specific: {stats['by_tier']['domain']}")
    print(f"  Explainer:       {stats['by_tier']['explainer']}")
    print(f"  Lived experience:{stats['by_tier']['lived']}")
    print(f"  Analysis:        {stats['by_tier']['analysis']}")
    print(f"\nBy domain:")
    for key in sorted(stats["domains"], key=lambda k: stats["domains"][k]["count"], reverse=True):
        d = stats["domains"][key]
        print(f"  {d['label']:15s}  {d['count']:4d} total  ({d['today']} today)")
    print("========================================\n")


def main():
    parser = argparse.ArgumentParser(description="Signal Board RSS ingest")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but don't write to disk")
    parser.add_argument("--stats", action="store_true", help="Print stats from existing data")
    args = parser.parse_args()

    # Stats-only mode
    if args.stats:
        existing = load_existing_articles()
        if not existing:
            print("No articles found. Run an ingest first.")
            sys.exit(1)
        print_stats(list(existing.values()))
        sys.exit(0)

    # Load feeds and existing articles
    feeds = load_feeds()
    existing = load_existing_articles()
    print(f"Loaded {len(feeds)} feeds, {len(existing)} existing articles\n")

    # Fetch all feeds
    new_articles = []

    for feed in feeds:
        articles = fetch_feed(feed)
        for article in articles:
            if article["id"] not in existing:
                new_articles.append(article)

    print(f"\nNew articles found: {len(new_articles)}")

    # AI classification for new articles (falls back to keywords if no API key)
    if new_articles:
        print("\nClassifying new articles...")
        classify_batch(new_articles)
        for article in new_articles:
            existing[article["id"]] = article

    new_count = len(new_articles)
    print(f"Articles added: {new_count}")

    # Sort by date (newest first)
    all_articles = sorted(existing.values(), key=lambda a: a["date"], reverse=True)

    # Compute stats
    stats = compute_stats(all_articles)

    # Write output
    if not args.dry_run:
        output = {
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "stats": stats,
            "articles": all_articles,
        }
        with open(ARTICLES_FILE, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"Wrote {len(all_articles)} articles to {ARTICLES_FILE}")
    else:
        print("(dry run — nothing written)")

    print_stats(all_articles)


if __name__ == "__main__":
    main()
