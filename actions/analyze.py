#!/usr/bin/env python3
"""
Signal Board — Daily narrative analysis generator.

Reads today's articles (with full text where available), clusters them
by shared story, analyzes how different source tiers frame each story,
identifies what community sources cover that national outlets miss,
and produces a structured JSON that the frontend renders.

Principles:
  - Simple, clear, factual language. No moral opinions.
  - Humanize where people come from without justifying harm.
  - If something is illegal, state that clearly (confirmed by law).
  - Contextualize every source: they are all media organizations with interests.
  - Preempt what readers want to know.
  - Never be ambiguous.

Usage:
    python actions/analyze.py                    # analyze today
    python actions/analyze.py --date 2026-03-28  # analyze specific date
"""

import json
import re
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, Counter

from domains import get_domain_labels

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
ARTICLES_FILE = ROOT / "data" / "articles.json"
DAILY_DIR = ROOT / "data" / "daily"

# Source context: factual, non-partisan descriptions of ownership/funding
# These help readers understand where information comes from.
SOURCE_CONTEXT = {
    "New York Times": "Publicly traded, headquartered in New York. Largest US newspaper by circulation. Generally regarded as center-left in editorial stance. Revenue from subscriptions and advertising.",
    "Fox News": "Owned by Fox Corporation (Murdoch family). Largest cable news network by viewership. Generally regarded as right-leaning in editorial and opinion programming. Revenue from advertising and cable fees.",
    "Wall Street Journal": "Owned by News Corp (Murdoch family). Second-largest US newspaper. News coverage is broadly centrist; editorial page leans conservative. Core audience is business and financial professionals.",
    "Washington Post": "Owned by Jeff Bezos since 2013. Major national newspaper. Generally regarded as center-left in editorial stance. Significant political reporting operation.",
    "CNN": "Owned by Warner Bros. Discovery. Major cable news network. Generally regarded as centrist to center-left. Revenue from advertising and cable fees.",
    "NPR": "Nonprofit public media organization funded by member stations, corporate sponsors, and foundations. Generally regarded as center-left. Reaches approximately 30 million weekly listeners.",
    "Bloomberg": "Founded and majority-owned by Michael Bloomberg. Dominant source for financial professionals. Coverage focused on markets and business. Bloomberg ran for president in 2020 as a Democrat.",
    "AP News": "Nonprofit cooperative owned by member newspapers and broadcasters. Supplies content to the majority of US newsrooms. Generally regarded as centrist wire service.",
    "Reuters": "Owned by Thomson Reuters. Major international wire service. Generally regarded as centrist. Core audience includes institutional investors and news organizations.",
    "Al Jazeera": "Funded by the government of Qatar. Major international news network. Provides significant coverage of the Middle East and Global South that US outlets often underreport. Qatar's foreign policy interests can influence editorial priorities.",
    "BBC World": "Funded by the UK license fee and UK government grants for international service. British public broadcaster. Generally regarded as centrist by international standards.",
    "The Guardian World": "Owned by the Scott Trust, a nonprofit. British newspaper. Generally regarded as left-leaning. No paywall, funded by reader contributions.",
    "National Review": "Conservative magazine founded by William F. Buckley Jr. in 1955. Represents the traditional conservative intellectual tradition.",
    "The Federalist": "Conservative online magazine. Represents populist and social conservative perspectives. Funded by advertising and the nonprofit FDRLST Media.",
    "Breitbart": "Right-wing news website founded in 2007. Represents nationalist and populist conservative perspectives. Previously led by Steve Bannon.",
    "Newsmax": "Conservative cable news and digital media company. Grew significantly during and after the 2020 election. Competes with Fox News for conservative audience.",
    "Heritage Foundation": "Conservative think tank founded in 1973. Produced Project 2025 policy document. Significant influence on Republican policy. Funded by conservative donors.",
    "Brookings": "Centrist-to-center-left think tank. Largest think tank in the US by budget. Significant influence on Democratic policy. Funded by foundations, corporations, and foreign governments.",
    "American Prospect": "Progressive magazine covering politics and policy. Explicitly left-of-center editorial stance.",
    "Reason": "Libertarian magazine. Opposes government intervention in both economic and social policy. Funded by the Reason Foundation.",
    "Arab American News": "Community newspaper serving Arab American communities, primarily based in Dearborn, Michigan. Provides perspective from approximately 3.7 million Arab Americans.",
    "Indian Country Today": "Nonprofit newsroom covering Native American communities and tribal affairs. Represents the perspective of approximately 9.7 million people who identify as American Indian or Alaska Native.",
    "El Diario NY": "Spanish-language daily newspaper serving Latino communities in the New York metro area. Part of ImpreMedia network. Reaches communities that may not consume English-language news.",
    "The Root": "Digital magazine covering African American news and culture. Owned by G/O Media.",
    "The Advocate": "LGBTQ+ news magazine, one of the oldest in the US. Covers issues affecting approximately 20 million LGBTQ+ Americans.",
    "Military Times": "Independent news organization covering military and veteran communities. Not affiliated with the Department of Defense. Serves approximately 18 million US veterans.",
    "Daily Yonder": "Nonprofit newsroom covering rural America. Approximately 46 million Americans live in rural areas.",
    "Mother Jones": "Progressive nonprofit magazine. Known for investigative reporting. Founded in 1976, named after labor organizer Mary Harris Jones.",
    "Haaretz": "Israeli liberal newspaper. Oldest daily newspaper in Israel. Generally regarded as left-leaning by Israeli standards. Provides English-language Israeli perspective on Middle East.",
    "Dawn": "Pakistani English-language newspaper. Oldest in Pakistan. Generally regarded as liberal by Pakistani standards. Provides South Asian perspective.",
    "Daily Maverick": "South African investigative publication. Independent nonprofit. Known for accountability journalism. Provides African perspective on democracy and governance.",
    "Global Voices": "International citizen media platform. Nonprofit. Translates and curates stories from 100+ countries in 40+ languages. Represents grassroots global perspectives.",
    "The New Humanitarian": "Independent nonprofit newsroom formerly part of the UN. Covers humanitarian crises and displacement. Provides perspective from conflict zones.",
    "TechCrunch": "Technology industry publication. Owned by Yahoo (Apollo Global Management). Covers startups, venture capital, and AI developments.",
    "Bellingcat": "Netherlands-based investigative journalism group. Uses open-source intelligence methods. Specializes in conflict verification and disinformation tracking.",
    "Defense One": "Publication owned by Government Executive Media Group. Covers defense policy, military technology, and national security.",
    "Cato Institute": "Libertarian think tank founded in 1977. Advocates limited government, free markets, and civil liberties. Funded by individual donors and foundations.",
    "Council on Foreign Relations": "Nonpartisan foreign policy think tank founded in 1921. Publishes Foreign Affairs journal. Major influence on US foreign policy establishment.",
    "CSIS": "Center for Strategic and International Studies. Bipartisan think tank. Major influence on defense and international security policy.",
    "New America": "Policy institute founded in 1999. Centrist to progressive. Covers technology policy, education, and national security.",
    "Urban Institute": "Nonpartisan research organization. Studies social and economic policy including housing, poverty, and healthcare.",
    "Migration Policy Institute": "Nonpartisan research organization. Studies immigration and refugee policy worldwide. Provides data-driven analysis.",
}

