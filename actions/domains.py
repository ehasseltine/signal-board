"""
Domain definitions for Signal Board.

Each domain has a name, color (for the dashboard), and keyword sets.
Keywords are matched against article titles and summaries.
An article can belong to multiple domains — those cross-domain
articles are the most valuable signals.

The keyword lists are intentionally broad to catch structural
connections. Better to over-tag and filter than to miss a link.
"""

# ——————————————————————————————————————————————————————————————————————
# SIGNAL BOARD CANONICAL TAXONOMY v1.0
# 15 plain-language labels. 5th-grade reading level.
# Articles receive ALL labels that apply — multi-tagging is the point.
# Locked: see GitHub issue #taxonomy-v1
# ——————————————————————————————————————————————————————————————————————

DOMAINS = {
    "war_and_conflict": {
        "label": "War & Conflict",
        "color": "#FF2D55",
        "keywords": [
            "war", "conflict", "military", "troops", "soldier", "airstrike",
            "missile", "bombing", "casualties", "ceasefire", "hostage",
            "invasion", "occupation", "armed", "weapons", "nuclear",
            "drone strike", "war crime", "terrorism", "militant",
            "peace talks", "ceasefire", "combat", "battlefield",
        ],
    },
    "whos_in_charge": {
        "label": "Who's in Charge",
        "color": "#FF9500",
        "keywords": [
            "election", "president", "prime minister", "parliament", "congress",
            "democracy", "authoritarian", "coup", "vote", "voting rights",
            "political party", "executive order", "impeachment", "government",
            "dictator", "leader", "cabinet", "senate", "opposition",
            "democratic backsliding", "protest against government",
        ],
    },
    "rules_and_courts": {
        "label": "Rules & Courts",
        "color": "#FFD60A",
        "keywords": [
            "court", "law", "judge", "lawsuit", "legal", "ruling", "verdict",
            "criminal charges", "prison", "police", "arrest", "deportation",
            "immigration court", "constitution", "civil rights", "regulation",
            "penalty", "fine", "discrimination", "justice", "sentencing",
            "injunction", "bill passed", "legislation",
        ],
    },
    "money_and_prices": {
        "label": "Money & Prices",
        "color": "#30D158",
        "keywords": [
            "price", "inflation", "cost", "economy", "market", "trade",
            "tariff", "sanction", "wage", "salary", "debt", "housing cost",
            "rent", "poverty", "inequality", "recession", "unemployment",
            "supply chain", "corporate earnings", "currency", "banking",
            "investment", "gdp", "interest rate",
        ],
    },
    "oil_and_energy": {
        "label": "Oil & Energy",
        "color": "#FF6B00",
        "keywords": [
            "oil", "gas", "coal", "pipeline", "energy price", "fuel",
            "power grid", "opec", "refinery", "nuclear power", "hormuz",
            "energy sanction", "crude oil", "lng", "natural gas",
            "strategic reserve", "fuel shortage", "energy supply",
        ],
    },
    "the_environment": {
        "label": "The Environment",
        "color": "#34C759",
        "keywords": [
            "climate", "weather", "flood", "wildfire", "drought",
            "pollution", "solar", "wind energy", "emissions", "biodiversity",
            "water supply", "deforestation", "plastic", "ocean",
            "renewable energy", "greenhouse gas", "environment",
            "conservation", "extinction",
        ],
    },
    "ai_and_technology": {
        "label": "AI & Technology",
        "color": "#00D4FF",
        "keywords": [
            "artificial intelligence", "automation", "algorithm", "robot",
            "social media", "surveillance", "data privacy", "deepfake",
            "misinformation", "platform", "tech company", "cybersecurity",
            "hacking", "internet", "software", "app", "ai",
            "machine learning", "facial recognition",
        ],
    },
    "health": {
        "label": "Health",
        "color": "#5AC8FA",
        "keywords": [
            "health", "hospital", "disease", "medicine", "mental health",
            "overdose", "addiction", "vaccine", "healthcare", "medical",
            "drug", "food safety", "public health", "disability",
            "reproductive health", "cancer", "epidemic", "pandemic",
            "pharmacy", "insurance coverage",
        ],
    },
    "work_and_workers": {
        "label": "Work & Workers",
        "color": "#BF5AF2",
        "keywords": [
            "worker", "job", "wage", "layoff", "union", "strike",
            "labor", "gig worker", "workplace", "minimum wage",
            "working conditions", "unemployment", "hire", "firing",
            "worker rights", "benefits", "automation replacing",
        ],
    },
    "communities": {
        "label": "Communities",
        "color": "#FF9500",
        "keywords": [
            "neighborhood", "school", "local", "community", "housing",
            "homeless", "rural", "small town", "city", "displacement",
            "gentrification", "indigenous", "local government",
            "local election", "local hospital", "public school",
            "affordable housing",
        ],
    },
    "media_and_information": {
        "label": "Media & Information",
        "color": "#FF2D55",
        "keywords": [
            "journalism", "media", "newspaper", "news outlet", "press freedom",
            "censorship", "propaganda", "disinformation", "misinformation",
            "newsroom", "journalist", "information", "platform control",
            "state media", "language access", "who gets a platform",
        ],
    },
    "rights_and_justice": {
        "label": "Rights & Justice",
        "color": "#0A84FF",
        "keywords": [
            "human rights", "civil rights", "immigrant rights", "lgbtq",
            "racial justice", "gender equality", "police violence",
            "accountability", "due process", "political prisoner",
            "free speech", "assembly", "discrimination", "deportation",
            "indigenous rights", "disability rights",
        ],
    },
    "global_relations": {
        "label": "Global Relations",
        "color": "#FFD60A",
        "keywords": [
            "diplomacy", "alliance", "treaty", "united nations", "nato",
            "foreign aid", "trade agreement", "border dispute",
            "great power", "bilateral", "multilateral", "espionage",
            "sanctions", "foreign policy", "geopolitics",
        ],
    },
    "food_and_land": {
        "label": "Food & Land",
        "color": "#30D158",
        "keywords": [
            "food", "farm", "farming", "agriculture", "hunger", "famine",
            "crop", "fertilizer", "land", "water rights", "fishing",
            "livestock", "food price", "food safety", "food supply",
            "food desert", "indigenous land",
        ],
    },
    "people_power": {
        "label": "People Power",
        "color": "#BF5AF2",
        "keywords": [
            "protest", "rally", "march", "organizing", "mutual aid",
            "civil disobedience", "grassroots", "civic", "whistleblower",
            "community-led", "solidarity", "voter organizing",
            "demonstration", "activist", "people power",
        ],
    },
}


