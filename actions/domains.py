"""
Domain definitions for Signal Board.

Each domain has a name, color (for the dashboard), and keyword sets.
Keywords are matched against article titles and summaries.
An article can belong to multiple domains — those cross-domain
articles are the most valuable signals.

The keyword lists are intentionally broad to catch structural
connections. Better to over-tag and filter than to miss a link.
"""

DOMAINS = {
    "ai": {
        "label": "AI",
        "color": "#6652FF",
        "keywords": [
            "artificial intelligence", "machine learning", "deep learning",
            "neural network", "large language model", "llm", "chatgpt",
            "openai", "anthropic", "google ai", "deepmind", "generative ai",
            "ai safety", "ai regulation", "ai governance", "ai ethics",
            "algorithmic", "automation", "autonomous", "computer vision",
            "natural language processing", "nlp", "ai model", "foundation model",
            "ai deployment", "ai policy", "ai risk", "ai workforce",
            "ai literacy", "ai training data", "synthetic media", "deepfake",
            "ai act", "frontier model", "ai executive order", "copilot",
            "ai startup", "ai chip", "gpu", "nvidia", "semiconductor",
            "content moderation", "recommendation algorithm",
            "chatbot", "ai system", "ai tool", "ai-powered",
            "machine intelligence", "robot", "robotics",
        ],
    },
    "labor": {
        "label": "Labor",
        "color": "#FF5400",
        "keywords": [
            "worker", "workforce", "employment", "unemployment", "layoff",
            "labor market", "wage", "minimum wage", "union", "unionize",
            "strike", "gig economy", "gig worker", "contractor", "freelance",
            "job loss", "job creation", "hiring", "automation", "displacement",
            "worker protection", "labor rights", "labor law", "collective bargaining",
            "workplace", "remote work", "return to office",
            "occupational", "pension", "retirement", "benefits",
            "workforce development", "retraining", "reskilling", "upskilling",
            "platform worker", "delivery driver", "warehouse",
            "income inequality", "economic mobility", "working class",
            "labor shortage", "immigration", "h-1b", "visa worker",
            "pay gap", "unpaid", "furlough", "staffing",
            "child care", "childcare", "paid leave", "sick leave",
            "working mom", "working parent", "cost of child",
        ],
    },
    "governance": {
        "label": "Governance",
        "color": "#FF0054",
        "keywords": [
            "regulation", "legislation", "policy", "executive order",
            "congress", "senate", "parliament", "european commission",
            "federal agency", "regulatory", "compliance", "enforcement",
            "democracy", "democratic institution", "election", "voting",
            "government accountability", "transparency", "oversight",
            "public administration", "procurement", "government contract",
            "digital government", "e-government", "public service",
            "rule of law", "judiciary", "supreme court", "court ruling",
            "antitrust", "monopoly", "competition policy",
            "national security", "intelligence", "surveillance",
            "international law", "treaty", "sanctions", "diplomacy",
            "authoritarianism", "press freedom", "civil liberties",
            "lobbying", "campaign finance", "political spending",
            "usda", "fda", "epa", "fema", "hud",
            "federal program", "government program", "public funding",
            "ban", "bans", "criminalize", "mandate",
            "medicaid", "medicare", "social security",
            "protest", "protests", "rally", "demonstration",
            "activist", "activism", "dissent",
        ],
    },
    "information": {
        "label": "Information",
        "color": "#9E0059",
        "keywords": [
            "journalism", "media", "news industry", "newsroom",
            "misinformation", "disinformation", "propaganda",
            "social media", "platform", "facebook", "meta", "twitter",
            "tiktok", "youtube", "instagram", "reddit",
            "content moderation", "section 230", "digital rights",
            "information ecosystem", "media literacy", "news literacy",
            "public knowledge", "information architecture",
            "local news", "news desert", "media consolidation",
            "fact-checking", "verification", "trust in media",
            "attention economy", "engagement", "viral",
            "newsletter", "podcast", "streaming", "creator economy",
            "data privacy", "surveillance capitalism",
            "open source", "public interest technology",
            "digital divide", "broadband", "internet access",
            "search engine", "seo", "discovery", "recommendation",
            "data broker", "data collection", "screen time",
            "tech company", "big tech", "tech industry",
            "online influence", "online harassment", "doxxing",
            "app", "dating app", "surveillance",
        ],
    },
    "economics": {
        "label": "Economics",
        "color": "#00C2A8",
        "keywords": [
            "economy", "economic", "gdp", "inflation", "recession",
            "interest rate", "federal reserve", "central bank",
            "stock market", "wall street", "investor", "venture capital",
            "trade", "tariff", "supply chain", "globalization",
            "inequality", "wealth gap", "poverty", "cost of living",
            "housing", "rent", "mortgage", "real estate",
            "healthcare cost", "student debt", "consumer debt",
            "tax", "fiscal policy", "government spending", "deficit",
            "cryptocurrency", "fintech", "banking",
            "antitrust", "merger", "acquisition", "market concentration",
            "small business", "startup", "entrepreneurship",
            "global south", "developing economy", "world bank", "imf",
            "industrial policy", "manufacturing", "reshoring",
            "ipo", "bond", "credit", "private credit", "fund",
            "investor", "loan", "lend", "lending", "predatory",
            "afford", "affordability", "cost of living",
            "gas price", "oil price", "energy price", "price",
            "billion", "trillion",
        ],
    },
    "climate": {
        "label": "Climate",
        "color": "#4CAF50",
        "keywords": [
            "climate change", "global warming", "greenhouse gas",
            "carbon emission", "carbon capture", "net zero",
            "renewable energy", "solar", "wind energy", "nuclear energy",
            "fossil fuel", "oil", "natural gas", "coal",
            "environmental", "biodiversity", "deforestation",
            "extreme weather", "hurricane", "wildfire", "drought", "flood",
            "sea level", "arctic", "glacier", "permafrost",
            "paris agreement", "cop", "climate policy", "climate finance",
            "environmental justice", "pollution", "air quality", "water quality",
            "sustainability", "circular economy", "green transition",
            "electric vehicle", "ev", "battery", "energy storage",
            "carbon tax", "emissions trading", "climate adaptation",
            "food security", "agriculture", "land use",
            "farm", "farmer", "crop", "livestock", "poultry",
            "food system", "food supply", "conservation",
            "water", "water supply", "contamination", "pfas",
            "wildfire smoke", "heat wave", "heatwave",
            "climate refugee", "climate migration",
        ],
    },
    "security": {
        "label": "Security",
        "color": "#D32F2F",
        "keywords": [
            "war", "military", "defense", "troops", "army", "navy",
            "air force", "pentagon", "missile", "airstrike", "bombing",
            "ceasefire", "conflict", "combat", "battlefield", "invasion",
            "iran", "strait of hormuz", "nuclear weapon", "nuclear strike",
            "weapons", "arms", "munitions", "drone strike",
            "terrorism", "counterterrorism", "insurgency",
            "intelligence", "cia", "nsa", "espionage", "spy",
            "cyber attack", "cyber warfare", "hacking",
            "veteran", "conscription", "draft",
            "war crime", "humanitarian crisis", "refugee",
            "nato", "defense spending", "arms deal", "weapons sale",
            "retaliation", "escalation", "deterrence",
            "hostage", "prisoner of war", "casualty", "civilian death",
        ],
    },
    "geopolitics": {
        "label": "Geopolitics",
        "color": "#1976D2",
        "keywords": [
            "geopolitical", "superpower", "great power",
            "china", "beijing", "xi jinping", "ccp",
            "russia", "moscow", "putin", "kremlin",
            "european union", "brussels", "nato",
            "middle east", "gulf state", "opec",
            "asia pacific", "indo-pacific", "south china sea",
            "territorial", "sovereignty", "annexation",
            "diplomat", "embassy", "ambassador", "foreign minister",
            "united nations", "security council", "general assembly",
            "alliance", "bilateral", "multilateral",
            "sphere of influence", "proxy", "buffer state",
            "belt and road", "brics", "g7", "g20",
            "north korea", "pyongyang", "nuclear program",
            "taiwan", "south korea", "japan", "asean",
            "africa", "african union", "sahel",
            "latin america", "arctic sovereignty",
            "global order", "world order", "hegemony",
            "foreign policy", "foreign aid", "humanitarian aid",
        ],
    },
    "domestic_politics": {
        "label": "Politics",
        "color": "#7B1FA2",
        "keywords": [
            "trump", "biden", "republican", "democrat", "gop",
            "congress", "house of representatives", "speaker",
            "midterm", "primary", "campaign", "ballot",
            "cpac", "rnc", "dnc", "caucus",
            "vance", "rubio", "desantis", "newsom",
            "hegseth", "patel", "musk", "doge",
            "executive order", "presidential", "oval office",
            "cabinet", "attorney general", "secretary of state",
            "impeachment", "indictment", "special counsel",
            "political party", "bipartisan", "partisan",
            "governor", "state legislature", "ballot measure",
            "voter", "gerrymandering", "redistricting",
            "supreme court nomination", "judicial appointment",
            "immigration policy", "border", "deportation",
            "culture war", "abortion", "gun control", "second amendment",
            "first amendment", "religious liberty",
            "political polarization", "populism", "progressive",
            "conservative", "liberal", "far right", "far left",
        ],
    },
    "legal": {
        "label": "Legal",
        "color": "#FF9800",
        "keywords": [
            # Courts and rulings
            "supreme court", "court ruling", "court order", "federal judge",
            "appeals court", "district court", "circuit court", "ruling",
            "lawsuit", "plaintiff", "defendant", "litigation", "verdict",
            "injunction", "preliminary injunction", "stay", "overturn",
            "precedent", "legal challenge", "class action", "settlement",
            "judicial review", "constitutional", "unconstitutional",
            # Regulatory and enforcement
            "regulation", "regulatory", "enforcement", "compliance",
            "consent decree", "penalty", "fine", "sanction",
            "ftc", "sec", "doj", "fcc", "epa", "osha", "nlrb", "cfpb",
            "department of justice", "attorney general", "prosecutor",
            "federal investigation", "indictment", "grand jury",
            # Executive and legislative law
            "executive order", "executive action", "signing statement",
            "legislation", "statute", "codify", "repeal", "amend",
            "bill signed", "bill passed", "enacted", "ratified",
            # Rights and civil law
            "civil rights", "civil liberties", "due process", "equal protection",
            "discrimination", "title ix", "title vii", "ada", "voting rights act",
            "criminal justice", "sentencing", "incarceration", "parole", "probation",
            "police", "policing", "qualified immunity", "use of force",
            "asylum", "immigration court", "deportation order",
            # Corporate and tech law
            "antitrust", "monopoly", "merger approval", "consent order",
            "intellectual property", "patent", "copyright",
            "data protection", "privacy law", "gdpr", "ccpa",
            "terms of service", "liability", "section 230",
            # International law
            "international law", "treaty", "convention", "tribunal",
            "war crime", "international criminal court", "icc",
            "extradition", "jurisdiction", "sovereignty",
        ],
    },
}


def tag_article(title: str, summary: str, full_text: str = "") -> list[str]:
    """
    Tag an article with matching domains based on keyword presence
    in title, summary, and full text. Returns list of domain keys.

    Title matches are weighted highest, summary next, full text lowest.
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
                score += 3  # title match is strong signal
            elif kw in summary_lower:
                score += 1  # summary match is weaker
            elif kw in full_lower:
                score += 0.5  # full text match is weakest but still counts

        if score >= 1:  # lowered threshold: catch more articles
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
