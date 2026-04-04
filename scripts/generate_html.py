"""
生成全球互联网动态情报站 HTML 页面
"""
import json
import os
from datetime import datetime, timedelta
from jinja2 import Template

def enrich(event):
    """确保事件有所有必要字段"""
    event.setdefault('why_important', event.get('summary', '待分析')[:25] if 'summary' in event else '待分析')
    event.setdefault('impact_scope', '未知')
    event.setdefault('companies', [])
    event.setdefault('level', 'C')
    event.setdefault('score', 5)
    event.setdefault('region', '未知')
    event.setdefault('event_types', ['other'])
    return event

def load_events():
    with open('data/events.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        grouped = {}
        for event in data:
            date = event.get('date', datetime.now().isoformat())[:10]
            grouped.setdefault(date, []).append(enrich(event))
        return grouped
    return {k: [enrich(e) for e in v] for k, v in data.items()}

def get_signal_events(events):
    """获取高价值信号事件：融资/并购/财报/战略（去重，按score排序，最多8条）"""
    seen = set()
    result = []
    for date in sorted(events.keys(), reverse=True):
        for event in events[date]:
            if event['url'] in seen:
                continue
            types = event.get('event_types', ['other'])
            if types and types[0] != 'other':
                seen.add(event['url'])
                result.append(event)
    result.sort(key=lambda x: x.get('score', 5), reverse=True)
    return result[:8]

def generate_html():
    events = load_events()
    sorted_dates = sorted(events.keys(), reverse=True)
    signal_events = get_signal_events(events)

    template = Template(open('scripts/template.html', 'r', encoding='utf-8').read())

    html = template.render(
        signal_events=signal_events,
        all_events=events,
        sorted_dates=sorted_dates,
        update_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )

    os.makedirs('docs', exist_ok=True)
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    total = sum(len(v) for v in events.values())
    print(f"✓ 生成完成：{len(events)} 天，共 {total} 条事件，{len(signal_events)} 条高价值信号")

if __name__ == '__main__':
    generate_html()