# Domain pair explanations: what the intersection means in plain language
PAIR_EXPLANATIONS = {
    'ai+climate': 'AI development and its energy costs or climate applications',
    'ai+economics': 'AI affecting markets, investment, and business models',
    'ai+governance': 'Government efforts to regulate or deploy AI',
    'ai+information': 'AI changing how information is produced and consumed',
    'ai+labor': 'AI and automation changing jobs and wages',
    'ai+legal': 'Courts and lawmakers addressing AI liability and rights',
    'ai+security': 'AI as military tool or national security concern',
    'climate+economics': 'Energy costs, food prices, and insurance rates linked to environmental change',
    'climate+domestic_politics': 'Environmental policy as a political issue',
    'climate+geopolitics': 'Climate diplomacy and international environmental agreements',
    'climate+governance': 'Environmental regulation and climate policy implementation',
    'climate+labor': 'Energy transition affecting workers and communities',
    'climate+legal': 'Environmental lawsuits and climate litigation',
    'climate+security': 'Environmental change creating security or military challenges',
    'domestic_politics+economics': 'Economic conditions shaping political debate',
    'domestic_politics+geopolitics': 'Foreign policy in domestic political debate',
    'domestic_politics+governance': 'Political conflict over how government agencies operate',
    'domestic_politics+information': 'How political information reaches voters',
    'domestic_politics+legal': 'Political disputes reaching the courts',
    'domestic_politics+security': 'Defense and public safety as political issues',
    'economics+geopolitics': 'Trade, sanctions, and global economic competition',
    'economics+governance': 'Tax policy, trade agreements, and government spending',
    'economics+information': 'Tech industry economics and media business models',
    'economics+labor': 'Jobs, wages, and whether economic growth reaches workers',
    'economics+legal': 'Antitrust enforcement, financial regulation, and corporate law',
    'economics+security': 'Military spending and conflict affecting markets',
    'geopolitics+governance': 'International diplomacy and alliance management',
    'geopolitics+legal': 'International law, treaties, and war crimes',
    'geopolitics+security': 'Military tensions between nations',
    'governance+information': 'Government regulation of media and information platforms',
    'governance+labor': 'Workplace regulation and labor law enforcement',
    'governance+legal': 'Government actions being challenged or upheld in courts',
    'governance+security': 'Defense policy and military strategy',
    'information+labor': 'Media coverage of labor issues and worker organizing',
    'information+legal': 'Free speech, media law, and platform regulation',
    'information+security': 'War coverage and information about military operations',
    'labor+legal': 'Employment law, worker rights cases, and workplace litigation',
    'labor+security': 'Military workforce and defense industry employment',
}


# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

def load_articles():
    if not ARTICLES_FILE.exists():
        print(f"ERROR: {ARTICLES_FILE} not found")
        return []
    with open(ARTICLES_FILE, "r") as f:
        data = json.load(f)
        return data.get("articles", [])


def load_daily_history(days=7):
    history = {}
    if not DAILY_DIR.exists():
        return history
    for daily_file in sorted(DAILY_DIR.glob("*.json")):
        if daily_file.name == "latest.json":
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


# ---------------------------------------------------------------------------
# TEXT ANALYSIS UTILITIES
# ---------------------------------------------------------------------------

def extract_keywords(text, min_len=5, top_n=20):
    """Extract the most frequent meaningful words from text."""
    stop = {'about','after','again','against','along','already','among',
            'another','around','based','because','before','being','between',
            'could','during','every','first','found','going','group',
            'house','including','known','large','later','least','level',
            'likely','major','making','might','never','number','often',
            'other','party','place','point','press','program','public',
            'really','since','small','something','still','system',
            'their','there','these','thing','think','those','three',
            'through','times','today','under','united','until',
            'using','watch','where','which','while','world','would',
            'years','state','states','house','report','officials',
            'according','tuesday','wednesday','thursday','friday',
            'saturday','sunday','monday','march','april','reuters',
            'associated','update','watch'}
    words = re.findall(r'[a-z]{%d,}' % min_len, text.lower())
    filtered = [w for w in words if w not in stop]
    return [w for w, _ in Counter(filtered).most_common(top_n)]


def cluster_articles_by_story(articles, threshold=0.3):
    """
    Group articles into story clusters based on shared title keywords.
    Returns list of clusters, each with articles and a topic label.
    """
    # Build keyword index
    article_keywords = {}
    for a in articles:
        title = a.get("title", "")
        text = a.get("text", "") or a.get("summary", "")
        combined = title + " " + title + " " + text[:500]  # weight title 2x
        kw = set(extract_keywords(combined, min_len=5, top_n=15))
        article_keywords[a["id"]] = kw

    # Find clusters by shared keywords (greedy)
    used = set()
    clusters = []

    # Sort articles by number of keywords (richest first)
    sorted_ids = sorted(article_keywords.keys(),
                        key=lambda x: len(article_keywords[x]), reverse=True)

    for anchor_id in sorted_ids:
        if anchor_id in used:
            continue
        anchor_kw = article_keywords[anchor_id]
        if not anchor_kw:
            continue

        cluster_ids = {anchor_id}
        cluster_kw = set(anchor_kw)

        for other_id in sorted_ids:
            if other_id in used or other_id == anchor_id:
                continue
            other_kw = article_keywords[other_id]
            if not other_kw:
                continue
            overlap = len(anchor_kw & other_kw) / max(len(anchor_kw | other_kw), 1)
            if overlap >= threshold:
                cluster_ids.add(other_id)
                cluster_kw |= other_kw

        if len(cluster_ids) >= 3:
            cluster_articles = [a for a in articles if a["id"] in cluster_ids]
            used |= cluster_ids
            clusters.append(cluster_articles)

    return clusters


