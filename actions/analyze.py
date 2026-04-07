#!/usr/bin/env python3
"""
Signal Board — Daily narrative analysis generator.

Reads today's articles (with AI classification, domain tags, structural
force tags, and cross-domain connection insights), clusters them by
STRUCTURAL FORCE (not keyword overlap), analyzes how different source
tiers and perspectives frame each force, and produces a structured JSON
that the frontend renders.

The key insight: articles about tariffs, articles about AI job loss, and
articles about immigration policy may all be driven by the same structural
force — "labor market transformation." This engine finds those connections.

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
SOURCES_FILE = ROOT / "data" / "sources.json"

# Source context: loaded from canonical sources.json (single source of truth)
def _load_source_context():
    """Load source descriptions from data/sources.json."""
    if SOURCES_FILE.exists():
        with open(SOURCES_FILE) as f:
            sources = json.load(f)
        return {name: entry.get("description", "") for name, entry in sources.items()}
    print("WARNING: data/sources.json not found, source descriptions will be empty")
    return {}

SOURCE_CONTEXT = _load_source_context()


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
            'associated','update','watch','people','trump','says',
            'president','could','should','would'}
    words = re.findall(r'[a-z]{%d,}' % min_len, text.lower())
    filtered = [w for w in words if w not in stop]
    return [w for w, _ in Counter(filtered).most_common(top_n)]


def normalize_force_tag(tag: str) -> str:
    """Normalize force tags for grouping (lowercase, strip whitespace)."""
    return tag.lower().strip().rstrip(".")


def compute_force_similarity(tag1: str, tag2: str) -> float:
    """
    Compute similarity between two force tags using word overlap.
    Returns 0-1 score.
    """
    words1 = set(tag1.lower().split())
    words2 = set(tag2.lower().split())
    if not words1 or not words2:
        return 0
    # Jaccard similarity
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    return intersection / union if union > 0 else 0


# ---------------------------------------------------------------------------
# STRUCTURAL FORCE CLUSTERING
# ---------------------------------------------------------------------------

def cluster_by_structural_force(articles):
    """
    Cluster articles by domain label — the 15 plain-language taxonomy labels.

    Previously grouped by force_tag (now retired). New strategy:
    1. Group articles by their most specific label combination (domain pair or single)
    2. Merge groups that share dominant labels and have keyword overlap
    3. This is topic-agnostic: works on any news, any day, any year

    Why domain pairs: a story tagged [war_and_conflict, oil_and_energy] is a
    different cluster from one tagged [war_and_conflict, whos_in_charge], even
    though both contain war_and_conflict. The combination is the structural unit.
    """
    # Only work with articles that have domain labels
    labeled = [a for a in articles if a.get("domains")]
    unlabeled = [a for a in articles if not a.get("domains")]

    # Step 1: Group by dominant label pair (or single label if only one)
    # Use the top-2 labels by frequency within each article's domain list
    def label_key(a):
        doms = sorted(a.get("domains", []))
        if len(doms) >= 2:
            return tuple(doms[:2])   # first two alphabetically = stable key
        elif len(doms) == 1:
            return (doms[0],)
        return ("untagged",)

    label_groups = defaultdict(list)
    for a in labeled:
        label_groups[label_key(a)].append(a)

    # Step 2: Merge groups that share at least one label AND have keyword overlap
    # This merges e.g. (war_and_conflict, global_relations) with
    # (global_relations, oil_and_energy) if their articles share keywords
    merged_groups = []
    used_keys = set()
    keys_by_size = sorted(label_groups.keys(), key=lambda k: len(label_groups[k]), reverse=True)

    for key in keys_by_size:
        if key in used_keys:
            continue
        group = list(label_groups[key])
        used_keys.add(key)
        key_labels = set(key)

        # Merge other groups that share a label with this one
        for other_key in keys_by_size:
            if other_key in used_keys:
                continue
            other_labels = set(other_key)
            # Merge if: shares a label AND groups aren't too large already
            if key_labels & other_labels and len(group) < 200:
                group.extend(label_groups[other_key])
                used_keys.add(other_key)

        if len(group) >= 2:
            merged_groups.append(group)

    # Step 3: Assign unlabeled articles to best matching group by keyword overlap
    for a in unlabeled:
        a_kw = set(extract_keywords(a.get("title", "") + " " + a.get("summary", "")[:200], min_len=4, top_n=10))
        best_group, best_score = None, 0
        for group in merged_groups:
            grp_kw = set()
            for ga in group[:5]:
                grp_kw.update(extract_keywords(ga.get("title", ""), min_len=4, top_n=5))
            if a_kw and grp_kw:
                score = len(a_kw & grp_kw) / len(a_kw | grp_kw)
                if score > best_score and score >= 0.25:
                    best_score, best_group = score, group
        if best_group is not None:
            best_group.append(a)

    return merged_groups


def score_force_cluster(cluster):
    """
    Score a structural force cluster for significance.

    Factors:
    - Source diversity (more unique sources = more significant)
    - Domain breadth (touches more domains = more structurally important)
    - Tier diversity (covered by national + local-regional + intl = broader relevance)
    - AI connection quality (articles with connection insights are richer)
    """
    sources = set(a["source"] for a in cluster)
    domains = set()
    tiers = set()
    has_connection = 0

    for a in cluster:
        for d in a.get("domains", []):
            domains.add(d)
        tier = a.get("tier", "")
        if tier in ("local-regional", "lived"):
            tiers.add("local-regional")
        elif tier in ("specialist", "domain"):
            tiers.add("specialist")
        else:
            tiers.add(tier)
        if a.get("connection"):
            has_connection += 1

    source_score = len(sources)
    domain_score = len(domains) * 2  # domain breadth matters most
    tier_score = len(tiers)
    connection_bonus = min(has_connection, 5)  # cap the bonus

    return source_score * domain_score + tier_score * 3 + connection_bonus


# ---------------------------------------------------------------------------
# EVENT-LEVEL CLUSTERING + FRAMING DIVERGENCE (for the Gap section)
# ---------------------------------------------------------------------------

def extract_entities(text):
    """
    Extract likely named entities (proper nouns) from a headline or summary.
    Uses capitalization patterns: sequences of capitalized words that aren't
    sentence-initial. Simple but effective for headlines where entities are
    dense and formatting is consistent.
    """
    if not text:
        return set()
    # Split into words, keep capitalized tokens that aren't common title words
    title_noise = {
        'The', 'A', 'An', 'In', 'On', 'At', 'To', 'For', 'Of', 'And',
        'But', 'Or', 'Is', 'Are', 'Was', 'Were', 'Has', 'Have', 'Had',
        'Will', 'Would', 'Could', 'Should', 'May', 'Can', 'Do', 'Does',
        'Did', 'Not', 'No', 'How', 'Why', 'What', 'When', 'Where', 'Who',
        'New', 'More', 'Over', 'After', 'With', 'From', 'Into', 'About',
        'Says', 'Said', 'Up', 'Out', 'Its', 'All', 'By', 'As', 'Be',
        'If', 'So', 'My', 'His', 'Her', 'Our', 'Their', 'This', 'That',
        'Report', 'Analysis', 'Opinion', 'Breaking', 'Update', 'Watch',
        'Live', 'First', 'Last', 'Big', 'Top', 'Key', 'Major', 'Latest',
    }
    words = text.split()
    entities = set()
    for i, word in enumerate(words):
        # Strip punctuation for matching
        clean = re.sub(r'[^\w]', '', word)
        if not clean:
            continue
        # Keep capitalized words that aren't noise and aren't sentence-start
        # (sentence-start = index 0 or preceded by period)
        is_sentence_start = (i == 0) or (i > 0 and words[i-1].endswith('.'))
        if clean[0].isupper() and clean not in title_noise:
            if not is_sentence_start or len(clean) > 3:
                entities.add(clean.lower())
        # Also keep ALL-CAPS acronyms (EU, NATO, FDA)
        if clean.isupper() and len(clean) >= 2 and clean not in title_noise:
            entities.add(clean.lower())
    return entities


def compute_event_similarity(art1, art2):
    """
    Compute how likely two articles cover the same event.
    Returns a 0-1 score based on entity overlap and keyword overlap.
    Entity overlap is weighted higher because shared proper nouns
    (people, orgs, places) are stronger event indicators than shared
    topic words.
    """
    title1 = art1.get("title", "")
    title2 = art2.get("title", "")
    summary1 = (art1.get("summary") or "")[:150]
    summary2 = (art2.get("summary") or "")[:150]

    text1 = title1 + " " + summary1
    text2 = title2 + " " + summary2

    # Entity overlap (proper nouns, acronyms)
    ent1 = extract_entities(text1)
    ent2 = extract_entities(text2)
    if ent1 and ent2:
        ent_jaccard = len(ent1 & ent2) / len(ent1 | ent2)
    else:
        ent_jaccard = 0

    # Keyword overlap (content words from title only, for precision)
    kw1 = set(re.findall(r'[a-z]{4,}', title1.lower()))
    kw2 = set(re.findall(r'[a-z]{4,}', title2.lower()))
    # Remove very common words
    common = {'that', 'this', 'with', 'from', 'have', 'will', 'been',
              'says', 'said', 'could', 'would', 'should', 'about',
              'after', 'over', 'into', 'also', 'more', 'than',
              'what', 'when', 'where', 'which', 'their', 'there',
              'were', 'some', 'just', 'like', 'make', 'made',
              'year', 'years', 'first', 'other', 'being', 'under',
              'report', 'reports', 'news'}
    kw1 -= common
    kw2 -= common
    if kw1 and kw2:
        kw_jaccard = len(kw1 & kw2) / len(kw1 | kw2)
    else:
        kw_jaccard = 0

    # Entity overlap weighted 0.65, keyword overlap weighted 0.35
    return ent_jaccard * 0.65 + kw_jaccard * 0.35


def cluster_events_within_force(force_cluster, similarity_threshold=0.15):
    """
    Within a structural force cluster, sub-group articles by shared event.
    Uses single-linkage agglomerative clustering: if any article in cluster A
    is similar enough to any article in cluster B, merge them.

    Returns a list of event clusters (each a list of articles).
    Only returns clusters with >= 3 articles from >= 2 sources.
    """
    if len(force_cluster) < 3:
        return []

    # Start with each article in its own cluster
    clusters = [[a] for a in force_cluster]

    # Precompute pairwise similarities
    n = len(force_cluster)
    sim_matrix = {}
    for i in range(n):
        for j in range(i + 1, n):
            sim = compute_event_similarity(force_cluster[i], force_cluster[j])
            sim_matrix[(i, j)] = sim

    # Single-linkage merge
    changed = True
    while changed:
        changed = False
        best_sim = 0
        best_pair = None

        for ci in range(len(clusters)):
            for cj in range(ci + 1, len(clusters)):
                # Max similarity between any pair across two clusters
                max_sim = 0
                for ai in clusters[ci]:
                    for aj in clusters[cj]:
                        idx_i = force_cluster.index(ai)
                        idx_j = force_cluster.index(aj)
                        key = (min(idx_i, idx_j), max(idx_i, idx_j))
                        s = sim_matrix.get(key, 0)
                        if s > max_sim:
                            max_sim = s

                if max_sim > best_sim:
                    best_sim = max_sim
                    best_pair = (ci, cj)

        if best_sim >= similarity_threshold and best_pair:
            ci, cj = best_pair
            clusters[ci] = clusters[ci] + clusters[cj]
            clusters.pop(cj)
            changed = True

    # Filter: need >= 3 articles from >= 2 distinct sources
    valid = []
    for cluster in clusters:
        sources = set(a.get("source", "") for a in cluster)
        if len(cluster) >= 3 and len(sources) >= 2:
            valid.append(cluster)

    return valid


def score_framing_divergence(event_cluster):
    """
    Score how much framing divergence exists within an event cluster.
    Higher score = outlets are framing the same event more differently.

    Components:
    1. Headline keyword divergence (avg pairwise Jaccard distance of titles)
    2. Tier spread (how many distinct source tiers cover this event)
    3. Source count (more sources = more perspectives)

    Returns a dict with the score and its components.
    """
    import math

    articles = event_cluster
    n = len(articles)

    # 1. Headline keyword divergence (avg pairwise)
    total_distance = 0
    pair_count = 0
    for i in range(n):
        kw_i = set(re.findall(r'[a-z]{4,}', articles[i].get("title", "").lower()))
        for j in range(i + 1, n):
            kw_j = set(re.findall(r'[a-z]{4,}', articles[j].get("title", "").lower()))
            if kw_i or kw_j:
                jaccard_sim = len(kw_i & kw_j) / len(kw_i | kw_j) if (kw_i | kw_j) else 0
                total_distance += (1 - jaccard_sim)
            else:
                total_distance += 1
            pair_count += 1

    avg_divergence = total_distance / max(pair_count, 1)

    # 2. Tier spread
    tiers = set()
    for a in articles:
        tier = a.get("tier", "unknown")
        if tier in ("local-regional", "lived"):
            tiers.add("local-regional")
        elif tier in ("specialist", "domain"):
            tiers.add("specialist")
        else:
            tiers.add(tier)
    tier_spread = len(tiers)

    # 3. Source count
    source_count = len(set(a.get("source", "") for a in articles))

    # Combined score
    score = (avg_divergence * 0.5
             + (tier_spread / 5.0) * 0.3  # normalize: 5 tiers = max
             + (math.log(max(source_count, 1)) / math.log(20)) * 0.2)  # normalize: 20 sources = max

    return {
        "score": round(score, 4),
        "keyword_divergence": round(avg_divergence, 4),
        "tier_spread": tier_spread,
        "source_count": source_count,
        "article_count": n,
    }


def analyze_event_divergence(articles, exclude_force=None):
    """
    The Gap section pipeline:
    1. Cluster articles by structural force
    2. Within each force cluster, sub-cluster by shared event
    3. Score each event cluster for framing divergence
    4. Return event clusters ranked by divergence score

    exclude_force: if provided, skip this force tag (already used for Thread)
    """
    # Use all articles with domain labels — force_tag is retired
    classified = [a for a in articles if a.get("domains")]
    force_clusters = cluster_by_structural_force(classified)

    all_event_clusters = []

    for force_cluster in force_clusters:
        # Get the primary label combination for this cluster
        label_counts = Counter()
        for a in force_cluster:
            for d in a.get("domains", []):
                label_counts[d] += 1
        primary_force = label_counts.most_common(1)[0][0] if label_counts else ""

        # Skip the label already used for Thread
        if exclude_force and primary_force == exclude_force:
            continue

        # Sub-cluster by shared event
        event_clusters = cluster_events_within_force(force_cluster)

        for ec in event_clusters:
            divergence = score_framing_divergence(ec)

            # Build a representative label from shared entities
            all_entities = Counter()
            for a in ec:
                for ent in extract_entities(a.get("title", "")):
                    all_entities[ent] += 1
            # Entities that appear in at least 40% of articles = shared actors
            threshold = max(len(ec) * 0.4, 2)
            shared_entities = [ent for ent, count in all_entities.most_common(10)
                              if count >= threshold]

            # Collect source details
            sources = list(set(a.get("source", "") for a in ec))
            tiers = list(set(
                ("local-regional" if a.get("tier") in ("local-regional", "lived") else
                 "specialist" if a.get("tier") in ("specialist", "domain") else
                 a.get("tier", "unknown"))
                for a in ec
            ))

            # Sample articles (one per source, max 8)
            seen_sources = set()
            sample_articles = []
            for a in ec:
                if a["source"] not in seen_sources and len(sample_articles) < 8:
                    seen_sources.add(a["source"])
                    sample_articles.append({
                        "title": a["title"][:150],
                        "source": a["source"],
                        "url": a.get("url", ""),
                        "tier": a.get("tier", ""),
                        "force_tag": a.get("force_tag", ""),
                        "connection": a.get("connection", ""),
                        "context": SOURCE_CONTEXT.get(a["source"], ""),
                    })

            all_event_clusters.append({
                "structural_force": primary_force,
                "shared_entities": shared_entities[:8],
                "divergence": divergence,
                "sources": sources,
                "tiers": tiers,
                "articles": sample_articles,
                "all_article_count": len(ec),
            })

    # Sort by divergence score, highest first
    all_event_clusters.sort(key=lambda x: x["divergence"]["score"], reverse=True)
    return all_event_clusters[:10]


# ---------------------------------------------------------------------------
# CORE ANALYSIS FUNCTIONS
# ---------------------------------------------------------------------------

def analyze_top_stories(articles):
    """
    Cluster articles by structural force, then for each force produce:
    - The structural force at work
    - A factual headline from the most representative article
    - How many sources from how many tiers cover it
    - How framing differs across tiers
    - What domains it touches
    - AI-generated connection insights
    """
    domain_labels = get_domain_labels()

    # Only cluster articles that have BOTH domain tags AND force_tags (AI-classified)
    # This prevents unclassified articles from creating junk clusters
    classified_articles = [a for a in articles if a.get("domains") and a.get("force_tag")]
    clusters = cluster_by_structural_force(classified_articles)

    # Score and sort
    clusters.sort(key=score_force_cluster, reverse=True)

    stories = []
    for cluster in clusters[:10]:  # Top 10 structural forces
        sources = list(set(a["source"] for a in cluster))
        tiers = list(set(
            ("local-regional" if a.get("tier") in ("local-regional", "lived") else
             "specialist" if a.get("tier") in ("specialist", "domain") else
             a.get("tier", "unknown"))
            for a in cluster
        ))

        # Domains this force touches
        all_domains = Counter()
        for a in cluster:
            for d in a.get("domains", []):
                all_domains[d] += 1
        top_domains = [domain_labels.get(d, d) for d, _ in all_domains.most_common(4)]

        # Extract the structural force label
        force_tags = Counter(normalize_force_tag(a.get("force_tag", "")) for a in cluster if a.get("force_tag"))
        primary_force = force_tags.most_common(1)[0][0] if force_tags else ""

        # All force tags in this cluster (shows the breadth)
        all_forces = [tag for tag, _ in force_tags.most_common(5) if tag]

        # Sort articles: prefer those with connection insights, then by tier
        tier_order = {"national": 0, "international": 1, "local-regional": 2,
                      "specialist": 3, "explainer": 4, "analysis": 5}
        sorted_arts = sorted(cluster,
                             key=lambda a: (0 if a.get("connection") else 1,
                                           tier_order.get(a.get("tier", ""), 9)))

        # Headline = best connection insight (explanatory), NOT an article title
        # If we have a connection insight, use it. Otherwise synthesize from force + domains.
        best_conn = next((a.get("connection", "") for a in sorted_arts if a.get("connection")), "")
        if best_conn:
            lead_title = best_conn
        else:
            # Synthesize: "Force at the intersection of Domain1 and Domain2"
            lead_title = f"{primary_force.title()} across {', '.join(top_domains[:3])}" if primary_force else sorted_arts[0]["title"] if sorted_arts else ""

        # Collect connection insights (the gold)
        connections = []
        seen_connections = set()
        for a in cluster:
            conn = a.get("connection", "")
            if conn and conn not in seen_connections:
                connections.append({
                    "text": conn,
                    "source": a["source"],
                    "title": a["title"][:80],
                    "domains": a.get("domains", []),
                    "context": SOURCE_CONTEXT.get(a["source"], ""),
                })
                seen_connections.add(conn)

        # How different tiers frame it
        tier_framing = {}
        for tier_name in ["national", "international", "local-regional", "specialist", "analysis"]:
            tier_arts = [a for a in cluster
                         if a.get("tier") == tier_name or
                         (tier_name == "local-regional" and a.get("tier") in ("local-regional", "lived")) or
                         (tier_name == "specialist" and a.get("tier") in ("specialist", "domain"))]
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
                    "connection": a.get("connection", ""),
                    "force_tag": a.get("force_tag", ""),
                })

        stories.append({
            "headline": lead_title,
            "structural_force": primary_force,
            "all_forces": all_forces,
            "source_count": len(sources),
            "tier_count": len(tiers),
            "tiers": tiers,
            "domains": top_domains,
            "domain_keys": [d for d, _ in all_domains.most_common(4)],
            "article_count": len(cluster),
            "connections": connections[:5],  # Top 5 connection insights
            "tier_framing": tier_framing,
            "articles": sample_articles,
        })

    return stories


def _load_source_tiers():
    """Load source tier data from data/sources.json."""
    if SOURCES_FILE.exists():
        with open(SOURCES_FILE) as f:
            sources = json.load(f)
        return {name: entry.get("tier", "") for name, entry in sources.items()}
    return {}

_SOURCE_TIERS = _load_source_tiers()


def analyze_what_connects(articles):
    """
    Find stories where sources from across different tiers
    converge on the same structural force.
    A story is "bridging" if it appears across 3+ different source tiers.
    """
    clusters = cluster_by_structural_force(articles)
    bridging = []

    for cluster in clusters:
        tier_buckets = defaultdict(set)
        for a in cluster:
            src = a["source"]
            tier = _SOURCE_TIERS.get(src, a.get("tier", ""))
            if tier:
                tier_buckets[tier].add(src)

        tier_count = len(tier_buckets)
        if tier_count >= 3 and sum(len(v) for v in tier_buckets.values()) >= 4:
            force_tags = Counter(normalize_force_tag(a.get("force_tag", ""))
                               for a in cluster if a.get("force_tag"))
            primary_force = force_tags.most_common(1)[0][0] if force_tags else ""

            lead = sorted(cluster, key=lambda a: (0 if a.get("connection") else 1))[0]
            tier_breakdown = {tier: list(sources)[:4] for tier, sources in tier_buckets.items()}
            bridging.append({
                "headline": lead["title"][:120],
                "structural_force": primary_force,
                "total_sources": len(set(a["source"] for a in cluster)),
                "spectrum_segments": tier_count,
                "tier_breakdown": tier_breakdown,
                "article_count": len(cluster),
                "domains": [d for d, _ in Counter(
                    d for a in cluster for d in a.get("domains", [])
                ).most_common(3)],
                "sample_connection": lead.get("connection", ""),
            })

    bridging.sort(key=lambda x: (x["spectrum_segments"], x["total_sources"]),
                  reverse=True)
    return bridging[:8]


def analyze_structural_forces_map(articles):
    """
    Build a map of ALL structural forces detected today and how they relate.
    This is the high-level "what's actually happening" view.

    Groups individual force_tags into force families, counts how many articles
    and domains each force family touches, and identifies which forces are
    connected (share articles or domains).
    """
    domain_labels = get_domain_labels()

    # Collect all force tags with their articles
    force_articles = defaultdict(list)
    for a in articles:
        tag = a.get("force_tag", "")
        if tag and a.get("domains"):
            force_articles[normalize_force_tag(tag)].append(a)

    # Build force families by merging similar tags
    families = []
    used = set()
    sorted_tags = sorted(force_articles.keys(), key=lambda t: len(force_articles[t]), reverse=True)

    for tag in sorted_tags:
        if tag in used:
            continue
        family_articles = list(force_articles[tag])
        family_tags = [tag]
        used.add(tag)

        for other in sorted_tags:
            if other in used:
                continue
            if compute_force_similarity(tag, other) >= 0.35:
                family_articles.extend(force_articles[other])
                family_tags.append(other)
                used.add(other)

        if len(family_articles) >= 2:
            domains = set()
            for a in family_articles:
                for d in a.get("domains", []):
                    domains.add(d)

            families.append({
                "force": tag,
                "related_forces": family_tags[1:] if len(family_tags) > 1 else [],
                "article_count": len(family_articles),
                "source_count": len(set(a["source"] for a in family_articles)),
                "domains": [domain_labels.get(d, d) for d in sorted(domains)],
                "domain_keys": sorted(domains),
                "sample_title": family_articles[0]["title"][:100],
            })

    families.sort(key=lambda f: f["article_count"] * len(f["domain_keys"]), reverse=True)
    return families[:25]


def analyze_cooperation_stories(articles):
    """
    The Seventh Question: Where are people being decent, and why is that
    not the headline?

    This surfaces articles where the AI classification detected cooperation,
    mutual aid, community response, institutional integrity, or cross-group
    solidarity. These are the stories the current information architecture
    is structurally incapable of conveying.

    Groups cooperation stories by type and connects them to the structural
    forces they exist within, because cooperation doesn't happen in a vacuum.
    It happens in response to pressure, inside crisis, alongside conflict.
    The darkness is real and the goodness is real and Signal Board shows both.
    """
    domain_labels = get_domain_labels()

    # Filter to articles with cooperation signals
    coop_articles = [a for a in articles if a.get("cooperation")]

    if not coop_articles:
        return {
            "total_cooperation_stories": 0,
            "cooperation_rate": 0,
            "by_type": [],
            "by_force": [],
            "highlights": [],
            "coverage_gap": [],
        }

    total = len(articles)
    coop_count = len(coop_articles)
    coop_rate = round(coop_count / max(total, 1) * 100)

    # Group by cooperation type
    type_groups = defaultdict(list)
    for a in coop_articles:
        ctype = a.get("cooperation_type", "unspecified").strip().lower()
        if ctype:
            type_groups[ctype].append(a)

    by_type = []
    for ctype, arts in sorted(type_groups.items(), key=lambda x: len(x[1]), reverse=True):
        sources = list(set(a["source"] for a in arts))
        domains = Counter()
        for a in arts:
            for d in a.get("domains", []):
                domains[d] += 1

        by_type.append({
            "type": ctype,
            "count": len(arts),
            "sources": sources[:5],
            "domains": [domain_labels.get(d, d) for d, _ in domains.most_common(3)],
            "sample": {
                "title": arts[0]["title"][:120],
                "source": arts[0]["source"],
                "url": arts[0].get("url", ""),
                "connection": arts[0].get("connection", ""),
            },
        })

    # Group by structural force (cooperation within crisis)
    force_coop = defaultdict(list)
    for a in coop_articles:
        tag = a.get("force_tag", "")
        if tag:
            force_coop[normalize_force_tag(tag)].append(a)

    by_force = []
    for force, arts in sorted(force_coop.items(), key=lambda x: len(x[1]), reverse=True)[:8]:
        coop_types = list(set(a.get("cooperation_type", "") for a in arts if a.get("cooperation_type")))
        by_force.append({
            "force": force,
            "cooperation_count": len(arts),
            "cooperation_types": coop_types[:3],
            "sample_title": arts[0]["title"][:120],
            "sample_source": arts[0]["source"],
        })

    # Highlight stories: cooperation stories from tiers that typically
    # get less attention (local-regional, specialist, solutions)
    # Deduplicated by source name — keep the first appearance of each source.
    highlights = []
    highlight_sources_seen = set()
    highlight_tiers = {"local-regional", "specialist", "solutions"}
    for a in coop_articles:
        tier = a.get("tier", "")
        src = a["source"]
        if src in highlight_sources_seen:
            continue
        if tier in highlight_tiers or any(alias == tier for alias in ["lived", "domain"]):
            highlight_sources_seen.add(src)
            highlights.append({
                "title": a["title"][:120],
                "source": src,
                "url": a.get("url", ""),
                "tier": tier,
                "cooperation_type": a.get("cooperation_type", ""),
                "force_tag": a.get("force_tag", ""),
                "connection": a.get("connection", ""),
                "context": SOURCE_CONTEXT.get(src, ""),
            })

    # Coverage gap: forces with MANY articles but ZERO cooperation signals
    # These are the places where the architecture might be hiding goodness
    force_total = defaultdict(int)
    force_coop_count = defaultdict(int)
    for a in articles:
        tag = a.get("force_tag", "")
        if tag:
            nt = normalize_force_tag(tag)
            force_total[nt] += 1
            if a.get("cooperation"):
                force_coop_count[nt] += 1

    coverage_gap = []
    for force, total_count in sorted(force_total.items(), key=lambda x: x[1], reverse=True):
        if total_count >= 5 and force_coop_count.get(force, 0) == 0:
            coverage_gap.append({
                "force": force,
                "article_count": total_count,
                "note": "No cooperation signals detected. Is goodness happening here that the coverage isn't showing?",
            })

    # Build a complete source → URL map for all cooperation articles.
    # The synthesis model may reference any cooperation source, not just the top 8 highlights.
    # This map lets the template link every outlet the synthesis mentions.
    all_source_urls = {}
    for a in coop_articles:
        src = a.get("source", "")
        url = a.get("url", "")
        if src and url and src not in all_source_urls:
            all_source_urls[src] = url

    return {
        "total_cooperation_stories": coop_count,
        "cooperation_rate": coop_rate,
        "by_type": by_type[:10],
        "by_force": by_force,
        "highlights": highlights[:8],
        "all_source_urls": all_source_urls,
        "coverage_gap": coverage_gap[:5],
    }


def analyze_local_regional_exclusive(articles):
    """
    Find stories that local-regional/specialist sources cover but national
    outlets do not. These are the gaps in mainstream coverage.
    """
    national_keywords = set()
    for a in articles:
        if a.get("tier") == "national":
            for w in re.findall(r'[a-z]{6,}', a.get("title", "").lower()):
                national_keywords.add(w)

    local_regional_stories = []
    for a in articles:
        if a.get("tier") not in ("local-regional", "lived", "specialist", "domain"):
            continue
        title_words = set(re.findall(r'[a-z]{6,}', a.get("title", "").lower()))
        if not title_words:
            continue
        overlap = len(title_words & national_keywords) / len(title_words)
        if overlap < 0.35:
            text = a.get("text", "") or a.get("summary", "")
            local_regional_stories.append({
                "title": a["title"][:120],
                "source": a["source"],
                "url": a.get("url", ""),
                "tier": a.get("tier", ""),
                "text_preview": text[:250] if text else "",
                "domains": a.get("domains", []),
                "connection": a.get("connection", ""),
                "force_tag": a.get("force_tag", ""),
                "context": SOURCE_CONTEXT.get(a["source"], ""),
            })

    seen = set()
    unique = []
    for s in local_regional_stories:
        if s["source"] not in seen:
            seen.add(s["source"])
            unique.append(s)

    return unique[:12]


def analyze_domain_collisions(articles, history):
    """
    Track which domain pairs are most active and whether they're
    rising or falling vs. the 7-day average. Now enriched with
    AI connection insights.
    """
    domain_labels = get_domain_labels()

    pair_today = defaultdict(int)
    pair_articles = defaultdict(list)
    pair_connections = defaultdict(list)

    for a in articles:
        doms = sorted(a.get("domains", []))
        for i in range(len(doms)):
            for j in range(i + 1, len(doms)):
                pair = (doms[i], doms[j])
                pair_today[pair] += 1
                if len(pair_articles[pair]) < 3:
                    pair_articles[pair].append({
                        "title": a["title"][:80],
                        "source": a["source"],
                        "url": a.get("url", ""),
                    })
                conn = a.get("connection", "")
                if conn and len(pair_connections[pair]) < 2:
                    pair_connections[pair].append(conn)

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

    # Domain pair explanations
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
        'climate+governance': 'Environmental regulation and climate policy implementation',
        'climate+labor': 'Energy transition affecting workers and communities',
        'climate+legal': 'Environmental lawsuits and climate litigation',
        'climate+security': 'Environmental change creating security challenges',
        'domestic_politics+economics': 'Economic conditions shaping political debate',
        'domestic_politics+governance': 'Political conflict over how government agencies operate',
        'domestic_politics+information': 'How political information reaches voters',
        'domestic_politics+legal': 'Political disputes reaching the courts',
        'domestic_politics+security': 'Defense and public safety as political issues',
        'economics+geopolitics': 'Trade, sanctions, and global economic competition',
        'economics+governance': 'Tax policy, trade agreements, and government spending',
        'economics+labor': 'Jobs, wages, and whether economic growth reaches workers',
        'economics+legal': 'Antitrust enforcement, financial regulation, and corporate law',
        'economics+security': 'Military spending and conflict affecting markets',
        'geopolitics+governance': 'International diplomacy and alliance management',
        'geopolitics+legal': 'International law, treaties, and war crimes',
        'geopolitics+security': 'Military tensions between nations',
        'governance+information': 'Government regulation of media and information platforms',
        'governance+labor': 'Workplace regulation and labor law enforcement',
        'governance+legal': 'Government actions challenged or upheld in courts',
        'governance+security': 'Defense policy and military strategy',
        'information+legal': 'Free speech, media law, and platform regulation',
        'labor+legal': 'Employment law, worker rights cases, and workplace litigation',
    }

    threads = []
    for pair, count in sorted(pair_today.items(), key=lambda x: x[1], reverse=True):
        d1, d2 = pair
        pair_key = "+".join(sorted([d1, d2]))
        explanation = PAIR_EXPLANATIONS.get(pair_key,
            f"{domain_labels.get(d1, d1)} and {domain_labels.get(d2, d2)}")

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
            "label": f"{domain_labels.get(d1, d1)} + {domain_labels.get(d2, d2)}",
            "explanation": explanation,
            "today_count": count,
            "trend": trend,
            "sample_articles": pair_articles[pair],
            "ai_connections": pair_connections.get(pair, []),
        })

    return threads[:15]


def analyze_source_spectrum(articles):
    """Count articles by source tier — all tiers, no gaps."""
    from collections import Counter
    tier_counts = Counter(a.get("tier", "unknown") for a in articles)
    # Merge legacy aliases
    if "domain" in tier_counts:
        tier_counts["specialist"] += tier_counts.pop("domain")
    if "lived" in tier_counts:
        tier_counts["local-regional"] += tier_counts.pop("lived")
    # Drop unknowns
    tier_counts.pop("unknown", None)
    tier_counts.pop("", None)
    return dict(tier_counts.most_common())


def generate_questions_people_are_asking(articles):
    """
    Based on the structural forces and domain collisions, generate
    the questions regular people would likely have.
    """
    domain_labels = get_domain_labels()

    pair_counts = Counter()
    for a in articles:
        doms = sorted(a.get("domains", []))
        for i in range(len(doms)):
            for j in range(i + 1, len(doms)):
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
        'ai+information': "How is AI changing what information you see and trust?",
        'governance+information': "How is the government shaping what information reaches you?",
        'ai+governance': "How are governments trying to regulate AI, and is it working?",
        'labor+economics': "Are workers benefiting from economic growth?",
    }

    questions = []
    for (d1, d2), count in pair_counts.most_common(12):
        pair_key = "+".join(sorted([d1, d2]))
        q = PAIR_QUESTIONS.get(pair_key)
        if q and count >= 2:
            relevant = [a for a in articles
                        if d1 in a.get("domains", []) and d2 in a.get("domains", [])]
            source_tiers = defaultdict(list)
            for a in relevant[:10]:
                tier = a.get("tier", "")
                if tier in ("local-regional", "lived"): tier = "local-regional"
                if tier in ("specialist", "domain"): tier = "specialist"
                if a["source"] not in [s["source"] for s in source_tiers[tier]]:
                    source_tiers[tier].append({
                        "source": a["source"],
                        "title": a["title"][:100],
                        "url": a.get("url", ""),
                        "context": SOURCE_CONTEXT.get(a["source"], ""),
                        "connection": a.get("connection", ""),
                    })

            # Get AI connection insights for this pair
            pair_connections = [a.get("connection", "") for a in relevant if a.get("connection")]

            questions.append({
                "question": q,
                "article_count": count,
                "domains": [domain_labels.get(d1, d1), domain_labels.get(d2, d2)],
                "sources_by_tier": {k: v[:2] for k, v in source_tiers.items()},
                "ai_insights": pair_connections[:3],
            })

    return questions[:8]


# ---------------------------------------------------------------------------
# MAIN ANALYSIS
# ---------------------------------------------------------------------------

def build_temporal_context(today_articles, analysis_date):
    """
    Compare today's data to yesterday's to surface what's shifting,
    surging, or emerging. This gives readers temporal orientation —
    'geopolitics coverage nearly tripled today' is more meaningful
    than a raw number.
    """
    from datetime import timedelta
    domain_labels = get_domain_labels()

    # Load all articles to find yesterday
    all_articles = load_articles()
    try:
        today_dt = datetime.strptime(analysis_date, "%Y-%m-%d")
        yesterday_str = (today_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    except ValueError:
        return {}

    yesterday_articles = [a for a in all_articles if a.get("date") == yesterday_str]
    if not yesterday_articles:
        return {"has_yesterday": False}

    # Domain comparison
    y_domains = Counter()
    t_domains = Counter()
    for a in yesterday_articles:
        for d in (a.get("domains") or []):
            y_domains[d] += 1
    for a in today_articles:
        for d in (a.get("domains") or []):
            t_domains[d] += 1

    domain_shifts = []
    for key in set(list(y_domains.keys()) + list(t_domains.keys())):
        y_count = y_domains.get(key, 0)
        t_count = t_domains.get(key, 0)
        if y_count == 0:
            change_pct = 100
        else:
            change_pct = round((t_count - y_count) / y_count * 100)
        label = domain_labels.get(key, key)
        domain_shifts.append({
            "domain": key,
            "label": label,
            "yesterday": y_count,
            "today": t_count,
            "change_pct": change_pct,
        })

    # Sort by absolute change magnitude
    domain_shifts.sort(key=lambda x: abs(x["change_pct"]), reverse=True)

    # Volume change
    y_total = len(yesterday_articles)
    t_total = len(today_articles)
    volume_change_pct = round((t_total - y_total) / max(y_total, 1) * 100)

    # Biggest surges and drops (top 3 each)
    surges = [d for d in domain_shifts if d["change_pct"] > 20][:3]
    drops = [d for d in domain_shifts if d["change_pct"] < -20][:3]

    # ── Force tag comparison (requires AI classification on both days) ──
    y_forces = Counter(a.get("force_tag", "") for a in yesterday_articles if a.get("force_tag"))
    t_forces = Counter(a.get("force_tag", "") for a in today_articles if a.get("force_tag"))

    # Cluster similar force tags using same similarity as main analysis
    y_force_clusters = cluster_by_structural_force(
        [a for a in yesterday_articles if a.get("force_tag")]
    )
    t_force_clusters = cluster_by_structural_force(
        [a for a in today_articles if a.get("force_tag")]
    )

    # cluster_by_structural_force returns list of lists — convert to dict
    # keyed by the most common force_tag in each cluster
    def clusters_to_dict(cluster_list):
        result = {}
        for group in cluster_list:
            tags = Counter(a.get("force_tag", "") for a in group if a.get("force_tag"))
            label = tags.most_common(1)[0][0] if tags else "unknown"
            label = normalize_force_tag(label)
            result[label] = group
        return result

    y_force_dict = clusters_to_dict(y_force_clusters)
    t_force_dict = clusters_to_dict(t_force_clusters)

    # Build named cluster summaries for comparison
    def summarize_clusters(clusters_dict):
        result = {}
        for label, arts in clusters_dict.items():
            dom_counts = Counter()
            for a in arts:
                for d in (a.get("domains") or []):
                    dom_counts[d] += 1
            top_domains = [d for d, _ in dom_counts.most_common(3)]
            conns = [a.get("connection", "") for a in arts if a.get("connection")]
            result[label] = {
                "count": len(arts),
                "domains": top_domains,
                "sample_insight": conns[0] if conns else "",
            }
        return result

    y_cluster_summary = summarize_clusters(y_force_dict)
    t_cluster_summary = summarize_clusters(t_force_dict)

    # Persisting forces (appeared both days) and new forces (only today)
    shared_forces = set(y_cluster_summary.keys()) & set(t_cluster_summary.keys())
    persisting = []
    for f in shared_forces:
        persisting.append({
            "force": f,
            "yesterday_count": y_cluster_summary[f]["count"],
            "today_count": t_cluster_summary[f]["count"],
            "domains": t_cluster_summary[f]["domains"],
            "insight": t_cluster_summary[f]["sample_insight"],
        })
    persisting.sort(key=lambda x: x["today_count"], reverse=True)

    new_forces = []
    for f in set(t_cluster_summary.keys()) - shared_forces:
        if t_cluster_summary[f]["count"] >= 3:  # only meaningful clusters
            new_forces.append({
                "force": f,
                "count": t_cluster_summary[f]["count"],
                "domains": t_cluster_summary[f]["domains"],
                "insight": t_cluster_summary[f]["sample_insight"],
            })
    new_forces.sort(key=lambda x: x["count"], reverse=True)

    faded_forces = []
    for f in set(y_cluster_summary.keys()) - set(t_cluster_summary.keys()):
        if y_cluster_summary[f]["count"] >= 3:
            faded_forces.append({
                "force": f,
                "count": y_cluster_summary[f]["count"],
                "domains": y_cluster_summary[f]["domains"],
            })
    faded_forces.sort(key=lambda x: x["count"], reverse=True)

    return {
        "has_yesterday": True,
        "yesterday_date": yesterday_str,
        "yesterday_total": y_total,
        "today_total": t_total,
        "volume_change_pct": volume_change_pct,
        "domain_shifts": domain_shifts,
        "surges": surges,
        "drops": drops,
        "persisting_forces": persisting[:8],
        "new_forces": new_forces[:8],
        "faded_forces": faded_forces[:5],
        "yesterday_classified": sum(1 for a in yesterday_articles if a.get("force_tag")),
        "today_classified": sum(1 for a in today_articles if a.get("force_tag")),
    }


def generate_daily_analysis(articles, analysis_date, history):
    domain_labels = get_domain_labels()
    unique_sources = set(a.get("source") for a in articles)
    cross_domain = sum(1 for a in articles if a.get("cross_domain", False))
    ai_classified = sum(1 for a in articles if a.get("force_tag"))
    has_connection = sum(1 for a in articles if a.get("connection"))

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
    structural_forces = analyze_structural_forces_map(articles)
    what_connects = analyze_what_connects(articles)
    local_regional_exclusive = analyze_local_regional_exclusive(articles)
    active_threads = analyze_domain_collisions(articles, history)
    source_spectrum = analyze_source_spectrum(articles)
    questions = generate_questions_people_are_asking(articles)

    # ── Event-level divergence for the Gap section ──
    # Exclude the Thread's force so Gap tells a different story
    thread_force = None
    if top_stories:
        scored = sorted(
            top_stories,
            key=lambda s: (s.get("tier_count", 1) * 100 + s.get("source_count", 0)),
            reverse=True
        )
        thread_force = scored[0].get("structural_force", "")
    event_divergence = analyze_event_divergence(articles, exclude_force=thread_force)

    # ── Temporal context: compare today vs yesterday ──
    temporal_context = build_temporal_context(articles, analysis_date)

    # ── Article URL index: outlet → URL for every source that published today ──
    # Used as a fallback by the frontend when synthesis text names an outlet
    # that is not in the section-specific article array.
    article_url_index = {}
    for a in articles:
        src = a.get("source", "")
        url = a.get("url", "")
        if src and url and src not in article_url_index:
            article_url_index[src] = url

    return {
        "date": analysis_date,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_stories": len(articles),
            "sources_reporting": len(unique_sources),
            "cross_domain": cross_domain,
            "cross_domain_pct": round(cross_domain / max(len(articles), 1) * 100),
            "ai_classified": ai_classified,
            "ai_classified_pct": round(ai_classified / max(len(articles), 1) * 100),
            "connection_insights": has_connection,
            "top_domain": top_domain,
            "domain_distribution": {
                domain_labels.get(d, d): count
                for d, count in dom_counts.most_common()
            },
        },
        "temporal_context": temporal_context,
        "top_stories": top_stories,
        "structural_forces": structural_forces,
        "what_connects": what_connects,
        "local_regional_exclusive": local_regional_exclusive,
        "active_threads": active_threads,
        "source_spectrum": source_spectrum,
        "questions": questions,
        "article_url_index": article_url_index,
        "event_divergence": event_divergence,
        # Backward compat
        "narrative_divergence": [
            {
                "topic": s["domains"][0] + " + " + s["domains"][1] if len(s["domains"]) >= 2 else s["domains"][0] if s["domains"] else "",
                "theme": s["headline"],
                "source_count": s["source_count"],
                "structural_force": s.get("structural_force", ""),
                "articles": s["articles"],
            }
            for s in top_stories[:3]
        ],
    }


def print_summary(analysis):
    s = analysis["summary"]
    print("\n" + "=" * 60)
    print("  SIGNAL BOARD — DAILY STRUCTURAL ANALYSIS")
    print("=" * 60)
    print(f"Date:                  {analysis['date']}")
    print(f"Total stories:         {s['total_stories']}")
    print(f"Sources reporting:     {s['sources_reporting']}")
    print(f"AI classified:         {s['ai_classified']} ({s['ai_classified_pct']}%)")
    print(f"Connection insights:   {s['connection_insights']}")
    print(f"Cross-domain:          {s['cross_domain']} ({s['cross_domain_pct']}%)")
    print(f"Top domain:            {s['top_domain']}")

    if analysis.get("top_stories"):
        print(f"\n--- TOP STRUCTURAL FORCES ({len(analysis['top_stories'])} found) ---")
        for i, st in enumerate(analysis["top_stories"][:8], 1):
            force = st.get("structural_force", "")
            domains = ", ".join(st["domains"][:3])
            print(f"\n  {i}. [{force.upper()}]")
            print(f"     {st['headline'][:80]}")
            print(f"     {st['source_count']} sources | {st['article_count']} articles | {domains}")
            if st.get("connections"):
                print(f"     Insight: {st['connections'][0]['text']}")

    if analysis.get("structural_forces"):
        print(f"\n--- STRUCTURAL FORCES MAP ({len(analysis['structural_forces'])} forces) ---")
        for f in analysis["structural_forces"][:10]:
            print(f"  • {f['force']:40s}  {f['article_count']:3d} articles  {f['source_count']:2d} sources  [{', '.join(f['domains'][:3])}]")

    if analysis.get("what_connects"):
        print(f"\n--- BRIDGING STORIES ({len(analysis['what_connects'])} found) ---")
        for i, b in enumerate(analysis["what_connects"][:3], 1):
            print(f"  {i}. {b['headline'][:60]}")
            print(f"     Force: {b.get('structural_force', 'n/a')} | {b['spectrum_segments']}/4 segments | {b['total_sources']} sources")

    local_excl = analysis.get("local_regional_exclusive", [])
    if local_excl:
        print(f"\n--- STRUCTURAL COVERAGE GAP ({len(local_excl)} stories only in local/regional/specialist) ---")
        for l in local_excl[:5]:
            print(f"  [{l.get('tier','')}] {l['source']}: {l.get('title','')[:70]}")

    if analysis.get("questions"):
        print(f"\n--- QUESTIONS PEOPLE ARE ASKING ---")
        for q in analysis["questions"][:5]:
            print(f"  ? {q['question']} ({q['article_count']} articles)")
            if q.get("ai_insights"):
                print(f"    → {q['ai_insights'][0]}")

    print("\n" + "=" * 60)


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
