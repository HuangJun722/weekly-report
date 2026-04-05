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
    """统一事件格式，确保所有事件都有中文 reason"""
    # 统一 event_types
    if 'event_types' not in event:
        cat = event.get('category', '其他')
        event['event_types'] = [CATEGORY_MAP.get(cat, 'other')]

    ev_type = event.get('event_types', ['other'])[0]

    # reason: 优先用 AI 分析，否则用标题（确保所有事件都有中文备注）
    why = event.get('why_important', '')
    if why in TRUNCATED_JUNK or why == '待分析' or len(why) < 10:
        event['reason'] = event.get('title', '')[:50]
    elif why:
        event['reason'] = why
    else:
        event['reason'] = event.get('title', '')[:50]

    event.setdefault('impact', event.get('impact_scope', '未知'))
    event.setdefault('insight_label', INSIGHT_LABEL_MAP.get(ev_type, '背景补充'))
    event.setdefault('level', 'C')
    event.setdefault('score', 5)
    event.setdefault('region', '未知')
    event.setdefault('companies', [])
    event.setdefault('source', '未知')

    for old_key in ('summary', 'category', 'impact_range', 'impact_scope', 'why_important', 'summary_short'):
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
    """去重后按 score 排序，最多20条"""
    seen = set()
    result = []
    for date in sorted(events.keys(), reverse=True):
        for event in events[date]:
            if event['url'] not in seen:
                seen.add(event['url'])
                if event.get('event_types', ['other'])[0] != 'other':
                    result.append(event)
    result.sort(key=lambda x: x.get('score', 5), reverse=True)
    return result[:20]

def build_weekly_summary(signals, all_events):
    """生成周报摘要"""
    all_days = sorted(all_events.keys(), reverse=True)
    total_events = sum(len(v) for v in all_events.values())

    # 信号统计
    sig_urls = {e['url'] for e in signals}
    funding = sum(1 for e in signals if e.get('event_types', [''])[0] == 'funding')
    ma = sum(1 for e in signals if e.get('event_types', [''])[0] == 'ma')
    earnings = sum(1 for e in signals if e.get('event_types', [''])[0] == 'earnings')
    strategy = sum(1 for e in signals if e.get('event_types', [''])[0] == 'strategy')

    # 区域覆盖
    regions_covered = len({e.get('region', '未知') for events_list in all_events.values() for e in events_list})

    # 一句话总结
    region_counts = {}
    for e in signals:
        r = e.get('region', '未知')
        region_counts[r] = region_counts.get(r, 0) + 1
    hot_region = max(region_counts, key=region_counts.get) if region_counts else ''

    parts = []
    if funding >= 3: parts.append(f"{hot_region}融资活跃（{funding}起）" if hot_region else f"融资活跃（{funding}起）")
    elif funding >= 1: parts.append(f"{funding}起融资")
    if ma >= 1: parts.append(f"{ma}起并购")
    if earnings >= 1: parts.append(f"{earnings}起财报")
    takeaway = "、".join(parts) if parts else f"共{total_events}条动态"

    return {
        'total_events': total_events,
        'total_signals': len(signals),
        'funding': funding,
        'ma': ma,
        'earnings': earnings,
        'strategy': strategy,
        'regions': regions_covered,
        'days': len(all_days),
        'takeaway': takeaway,
        'top3': signals[:3],
    }

def is_monday():
    """判断今天是否周一（北京时间）"""
    return datetime.now().weekday() == 0

def generate_html():
    events = load_events()
    sorted_dates = sorted(events.keys(), reverse=True)
    signals = get_signal_events(events)
    latest_date = sorted_dates[0] if sorted_dates else None

    # 今日重点信号
    today_feature = signals[0] if signals else None

    # 今日全部动态（信号 + 非信号，按 score 排序）
    sig_urls = {e['url'] for e in signals}
    today_non_sig = [e for e in events.get(latest_date, []) if e['url'] not in sig_urls]
    all_feed = signals + today_non_sig
    all_feed.sort(key=lambda x: x.get('score', 5), reverse=True)

    # 历史（7天内，除今天）
    cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    history_dates = [d for d in sorted_dates if d >= cutoff and d != latest_date]
    history = [(d, events.get(d, [])) for d in history_dates]

    # 周报摘要：始终生成，作为 hero 区域的数据来源
    weekly = build_weekly_summary(signals, events)

    template = Template(open('scripts/template.html', 'r', encoding='utf-8').read())
    html = template.render(
        weekly=weekly,
        today_feature=today_feature,
        all_feed=all_feed,
        history=history,
        update_time=datetime.now().strftime('%Y-%m-%d %H:%M'),
    )

    os.makedirs('docs', exist_ok=True)
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    wstr = f"周一报" if weekly else "平日视图"
    print(f"OK [{wstr}] | {len(all_feed)} 条 | {len(history)} 天往期")

if __name__ == '__main__':
    generate_html()