# ---------------------------------------------------------------------------
# CORE ANALYSIS FUNCTIONS
# ---------------------------------------------------------------------------

def analyze_top_stories(articles):
    """
    Cluster articles into stories, then for each story produce:
    - A factual headline
    - How many sources from how many tiers cover it
    - How framing differs across tiers
    - What domains it touches
    - Source articles with source context
    """
    domain_labels = get_domain_labels()
    clusters = cluster_articles_by_story(articles, threshold=0.25)

    # Sort by number of unique sources (broadest coverage first)
    clusters.sort(key=lambda c: len(set(a["source"] for a in c)), reverse=True)

    stories = []
    for cluster in clusters[:8]:  # Top 8 stories
        sources = list(set(a["source"] for a in cluster))
        tiers = list(set(
            ("community" if a.get("tier") in ("community","lived") else
             "specialist" if a.get("tier") in ("specialist","domain") else
             a.get("tier","unknown"))
            for a in cluster
        ))

        # Domains this story touches
        all_domains = Counter()
        for a in cluster:
            for d in a.get("domains", []):
                all_domains[d] += 1
        top_domains = [domain_labels.get(d, d) for d, _ in all_domains.most_common(3)]

        # Extract the most representative title (from largest outlet)
        tier_order = {"national": 0, "international": 1, "community": 2,
                      "specialist": 3, "explainer": 4, "analysis": 5}
        sorted_arts = sorted(cluster,
                             key=lambda a: tier_order.get(a.get("tier",""), 9))
        lead_title = sorted_arts[0]["title"] if sorted_arts else ""

        # How different tiers frame it (extract distinctive title words per tier)
        tier_framing = {}
        for tier_name in ["national", "international", "community", "specialist", "analysis"]:
            tier_arts = [a for a in cluster
                         if a.get("tier") == tier_name or
                         (tier_name == "community" and a.get("tier") in ("community","lived")) or
                         (tier_name == "specialist" and a.get("tier") in ("specialist","domain"))]
            if not tier_arts:
                continue
            tier_titles = " ".join(a["title"] for a in tier_arts)
            tier_kw = extract_keywords(tier_titles, min_len=4, top_n=8)
            sample = tier_arts[0]
            tier_framing[tier_name] = {
                "count": len(tier_arts),
                "keywords": tier_kw[:5],
                "sample": {
                    "title": sample["title"][:120],
                    "source": sample["source"],
                    "url": sample.get("url", ""),
                    "context": SOURCE_CONTEXT.get(sample["source"], ""),
                },
            }

        # Sample articles (one per source, max 6)
        seen_sources = set()
        sample_articles = []
        for a in sorted_arts:
            if a["source"] not in seen_sources and len(sample_articles) < 6:
                seen_sources.add(a["source"])
                sample_articles.append({
                    "title": a["title"][:120],
                    "source": a["source"],
                    "url": a.get("url", ""),
                    "tier": a.get("tier", ""),
                    "paywall": a.get("paywall", False),
                    "context": SOURCE_CONTEXT.get(a["source"], ""),
                })

        stories.append({
            "headline": lead_title[:120],
            "source_count": len(sources),
            "tier_count": len(tiers),
            "tiers": tiers,
            "domains": top_domains,
            "domain_keys": [d for d, _ in all_domains.most_common(3)],
            "article_count": len(cluster),
            "tier_framing": tier_framing,
            "articles": sample_articles,
        })

    return stories


