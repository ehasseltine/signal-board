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
}


def tag_article(title: str, summary: str) -> list[str]:
    """
    Tag an article with matching domains based on keyword presence
    in title and summary. Returns list of domain keys.

    Title matches are weighted higher (a keyword in a headline
    is a stronger signal than one buried in a summary).
    """
    text_lower = f"{title} {summary}".lower()
    title_lower = title.lower()

    matches = []
    for domain_key, domain in DOMAINS.items():
        score = 0
        for keyword in domain["keywords"]:
            kw = keyword.lower()
            if kw in title_lower:
                score += 3  # title match is strong signal
            elif kw in text_lower:
                score += 1  # summary match is weaker

        if score >= 2:  # threshold: at least one title match or two summary matches
            matches.append(domain_key)

    return matches


def get_domain_colors() -> dict:
    """Return domain key -> color mapping for the frontend."""
    return {k: v["color"] for k, v in DOMAINS.items()}


def get_domain_labels() -> dict:
    """Return domain key -> display label mapping."""
    return {k: v["label"] for k, v in DOMAINS.items()}
