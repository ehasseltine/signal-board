#!/usr/bin/env python3
"""
Format Signal Board daily data into an HTML email for Substack import.

Reads the daily JSON from data/daily/latest.json and outputs formatted HTML
designed to feel like a letter from someone who did the reading, not a
reformatted web dashboard.

Structure:
  1. Personal lead (newsletter_lead or generated from editorial)
  2. The Daily Thread (synthesis paragraph only, link to full)
  3. The Daily Gap (synthesis paragraph only, link to full)
  4. Meanwhile (2-3 cooperation highlights, link to full)
  5. Footer with links

Substack accepts email imports at a secret address that auto-creates draft
posts from the email body.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from html import escape


SITE_URL = "https://signal-board.org"


def load_daily_json(json_path):
    """Load the latest daily JSON file."""
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {json_path} not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)


def sanitize(text):
    """Escape HTML special characters."""
    return escape(text)


def paragraphs(text):
    """Convert plain text to HTML paragraphs, splitting on double newlines."""
    if not text:
        return ""
    parts = text.strip().split("\n\n")
    return "".join(f"<p>{sanitize(p.strip())}</p>" for p in parts if p.strip())


def format_newsletter(data):
    """Build the newsletter HTML from daily pipeline data."""
    editorial = data.get("editorial", {})
    story_syntheses = data.get("story_syntheses", [])
    cooperation = data.get("cooperation", {})
    summary = data.get("summary", {})
    date_str = data.get("date", "")

    # Parse date
    try:
        date_obj = datetime.fromisoformat(date_str)
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
    except (ValueError, TypeError):
        formatted_date = date_str

    total_stories = summary.get("total_stories", 0)
    sources_reporting = summary.get("sources_reporting", 0)
    coop_count = cooperation.get("total_cooperation_stories", 0)

    # Find story syntheses by role
    thread = next((s for s in story_syntheses if s.get("role") == "thread"), {})
    gap = next((s for s in story_syntheses if s.get("role") == "gap"), {})
    meanwhile = next((s for s in story_syntheses if s.get("role") == "meanwhile"), {})

    accessible_headline = editorial.get("accessible_headline", editorial.get("headline", "Signal Board"))
    newsletter_lead = editorial.get("newsletter_lead", "")

    # Fallback lead if newsletter_lead wasn't generated
    if not newsletter_lead:
        sub = editorial.get("subheadline", "")
        newsletter_lead = (
            f"Today Signal Board read {total_stories:,} articles from {sources_reporting} sources. "
            f"{sub}"
        )

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{sanitize(accessible_headline)}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #FFF8E7; font-family: Georgia, 'Times New Roman', serif;">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #FFF8E7;">
<tr><td align="center" style="padding: 32px 16px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%;">

<!-- HEADER -->
<tr><td style="padding: 0 0 24px 0;">
<p style="margin: 0; font-family: Georgia, serif; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: #8B7355;">{formatted_date}</p>
<h1 style="margin: 8px 0 0 0; font-family: Georgia, serif; font-size: 28px; line-height: 1.3; color: #1B2A4B; font-weight: 700;">Signal Board</h1>
</td></tr>

<!-- PERSONAL LEAD -->
<tr><td style="padding: 0 0 32px 0;">
<p style="margin: 0; font-family: Georgia, serif; font-size: 18px; line-height: 1.7; color: #1B2A4B;">{sanitize(newsletter_lead)}</p>
</td></tr>

<!-- DIVIDER -->
<tr><td style="padding: 0 0 28px 0;"><hr style="border: none; border-top: 1px solid #D4C5A9; margin: 0;"></td></tr>

<!-- THE DAILY THREAD -->
<tr><td style="padding: 0 0 28px 0;">
<p style="margin: 0 0 8px 0; font-family: -apple-system, Arial, sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #D94032;">The Daily Thread</p>
{paragraphs(thread.get("synthesis", ""))}
<p style="margin: 12px 0 0 0;"><a href="{SITE_URL}/today/#thread" style="color: #D94032; text-decoration: underline; font-family: -apple-system, Arial, sans-serif; font-size: 14px;">See how outlets framed it differently &rarr;</a></p>
</td></tr>

<!-- DIVIDER -->
<tr><td style="padding: 0 0 28px 0;"><hr style="border: none; border-top: 1px solid #D4C5A9; margin: 0;"></td></tr>

<!-- THE DAILY GAP -->
<tr><td style="padding: 0 0 28px 0;">
<p style="margin: 0 0 8px 0; font-family: -apple-system, Arial, sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #0B7A5E;">The Daily Gap</p>
{paragraphs(gap.get("synthesis", ""))}
<p style="margin: 12px 0 0 0;"><a href="{SITE_URL}/today/#gap" style="color: #D94032; text-decoration: underline; font-family: -apple-system, Arial, sans-serif; font-size: 14px;">Read the full framing comparison &rarr;</a></p>
</td></tr>

<!-- DIVIDER -->
<tr><td style="padding: 0 0 28px 0;"><hr style="border: none; border-top: 1px solid #D4C5A9; margin: 0;"></td></tr>

<!-- MEANWHILE -->
<tr><td style="padding: 0 0 28px 0;">
<p style="margin: 0 0 8px 0; font-family: -apple-system, Arial, sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #07743F;">Meanwhile: {coop_count} stories of people showing up</p>
{paragraphs(meanwhile.get("synthesis", ""))}
<p style="margin: 12px 0 0 0;"><a href="{SITE_URL}/today/#meanwhile" style="color: #D94032; text-decoration: underline; font-family: -apple-system, Arial, sans-serif; font-size: 14px;">See all {coop_count} cooperation stories &rarr;</a></p>
</td></tr>

<!-- DIVIDER -->
<tr><td style="padding: 0 0 28px 0;"><hr style="border: none; border-top: 1px solid #D4C5A9; margin: 0;"></td></tr>

<!-- FOOTER -->
<tr><td style="padding: 0;">
<p style="margin: 0 0 16px 0; font-family: Georgia, serif; font-size: 15px; line-height: 1.7; color: #5C5040;">Signal Board reads {sources_reporting} sources every day across the political spectrum, across borders, and across languages. The full daily analysis, with framing comparisons, source cards, and the complete data, is always free at signal-board.org.</p>

<p style="margin: 0 0 8px 0;"><a href="{SITE_URL}/today/" style="color: #D94032; text-decoration: underline; font-family: -apple-system, Arial, sans-serif; font-size: 14px;">Read the full analysis &rarr;</a></p>
<p style="margin: 0 0 20px 0;"><a href="{SITE_URL}/archive/" style="color: #D94032; text-decoration: underline; font-family: -apple-system, Arial, sans-serif; font-size: 14px;">Browse the archive &rarr;</a></p>

<p style="margin: 0; font-family: -apple-system, Arial, sans-serif; font-size: 12px; color: #8B7355;">No tracking. No ads. No algorithms.</p>
</td></tr>

</table>
</td></tr>
</table>

</body>
</html>"""

    return html, accessible_headline


def main():
    """Main entry point."""
    data_paths = [
        Path("data/daily/latest.json"),
        Path("public/data/daily/latest.json"),
    ]

    data_path = None
    for path in data_paths:
        if path.exists():
            data_path = path
            break

    if not data_path:
        print(f"Error: Could not find latest.json in any of {data_paths}", file=sys.stderr)
        sys.exit(1)

    data = load_daily_json(data_path)

    # Validate minimum required fields
    if not data.get("story_syntheses"):
        print("Error: No story_syntheses in daily data. Run synthesize.py first.", file=sys.stderr)
        sys.exit(1)

    html_body, subject = format_newsletter(data)

    # Output mode: --subject prints just the subject line,
    # --html (default) prints the full HTML body
    if len(sys.argv) > 1 and sys.argv[1] == "--subject":
        print(subject)
    else:
        print(html_body)


if __name__ == "__main__":
    main()