def analyze_what_connects(articles):
    """
    Find stories where sources from across the political/demographic spectrum
    converge on the same topic. This is the proof that shared attention exists.
    """
    LEFT = {'New York Times','Washington Post','NPR','CNN','The Atlantic',
            'NBC News','ABC News','Vox','American Prospect','The Intercept',
            'Prism','Mother Jones','Center for American Progress',
            'Roosevelt Institute','Brookings'}
    RIGHT = {'Fox News','National Review','Washington Examiner','Washington Times',
             'Daily Wire','The Dispatch','Reason','RealClearPolitics',
             'The Federalist','Newsmax','The Blaze','Breitbart',
             'Heritage Foundation','American Enterprise Institute',
             'Hoover Institution','Hudson Institute','Cato Institute'}
    INTL = {'BBC World','The Guardian World','Al Jazeera','Deutsche Welle',
            'France 24','South China Morning Post','The Hindu','NHK World',
            'ABC Australia','Rappler','Meduza','Times of India','Straits Times',
            'Haaretz','Dawn','The Korea Herald','Bangkok Post','Taipei Times',
            'Channel News Asia','Daily Maverick','Jamaica Observer',
            'The Japan Times','Anadolu Agency','Global Voices',
            'The New Humanitarian','Scroll.in','Balkan Insight','Nikkei Asia',
            'The East African','The Globe and Mail','Press Gazette'}

    clusters = cluster_articles_by_story(articles, threshold=0.3)
    bridging = []

    for cluster in clusters:
        left = set(); right = set(); intl = set(); community = set()
        for a in cluster:
            src = a["source"]
            if src in LEFT: left.add(src)
            elif src in RIGHT: right.add(src)
            elif src in INTL: intl.add(src)
            elif a.get("tier") in ("community","lived"): community.add(src)

        segments = sum(1 for g in [left, right, intl, community] if g)
        if segments >= 3 and len(left|right|intl|community) >= 5:
            lead = cluster[0]
            bridging.append({
                "headline": lead["title"][:120],
                "total_sources": len(set(a["source"] for a in cluster)),
                "spectrum_segments": segments,
                "left_sources": list(left)[:3],
                "right_sources": list(right)[:3],
                "international_sources": list(intl)[:3],
                "community_sources": list(community)[:3],
                "article_count": len(cluster),
                "domains": [d for d, _ in Counter(
                    d for a in cluster for d in a.get("domains", [])
                ).most_common(3)],
            })

    bridging.sort(key=lambda x: (x["spectrum_segments"], x["total_sources"]),
                  reverse=True)
    return bridging[:6]


def analyze_community_exclusive(articles):
    """
    Find stories that community/specialist sources cover but national
    outlets do not. These are the gaps in mainstream coverage.
    """
    national_keywords = set()
    for a in articles:
        if a.get("tier") == "national":
            for w in re.findall(r'[a-z]{6,}', a.get("title","").lower()):
                national_keywords.add(w)

    community_stories = []
    for a in articles:
        if a.get("tier") not in ("community", "lived", "specialist", "domain"):
            continue
        title_words = set(re.findall(r'[a-z]{6,}', a.get("title","").lower()))
        if not title_words:
            continue
        overlap = len(title_words & national_keywords) / len(title_words)
        if overlap < 0.35:
            text = a.get("text", "") or a.get("summary", "")
            community_stories.append({
                "title": a["title"][:120],
                "source": a["source"],
                "url": a.get("url", ""),
                "tier": a.get("tier", ""),
                "text_preview": text[:250] if text else "",
                "domains": a.get("domains", []),
                "context": SOURCE_CONTEXT.get(a["source"], ""),
            })

    # Deduplicate by source (one per source)
    seen = set()
    unique = []
    for s in community_stories:
        if s["source"] not in seen:
            seen.add(s["source"])
            unique.append(s)

    return unique[:12]


def analyze_domain_collisions(articles, history):
    """
    Track which domain pairs are most active and whether they're
    rising or falling vs. the 7-day average.
    """
    domain_labels = get_domain_labels()

    pair_today = defaultdict(int)
    pair_articles = defaultdict(list)
    for a in articles:
        doms = sorted(a.get("domains", []))
        for i in range(len(doms)):
            for j in range(i+1, len(doms)):
                pair = (doms[i], doms[j])
                pair_today[pair] += 1
                if len(pair_articles[pair]) < 3:
                    pair_articles[pair].append({
                        "title": a["title"][:80],
                        "source": a["source"],
                        "url": a.get("url", ""),
                    })

    # Rolling average from history
    pair_avg = defaultdict(float)
    hist_dates = sorted(history.keys())[-6:]
    if hist_dates:
        for date_key in hist_dates:
            for thread in history[date_key].get("active_threads", []):
                pair = thread.get("pair")
                if pair and isinstance(pair, list):
                    key = tuple(sorted(pair))
                    pair_avg[key] += thread.get("today_count", 0)
        for p in pair_avg:
            pair_avg[p] /= len(hist_dates)

    threads = []
    for pair, count in sorted(pair_today.items(), key=lambda x: x[1], reverse=True):
        d1, d2 = pair
        pair_key = "+".join(sorted([d1, d2]))
        explanation = PAIR_EXPLANATIONS.get(pair_key,
            f"{domain_labels.get(d1,d1)} and {domain_labels.get(d2,d2)}")

        avg = pair_avg.get(pair, 0)
        if avg == 0:
            trend = "new" if count > 0 else "stable"
        elif count > avg * 1.25:
            trend = "rising"
        elif count < avg * 0.75:
            trend = "falling"
        else:
            trend = "stable"

        threads.append({
            "pair": list(pair),
            "label": f"{domain_labels.get(d1,d1)} + {domain_labels.get(d2,d2)}",
            "explanation": explanation,
            "today_count": count,
            "trend": trend,
            "sample_articles": pair_articles[pair],
        })

    return threads[:15]


