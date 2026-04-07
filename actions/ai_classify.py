"""
AI-powered article classification for Signal Board.

Uses the Anthropic API (Claude) to classify articles into domains
and generate plain-language explanations of structural connections
between domains. BATCHED: sends 10-15 articles per API call to
maximize coverage and stay within rate limits.

Falls back to keyword-based tagging if the API is unavailable.

Cost estimate at ~1000 articles/day with Claude Haiku (batched):
  - ~70 API calls instead of ~1000
  - ~$0.50/day = ~$15/month
"""

import os
import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

# Try to import anthropic; if not installed, AI classification won't work
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

DOMAIN_DESCRIPTIONS = {
    "ai": "AI — Artificial intelligence, machine learning, automation, algorithms, AI regulation, chatbots, deepfakes, semiconductors",
    "labor": "Labor — Jobs, workers, wages, unions, layoffs, gig economy, working conditions, employment law",
    "governance": "Governance — Government agencies, executive orders, federal/state policy, public services, regulatory actions, FEMA, EPA, FDA, USDA",
    "information": "Information — Media, journalism, social platforms, misinformation, data privacy, surveillance, tech companies, content moderation",
    "economics": "Economics — Markets, trade, inflation, GDP, interest rates, prices, corporate earnings, supply chains, housing, debt",
    "climate": "Climate — Environment, energy, emissions, extreme weather, fossil fuels, renewables, pollution, water, agriculture, biodiversity",
    "security": "Security — Military, defense, cybersecurity, terrorism, policing, intelligence agencies, weapons, national security",
    "geopolitics": "Geopolitics — International relations, diplomacy, foreign policy, NATO, UN, sanctions, wars, treaties between nations",
    "domestic_politics": "Politics — U.S. political parties, elections, campaigns, Congress, partisan conflicts, voting, political strategy",
    "legal": "Legal — Courts, judges, lawsuits, legislation, constitutional law, enforcement, DOJ, civil rights, regulations, executive orders challenged in court",
}

# Canonical force vocabulary — constrained list that clusters cleanly.
# The model MUST choose one of these. Free-form tags produce unmergeable noise.
FORCE_VOCABULARY = """
Pick the single best match from this list. If none fits well, pick the closest.

Military & Conflict:
- military escalation          (armed conflict intensifying, strikes, casualties)
- military de-escalation       (ceasefire, withdrawal, peace talks succeeding)
- coercive diplomacy           (threat of force used to extract political concession)
- proxy conflict               (nations fighting through third-party actors)
- civilian harm in conflict    (non-combatants killed, displaced, or economically harmed by war)

Economics & Trade:
- trade weaponization          (tariffs, sanctions, or export controls used as geopolitical leverage)
- supply chain disruption      (war, policy, or disaster breaking production and delivery)
- market volatility            (prices, currencies, or asset values swinging sharply)
- regulatory capture           (industry influencing the rules meant to govern it)
- automation displacing workers (AI or robots replacing human jobs at scale)
- media consolidation          (ownership concentration reducing independent journalism)

Governance & Power:
- democratic erosion           (institutions, courts, or elections undermined by executive power)
- democratic resilience        (institutions, courts, or civil society pushing back successfully)
- electoral competition        (election campaigns, polls, voting access, electoral outcomes)
- institutional accountability (officials, agencies, or corporations held to account)
- executive overreach          (executive branch acting beyond legal authority)
- information manipulation     (state or platform actors distorting public knowledge)

Energy & Resources:
- energy weaponization         (oil, gas, or electricity used as geopolitical leverage)
- resource chokepoint          (control of a critical supply route or extraction site)
- climate-driven disruption    (extreme weather, drought, or emissions affecting economy or policy)
- food security threat         (agricultural supply disrupted by conflict, climate, or policy)

Technology & Society:
- platform power               (tech platforms controlling access to information or commerce)
- AI governance gap            (AI deployed faster than regulation or safety frameworks)
- surveillance expansion       (governments or companies extending monitoring of populations)

Labor & Community:
- labor precarity              (workers losing security through gig work, layoffs, or automation)
- community organizing         (residents, workers, or communities building collective power)
- mutual aid                   (people providing direct support outside formal institutions)

Other:
- geopolitical realignment     (alliances, partnerships, or spheres of influence shifting)
- public health pressure       (disease, addiction, or healthcare costs straining communities)
- other                        (use only if genuinely none of the above fit)
"""

