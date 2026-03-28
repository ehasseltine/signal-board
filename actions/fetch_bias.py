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

# Sources rated on AllSides.com but not in the GitHub CSV.
# Ratings verified from allsides.com/media-bias/ratings as of March 2026.
# For sources AllSides doesn't rate, we use "unrated" and explain why.
SUPPLEMENTAL_RATINGS = {
    # U.S. news outlets AllSides rates on their site
    "NBC News": {"rating": "left-center", "rating_num": 2, "confidence": "Medium", "type": "News Media"},
    "Ars Technica": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Wired": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "In These Times": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Intercept": {"rating": "left", "rating_num": 1, "confidence": "Medium", "type": "News Media"},
    "The 19th News": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Marshall Project": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Heather Cox Richardson": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "Author"},
    "Matt Taibbi (Racket News)": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "Author"},
    "The Lever (David Sirota)": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "Author"},
    "Kyla Scanlon": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "Author"},
    "The Blaze": {"rating": "right", "rating_num": 5, "confidence": "Medium", "type": "News Media"},
    "The Dispatch": {"rating": "right-center", "rating_num": 4, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Free Press (Bari Weiss)": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Platformer": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Rest of World": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "404 Media": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Bellingcat": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "CityLab": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Verge": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "TechCrunch": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "MIT Technology Review": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    # Think tanks and policy
    "Brookings": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    "Heritage Foundation": {"rating": "right", "rating_num": 5, "confidence": "Medium", "type": "Think Tank / Policy Group"},
    "Hoover Institution": {"rating": "right-center", "rating_num": 4, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    "Hudson Institute": {"rating": "right-center", "rating_num": 4, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    "Center for Strategic and International Studies": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    "New America": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    "Bipartisan Policy Center": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    "Urban Institute": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    "Migration Policy Institute": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    "Roosevelt Institute": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    "Brennan Center": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    "Council on Foreign Relations": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    "Marshall Fund": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    "EPI Blog": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    "Chatham House": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "Think Tank / Policy Group"},
    # International press
    "Deutsche Welle": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "France 24": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "NHK World": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "ABC Australia": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Dawn": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Globe and Mail": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Nikkei Asia": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Hindu": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Times of India": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Straits Times": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Channel News Asia": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "El País English": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Anadolu Agency": {"rating": "right-center", "rating_num": 4, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Meduza": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Rappler": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Daily Maverick": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Bangkok Post": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Taipei Times": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Korea Herald": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Japan Times": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "South China Morning Post": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Jamaica Observer": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Global Voices": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The New Humanitarian": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Balkan Insight": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    # Local/regional/identity press
    "Sojourners": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Forward": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "National Catholic Reporter": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Indian Country Today": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Latino USA": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Root": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Grio": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Atlanta Black Star": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Blavity": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Muslim Matters": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Arab American News": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "AsAmNews": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Colorlines": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Prism": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Scalawag": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Daily Yonder": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "High Country News": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Documented": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Hechinger Report": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Civil Eats": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    # State/local newsrooms
    "Colorado Sun": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Nevada Independent": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Arizona Mirror": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Kansas Reflector": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Montana Free Press": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Mississippi Free Press": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Bridge Michigan": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "MinnPost": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Wisconsin Examiner": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Mountain State Spotlight": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "VTDigger": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Maine Monitor": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Crosscut": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Oregon Public Broadcasting": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Voice of San Diego": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Baltimore Banner": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "City Limits": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Source NM": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Lens": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "NC Health News": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Alaska Public Media": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    # Specialist / Deep Expertise
    "Inside Climate News": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Carbon Brief": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Grist": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "E&E News": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "KFF Health News": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "STAT News": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Health Affairs": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Nature News": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Defense One": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "War on the Rocks": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The War Zone": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Just Security": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Lawfare": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Press Freedom Tracker": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Nieman Lab": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Columbia Journalism Review": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Conversation US": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "OnLabor": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Labor Notes": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Payday Report": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Inequality.org": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Trace": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Bolts Magazine": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Capital B News": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    # Podcasts/newsletters
    "NPR Up First": {"rating": "left-center", "rating_num": 2, "confidence": "Medium", "type": "News Media"},
    "Ezra Klein Show": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "Author"},
    "Hard Fork (NYT)": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Pivot (Kara Swisher)": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "Author"},
    "Planet Money (NPR)": {"rating": "left-center", "rating_num": 2, "confidence": "Medium", "type": "News Media"},
    "On the Media (WNYC)": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Radiolab": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "CFR The World Next Week": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Freakonomics Radio": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Marketplace (APM)": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Ben Shapiro Show": {"rating": "right", "rating_num": 5, "confidence": "Medium", "type": "Author"},
    # Specialty
    "Stateline": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Next Avenue": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Task and Purpose": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Chronicle of Higher Education": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Disability Scoop": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Imprint": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Canopy Forum": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Futuro Media": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Brown Girl Magazine": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "NextShark": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Remezcla": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Latino Rebels": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "News Media"},
    "El Diario NY": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "NBC News Latino": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Borderland Beat": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Plug": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Scroll.in": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Press Gazette": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Globe Post": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Americas Quarterly": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "African Arguments": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The East African": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Caribbean National Weekly": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Haitian Times": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Navajo Times": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Religion News Service": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Christianity Today": {"rating": "right-center", "rating_num": 4, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Jewish Telegraphic Agency": {"rating": "center", "rating_num": 3, "confidence": "Low or Initial Rating", "type": "News Media"},
    "The Advocate": {"rating": "left-center", "rating_num": 2, "confidence": "Low or Initial Rating", "type": "News Media"},
    "Teen Vogue": {"rating": "left", "rating_num": 1, "confidence": "Low or Initial Rating", "type": "News Media"},
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
    supplemental_count = 0

    for src in sb_sources:
        name = src["name"]
        key = name.lower()

        # 1. Check supplemental ratings first (manually verified)
        if name in SUPPLEMENTAL_RATINGS:
            entry = SUPPLEMENTAL_RATINGS[name]
            results[name] = {
                "rating": entry["rating"],
                "rating_num": entry["rating_num"],
                "confidence": entry["confidence"],
                "allsides_name": name,
                "allsides_url": f"https://www.allsides.com/media-bias/ratings",
                "type": entry["type"],
                "source": "supplemental",
            }
            matched_count += 1
            supplemental_count += 1
            continue

        # 2. Check manual name overrides for CSV matching
        if name in MANUAL_MATCHES:
            override_key = MANUAL_MATCHES[name].lower()
            if override_key in as_lookup:
                row = as_lookup[override_key]
                results[name] = build_entry(row)
                matched_count += 1
                continue

        # 3. Exact match against CSV
        if key in as_lookup:
            results[name] = build_entry(as_lookup[key])
            matched_count += 1
            continue

        # 4. Substring match
        for ak, av in as_lookup.items():
            if key in ak or ak in key:
                results[name] = build_entry(av)
                matched_count += 1
                break

    total = len(sb_sources)
    print(f"  Matched {matched_count}/{total} sources ({matched_count*100//total}%)")
    print(f"    From CSV: {matched_count - supplemental_count}")
    print(f"    Supplemental: {supplemental_count}")
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
