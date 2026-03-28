"""
AI-powered article classification for Signal Board.

Uses the Anthropic API (Claude) to classify articles into domains
and generate plain-language explanations of why each article matters
at that intersection. Falls back to keyword-based tagging if the API
is unavailable or the key is not set.

Cost estimate at ~1000 articles/day with Claude Haiku:
  - ~$1.50/day = ~$45/month
"""

import os
import json
import time

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

SYSTEM_PROMPT = """You classify news articles for Signal Board, a tool that helps people see how today's biggest stories connect across topics.

Given an article's title and summary, you must:
1. Assign one or more domain tags from the list below
2. If the article touches 2+ domains, write ONE short sentence (max 15 words) explaining the connection in plain language a middle schooler would understand

Domains:
{domains}

Rules:
- Only tag domains that are genuinely central to the article, not just mentioned in passing
- Consumer product reviews, lifestyle content, recipes, and celebrity gossip should get NO domains (return empty)
- The connection sentence should explain WHY these topics overlap in this specific story, not just name the topics
- Be specific to the article, not generic

Respond ONLY with valid JSON, no other text:
{{"domains": ["domain_key", ...], "connection": "sentence or empty string"}}"""

def get_client():
    """Get Anthropic client if available."""
    if not HAS_ANTHROPIC or not ANTHROPIC_API_KEY:
        return None
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def classify_article(title: str, summary: str, client=None) -> dict:
    """
    Classify a single article using Claude.

    Returns: {"domains": [...], "connection": "..."}
    Returns None if classification fails (caller should fall back to keywords).
    """
    if client is None:
        return None

    domain_list = "\n".join(f"- {v}" for v in DOMAIN_DESCRIPTIONS.values())
    system = SYSTEM_PROMPT.format(domains=domain_list)

    user_msg = f"Title: {title}\nSummary: {summary[:400] if summary else '(no summary)'}"

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )

        text = response.content[0].text.strip()
        # Parse JSON from response
        result = json.loads(text)

        # Validate domains
        valid_domains = list(DOMAIN_DESCRIPTIONS.keys())
        domains = [d for d in result.get("domains", []) if d in valid_domains]
        connection = result.get("connection", "")

        return {"domains": domains, "connection": connection if len(domains) > 1 else ""}

    except json.JSONDecodeError:
        return None
    except Exception as e:
        # Rate limit or other API error
        if "rate" in str(e).lower():
            time.sleep(2)
        return None


def classify_batch(articles: list[dict], batch_size: int = 20) -> list[dict]:
    """
    Classify a batch of articles using AI.

    Modifies articles in-place, adding 'domains', 'cross_domain', and 'connection' fields.
    Falls back to keyword tagging for any articles that fail AI classification.

    Returns the list of articles with updated fields.
    """
    from domains import tag_article  # keyword fallback

    client = get_client()

    if client is None:
        print("  AI classification unavailable (no API key or anthropic not installed)")
        print("  Falling back to keyword-based tagging")
        for a in articles:
            a["domains"] = tag_article(a["title"], a.get("summary", ""))
            a["cross_domain"] = len(a["domains"]) > 1
            a["connection"] = ""
        return articles

    print(f"  AI classification: processing {len(articles)} articles...")
    ai_count = 0
    fallback_count = 0

    for i, a in enumerate(articles):
        result = classify_article(a["title"], a.get("summary", ""), client)

        if result and result["domains"]:
            a["domains"] = result["domains"]
            a["cross_domain"] = len(result["domains"]) > 1
            a["connection"] = result.get("connection", "")
            ai_count += 1
        else:
            # Fallback to keywords
            a["domains"] = tag_article(a["title"], a.get("summary", ""))
            a["cross_domain"] = len(a["domains"]) > 1
            a["connection"] = ""
            fallback_count += 1

        # Progress indicator every 50 articles
        if (i + 1) % 50 == 0:
            print(f"    ... {i+1}/{len(articles)} classified")

        # Small delay to stay within rate limits
        if (i + 1) % batch_size == 0:
            time.sleep(0.5)

    print(f"  AI classified: {ai_count}, keyword fallback: {fallback_count}")
    return articles
