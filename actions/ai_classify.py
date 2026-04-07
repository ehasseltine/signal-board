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

# ——————————————————————————————————————————————————————————————————————————————
# SIGNAL BOARD CANONICAL TAXONOMY v1.0
# 15 plain-language labels. Written for a 5th-grade reading level.
# Articles can and should receive MULTIPLE labels — the point is that everything is connected.
# Locked: see GitHub issue #taxonomy-v1
# ——————————————————————————————————————————————————————————————————————————————

DOMAIN_DESCRIPTIONS = {
    "war_and_conflict": (
        "War & Conflict — Fighting, weapons, military operations, airstrikes, casualties, "
        "soldiers, hostages, war crimes, peace talks, ceasefire, nuclear weapons, terrorism, "
        "drone strikes, invasions, occupations, armed groups"
    ),
    "whos_in_charge": (
        "Who's in Charge — Elections, who holds power, presidents and prime ministers, "
        "parliaments and congresses, challenges to leaders, coups, protests against government, "
        "authoritarian leaders, democratic backsliding, political parties, voting rights, "
        "executive orders, government appointments, impeachment"
    ),
    "rules_and_courts": (
        "Rules & Courts — Laws being passed or struck down, court cases, judges, lawsuits, "
        "legal fights, criminal charges, police, prisons, immigration courts, deportation orders, "
        "constitutional rights, civil rights, discrimination, corporate penalties, regulation"
    ),
    "money_and_prices": (
        "Money & Prices — What things cost, inflation, wages, markets, trade, tariffs, "
        "corporate earnings, debt, housing costs, supply chains, sanctions, economic inequality, "
        "poverty, currency, banking, investment, recession, unemployment"
    ),
    "oil_and_energy": (
        "Oil & Energy — Oil, gas, coal, pipelines, energy prices, fuel shortages, power grids, "
        "shipping routes for energy, energy sanctions, OPEC, refineries, nuclear power, "
        "strategic oil reserves, energy as a weapon"
    ),
    "the_environment": (
        "The Environment — Climate change, extreme weather, floods, wildfires, drought, "
        "pollution, clean energy, solar, wind, emissions, biodiversity, water supply, "
        "land use, environmental laws, plastic waste, oceans, forests"
    ),
    "ai_and_technology": (
        "AI & Technology — Artificial intelligence, automation, social media platforms, "
        "surveillance cameras and tracking, algorithms deciding outcomes, data privacy, "
        "deepfakes, misinformation spread by platforms, robots, tech company power, "
        "internet access, cybersecurity, hacking"
    ),
    "health": (
        "Health — Disease outbreaks, healthcare access, hospitals closing or opening, "
        "medicine costs, mental health, overdoses and addiction, food safety, "
        "public health emergencies, vaccines, reproductive health, disability rights"
    ),
    "work_and_workers": (
        "Work & Workers — Jobs, wages, layoffs, unions, strikes, gig work, labor rights, "
        "workplace safety, child labor, unpaid work, automation replacing jobs, "
        "worker organizing, minimum wage, benefits, working conditions"
    ),
    "communities": (
        "Communities — Local government, neighborhoods, schools, housing, homelessness, "
        "local hospitals and services, community responses to crisis, Indigenous communities, "
        "rural areas, small towns, city neighborhoods, local elections, "
        "displacement, gentrification"
    ),
    "media_and_information": (
        "Media & Information — Who controls what people know, journalism closures, "
        "propaganda and disinformation, censorship, press freedom, newsroom layoffs, "
        "social media manipulation, state-controlled media, information gaps, "
        "language access, who gets a platform and who doesn't"
    ),
    "rights_and_justice": (
        "Rights & Justice — Civil rights, human rights, immigrant rights, LGBTQ rights, "
        "racial justice, gender equality, disability rights, police violence, "
        "accountability for abuse, access to justice, due process, "
        "political prisoners, freedom of speech and assembly"
    ),
    "global_relations": (
        "Global Relations — Countries dealing with each other, alliances, treaties, "
        "diplomacy, UN and international bodies, sanctions between countries, "
        "foreign aid, trade agreements, border disputes, great power competition, "
        "NATO, regional blocs, espionage"
    ),
    "food_and_land": (
        "Food & Land — Farming, food prices, hunger, food supply disruptions, "
        "land ownership and access, agricultural policy, food adulteration, "
        "water rights, fishing rights, livestock, crop failures, "
        "food deserts, indigenous land rights"
    ),
    "people_power": (
        "People Power — Protests, community organizing, mutual aid, strikes, "
        "civil disobedience, grassroots movements, civic participation, "
        "whistleblowers, community-led solutions, voter organizing, "
        "solidarity, people holding institutions accountable from below"
    ),
}

