# ~now.py: Print current date, time, weekday, and ISO week in plain text or with format
# Example: `~now.py`  
# Example: `~now.py{show:date;format:%d/%m/%Y}`  
# Example: `~now.py{show:time}`  
#  
# <b>Attribute reference:</b>
#   - <span style='color:#4EC9B0'>show</span>: <span style='color:#D7BA7D'>date</span>, <span style='color:#D7BA7D'>time</span>, <span style='color:#D7BA7D'>weekday</span>, <span style='color:#D7BA7D'>week</span>, or <span style='color:#D7BA7D'>all</span> (default: <span style='color:#D7BA7D'>all</span>)
#   - <span style='color:#4EC9B0'>format</span>: <span style='color:#D7BA7D'>strftime format string</span> (applies if only one field is shown)
import os
from datetime import datetime

show = os.environ.get('SNIPPET_SHOW', 'all').lower()
fmt = os.environ.get('SNIPPET_FORMAT', None)
mono = os.environ.get('SNIPPET_MONOCHTOME', 'false').lower() in ("true", "1", "yes")
now = datetime.now()

show_set = set(s.strip() for s in show.replace(',', ';').split(';') if s.strip())
if not show_set or show_set == {'all'}:
    show_set = {'date', 'time', 'weekday', 'week'}
else:
    show_set.discard('all')

lines = []
if 'date' in show_set:
    date_fmt = fmt if fmt and len(show_set) == 1 else '%Y-%m-%d'
    val = now.strftime(date_fmt)
    if not mono:
        val = f"<span style='color:#4EC9B0'>{val}</span>"
    lines.append(val)
if 'time' in show_set:
    time_fmt = fmt if fmt and len(show_set) == 1 else '%H:%M:%S'
    val = now.strftime(time_fmt)
    if not mono:
        val = f"<span style='color:#D7BA7D'>{val}</span>"
    lines.append(val)
if 'weekday' in show_set:
    val = f"Weekday: {now.strftime('%A')}"
    if not mono:
        val = f"<span style='color:#B5CEA8'>{val}</span>"
    lines.append(val)
if 'week' in show_set or 'isoweek' in show_set:
    val = f"ISO Week: {now.strftime('%G-W%V')}"
    if not mono:
        val = f"<span style='color:#C586C0'>{val}</span>"
    lines.append(val)

print("<br>".join(lines) if not mono else "\n".join(lines))
