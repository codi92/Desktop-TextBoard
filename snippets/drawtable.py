# drawtable.py: Output an HTML table with the specified number of rows and columns
# Usage: ~drawtable.py{rows:3;columns:4;border_color:#2196f3;border_width:2px}
# Parameters:
#   rows         - Number of table rows (default: 3, min: 1, max: 20)
#   columns      - Number of table columns (default: 3, min: 1, max: 20)
#   border_color - Table border color (default: #2196f3)
#   border_width - Table border width (default: 1px)
# Example: ~drawtable.py{rows:2;columns:5;border_color:red;border_width:3px}

import os

rows = int(os.environ.get("SNIPPET_ROWS", 3))
columns = int(os.environ.get("SNIPPET_COLUMNS", 3))
rows = max(1, min(rows, 20))
columns = max(1, min(columns, 20))
border_color = os.environ.get("SNIPPET_BORDER_COLOR", "#2196f3")
border_width = os.environ.get("SNIPPET_BORDER_WIDTH", "1px")

html = [f"<table border='0' cellpadding='6' style='border-collapse:collapse;background:#222;color:#d4d4d4;font-family:monospace;font-size:15px;border:{border_width} solid {border_color};'>"]
for r in range(rows):
    html.append("  <tr>")
    for c in range(columns):
        html.append(f"    <td style='border:{border_width} solid {border_color};'>{'R'+str(r+1)+'C'+str(c+1)}</td>")
    html.append("  </tr>")
html.append("</table>")

print("\n".join(html))
