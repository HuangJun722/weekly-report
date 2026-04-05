"""
生成全球互联网动态情报站 HTML 页面
"""
import json
import os
from datetime import datetime, timedelta
from jinja2 import Template

# 旧格式 category → event_types 映射
CATEGORY_MAP = {
    '融资': 'funding', '并购': 'ma', 'IPO': 'earnings',
    '财报': 'earnings', '战略': 'strategy', '其他': 'other',
    '上市': 'earnings', '扩张': 'strategy',
}

# insight_label 默认规则（按事件类型）
INSIGHT_LABEL_MAP = {
    'funding': '资金流向',
    'ma': '资金流向',
    'earnings': '背景补充',
    'strategy': '合作机会',
    'other': '背景补充',
}

# 被截断的垃圾字段（旧格式遗留）
TRUNCATED_JUNK = {
    'Show HN: I built a f', 'Big-Endian Testing w', 'April 2026 TLDR Setu',
    'Show HN: I built a frontp', 'Show HN: ctx – an Ag',
    'Samsung Magician dis', 'Google releases Gemm', 'Show HN: Apfel – The',
    'Decisions that erode', 'What Category Theory',
    'ESP32-S31: Dual-Core', 'Yeachan-Heo/oh-my-co', 'onyx-dot-app/onyx',
    'google-research/time', 'siddharthvaddem/open', 'dmtrKovalenko/fff.nv',
    'f/prompts.chat', 'sherlock-project/she',
}

def enrich(event):
    """统一事件格式，确保所有字段存在且有效"""
    # 统一 event_types（旧格式用 category）
    if 'event_types' not in event:
        cat = event.get('category', '其他')
        event['event_types'] = [CATEGORY_MAP.get(cat, 'other')]

    ev_type = event.get('event_types', ['other'])[0]

    # 统一新字段（从旧字段迁移）
    why = event.get('why_important', '')
    if why in TRUNCATED_JUNK or (len(why) < 15 and why != '待分析'):
        event['reason'] = event.get('title', '')[:60]
    elif why and why != '待分析':
        event.setdefault('reason', why)

    # 新字段默认值
    event.setdefault('summary_short', event.get('title', '')[:25])
    event.setdefault('reason', '待分析')
    event.setdefault('impact', event.get('impact_scope', '未知'))
    event.setdefault('insight_label', INSIGHT_LABEL_MAP.get(ev_type, '背景补充'))
    event.setdefault('level', 'C')
    event.setdefault('score', 5)
    event.setdefault('region', '未知')
    event.setdefault('companies', [])
    event.setdefault('source', '未知')

    # 清理旧格式遗留字段
    for old_key in ('summary', 'category', 'impact_range', 'impact_scope', 'why_important'):
        event.pop(old_key, None)

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
    print(f"OK: {len(events)} days, {total} events total, {len(signal_events)} high-value signals")

if __name__ == '__main__':
    generate_html()