# force_tag is retired. Classification now uses only the 15 plain-language domain labels.
# Articles receive ALL labels that genuinely apply — multi-tagging is correct, not noise.
FORCE_VOCABULARY = ""  # kept for import compatibility only

# System prompt for batched classification
BATCH_SYSTEM_PROMPT = """You classify news articles for Signal Board.

Signal Board uses 15 plain-language topic labels. Your job is to tag each article with EVERY label that genuinely applies. Most news stories touch more than one topic — that's intentional. A story about fuel prices during a war should get both "Oil & Energy" AND "War & Conflict" AND "Money & Prices". Do not limit to one label.

You will receive a numbered list of articles (title + summary). For EACH article:

1. LABELS: Assign every label from the list below that is genuinely central to the article.
   - Pure entertainment, celebrity gossip, sports scores, recipes, product reviews with no social/political/economic dimension: return empty labels list.
   - When in doubt, include the label. Under-tagging loses connections. Over-tagging is always correctable.

2. CONNECTION: If 2+ labels are tagged, write ONE plain-English sentence (max 20 words) saying HOW these topics connect in this specific story. Write it so a 10-year-old could understand.
   Example: "War in the Middle East is making gas more expensive for families everywhere."
   NOT: "Geopolitical conflict creates supply chain disruption impacting energy markets."

Labels:
{domains}

Rules:
- Label keys must exactly match keys in the list (e.g. "war_and_conflict", "money_and_prices")
- Tag every label that applies — stories are connected by design
- Connection sentence must be plain English, not policy language
- No force_tag field — it is retired

Respond ONLY with a valid JSON array, one object per article in order:
[
  {{"id": 1, "domains": ["label_key", ...], "connection": "plain English sentence or empty string"}},
  ...
]"""

# Single-article fallback prompt (for stragglers)
SINGLE_SYSTEM_PROMPT = """You classify news articles for Signal Board.

Given an article's title and summary, assign EVERY plain-language label from the list below that genuinely applies. Most articles touch multiple topics — tag all of them.

1. LABELS: Every label that is central to this story. Pure entertainment/sports/celebrity with no social dimension: return empty list.
2. CONNECTION: If 2+ labels tagged, one plain-English sentence (max 20 words) saying how they connect. Write for a 10-year-old.

Labels:
{domains}

Rules:
- Tag every label that applies — multi-tagging is correct
- connection must be plain English, not policy jargon
- No force_tag field

Respond ONLY with valid JSON:
{{"domains": ["label_key", ...], "connection": "plain English sentence or empty string"}}"""


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
# CANONICAL_FORCES retired. The 15 plain-language domain labels are now the taxonomy.
# Kept as empty list for any code that imports this name.
CANONICAL_FORCES = list(DOMAIN_DESCRIPTIONS.keys())


def validate_force_tag(raw_tag: str) -> str:
    """Retired — force_tag is no longer used. Returns empty string."""
    return ""


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
    domain_list = "\n".join(f"- {k}: {v}" for k, v in DOMAIN_DESCRIPTIONS.items())
    system = BATCH_SYSTEM_PROMPT.format(domains=domain_list)

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
                output.append({
                    "domains": domains,
                    "connection": connection if len(domains) > 1 else "",
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
                            output.append({
                                "domains": domains,
                                "connection": connection if len(domains) > 1 else "",
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
                # Retired fields — remove if present from old data
                a.pop("force_tag", None)
                a.pop("cooperation", None)
                a.pop("cooperation_type", None)
                ai_count += 1
            else:
                # Fallback to keywords
                a["domains"] = tag_article(a["title"], a.get("summary", ""), a.get("text", ""))
                a["cross_domain"] = len(a["domains"]) > 1
                a["connection"] = ""
                a.pop("force_tag", None)
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
    domain_list = "\n".join(f"- {k}: {v}" for k, v in DOMAIN_DESCRIPTIONS.items())
    system = SINGLE_SYSTEM_PROMPT.format(domains=domain_list)
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
        return {
            "domains": domains,
            "connection": connection if len(domains) > 1 else "",
        }
    except Exception:
        return None
