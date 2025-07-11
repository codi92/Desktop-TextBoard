# format_url.py: Output a formatted HTML link with color and optional display name
# Usage: ~format_url.py{url:https://example.com;name:Example;collor:blue}
# Parameters:
#   url    - The URL to link to (default: https://example.com)
#   name   - The display text for the link (default: the URL)
#   collor - The link color (named or any CSS color, default: blue)
# Example: ~format_url.py{url:https://github.com;name:GitHub;collor:teal}

import os

# Get parameters from environment variables
url = os.environ.get("SNIPPET_URL", "https://example.com")
name = os.environ.get("SNIPPET_NAME", "").strip()
color = os.environ.get("SNIPPET_COLLOR", "blue").lower()

# Supported color names
color_map = {
    "blue": "#2196f3",
    "red": "#e53935",
    "green": "#43a047",
    "orange": "#fb8c00",
    "purple": "#8e24aa",
    "teal": "#00897b",
    "pink": "#d81b60",
    "yellow": "#fbc02d",
    "white": "#fff",
    "black": "#222",
    "white": "#fff",
}

html_color = color_map.get(color, color)  # fallback to raw value if not in map

# Output a formatted HTML link
if name:
    print(f'<a href="{url}" style="color:{html_color};text-decoration:underline;">{name}</a>')
else:
    print(f'<a href="{url}" style="color:{html_color};text-decoration:underline;">{url}</a>')
