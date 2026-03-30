#!/usr/bin/env python3
"""
Format Signal Board daily data into an HTML email for Substack import.

Reads the daily JSON from data/daily/latest.json and outputs formatted HTML
that will be imported as a Substack draft post.

Substack accepts email imports at a secret address that auto-creates draft posts
from the email body. This script generates HTML formatted for that pipeline.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from html import escape


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


def get_editorial_fields(data):
    """Extract editorial fields from the daily data."""
    editorial = data.get('editorial', {})

    return {
        'headline': editorial.get('headline', ''),
        'accessible_headline': editorial.get('accessible_headline', ''),
        'subheadline': editorial.get('subheadline', ''),
        'synthesis': editorial.get('synthesis', ''),
        'cooperation_highlight': editorial.get('cooperation_highlight', ''),
        'coverage_gap_note': editorial.get('coverage_gap_note', ''),
        'thread_to_watch': editorial.get('thread_to_watch', ''),
        'date': data.get('date', ''),
    }


def sanitize_html(text):
    """Escape HTML special characters in text."""
    return escape(text)


def format_html_body(fields):
    """
    Format extracted fields into an HTML email body for Substack.

    The format is designed to be imported by Substack's email-to-post feature,
    which converts this HTML into a draft post.
    """

    date_str = fields['date']
    synthesis = sanitize_html(fields['synthesis'])
    cooperation = sanitize_html(fields['cooperation_highlight'])
    coverage_gap = sanitize_html(fields['coverage_gap_note'])
    thread = sanitize_html(fields['thread_to_watch'])

    # Parse date for readability
    try:
        date_obj = datetime.fromisoformat(date_str)
        formatted_date = date_obj.strftime('%B %d, %Y')
    except (ValueError, TypeError):
        formatted_date = date_str

    # Build the HTML email body
    # Substack's email import looks for <body> content to convert to post
    html = f"""<html>
<head>
    <meta charset="UTF-8">
    <title>{sanitize_html(fields['accessible_headline'])}</title>
</head>
<body>
<p><strong>{formatted_date}</strong></p>

<h2>{sanitize_html(fields['headline'])}</h2>

<p><em>{sanitize_html(fields['subheadline'])}</em></p>

<h3>Today's Synthesis</h3>
<p>{synthesis}</p>

<h3>Cooperation Highlight</h3>
<p>{cooperation}</p>

<h3>Coverage Gap</h3>
<p>{coverage_gap}</p>

<h3>Thread to Watch</h3>
<p>{thread}</p>

<hr>

<p><a href="https://signal-board.org/today/">Read full analysis at Signal Board</a></p>

</body>
</html>"""

    return html


def main():
    """Main entry point."""
    # Determine the data path - check multiple locations
    data_paths = [
        Path('data/daily/latest.json'),
        Path('public/data/daily/latest.json'),
    ]

    data_path = None
    for path in data_paths:
        if path.exists():
            data_path = path
            break

    if not data_path:
        print(f"Error: Could not find latest.json in any of {data_paths}", file=sys.stderr)
        sys.exit(1)

    # Load and process the data
    data = load_daily_json(data_path)
    fields = get_editorial_fields(data)

    # Validate required fields
    required = ['accessible_headline', 'synthesis', 'cooperation_highlight',
                'coverage_gap_note', 'thread_to_watch', 'date']
    missing = [f for f in required if not fields.get(f)]

    if missing:
        print(f"Error: Missing required fields: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # Output the formatted HTML to stdout
    html_body = format_html_body(fields)
    print(html_body)


if __name__ == '__main__':
    main()
