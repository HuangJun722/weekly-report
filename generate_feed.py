import json, datetime, html, hashlib, os

with open('data/events.json', 'r', encoding='utf-8') as f:
    events = json.load(f)

flattened = []
for date_str, day_events in events.items():
    for ev in day_events:
        ev['date_str'] = date_str
        flattened.append(ev)

flattened.sort(key=lambda x: x['date_str'], reverse=True)
flattened = flattened[:50]

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
feed_id = 'tag:weekly-report,2026:main'

feed = f'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>全球互联网百晓生 · 事件流</title>
  <subtitle>实时事件订阅源，基于情报站数据</subtitle>
  <id>{feed_id}</id>
  <updated>{now}</updated>
  <link href="https://weekly-report.ai/" rel="alternate"/>
  <link href="feed.xml" rel="self" type="application/atom+xml"/>
  <author><name>Global Internet Intelligence Station</name></author>
  <rights>CC BY-NC 4.0</rights>
'''

for ev in flattened:
    uid_base = ev.get('url', ev.get('title', '')) + ev['date_str']
    uid_hash = hashlib.sha1(uid_base.encode('utf-8')).hexdigest()[:8]
    entry_id = f'tag:weekly-report,2026:event-{uid_hash}'
    updated = ev['date_str'] + 'T00:00:00Z'
    title = html.escape(ev.get('title', '无标题'))
    url = ev.get('url', '')
    summary_parts = []
    if ev.get('reason'):
        summary_parts.append(f'<p>{html.escape(ev["reason"])}</p>')
    tags = []
    if ev.get('insight_label'):
        tags.append(f'标签：{html.escape(ev["insight_label"])}')
    if ev.get('event_types'):
        tags.append(f'类型：{", ".join(html.escape(t) for t in ev["event_types"])}')
    if ev.get('region'):
        tags.append(f'地区：{html.escape(ev["region"])}')
    if ev.get('level'):
        tags.append(f'级别：{html.escape(ev["level"])}')
    if tags:
        summary_parts.append(f'<p>{" | ".join(tags)}</p>')
    if ev.get('source'):
        summary_parts.append(f'<p>来源：{html.escape(ev["source"])}</p>')
    summary = ''.join(summary_parts)

    entry = f'''
  <entry>
    <title>{title}</title>
    <link href="{url}"/>
    <id>{entry_id}</id>
    <updated>{updated}</updated>
    <summary type="html">{summary}</summary>
  </entry>'''
    feed += entry

feed += '\n</feed>\n'

feed_path = 'docs/feed.xml'
os.makedirs(os.path.dirname(feed_path), exist_ok=True)
with open(feed_path, 'w', encoding='utf-8') as f:
    f.write(feed)
print(f'Feed generated: {feed_path}')
