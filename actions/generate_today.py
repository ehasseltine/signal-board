#!/usr/bin/env python3
"""
Signal Board Daily Page Generator

Reads the pipeline output (docs/data/daily/latest.json), selects stories for
three categories (Daily Thread, Daily Gap, Meanwhile), and generates a beautiful
HTML page at docs/today/index.html.

Story Selection Logic:
- Daily Thread: mega story with most sources + richest cross_spectrum data
- Daily Gap: story showing framing differences (independent/intl vs mainstream US)
- Meanwhile: community action, resistance, municipal decisions, positive change
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


# Design tokens
COLORS = {
    "cream": "#F5EFDF",
    "navy": "#1B2A4A",
    "red": "#D94032",
    "green": "#2D8A4E",
    "ink": "#2B2B2B",
    "light_gray": "#E8E3D6",
}

FONTS = {
    "display": "Abril Fatface",
    "body": "Lora",
    "handwritten": "Caveat",
    "ui": "Inter",
}

# Known source backgrounds
SOURCE_CONTEXT = {
    "Dawn": "Founded 1941, oldest English-language newspaper in Pakistan",
    "Arab American News": "Published in Dearborn MI since 1984, independent",
    "The Advocate": "Oldest LGBTQ+ publication in US, founded 1967",
    "Colorado Sun": "Founded 2018 by ex-Denver Post journalists",
    "Indian Country Today": "Native American news, founded 1981",
    "El Diario NY": "Oldest Spanish-language daily in US",
    "Inside Climate News": "Pulitzer-winning nonprofit climate journalism",
    "Mother Jones": "Nonprofit investigative journalism",
}


def load_pipeline_data(json_path: str) -> Dict[str, Any]:
    """Load pipeline JSON output with graceful fallback."""
    try:
        with open(json_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Pipeline data not found at {json_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_path}: {e}", file=sys.stderr)
        sys.exit(1)


def count_spectrum_sources(cross_spectrum: Dict[str, Any]) -> int:
    """Count unique sources across all spectrum categories."""
    sources = set()
    for category in ["left_lean", "center", "right_lean", "international", "independent"]:
        if category in cross_spectrum and cross_spectrum[category]:
            # Extract source names from framing text if available
            sources.add(category)
    return len(sources)


def select_daily_thread(mega_stories: List[Dict]) -> Optional[Dict]:
    """
    Select Daily Thread: mega story with most sources AND richest cross_spectrum.
    Should have sources from at least 3 different political/geographic categories.
    """
    best_story = None
    best_score = 0

    for story in mega_stories:
        article_count = story.get("article_count", 0)
        cross_spectrum = story.get("cross_spectrum", {})

        # Count populated spectrum categories
        populated_categories = sum(
            1 for cat in ["left_lean", "center", "right_lean", "international", "independent"]
            if cross_spectrum.get(cat)
        )

        # Score: prioritize populated categories, then article count
        score = (populated_categories * 1000) + article_count

        if score > best_score and populated_categories >= 3:
            best_score = score
            best_story = story

    return best_story


def select_daily_gap(mega_stories: List[Dict], local_regional: Dict) -> Optional[Dict]:
    """
    Select Daily Gap: story showing framing differences between independent/intl
    sources vs mainstream US outlets. Or notable_coverage from local_regional.
    """
    gap_story = None
    best_framing_gap = 0

    # Look for framing differences in mega stories
    for story in mega_stories:
        cross_spectrum = story.get("cross_spectrum", {})
        independent_text = cross_spectrum.get("independent", "")
        intl_text = cross_spectrum.get("international", "")
        mainstream_text = (
            cross_spectrum.get("left_lean", "") +
            " " +
            cross_spectrum.get("center", "") +
            " " +
            cross_spectrum.get("right_lean", "")
        )

        # Simple heuristic: if independent/intl exist and differ from mainstream
        if (independent_text or intl_text) and mainstream_text:
            framing_gap = 1  # Mark as having potential gap
            if framing_gap > best_framing_gap:
                best_framing_gap = framing_gap
                gap_story = story

    # If no framing gap found, look for notable coverage in local_regional
    if not gap_story and local_regional:
        notable = local_regional.get("notable_coverage", [])
        if notable:
            # Create synthetic story from notable coverage
            gap_story = {
                "title": local_regional.get("narrative", "Local and Regional News")[:100],
                "from_local": True,
                "sources": {
                    src["source"]: {"url": src.get("url", "")}
                    for src in notable
                },
                "synthesis": {
                    "narrative": local_regional.get("narrative", ""),
                    "key_developments": local_regional.get("themes", []),
                },
            }

    return gap_story


def select_meanwhile(mega_stories: List[Dict], local_regional: Dict) -> Optional[Dict]:
    """
    Select Meanwhile: stories about community action, resistance, municipal decisions,
    positive structural change. Feel warm and human without being sentimental.
    """
    meanwhile_story = None

    # Keywords suggesting "meanwhile" content
    meanwhile_keywords = [
        "community",
        "local",
        "action",
        "resistance",
        "municipal",
        "council",
        "support",
        "care",
        "organizing",
        "initiative",
        "movement",
        "solidarity",
    ]

    # Check local_regional first (highest probability)
    if local_regional:
        narrative = local_regional.get("narrative", "").lower()
        themes = local_regional.get("themes", [])

        if any(kw in narrative for kw in meanwhile_keywords) or any(
            kw in str(t).lower() for t in themes for kw in meanwhile_keywords
        ):
            meanwhile_story = {
                "title": "Communities Taking Action",
                "from_local": True,
                "synthesis": {
                    "narrative": local_regional.get("narrative", ""),
                    "key_developments": local_regional.get("themes", []),
                },
                "sources": {
                    src["source"]: {"url": src.get("url", "")}
                    for src in local_regional.get("notable_coverage", [])
                },
            }

    # If not found in local, search mega stories
    if not meanwhile_story:
        for story in mega_stories:
            title = story.get("title", "").lower()
            narrative = story.get("synthesis", {}).get("narrative", "").lower()

            if any(kw in title or kw in narrative for kw in meanwhile_keywords):
                meanwhile_story = story
                break

    return meanwhile_story


def get_source_context(source_name: str) -> Optional[str]:
    """Return source context if known."""
    return SOURCE_CONTEXT.get(source_name)


def extract_top_sources(sources_dict: Dict) -> List[str]:
    """Extract top 3-5 source names from sources dict."""
    return list(sources_dict.keys())[:5]


def generate_svg_icon(icon_type: str) -> str:
    """Generate SVG icon for category."""
    if icon_type == "thread":
        return '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" class="category-icon">
            <line x1="20" y1="20" x2="50" y2="50" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
            <line x1="80" y1="20" x2="50" y2="50" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
            <line x1="50" y1="50" x2="50" y2="80" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
            <circle cx="50" cy="50" r="4" fill="currentColor"/>
        </svg>'''
    elif icon_type == "gap":
        return '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" class="category-icon">
            <rect x="20" y="20" width="15" height="60" fill="currentColor"/>
            <rect x="65" y="20" width="15" height="60" fill="currentColor"/>
        </svg>'''
    elif icon_type == "meanwhile":
        return '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" class="category-icon">
            <circle cx="50" cy="50" r="30" stroke="currentColor" stroke-width="2" fill="none"/>
            <circle cx="50" cy="50" r="12" fill="currentColor"/>
        </svg>'''
    return ""


def build_html(
    pipeline_data: Dict,
    thread_story: Optional[Dict],
    gap_story: Optional[Dict],
    meanwhile_story: Optional[Dict],
) -> str:
    """Generate complete HTML page."""

    date_str = pipeline_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    summary = pipeline_data.get("summary", {})

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Signal Board - Today</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Abril+Fatface&family=Caveat:wght@400;700&family=Inter:wght@400;500;600;700&family=Lora:ital,wght@0,400;0,500;0,700;1,400;1,500&display=swap');

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --cream: {COLORS["cream"]};
            --navy: {COLORS["navy"]};
            --red: {COLORS["red"]};
            --green: {COLORS["green"]};
            --ink: {COLORS["ink"]};
            --light-gray: {COLORS["light_gray"]};
        }}

        body {{
            font-family: {FONTS["body"]}, Georgia, serif;
            line-height: 1.7;
            color: var(--ink);
            background: var(--cream);
        }}

        .progress-bar {{
            position: fixed;
            top: 0;
            left: 0;
            height: 4px;
            background: var(--red);
            z-index: 1000;
            animation: progress 2s ease-out forwards;
        }}

        @keyframes progress {{
            from {{ width: 0%; }}
            to {{ width: 100%; }}
        }}

        header {{
            background: var(--navy);
            color: var(--cream);
            padding: 3rem 1rem;
            text-align: center;
        }}

        .header-wrap {{
            max-width: 1280px;
            margin: 0 auto;
        }}

        h1 {{
            font-family: {FONTS["display"]}, serif;
            font-size: 4rem;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
            color: var(--red);
        }}

        .date {{
            font-family: {FONTS["ui"]}, sans-serif;
            font-size: 0.95rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            opacity: 0.9;
        }}

        .summary-stats {{
            max-width: 1280px;
            margin: 2rem auto;
            padding: 0 1rem;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
        }}

        .stat-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid var(--red);
        }}

        .stat-number {{
            font-family: {FONTS["display"]}, serif;
            font-size: 2rem;
            color: var(--red);
            display: block;
        }}

        .stat-label {{
            font-family: {FONTS["ui"]}, sans-serif;
            font-size: 0.85rem;
            color: var(--navy);
            margin-top: 0.5rem;
        }}

        .summary-cards {{
            max-width: 1280px;
            margin: 2rem auto;
            padding: 0 1rem;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
        }}

        .summary-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }}

        .summary-card:hover {{
            border-color: var(--red);
            transform: translateY(-4px);
        }}

        .summary-card h2 {{
            font-family: {FONTS["display"]}, serif;
            font-size: 1.5rem;
            color: var(--navy);
            margin-bottom: 0.5rem;
        }}

        .summary-card p {{
            font-size: 0.95rem;
            color: #666;
            line-height: 1.6;
        }}

        .category-section {{
            padding: 3rem 1rem;
            margin-bottom: 1rem;
        }}

        .category-section:nth-child(odd) {{
            background: var(--navy);
            color: var(--cream);
        }}

        .category-section:nth-child(even) {{
            background: var(--cream);
            color: var(--ink);
        }}

        .category-wrap {{
            max-width: 1080px;
            margin: 0 auto;
        }}

        .category-header {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .category-icon {{
            width: 60px;
            height: 60px;
            color: var(--red);
            flex-shrink: 0;
        }}

        .category-title {{
            font-family: {FONTS["display"]}, serif;
            font-size: 2.5rem;
            letter-spacing: 0.05em;
        }}

        .category-subtitle {{
            font-family: {FONTS["handwritten"]}, cursive;
            font-size: 1.1rem;
            opacity: 0.8;
        }}

        .story-title {{
            font-size: 1.5rem;
            margin-bottom: 1rem;
            line-height: 1.4;
        }}

        .category-section:nth-child(odd) .story-title {{
            color: var(--red);
        }}

        .story-synthesis {{
            margin: 1.5rem 0;
            font-size: 1.05rem;
            line-height: 1.8;
        }}

        .cross-spectrum {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }}

        .spectrum-block {{
            padding: 1.5rem;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.1);
        }}

        .category-section:nth-child(even) .spectrum-block {{
            background: rgba(27, 42, 74, 0.05);
        }}

        .spectrum-label {{
            font-family: {FONTS["ui"]}, sans-serif;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.75rem;
            opacity: 0.8;
        }}

        .spectrum-text {{
            font-size: 0.95rem;
            line-height: 1.6;
        }}

        .sources-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }}

        .source-item {{
            padding: 1rem;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.08);
            font-size: 0.9rem;
        }}

        .category-section:nth-child(even) .source-item {{
            background: rgba(27, 42, 74, 0.05);
        }}

        .source-name {{
            font-weight: 600;
            color: var(--red);
            display: block;
            margin-bottom: 0.3rem;
        }}

        .source-context {{
            font-size: 0.85rem;
            opacity: 0.75;
        }}

        .dot-grid {{
            display: grid;
            grid-template-columns: repeat(10, 1fr);
            gap: 0.5rem;
            margin: 1.5rem 0;
            max-width: 300px;
        }}

        .dot {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: var(--red);
            opacity: 0.3;
        }}

        .dot.filled {{
            opacity: 1;
        }}

        .article-count {{
            font-family: {FONTS["display"]}, serif;
            font-size: 1.2rem;
            margin: 1rem 0;
        }}

        .scroll-reveal {{
            opacity: 0;
            transform: translateY(20px);
            animation: reveal 0.6s ease-out forwards;
        }}

        @keyframes reveal {{
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        footer {{
            background: var(--navy);
            color: var(--cream);
            padding: 2rem 1rem;
            text-align: center;
            font-size: 0.9rem;
            margin-top: 3rem;
        }}

        .footer-wrap {{
            max-width: 1280px;
            margin: 0 auto;
        }}

        .pull-quote {{
            font-family: {FONTS["body"]}, Georgia, serif;
            font-style: italic;
            margin: 1.5rem 0;
            padding: 1.5rem;
            border-left: 4px solid var(--red);
            font-size: 1.1rem;
            line-height: 1.8;
        }}

        .category-section:nth-child(odd) .pull-quote {{
            border-left-color: var(--cream);
            background: rgba(255, 255, 255, 0.08);
        }}

        @media (max-width: 768px) {{
            h1 {{ font-size: 2.5rem; }}
            .category-title {{ font-size: 1.8rem; }}
            .story-title {{ font-size: 1.2rem; }}
            .category-header {{ flex-direction: column; align-items: flex-start; gap: 1rem; }}
            .summary-cards {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="progress-bar"></div>

    <header>
        <div class="header-wrap">
            <h1>SIGNAL BOARD</h1>
            <p class="date">{date_str}</p>
        </div>
    </header>

    <div class="summary-stats">
        <div class="stat-card scroll-reveal">
            <span class="stat-number">{summary.get("total_articles", "N/A")}</span>
            <span class="stat-label">Articles analyzed</span>
        </div>
        <div class="stat-card scroll-reveal">
            <span class="stat-number">{summary.get("sources_reporting", "N/A")}</span>
            <span class="stat-label">Sources reporting today</span>
        </div>
        <div class="stat-card scroll-reveal">
            <span class="stat-number">{len(summary.get("categories_covered", []))}</span>
            <span class="stat-label">Topics covered</span>
        </div>
    </div>

    <div class="summary-cards">
        <div class="summary-card scroll-reveal" onclick="document.getElementById('thread').scrollIntoView({{behavior: 'smooth'}})">
            <h2>Daily Thread</h2>
            <p>How one story connects across sources and perspectives. See how different outlets frame the same news.</p>
        </div>
        <div class="summary-card scroll-reveal" onclick="document.getElementById('gap').scrollIntoView({{behavior: 'smooth'}})">
            <h2>Daily Gap</h2>
            <p>What corporate outlets miss. Stories where independent and international sources show a different picture.</p>
        </div>
        <div class="summary-card scroll-reveal" onclick="document.getElementById('meanwhile').scrollIntoView({{behavior: 'smooth'}})">
            <h2>Meanwhile</h2>
            <p>Who showed up. Communities taking care of each other, organizing, acting, building something better.</p>
        </div>
    </div>
'''

    # Daily Thread section
    if thread_story:
        html += _build_story_section(
            "thread",
            "Daily Thread",
            "how one story connects",
            thread_story,
        )
    else:
        html += _build_missing_section("thread", "Daily Thread")

    # Daily Gap section
    if gap_story:
        html += _build_story_section(
            "gap",
            "Daily Gap",
            "what gets missed",
            gap_story,
        )
    else:
        html += _build_missing_section("gap", "Daily Gap")

    # Meanwhile section
    if meanwhile_story:
        html += _build_story_section(
            "meanwhile",
            "Meanwhile",
            "people taking action",
            meanwhile_story,
        )
    else:
        html += _build_missing_section("meanwhile", "Meanwhile")

    html += f'''
    <footer>
        <div class="footer-wrap">
            <p>Signal Board detects and analyzes news patterns daily. <a href="/how-it-works" style="color: var(--red); text-decoration: none;">Learn how it works.</a></p>
            <p style="margin-top: 1rem; opacity: 0.7;">Generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC</p>
        </div>
    </footer>

    <script>
        // Intersection Observer for scroll reveals
        const reveals = document.querySelectorAll('.scroll-reveal');
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    const delay = Math.random() * 0.3;
                    entry.target.style.animationDelay = delay + 's';
                    entry.target.style.animationPlayState = 'running';
                }}
            }});
        }}, {{ threshold: 0.1 }});

        reveals.forEach(el => {{
            el.style.animationPlayState = 'paused';
            observer.observe(el);
        }});
    </script>
</body>
</html>
'''

    return html


def _build_story_section(icon_type: str, title: str, subtitle: str, story: Dict) -> str:
    """Build a category section for a story."""

    section_id = icon_type
    synthesis = story.get("synthesis", {})
    narrative = synthesis.get("narrative", "")
    cross_spectrum = story.get("cross_spectrum", {})
    sources = story.get("sources", {})
    article_count = story.get("article_count", 0)
    story_title = story.get("title", "Untitled")

    html = f'''
    <section class="category-section" id="{section_id}">
        <div class="category-wrap scroll-reveal">
            <div class="category-header">
                {generate_svg_icon(icon_type)}
                <div>
                    <h2 class="category-title">{title}</h2>
                    <p class="category-subtitle">{subtitle}</p>
                </div>
            </div>

            <h3 class="story-title">{story_title}</h3>
'''

    if narrative:
        html += f'<div class="story-synthesis">{_escape_html(narrative)}</div>'

    # Article count with dot grid
    if article_count:
        num_dots = min(int(article_count / 20) + 1, 30)
        html += f'<div class="article-count">{article_count} articles</div>'
        html += '<div class="dot-grid">'
        for i in range(min(30, num_dots)):
            html += '<div class="dot filled"></div>'
        for i in range(max(0, 30 - num_dots)):
            html += '<div class="dot"></div>'
        html += '</div>'

    # Cross spectrum representation
    if cross_spectrum and any(cross_spectrum.values()):
        html += '<div class="cross-spectrum">'

        spectrum_order = ["left_lean", "center", "right_lean", "international", "independent"]
        spectrum_labels = {
            "left_lean": "Left-leaning outlets",
            "center": "Centrist outlets",
            "right_lean": "Right-leaning outlets",
            "international": "International coverage",
            "independent": "Independent & nonprofit",
        }

        for key in spectrum_order:
            text = cross_spectrum.get(key, "")
            if text:
                label = spectrum_labels.get(key, key)
                html += f'''
            <div class="spectrum-block scroll-reveal">
                <div class="spectrum-label">{label}</div>
                <div class="spectrum-text">{_escape_html(text)}</div>
            </div>
'''
        html += '</div>'

    # Top sources
    if sources:
        top_sources = extract_top_sources(sources)
        html += '<div class="sources-grid">'

        for source_name in top_sources:
            source_data = sources.get(source_name, {})
            context = get_source_context(source_name)
            context_html = (
                f'<div class="source-context">{_escape_html(context)}</div>'
                if context
                else ""
            )
            html += f'''
            <div class="source-item scroll-reveal">
                <span class="source-name">{_escape_html(source_name)}</span>
                {context_html}
            </div>
'''
        html += '</div>'

    html += '        </div>\n    </section>\n'
    return html


def _build_missing_section(icon_type: str, title: str) -> str:
    """Build placeholder section when story selection fails."""
    return f'''
    <section class="category-section" id="{icon_type}">
        <div class="category-wrap">
            <div class="category-header">
                {generate_svg_icon(icon_type)}
                <div>
                    <h2 class="category-title">{title}</h2>
                </div>
            </div>
            <p style="font-style: italic; opacity: 0.7;">
                No story selected for this category today. Check back tomorrow for the latest analysis.
            </p>
        </div>
    </section>
'''


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def write_html(html: str, output_path: str) -> None:
    """Write HTML to file with proper directory creation."""
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(html)


def print_summary(
    date_str: str,
    thread_story: Optional[Dict],
    gap_story: Optional[Dict],
    meanwhile_story: Optional[Dict],
) -> None:
    """Print summary of generated page to stdout."""
    print(f"\n=== Signal Board Daily Page Generated ===")
    print(f"Date: {date_str}")
    print(f"\nDaily Thread: {thread_story.get('title', 'Not selected')[:60] if thread_story else 'Not selected'}")
    print(f"Daily Gap:   {gap_story.get('title', 'Not selected')[:60] if gap_story else 'Not selected'}")
    print(f"Meanwhile:   {meanwhile_story.get('title', 'Not selected')[:60] if meanwhile_story else 'Not selected'}")
    print(f"\nHTML written to: docs/today/index.html")
    print("========================================\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Signal Board daily page from pipeline output"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selections without writing files",
    )
    parser.add_argument(
        "--input",
        default="docs/data/daily/latest.json",
        help="Path to pipeline output JSON",
    )
    parser.add_argument(
        "--output",
        default="docs/today/index.html",
        help="Output path for generated HTML",
    )

    args = parser.parse_args()

    # Load pipeline data
    pipeline_data = load_pipeline_data(args.input)

    # Extract data
    mega_stories = pipeline_data.get("mega_stories", [])
    local_regional = pipeline_data.get("local_regional_synthesis", {})

    # Select stories
    thread_story = select_daily_thread(mega_stories)
    gap_story = select_daily_gap(mega_stories, local_regional)
    meanwhile_story = select_meanwhile(mega_stories, local_regional)

    # Print summary
    date_str = pipeline_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    print_summary(date_str, thread_story, gap_story, meanwhile_story)

    if args.dry_run:
        print("Dry run mode: no files written.")
        return

    # Generate HTML
    html = build_html(pipeline_data, thread_story, gap_story, meanwhile_story)

    # Write output
    write_html(html, args.output)
    print(f"File written to {args.output}")


if __name__ == "__main__":
    main()