def analyze_source_spectrum(articles):
    """Count articles by source tier."""
    return {
        "national": sum(1 for a in articles if a.get("tier") == "national"),
        "international": sum(1 for a in articles if a.get("tier") == "international"),
        "specialist": sum(1 for a in articles if a.get("tier") in ("specialist","domain")),
        "explainer": sum(1 for a in articles if a.get("tier") == "explainer"),
        "community": sum(1 for a in articles if a.get("tier") in ("community","lived")),
        "analysis": sum(1 for a in articles if a.get("tier") == "analysis"),
    }


def generate_questions_people_are_asking(articles):
    """
    Based on the top stories, generate the questions regular people
    would likely have, and point to which sources address them.
    """
    domain_labels = get_domain_labels()

    # Count domains
    dom_counts = Counter()
    for a in articles:
        for d in a.get("domains", []):
            dom_counts[d] += 1

    # Generate questions based on the most active domain pairs
    pair_counts = Counter()
    for a in articles:
        doms = sorted(a.get("domains", []))
        for i in range(len(doms)):
            for j in range(i+1, len(doms)):
                pair_counts[(doms[i], doms[j])] += 1

    PAIR_QUESTIONS = {
        'economics+security': "How is the conflict affecting prices and the economy?",
        'domestic_politics+governance': "What is the government actually doing right now?",
        'domestic_politics+legal': "What legal challenges are being filed, and what do they mean?",
        'domestic_politics+security': "How are defense and security decisions being shaped by politics?",
        'governance+legal': "Which government actions are being challenged in court?",
        'climate+economics': "How are energy and environmental changes affecting costs?",
        'climate+security': "How is environmental change creating security risks?",
        'ai+labor': "How is automation changing the job market?",
        'economics+labor': "Are wages keeping up with costs?",
        'geopolitics+security': "What is the current state of international military tensions?",
        'domestic_politics+information': "How is political information reaching voters differently?",
        'governance+security': "What military and defense policy decisions are being made?",
        'ai+economics': "How is AI affecting markets and investment?",
        'economics+geopolitics': "How are trade and global power shifts affecting the US economy?",
    }

    questions = []
    for (d1, d2), count in pair_counts.most_common(8):
        pair_key = "+".join(sorted([d1, d2]))
        q = PAIR_QUESTIONS.get(pair_key)
        if q and count >= 3:
            # Find sources that address this question
            relevant = [a for a in articles
                        if d1 in a.get("domains",[]) and d2 in a.get("domains",[])]
            source_tiers = defaultdict(list)
            for a in relevant[:10]:
                tier = a.get("tier","")
                if tier in ("community","lived"): tier = "community"
                if tier in ("specialist","domain"): tier = "specialist"
                if a["source"] not in [s["source"] for s in source_tiers[tier]]:
                    source_tiers[tier].append({
                        "source": a["source"],
                        "title": a["title"][:100],
                        "url": a.get("url",""),
                        "context": SOURCE_CONTEXT.get(a["source"],""),
                    })

            questions.append({
                "question": q,
                "article_count": count,
                "domains": [domain_labels.get(d1,d1), domain_labels.get(d2,d2)],
                "sources_by_tier": {k: v[:2] for k, v in source_tiers.items()},
            })

    return questions[:6]


# ---------------------------------------------------------------------------
# MAIN ANALYSIS
# ---------------------------------------------------------------------------

