# ~gpt.py: Query OpenAI GPT and print the response as plain text or HTML
# Example: `~gpt.py{prompt:Write a haiku about the sea}`
#
# <b>Attribute reference:</b>
#   - <span style='color:#4EC9B0'>prompt</span>: <span style='color:#D7BA7D'>Your question or prompt for GPT</span> (required)
#   - <span style='color:#4EC9B0'>model</span>: <span style='color:#D7BA7D'>openai model name</span> (optional, default: gpt-3.5-turbo)
#
# Requires: .env file in root dir with OPENAI_API_KEY=sk-...
import os
import sys
import json
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

api_key = os.environ.get('OPENAI_API_KEY')
api_base = os.environ.get('OPENAI_API_BASE', 'https://api.openai.com/v1/chat/completions')
prompt = os.environ.get('SNIPPET_PROMPT')
model = os.environ.get('SNIPPET_MODEL', 'gpt-3.5-turbo')
if not api_key:
    print('[Error: OPENAI_API_KEY not set in .env]')
    sys.exit(1)
if not prompt:
    print('[Error: No prompt provided. Use {prompt:...}]')
    sys.exit(1)
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
}
data = {
    'model': model,
    'messages': [
        {'role': 'user', 'content': prompt}
    ],
    'max_tokens': 256,
    'temperature': 0.7,
}
try:
    resp = requests.post(api_base, headers=headers, json=data, timeout=20)
    resp.raise_for_status()
    result = resp.json()
    answer = result['choices'][0]['message']['content'].strip()
    print(answer)
except Exception as e:
    print(f'[Error: {e}]')
