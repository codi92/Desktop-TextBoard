# ~peyno_block_diagram.py: Render a step-based block diagram as SVG from JSON input
# Usage: ~peyno_block_diagram.py{json:...}

import os, json, sys
from pathlib import Path

def render_svg(diagram):
    BLOCK_WIDTH, BLOCK_HEIGHT, V_SPACING, H_SPACING = 140, 48, 48, 60
    DECISION_WIDTH, DECISION_HEIGHT = 80, 60
    positions, maxX, maxY = {}, 0, 0

    def layout(stepId, x, y):
        nonlocal maxX, maxY
        if stepId in positions:
            return
        positions[stepId] = (x, y)
        maxX, maxY = max(maxX, x), max(maxY, y)
        step = diagram['steps'].get(stepId)
        if not step:
            return
        if step['type'] == 'decision' and 'branches' in step:
            for i, (branch, target_id) in enumerate(step['branches'].items()):
                dx = (i - (len(step['branches']) - 1) / 2) * H_SPACING
                layout(target_id, x + dx, y + V_SPACING + DECISION_HEIGHT / 2)
        elif 'next' in step:
            layout(step['next'], x, y + V_SPACING + BLOCK_HEIGHT / 2)

    layout(diagram['start'], 0, 0)

    svg = []

    def draw_arrow(x1, y1, x2, y2, label=None):
        midX, midY = (x1 + x2) / 2, (y1 + y2) / 2
        path = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#333" stroke-width="2" marker-end="url(#arrow)"/>'
        if label:
            path += f'<text x="{midX+8}" y="{midY-4}" font-size="13" fill="#333">{label}</text>'
        return path

    for step_id, (x, y) in positions.items():
        step = diagram['steps'].get(step_id)
        if step['type'] == 'decision':
            for branch, target_id in step.get('branches', {}).items():
                if target_id not in positions:
                    continue
                to_x, to_y = positions[target_id]
                svg.append(draw_arrow(x + DECISION_WIDTH/2, y + DECISION_HEIGHT, to_x + BLOCK_WIDTH/2, to_y, branch))
        elif 'next' in step:
            target_id = step['next']
            if target_id in positions:
                to_x, to_y = positions[target_id]
                svg.append(draw_arrow(x + BLOCK_WIDTH/2, y + BLOCK_HEIGHT, to_x + BLOCK_WIDTH/2, to_y))

    for step_id, (x, y) in positions.items():
        step = diagram['steps'].get(step_id)
        if step['type'] == 'start':
            svg.append(f'<ellipse cx="{x+BLOCK_WIDTH/2}" cy="{y+BLOCK_HEIGHT/2}" rx="{BLOCK_WIDTH/2}" ry="{BLOCK_HEIGHT/2}" fill="#bdf" stroke="#333"/>')
            svg.append(f'<text x="{x+BLOCK_WIDTH/2}" y="{y+BLOCK_HEIGHT/2+5}" text-anchor="middle" font-size="16">{step.get("label", "Start")}</text>')
        elif step['type'] == 'end':
            svg.append(f'<ellipse cx="{x+BLOCK_WIDTH/2}" cy="{y+BLOCK_HEIGHT/2}" rx="{BLOCK_WIDTH/2}" ry="{BLOCK_HEIGHT/2}" fill="#fbb" stroke="#333"/>')
            svg.append(f'<text x="{x+BLOCK_WIDTH/2}" y="{y+BLOCK_HEIGHT/2+5}" text-anchor="middle" font-size="16">{step.get("label", "End")}</text>')
        elif step['type'] == 'process':
            svg.append(f'<rect x="{x}" y="{y}" width="{BLOCK_WIDTH}" height="{BLOCK_HEIGHT}" rx="10" fill="#efe" stroke="#333"/>')
            svg.append(f'<text x="{x+BLOCK_WIDTH/2}" y="{y+BLOCK_HEIGHT/2+5}" text-anchor="middle" font-size="16">{step.get("label", step_id)}</text>')
        elif step['type'] == 'decision':
            cx, cy = x + DECISION_WIDTH/2, y + DECISION_HEIGHT/2
            svg.append(f'<polygon points="{cx},{y} {x+DECISION_WIDTH},{cy} {cx},{y+DECISION_HEIGHT} {x},{cy}" fill="#ffd" stroke="#333"/>')
            svg.append(f'<text x="{cx}" y="{cy+5}" text-anchor="middle" font-size="15">{step.get("label", "?")}</text>')

    pad = 40
    minX = min(x for x, _ in positions.values())
    minY = min(y for _, y in positions.values())
    width = (maxX - minX) + BLOCK_WIDTH + pad * 2
    height = maxY + BLOCK_HEIGHT + pad * 2

    return f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" style="background:#fafaff"><defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#333"/></marker></defs><g transform="translate({pad - minX},{pad - minY})">{''.join(svg)}</g></svg>'''.replace("\n", "")

if __name__ == "__main__":
    raw_json = os.environ.get("SNIPPET_JSON", "").strip()
    if not raw_json:
        print("<pre style='color:red'>Missing input: SNIPPET_JSON</pre>")
        sys.exit(1)

    try:
        diagram = json.loads(raw_json)
        print(render_svg(diagram))
    except Exception as e:
        print(f"<pre style='color:red'>Invalid JSON: {e}</pre>")
        sys.exit(1)