# System prompt for batched classification
BATCH_SYSTEM_PROMPT = """You classify news articles for Signal Board.

You will receive a numbered list of articles (title + summary). For EACH article:

1. DOMAINS: Assign one or more domain tags from the list below. Only tag domains genuinely central to the article.
   - Consumer product reviews, lifestyle, recipes, celebrity gossip, entertainment, sports with no policy angle: return empty domains list.

2. CONNECTION: If 2+ domains are tagged, write ONE sentence (max 20 words) explaining the STRUCTURAL mechanism connecting them — not just naming the topics, but WHY this specific story sits at their intersection.

3. FORCE_TAG: Choose the single best-matching structural force from the vocabulary below. This is the underlying pattern driving the story, not the surface topic. You MUST pick from the provided list — do not invent new labels.

Domains:
{domains}

Force vocabulary:
{forces}

Rules:
- force_tag must exactly match one of the labels in the force vocabulary (e.g. "military escalation", "regulatory capture")
- connection sentence explains mechanism, not topic names
- Be precise. If uncertain between two forces, pick the one most central to WHY this story exists today.

Respond ONLY with a valid JSON array, one object per article in order:
[
  {{"id": 1, "domains": ["domain_key", ...], "connection": "sentence or empty string", "force_tag": "force label from vocabulary"}},
  ...
]"""

# Single-article fallback prompt (for stragglers)
SINGLE_SYSTEM_PROMPT = """You classify news articles for Signal Board.

Given an article's title and summary:
1. Assign one or more domain tags from the list below
2. If 2+ domains, write ONE sentence (max 20 words) explaining the structural mechanism connecting them
3. Assign a force_tag — pick from the force vocabulary below, exact match required

Domains:
{domains}

Force vocabulary:
{forces}

Rules:
- Only tag domains genuinely central to the article
- Consumer reviews, lifestyle, recipes, celebrity gossip, entertainment, sports: empty domains
- force_tag must exactly match a label in the force vocabulary

Respond ONLY with valid JSON:
{{"domains": ["domain_key", ...], "connection": "sentence or empty string", "force_tag": "force label from vocabulary"}}"""


