# fontawesome_icon.py: Download a Font Awesome SVG icon by icon name and output as HTML <svg>
# Usage: ~fontawesome_icon.py{icon:github;style:brands;size:16}
# Parameters:
#   icon  - The Font Awesome icon name (e.g. 'github', 'user', 'arrow-right')
#   style - Icon style: 'solid', 'regular', or 'brands' (default: solid, will try all if not found)
#   size  - Icon size in px (optional, powers of two: 16, 32, 64, 128, 256, 512, 1024; default: 64)
#   (In DesktopTextBoard, you can scale the icon by placing the cursor on it and pressing + or - to change the size in powers of two.)
# Example: ~fontawesome_icon.py{icon:github;style:brands;size:16}
#
# Output: Cleaned SVG with requested size, suitable for direct HTML embedding.

import os
import sys
import requests
import re

icon = os.environ.get("SNIPPET_ICON", "github").strip().lower()
style = os.environ.get("SNIPPET_STYLE", "").strip().lower()
size = os.environ.get("SNIPPET_SIZE", "").strip()
if not icon:
    print("[No icon provided]")
    sys.exit(1)

styles = ["solid", "regular", "brands"]
if style in styles:
    styles = [style] + [s for s in styles if s != style]

found = False
for s in styles:
    svg_url = f"https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/{s}/{icon}.svg"
    resp = requests.get(svg_url, timeout=10)
    if resp.status_code == 200:
        svg = resp.text
        # Clean SVG for embedding
        svg = re.sub(r'<\?xml.*?\?>', '', svg, flags=re.DOTALL)
        svg = re.sub(r'<!DOCTYPE.*?>', '', svg, flags=re.DOTALL)
        svg = svg.strip()
        # Only allow sizes that are powers of two from 16 to 1024 (2^4 to 2^10)
        allowed_sizes = [2 ** n for n in range(4, 11)]
        # Always override width/height with size if provided, else default to 64 (2^6)
        if size.isdigit():
            sz = int(size)
            if sz not in allowed_sizes:
                sz = 64  # fallback to default if not allowed
        else:
            sz = 64  # 2^6, default to 64px if not specified
        # Extract viewBox from SVG (required for scaling)
        viewbox_match = re.search(r'viewBox="([^"]*)"', svg)
        viewbox = viewbox_match.group(1) if viewbox_match else None
        if not viewbox:
            orig_viewbox = re.search(r'<svg[^>]*viewBox="([^"]*)"', resp.text)
            if orig_viewbox:
                viewbox = orig_viewbox.group(1)
        # Build a new SVG tag with only the correct attributes
        svg_body = re.sub(r'<svg[^>]*>', '', svg, count=1)
        svg_body = re.sub(r'</svg>', '', svg_body, count=1)
        new_svg_tag = f'<svg width="{sz}" height="{sz}" style="width:{sz}px;height:{sz}px;"'
        if viewbox:
            new_svg_tag += f' viewBox="{viewbox}"'
        new_svg_tag += '>'
        svg = new_svg_tag + svg_body + '</svg>'
        print(svg)
        found = True
        break
if not found:
    print(f"[No icon found for '{icon}' in styles: {', '.join(styles)}]")
