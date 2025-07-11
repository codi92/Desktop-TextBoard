# ~postjson.py: Output a syntax-highlighted JSON block for DesktopTextBoard
# Example: ~postjson.py
import json
import re

post = {
    "user": "alice",
    "message": "Hello, world!",
    "timestamp": "2025-07-08T12:34:56"
}

json_str = json.dumps(post, indent=2, ensure_ascii=False)

# Simple JSON syntax highlighter using HTML spans
# Colors: key=#9CDCFE, string=#CE9178, number=#B5CEA8, punctuation=#D4D4D4

def highlight_json(json_str):
    def repl(match):
        key, string, number, punct = match.group(1), match.group(2), match.group(3), match.group(4)
        if key:
            return f'<span style="color:#9CDCFE">{key}</span>'
        if string:
            return f'<span style="color:#CE9178">{string}</span>'
        if number:
            return f'<span style="color:#B5CEA8">{number}</span>'
        if punct:
            return f'<span style="color:#D4D4D4">{punct}</span>'
        return match.group(0)
    # Regex: key, string, number, punctuation
    pattern = r'("[^"]*": )|("[^"]*")|(\b\d+\b)|([{}\[\]:,])'
    return re.sub(pattern, repl, json_str)

highlighted = highlight_json(json_str)

print(f"<pre style='background:#1e1e1e;color:#d4d4d4;border:1px solid #333;padding:8px;font-family:Consolas,monospace;font-size:1em'>{highlighted}</pre>")