def generate_daily_analysis(articles, analysis_date, history):
    domain_labels = get_domain_labels()
    unique_sources = set(a.get("source") for a in articles)
    cross_domain = sum(1 for a in articles if a.get("cross_domain", False))

    dom_counts = Counter()
    for a in articles:
        for d in a.get("domains", []):
            dom_counts[d] += 1

    top_domain = ""
    if dom_counts:
        top_key = dom_counts.most_common(1)[0][0]
        top_domain = domain_labels.get(top_key, top_key)

    # Run all analysis components
    top_stories = analyze_top_stories(articles)
    what_connects = analyze_what_connects(articles)
    community_exclusive = analyze_community_exclusive(articles)
    active_threads = analyze_domain_collisions(articles, history)
    source_spectrum = analyze_source_spectrum(articles)
    questions = generate_questions_people_are_asking(articles)

    return {
        "date": analysis_date,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_stories": len(articles),
            "sources_reporting": len(unique_sources),
            "cross_domain": cross_domain,
            "cross_domain_pct": round(cross_domain / max(len(articles), 1) * 100),
            "top_domain": top_domain,
        },
        "top_stories": top_stories,
        "what_connects": what_connects,
        "community_exclusive": community_exclusive,
        "active_threads": active_threads,
        "source_spectrum": source_spectrum,
        "questions": questions,
        # Keep old keys for backward compat with frontend
        "narrative_divergence": [
            {
                "topic": s["domains"][0] + " + " + s["domains"][1] if len(s["domains"]) >= 2 else s["domains"][0] if s["domains"] else "",
                "theme": s["headline"],
                "source_count": s["source_count"],
                "articles": s["articles"],
            }
            for s in top_stories[:3]
        ],
    }


def print_summary(analysis):
    s = analysis["summary"]
    print("\n========== DAILY NARRATIVE ANALYSIS ==========")
    print(f"Date:               {analysis['date']}")
    print(f"Total stories:      {s['total_stories']}")
    print(f"Sources reporting:  {s['sources_reporting']}")
    print(f"Cross-domain:       {s['cross_domain']} ({s['cross_domain_pct']}%)")
    print(f"Top domain:         {s['top_domain']}")

    if analysis.get("top_stories"):
        print(f"\nTop stories ({len(analysis['top_stories'])} found):")
        for i, st in enumerate(analysis["top_stories"][:5], 1):
            print(f"  {i}. {st['headline'][:70]} ({st['source_count']} sources, {st['tier_count']} tiers)")

    if analysis.get("what_connects"):
        print(f"\nBridging stories ({len(analysis['what_connects'])} found):")
        for i, b in enumerate(analysis["what_connects"][:3], 1):
            print(f"  {i}. {b['headline'][:60]} ({b['spectrum_segments']}/4 spectrum segments)")

    if analysis.get("community_exclusive"):
        print(f"\nCommunity-exclusive ({len(analysis['community_exclusive'])} found):")
        for i, c in enumerate(analysis["community_exclusive"][:5], 1):
            print(f"  {i}. [{c['source']}] {c['title'][:60]}")

    if analysis.get("questions"):
        print(f"\nQuestions people are asking:")
        for q in analysis["questions"][:4]:
            print(f"  ? {q['question']} ({q['article_count']} articles)")

    print("===========================================\n")


def main():
    parser = argparse.ArgumentParser(description="Signal Board daily analysis")
    parser.add_argument("--date", type=str, default=None)
    args = parser.parse_args()

    if args.date:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
            analysis_date = args.date
        except ValueError:
            print(f"ERROR: Invalid date '{args.date}'")
            sys.exit(1)
    else:
        analysis_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"Analyzing articles for {analysis_date}")

    all_articles = load_articles()
    if not all_articles:
        print("ERROR: No articles found.")
        sys.exit(1)

    history = load_daily_history(days=7)
    articles = [a for a in all_articles if a.get("date") == analysis_date]

    if not articles:
        print(f"WARNING: No articles for {analysis_date}, using all recent")
        articles = all_articles[:1500]

    analysis = generate_daily_analysis(articles, analysis_date, history)

    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    dated_file = DAILY_DIR / f"{analysis_date}.json"
    with open(dated_file, "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"Wrote {dated_file}")

    latest_file = DAILY_DIR / "latest.json"
    with open(latest_file, "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"Wrote {latest_file}")

    print_summary(analysis)


if __name__ == "__main__":
    main()
