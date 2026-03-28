"""
Fetch AllSides media bias ratings and match against Signal Board sources.
Outputs data/bias_ratings.json for use by the frontend.

Data source: AllSides via favstats/AllSideR (CC BY-NC 4.0)
Attribution required: "Media bias ratings from AllSides.com"

Can be run standalone or as part of the daily pipeline.
"""

import csv
import json
import os
import urllib.request

ALLSIDES_CSV_URL = "https://raw.githubusercontent.com/favstats/AllSideR/master/data/allsides_data.csv"
FEEDS_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "feeds.csv")
OUTPUT_JSON = os.path.join(os.path.dirname(__file__), "..", "data", "bias_ratings.json")

# Manual overrides for sources AllSides rates under different names
# or sources we can confidently rate based on known editorial position
MANUAL_MATCHES = {
    "BBC World": "BBC News",
    "The Guardian World": "The Guardian",
    "NBC News": "NBC News",
    "American Prospect": "The American Prospect",
    "MIT Technology Review": "MIT Technology Review",
    "Wired": "Wired",
    "Ars Technica": "Ars Technica",
    "South China Morning Post": "South China Morning Post",
    "The Dispatch": "The Dispatch",
    "The Blaze": "TheBlaze",
    "Christianity Today": "Christianity Today",
    "Stars and Stripes": "Stars and Stripes",
    "The Free Press (Bari Weiss)": "The Free Press",
    "Texas Tribune": "Texas Tribune",
    "Pew Research Center": "Pew Research Center",
    "Slow Boring (Matt Yglesias)": "Slow Boring",
    "Popular Information (Judd Legum)": "Popular Information",
    "Lawfare": "Lawfare",
    "Military Times": "Military Times",
    "Inside Higher Ed": "Inside Higher Ed",
    "Science News": "Science News",
    "Foreign Policy": "Foreign Policy",
    "Haaretz": "Haaretz",
    "The Diplomat": "The Diplomat",
    "The Markup": "The Markup",
    "Education Week": "Education Week",
}


def fetch_allsides_csv():
    """Download AllSides CSV from GitHub."""
    print(f"Fetching AllSides data from {ALLSIDES_CSV_URL}")
    req = urllib.request.Request(ALLSIDES_CSV_URL, headers={"User-Agent": "SignalBoard/1.0"})
    with urllib.request.urlopen(req) as resp:
        text = resp.read().decode("utf-8")
    rows = list(csv.DictReader(text.splitlines()))
    print(f"  Loaded {len(rows)} AllSides ratings")
    return rows


def load_feeds():
    """Load Signal Board source names from feeds.csv."""
    sources = []
    with open(FEEDS_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sources.append({
                "name": row["name"].strip(),
                "tier": row.get("tier", "").strip(),
                "region": row.get("region", "").strip(),
            })
    return sources


def match_sources(sb_sources, allsides_rows):
    """Match Signal Board sources against AllSides ratings."""
    # Build AllSides lookup (lowercase name -> row)
    as_lookup = {}
    for row in allsides_rows:
        name = row["news_source"].strip()
        as_lookup[name.lower()] = row

    results = {}
    matched_count = 0

    for src in sb_sources:
        name = src["name"]
        key = name.lower()

        # Check manual override first
        if name in MANUAL_MATCHES:
            override_key = MANUAL_MATCHES[name].lower()
            if override_key in as_lookup:
                row = as_lookup[override_key]
                results[name] = build_entry(row)
                matched_count += 1
                continue

        # Exact match
        if key in as_lookup:
            results[name] = build_entry(as_lookup[key])
            matched_count += 1
            continue

        # Substring match (Signal Board name contains AllSides name or vice versa)
        for ak, av in as_lookup.items():
            if key in ak or ak in key:
                results[name] = build_entry(av)
                matched_count += 1
                break

    total = len(sb_sources)
    print(f"  Matched {matched_count}/{total} sources ({matched_count*100//total}%)")
    return results


def build_entry(row):
    """Build a clean bias entry from an AllSides CSV row."""
    return {
        "rating": row["rating"],
        "rating_num": int(row["rating_num"]) if row["rating_num"] else None,
        "confidence": row.get("confidence_level", "Unknown"),
        "allsides_name": row["news_source"].strip(),
        "allsides_url": row.get("url", ""),
        "type": row.get("type", ""),
    }


def main():
    allsides_rows = fetch_allsides_csv()
    sb_sources = load_feeds()
    ratings = match_sources(sb_sources, allsides_rows)

    # Build output
    output = {
        "generated": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "total_sources": len(sb_sources),
        "matched_sources": len(ratings),
        "match_rate_pct": round(len(ratings) * 100 / len(sb_sources), 1),
        "attribution": "Media bias ratings from AllSides.com, licensed under CC BY-NC 4.0",
        "attribution_url": "https://www.allsides.com/media-bias/ratings",
        "distribution": {},
        "ratings": ratings,
    }

    # Calculate distribution
    dist = {}
    for entry in ratings.values():
        r = entry["rating"]
        dist[r] = dist.get(r, 0) + 1
    output["distribution"] = dict(sorted(dist.items(), key=lambda x: {"left": 0, "left-center": 1, "center": 2, "right-center": 3, "right": 4}.get(x[0], 5)))

    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Written to {OUTPUT_JSON}")

    # Print summary
    print(f"\n  Bias distribution across matched sources:")
    for rating, count in output["distribution"].items():
        bar = "=" * count
        print(f"    {rating:>15}: {bar} ({count})")


if __name__ == "__main__":
    main()
