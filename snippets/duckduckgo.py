# duckduckgo.py: Search DuckDuckGo using the HTML endpoint and print the top N results as HTML.
# Usage: ~duckduckgo.py{q:python cli search;r:5}
# Parameters:
#   q - The search query (required)
#
# Output: Top N DuckDuckGo results as HTML (title + snippet + link), or a fallback message.
# Notes: Handles Unicode and special characters robustly. Cleans DuckDuckGo redirect URLs. Prints raw HTML for debugging.

import os
import sys
import requests
from bs4 import BeautifulSoup
import urllib.parse

def html_escape(text):
    import html
    return html.escape(text)

query = os.environ.get("SNIPPET_Q", "").strip().lower()
    
if not query:
    print("[No search query provided]")
    sys.exit(1)

# Add support for SNIPPET_R (number of results to show)
r_param = os.environ.get("SNIPPET_R")
try:
    num_results = int(r_param) if r_param and str(r_param).isdigit() else 3
except Exception:
    num_results = 3

url = "https://html.duckduckgo.com/html/"
params = {"q": query}
headers = {"User-Agent": "Mozilla/5.0"}

try:
    resp = requests.get(url, params=params, headers=headers, timeout=10, allow_redirects=True)
    # Try both lxml and html.parser, fallback to html.parser if lxml fails
    try:
        soup = BeautifulSoup(resp.content, "lxml")
    except Exception:
        soup = BeautifulSoup(resp.content, "html.parser")
    results = soup.find_all("div", class_="result")
    if results:
        html = '<div style="font-family:monospace;font-size:15px;max-width:600px;word-break:break-word;white-space:pre-wrap;">'
        for first in results[:num_results]:
            title_tag = first.find("a", class_="result__a")
            snippet_tag = first.find("a", class_="result__snippet") or first.find("div", class_="result__snippet")
            href = title_tag['href'] if title_tag and title_tag.has_attr('href') else None
            title = title_tag.get_text(strip=True) if title_tag else None
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else None
            # Clean DuckDuckGo redirect URLs
            clean_url = href
            if href and href.startswith('//duckduckgo.com/l/?uddg='):
                parsed = urllib.parse.urlparse(href)
                qs = urllib.parse.parse_qs(parsed.query)
                uddg = qs.get('uddg', [None])[0]
                if uddg:
                    clean_url = urllib.parse.unquote(uddg)
            # Remove forced utf-8 encode/decode, rely on BeautifulSoup's parsing
            if title and clean_url:
                html += f'<a href="{html_escape(clean_url)}" style="color:#2196f3;text-decoration:none;font-weight:bold;">{html_escape(title)}</a><br>'
            if snippet:
                html += f'<span style="color:#aaa;">{html_escape(snippet)}</span><br>'
            if clean_url:
                html += f'<span style="color:#888;font-size:12px;">{html_escape(clean_url)}</span>'
            html += '<br><br>'
        html += '</div>'
        print(html)
    else:
        print(f'<div style="color:#f55;font-family:monospace;font-size:15px;">[No results found for {html_escape(query)}]</div>')
except Exception as e:
    print(f"[DuckDuckGo HTML search error: {e}]")
