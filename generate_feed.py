import datetime, html, hashlib, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT / 'scripts'
os.chdir(ROOT)
sys.path.insert(0, str(SCRIPTS_DIR))
from generate_html import build_display_context
from view_selectors import select_feed_events

context = build_display_context()
feed_date = context['main_date']
MAX_FEED_EVENTS = 5


def text_value(value):
    return str(value or '').strip()


def first_text(*values):
    for value in values:
        text = text_value(value)
        if text:
            return text
    return ''


def display_source(ev):
    source = first_text(ev.get('display_source'), ev.get('source_detail'), ev.get('publisher'), ev.get('source'), '未知来源')
    raw_source = text_value(ev.get('source'))
    if raw_source and raw_source != source:
        return f'{source}（{raw_source}）'
    return source


def entry_title(ev):
    return first_text(ev.get('display_title'), ev.get('summary_short'), ev.get('reason'), ev.get('title'), '无标题')


def xml_attr(value):
    return html.escape(text_value(value), quote=True)


def xml_text(value):
    return html.escape(text_value(value), quote=False)


feed_events, fallback_feed_date = select_feed_events(
    context['today_events'],
    context.get('all_events_for_list', []),
)
if fallback_feed_date:
    feed_date = fallback_feed_date


def entry_summary(ev):
    parts = []
    reason = text_value(ev.get('reason'))
    impact = text_value(ev.get('display_impact') or ev.get('impact'))
    if impact == '未知':
        impact = ''
    original_title = text_value(ev.get('original_title') or ev.get('title'))
    title = entry_title(ev)

    if original_title and original_title != title:
        parts.append(f'<p><strong>原题：</strong>{html.escape(original_title)}</p>')
    if reason:
        parts.append(f'<p><strong>为什么重要：</strong>{html.escape(reason)}</p>')
    if impact:
        parts.append(f'<p><strong>影响：</strong>{html.escape(impact)}</p>')

    meta = []
    if ev.get('insight_label'):
        meta.append(f'标签：{html.escape(text_value(ev.get("insight_label")))}')
    if ev.get('event_types'):
        meta.append(f'类型：{", ".join(html.escape(str(t)) for t in ev["event_types"])}')
    if ev.get('region'):
        meta.append(f'地区：{html.escape(text_value(ev.get("region")))}')
    if ev.get('company_name'):
        meta.append(f'公司：{html.escape(text_value(ev.get("company_name")))}')
    meta.append(f'来源：{html.escape(display_source(ev))}')
    parts.append(f'<p>{" | ".join(meta)}</p>')
    return ''.join(parts)

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
feed_id = 'tag:weekly-report,2026:main'

feed = f'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>全球互联网百晓生 · 事件流</title>
  <subtitle>高价值事件推送，复用情报站每日事件卡片</subtitle>
  <id>{feed_id}</id>
  <updated>{now}</updated>
  <link href="https://weekly-report.ai/" rel="alternate"/>
  <link href="feed.xml" rel="self" type="application/atom+xml"/>
  <author><name>Global Internet Intelligence Station</name></author>
  <rights>CC BY-NC 4.0</rights>
'''

for ev in feed_events[:MAX_FEED_EVENTS]:
    entry_date = (ev.get('date') or feed_date or '')[:10]
    uid_base = ev.get('url', ev.get('title', '')) + entry_date
    uid_hash = hashlib.sha1(uid_base.encode('utf-8')).hexdigest()[:8]
    entry_id = f'tag:weekly-report,2026:event-{uid_hash}'
    updated = entry_date + 'T00:00:00Z'
    title = xml_text(entry_title(ev))
    url = xml_attr(ev.get('url', ''))
    summary = html.escape(entry_summary(ev), quote=False)

    entry = f'''
  <entry>
    <title>{title}</title>
    <link href="{url}"/>
    <id>{xml_text(entry_id)}</id>
    <updated>{updated}</updated>
    <summary type="html">{summary}</summary>
  </entry>'''
    feed += entry

feed += '\n</feed>\n'

feed_path = ROOT / 'docs' / 'feed.xml'
os.makedirs(feed_path.parent, exist_ok=True)
with open(feed_path, 'w', encoding='utf-8') as f:
    f.write(feed)
print(f'Feed generated: {feed_path}')
