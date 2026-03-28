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

# System prompt for batched classification
BATCH_SYSTEM_PROMPT = """You classify news articles for Signal Board, a tool that helps people see how today's biggest stories connect across domains that are usually treated as separate.

You will receive a numbered list of articles (title + summary). For EACH article, you must:
1. Assign one or more domain tags from the list below
2. If the article touches 2+ domains, write ONE sentence (max 20 words) explaining the STRUCTURAL connection — not just naming the topics, but WHY they intersect in this story
3. Assign a "force_tag" — a 2-5 word label for the underlying structural force at work (e.g., "automation displacing workers", "trade weaponization", "democratic erosion", "information asymmetry", "regulatory capture"). This is the deeper pattern, not the headline topic.

Domains:
{domains}

Rules:
- Only tag domains that are genuinely central to the article, not just mentioned in passing
- Consumer product reviews, lifestyle content, recipes, celebrity gossip, entertainment, and sports should get NO domains — return empty domains list
- The connection sentence should explain WHY these topics overlap, not just name them
- The force_tag should name the structural force or pattern at work — think like a systems analyst, not a headline writer
- Be specific to each article, not generic

Respond ONLY with a valid JSON array, one object per article in order:
[
  {{"id": 1, "domains": ["domain_key", ...], "connection": "sentence or empty string", "force_tag": "structural force label"}},
  ...
]"""

# Single-article fallback prompt (for stragglers)
SINGLE_SYSTEM_PROMPT = """You classify news articles for Signal Board, a tool that helps people see how today's biggest stories connect across topics.

Given an article's title and summary, you must:
1. Assign one or more domain tags from the list below
2. If the article touches 2+ domains, write ONE sentence (max 20 words) explaining the structural connection
3. Assign a "force_tag" — a 2-5 word label for the underlying structural force at work

Domains:
{domains}

Rules:
- Only tag domains that are genuinely central to the article, not just mentioned in passing
- Consumer product reviews, lifestyle, recipes, celebrity gossip, entertainment, sports: NO domains (empty list)
- Connection sentence: explain WHY these topics overlap, not just name them
- force_tag: the deeper structural pattern (e.g., "regulatory capture", "automation displacing workers")

Respond ONLY with valid JSON:
{{"domains": ["domain_key", ...], "connection": "sentence or empty string", "force_tag": "structural force label"}}"""


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
            max_tokens=2000,
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
                force_tag = r.get("force_tag", "")
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
                    max_tokens=2000,
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
                            force_tag = r.get("force_tag", "")
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
                ai_count += 1
            else:
                # Fallback to keywords
                a["domains"] = tag_article(a["title"], a.get("summary", ""), a.get("text", ""))
                a["cross_domain"] = len(a["domains"]) > 1
                a["connection"] = ""
                a["force_tag"] = ""
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
        force_tag = result.get("force_tag", "")
        return {
            "domains": domains,
            "connection": connection if len(domains) > 1 else "",
            "force_tag": force_tag,
        }
    except Exception:
        return None
