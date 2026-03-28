#!/usr/bin/env python3
"""
Re-classify today's articles using the new batched AI system.
Reads articles.json, re-classifies today's articles with AI,
and writes the updated file back.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

# Add actions dir to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_classify import classify_batch
from domains import get_domain_labels

ROOT = Path(__file__).resolve().parent.parent
ARTICLES_FILE = ROOT / "data" / "articles.json"

def main():
    # Load .env if present
    env_file = ROOT / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

    # Reload the API key after env
    import ai_classify
    ai_classify.ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

    print("Loading articles...")
    with open(ARTICLES_FILE, "r") as f:
        data = json.load(f)

    all_articles = data.get("articles", [])
    print(f"Total articles: {len(all_articles)}")

    # Find today's date (most common date in recent articles)
    date_counts = Counter(a["date"] for a in all_articles[:2000])
    today = date_counts.most_common(1)[0][0]
    print(f"Today's date: {today}")

    today_articles = [a for a in all_articles if a["date"] == today]
    print(f"Articles to classify: {len(today_articles)}")

    # Run batched AI classification
    print("\nStarting batched AI classification...")
    classify_batch(today_articles, batch_size=12)

    # Update articles back into the full list
    today_ids = {a["id"] for a in today_articles}
    today_map = {a["id"]: a for a in today_articles}
    updated = []
    for a in all_articles:
        if a["id"] in today_map:
            updated.append(today_map[a["id"]])
        else:
            updated.append(a)

    # Stats
    domain_labels = get_domain_labels()
    ai_classified = sum(1 for a in today_articles if a.get("connection") or a.get("force_tag"))
    tagged = sum(1 for a in today_articles if a.get("domains"))
    cross_domain = sum(1 for a in today_articles if a.get("cross_domain"))
    untagged = sum(1 for a in today_articles if not a.get("domains"))

    # Force tag distribution
    force_tags = Counter(a.get("force_tag", "") for a in today_articles if a.get("force_tag"))

    print(f"\n{'='*50}")
    print(f"CLASSIFICATION RESULTS")
    print(f"{'='*50}")
    print(f"Total articles:     {len(today_articles)}")
    print(f"AI classified:      {ai_classified} ({round(ai_classified/max(len(today_articles),1)*100)}%)")
    print(f"Tagged (any):       {tagged} ({round(tagged/max(len(today_articles),1)*100)}%)")
    print(f"Cross-domain:       {cross_domain} ({round(cross_domain/max(len(today_articles),1)*100)}%)")
    print(f"Untagged/filtered:  {untagged} ({round(untagged/max(len(today_articles),1)*100)}%)")

    print(f"\nDomain distribution:")
    dom_counts = Counter()
    for a in today_articles:
        for d in a.get("domains", []):
            dom_counts[d] += 1
    for d, count in dom_counts.most_common():
        label = domain_labels.get(d, d)
        print(f"  {label:15s}  {count:4d}")

    print(f"\nTop structural forces detected:")
    for tag, count in force_tags.most_common(20):
        if tag:
            print(f"  {tag:40s}  {count:3d} articles")

    # Sample some connection insights
    connections = [a for a in today_articles if a.get("connection")]
    print(f"\nSample cross-domain connections ({len(connections)} total):")
    for a in connections[:10]:
        print(f"  [{', '.join(a['domains'][:3])}] {a['title'][:60]}")
        print(f"    -> {a['connection']}")
        if a.get('force_tag'):
            print(f"    Force: {a['force_tag']}")

    # Write back
    data["articles"] = updated
    data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(ARTICLES_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nWrote updated articles to {ARTICLES_FILE}")

if __name__ == "__main__":
    main()
