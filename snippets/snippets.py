# ~snippets.py: List all available snippets with descriptions and usage examples
# Example: `~snippets.py`  
# Example: `~snippets.py{now.py}`  
#  
# <b>Attribute reference:</b>
#   - <span style='color:#4EC9B0'>snippet</span>: <span style='color:#D7BA7D'>name of a snippet file (e.g. now.py)</span> (optional, to filter or show details for a specific snippet)
import os
import re
import sys

snippets_dir = os.path.join(os.path.dirname(__file__))
files = [f for f in os.listdir(snippets_dir) if f.endswith('.py')]

# Check for snippet filter via environment variable or sys.argv (for compatibility)
snippet_filter = None
if 'SNIPPET_SHOW' in os.environ:
    snippet_filter = os.environ['SNIPPET_SHOW'].strip()
elif len(sys.argv) > 1:
    arg = sys.argv[1].strip()
    # Accept both '{show:now.py}' and 'show=now.py' forms
    if arg.startswith('{') and arg.endswith('}'):
        inner = arg[1:-1].strip()
        if inner.lower().startswith('show:'):
            snippet_filter = inner[5:].strip()
    elif '=' in arg:
        k, v = arg.split('=', 1)
        if k.lower() == 'show':
            snippet_filter = v.strip()
    else:
        snippet_filter = arg

html = []
if snippet_filter:
    html.append("<b>Snippet Details:</b><br><ul style='margin-left:0.5em'>")
else:
    html.append("<b>Available Snippets:</b><br><ul style='margin-left:0.5em'>")
for fname in sorted(files):
    if snippet_filter and fname != snippet_filter:
        continue
    path = os.path.join(snippets_dir, fname)
    desc = ""
    examples = []
    attributes = []
    # Try to extract description, examples, and attribute reference from the first comment lines
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith('#'):
                    m = re.match(r'#\s*~?([\w_\-]+\.py)\s*:\s*(.*)', line)
                    if m:
                        desc = m.group(2)
                    elif 'example' in line.lower():
                        # Extract code in backticks for colorizing
                        code_match = re.findall(r'`([^`]+)`', line)
                        if code_match:
                            for code in code_match:
                                examples.append(f"<code style='color:#4EC9B0;background:#232323;padding:1px 4px;border-radius:3px'>{code}</code>")
                        else:
                            # Fallback: just show the line
                            examples.append(f"<span style='color:#6A9955'>{line.strip('#').strip()}</span>")
                    elif 'attribute reference' in line.lower():
                        # Start collecting attribute lines
                        attributes.append("<br><span style='color:#B5CEA8;font-size:0.95em'><b>Attributes:</b></span>")
                elif line.strip().startswith('#') and ('`' in line):
                    # Attribute lines with backticks
                    attr_line = re.sub(r'`([^`]+)`', r"<code style='color:#D7BA7D;background:#232323;padding:1px 4px;border-radius:3px'>\1</code>", line.strip('#').strip())
                    attributes.append(f"<span style='color:#B5CEA8;font-size:0.95em'>{attr_line}</span>")
                elif line.strip() and not line.strip().startswith('#'):
                    break
    except Exception as e:
        desc = f"[Error reading: {e}]"
    html.append(f"<li><b>{fname}</b>: {desc}")
    if examples:
        html.append("<br><span style='color:#6A9955;font-size:0.95em'>Usage: " + ' '.join(examples) + "</span>")
    if attributes:
        html.append(''.join(attributes))
    html.append("</li>")
    if snippet_filter:
        break  # Only show the first match if filtering
html.append("</ul>")
print(''.join(html))