def get_client():
    """Get Anthropic client if available."""
    if not HAS_ANTHROPIC or not ANTHROPIC_API_KEY:
        return None
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def parse_ai_response(text: str) -> any:
    """Parse JSON from AI response, handling markdown fences and common issues."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()
    # Strip leading 'json' label
    if text.startswith("json"):
        text = text[4:].strip()
    return json.loads(text)


# Canonical force labels extracted from FORCE_VOCABULARY
CANONICAL_FORCES = [
    "military escalation", "military de-escalation", "coercive diplomacy",
    "proxy conflict", "civilian harm in conflict",
    "trade weaponization", "supply chain disruption", "market volatility",
    "regulatory capture", "automation displacing workers", "media consolidation",
    "democratic erosion", "democratic resilience", "electoral competition",
    "institutional accountability", "executive overreach", "information manipulation",
    "energy weaponization", "resource chokepoint", "climate-driven disruption",
    "food security threat",
    "platform power", "AI governance gap", "surveillance expansion",
    "labor precarity", "community organizing", "mutual aid",
    "geopolitical realignment", "public health pressure", "other",
]


def validate_force_tag(raw_tag: str) -> str:
    """Snap a model-returned force tag to the closest canonical label."""
    if not raw_tag:
        return ""
    tag_lower = raw_tag.lower().strip()
    # Exact match first
    if tag_lower in CANONICAL_FORCES:
        return tag_lower
    # Partial match — find canonical force with most word overlap
    tag_words = set(tag_lower.split())
    best, best_score = "", 0
    for canon in CANONICAL_FORCES:
        canon_words = set(canon.split())
        score = len(tag_words & canon_words) / max(len(tag_words | canon_words), 1)
        if score > best_score:
            best, best_score = canon, score
    # Accept if reasonable overlap; otherwise "other"
    return best if best_score >= 0.3 else "other"


def validate_domains(raw_domains: list) -> list:
    """Convert AI-returned domain names/labels to valid domain keys."""
    valid_domains = list(DOMAIN_DESCRIPTIONS.keys())
    label_to_key = {}
    for k, v in DOMAIN_DESCRIPTIONS.items():
        label = v.split(" — ")[0].strip().lower()
        label_to_key[label] = k
        label_to_key[k] = k

    domains = []
    for d in raw_domains:
        dl = d.lower().strip()
        if dl in label_to_key:
            domains.append(label_to_key[dl])
        elif dl.replace(" ", "_") in valid_domains:
            domains.append(dl.replace(" ", "_"))
    return list(dict.fromkeys(domains))  # dedupe preserving order


def classify_batch_chunk(articles_chunk: list[dict], chunk_index: int, client) -> list[dict]:
    """
    Classify a chunk of 10-15 articles in a single API call.
    Returns list of classification results aligned with input order.
    """
    domain_list = "\n".join(f"- {v}" for v in DOMAIN_DESCRIPTIONS.values())
    system = BATCH_SYSTEM_PROMPT.format(domains=domain_list, forces=FORCE_VOCABULARY)

    # Build the numbered article list
    lines = []
    for i, a in enumerate(articles_chunk, 1):
        title = a.get("title", "")
        summary = a.get("summary", "") or a.get("text", "")
        lines.append(f"{i}. Title: {title}\n   Summary: {summary[:300]}")

    user_msg = "\n\n".join(lines)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3000,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )

        results = parse_ai_response(response.content[0].text)

        if not isinstance(results, list):
            return [None] * len(articles_chunk)

        # Map results by id (1-indexed)
        result_map = {}
        for r in results:
            rid = r.get("id")
            if rid is not None:
                result_map[int(rid)] = r

        output = []
        for i in range(1, len(articles_chunk) + 1):
            r = result_map.get(i)
            if r:
                domains = validate_domains(r.get("domains", []))
                connection = r.get("connection", "")
                force_tag = validate_force_tag(r.get("force_tag", ""))
                output.append({
                    "domains": domains,
                    "connection": connection if len(domains) > 1 else "",
                    "force_tag": force_tag,
                })
            else:
                output.append(None)

        return output

    except json.JSONDecodeError as e:
        print(f"    Chunk {chunk_index}: JSON parse error — {e}")
        return [None] * len(articles_chunk)
    except Exception as e:
        err = str(e).lower()
        if "rate" in err or "429" in err:
            print(f"    Chunk {chunk_index}: Rate limited, waiting 5s...")
            time.sleep(5)
            # Retry once
            try:
                response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=3000,
                    system=system,
                    messages=[{"role": "user", "content": user_msg}],
                )
                results = parse_ai_response(response.content[0].text)
                if isinstance(results, list):
                    result_map = {}
                    for r in results:
                        rid = r.get("id")
                        if rid is not None:
                            result_map[int(rid)] = r
                    output = []
                    for i in range(1, len(articles_chunk) + 1):
                        r = result_map.get(i)
                        if r:
                            domains = validate_domains(r.get("domains", []))
                            connection = r.get("connection", "")
                            force_tag = validate_force_tag(r.get("force_tag", ""))
                            output.append({
                                "domains": domains,
                                "connection": connection if len(domains) > 1 else "",
                                "force_tag": force_tag,
                            })
                        else:
                            output.append(None)
                    return output
            except Exception:
                pass
        else:
            print(f"    Chunk {chunk_index}: API error — {e}")
        return [None] * len(articles_chunk)


def classify_batch(articles: list[dict], batch_size: int = 12) -> list[dict]:
    """
    Classify articles using batched AI calls (10-15 articles per API call).
    Uses parallel threads for speed.

    Modifies articles in-place, adding 'domains', 'cross_domain', 'connection',
    and 'force_tag' fields. Falls back to keyword tagging for failures.

    Returns the list of articles with updated fields.
    """
    from domains import tag_article  # keyword fallback

    client = get_client()

    if client is None:
        print("  AI classification unavailable (no API key or anthropic not installed)")
        print("  Falling back to keyword-based tagging")
        for a in articles:
            a["domains"] = tag_article(a["title"], a.get("summary", ""), a.get("text", ""))
            a["cross_domain"] = len(a["domains"]) > 1
            a["connection"] = ""
            a["force_tag"] = ""
            a["cooperation"] = False
            a["cooperation_type"] = ""
        return articles

    # Split into chunks
    chunks = []
    for i in range(0, len(articles), batch_size):
        chunks.append(articles[i:i + batch_size])

    total_chunks = len(chunks)
    print(f"  AI classification: {len(articles)} articles in {total_chunks} batches of ~{batch_size}...")

    ai_count = 0
    fallback_count = 0

    # Process chunks with parallel threads (4 concurrent API calls)
    max_workers = 4
    chunk_results = [None] * total_chunks

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for idx, chunk in enumerate(chunks):
            # Stagger submissions slightly to avoid burst rate limits
            future = executor.submit(
                classify_batch_chunk, chunk, idx, client
            )
            futures[future] = idx

        for future in as_completed(futures):
            idx = futures[future]
            try:
                chunk_results[idx] = future.result()
            except Exception as e:
                print(f"    Chunk {idx} failed: {e}")
                chunk_results[idx] = [None] * len(chunks[idx])

            completed = sum(1 for cr in chunk_results if cr is not None)
            if completed % 10 == 0 or completed == total_chunks:
                print(f"    ... {completed}/{total_chunks} batches complete")

    # Apply results to articles
    article_idx = 0
    for chunk_idx, chunk in enumerate(chunks):
        results = chunk_results[chunk_idx] or [None] * len(chunk)
        for i, a in enumerate(chunk):
            result = results[i] if i < len(results) else None
            if result and result.get("domains"):
                a["domains"] = result["domains"]
                a["cross_domain"] = len(result["domains"]) > 1
                a["connection"] = result.get("connection", "")
                a["force_tag"] = result.get("force_tag", "")
                # Cooperation fields removed — too noisy at Haiku cost point
                a.pop("cooperation", None)
                a.pop("cooperation_type", None)
                ai_count += 1
            else:
                # Fallback to keywords
                a["domains"] = tag_article(a["title"], a.get("summary", ""), a.get("text", ""))
                a["cross_domain"] = len(a["domains"]) > 1
                a["connection"] = ""
                a["force_tag"] = ""
                a.pop("cooperation", None)
                a.pop("cooperation_type", None)
                fallback_count += 1
            article_idx += 1

    pct = round(ai_count / max(len(articles), 1) * 100)
    print(f"  AI classified: {ai_count} ({pct}%), keyword fallback: {fallback_count}")
    return articles


# Legacy single-article function (kept for compatibility)
def classify_article(title: str, summary: str, client=None) -> dict:
    """Classify a single article. Use classify_batch for bulk processing."""
    if client is None:
        return None
    domain_list = "\n".join(f"- {v}" for v in DOMAIN_DESCRIPTIONS.values())
    system = SINGLE_SYSTEM_PROMPT.format(domains=domain_list, forces=FORCE_VOCABULARY)
    user_msg = f"Title: {title}\nSummary: {summary[:400] if summary else '(no summary)'}"
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        result = parse_ai_response(response.content[0].text)
        domains = validate_domains(result.get("domains", []))
        connection = result.get("connection", "")
        force_tag = validate_force_tag(result.get("force_tag", ""))
        return {
            "domains": domains,
            "connection": connection if len(domains) > 1 else "",
            "force_tag": force_tag,
        }
    except Exception:
        return None
