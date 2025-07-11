# ~text.py: Example snippet to show passed attributes as HTML
# Example: ~text.py{name:joe;password:doe}
import os

name = os.environ.get('SNIPPET_NAME', 'unknown')
password = os.environ.get('SNIPPET_PASSWORD', 'unknown')

print(f"<b>Name:</b> <span style='color:#4EC9B0'>{name}</span><br>")
print(f"<b>Password:</b> <span style='color:#CE9178'>{password}</span>")
