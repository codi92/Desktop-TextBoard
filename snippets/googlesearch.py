# ~googlesearch.py: Search Google and print the top result links and snippets as colorized HTML
# Example: `~googlesearch.py{q:python async example}`
#
# <b>Attribute reference:</b>
#   - <span style='color:#4EC9B0'>q</span>: <span style='color:#D7BA7D'>Your search query</span> (required)
#   - <span style='color:#4EC9B0'>num</span>: <span style='color:#D7BA7D'>Number of results</span> (optional, default: 3)
#
# Note: This uses the SerpAPI service. You need a SERPAPI_KEY in your .env file.
# If a BASE_URL is set in .env, it will be used as the search endpoint.
import os
import sys
import requests
from pathlib import Path

root = Path(__file__).parent.parent
env_path = root / '.env'
if env_path.exists():
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                os.environ.setdefault(k, v)

api_key = os.environ.get('SERPAPI_KEY')
query = os.environ.get('SNIPPET_Q')
num = int(os.environ.get('SNIPPET_NUM', '3'))
base_url = os.environ.get('SERPAPI_BASE_URL', 'https://serpapi.com/search')
if not api_key:
    print('[Error: SERPAPI_KEY not set in .env]')
    sys.exit(1)
if not query:
    print('[Error: No query provided. Use {q:...}]')
    sys.exit(1)

params = {
    'q': query,
    'api_key': api_key,
    'num': num,
    'engine': 'google',
}
try:
    resp = requests.get(base_url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    results = data.get('organic_results', [])
    if not results:
        print('[No results found]')
    html = []
    html.append('<style>\na[href^="http"]:hover { text-decoration: underline; cursor: pointer; }\n</style>')
    for r in results[:num]:
        title = r.get('title','')
        url = r.get('link','')
        snippet = r.get('snippet','')
        html.append(f'<div style="margin-bottom:1em">'
                   f'<b style="color:#4EC9B0;font-size:1.08em">{title}</b><br>'
                   f'<a href="{url}" style="color:#569CD6;text-decoration:underline" target="_blank">{url}</a><br>'
                   f'<span style="color:#B5CEA8">{snippet}</span>'
                   f'</div>')
    print(''.join(html))
except Exception as e:
    print(f'[Error: {e}]')