def tag_article(title: str, summary: str, full_text: str = "") -> list[str]:
    """
    Tag an article with all matching labels from the 15-label taxonomy.
    Returns list of domain keys. Multiple tags are expected and correct.
    """
    title_lower = title.lower()
    summary_lower = f"{title} {summary}".lower()
    full_lower = f"{title} {summary} {full_text}".lower() if full_text else summary_lower

    matches = []
    for domain_key, domain in DOMAINS.items():
        score = 0
        for keyword in domain["keywords"]:
            kw = keyword.lower()
            if kw in title_lower:
                score += 3
            elif kw in summary_lower:
                score += 1
            elif kw in full_lower:
                score += 0.5
        if score >= 1:
            matches.append(domain_key)
    return matches


# ---------------------------------------------------------------------------
# TIER DEFINITIONS — canonical names, labels, and legacy aliases
# ---------------------------------------------------------------------------

TIERS = {
    "national": {"label": "National", "color": "#6652FF"},
    "international": {"label": "International", "color": "#1976D2"},
    "specialist": {"label": "Specialist", "color": "#00C2A8", "aliases": ["domain"]},
    "local-regional": {"label": "Local & Regional", "color": "#FF5400", "aliases": ["lived", "community"]},
    "analysis": {"label": "Analysis & Think Tank", "color": "#9E0059"},
    "podcast": {"label": "Podcast", "color": "#7B1FA2"},
    "explainer": {"label": "Explainer", "color": "#FF9800"},
    "newsletter": {"label": "Newsletter", "color": "#4CAF50"},
    "government": {"label": "Government", "color": "#D32F2F"},
    "research": {"label": "Research", "color": "#795548"},
    "solutions": {"label": "Solutions Journalism", "color": "#00BCD4"},
}

# Map any legacy tier name to the canonical key
TIER_ALIAS_MAP = {}
for _key, _info in TIERS.items():
    TIER_ALIAS_MAP[_key] = _key
    for _alias in _info.get("aliases", []):
        TIER_ALIAS_MAP[_alias] = _key


def normalize_tier(tier: str) -> str:
    """Convert any tier name (including legacy aliases) to canonical form."""
    return TIER_ALIAS_MAP.get(tier.strip().lower(), tier.strip().lower())


def get_tier_labels() -> dict:
    """Return tier key -> display label mapping."""
    return {k: v["label"] for k, v in TIERS.items()}


def get_domain_colors() -> dict:
    """Return domain key -> color mapping for the frontend."""
    return {k: v["color"] for k, v in DOMAINS.items()}


def get_domain_labels() -> dict:
    """Return domain key -> display label mapping."""
    return {k: v["label"] for k, v in DOMAINS.items()}
