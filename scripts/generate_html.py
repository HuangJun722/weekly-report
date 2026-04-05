"""
生成全球互联网动态情报站 HTML 页面
评分系统：基于 Galtung & Ruge 新闻价值理论 + 金融情报平台通用因子
核心因子：金额规模(对数) · 事件类型 · 地区权重 · 行业相关性 · 公司质量
"""
import json
import os
import re
from datetime import datetime, timedelta
from jinja2 import Template

CATEGORY_MAP = {
    '融资': 'funding', '并购': 'ma', 'IPO': 'earnings',
    '财报': 'earnings', '战略': 'strategy', '其他': 'other',
    '上市': 'earnings', '扩张': 'strategy',
}
INSIGHT_LABEL_MAP = {
    'funding': '融资', 'ma': '并购',
    'earnings': '财报', 'strategy': '战略', 'other': '其他',
}
TRUNCATED_JUNK = {
    'Show HN: I built a f', 'Big-Endian Testing w', 'April 2026 TLDR Setu',
    'Show HN: I built a frontp', 'Show HN: ctx – an Ag',
    'Samsung Magician dis', 'Google releases Gemm', 'Show HN: Apfel – The',
    'Decisions that erode', 'What Category Theory',
    'ESP32-S31: Dual-Core', 'Yeachan-Heo/oh-my-co', 'onyx-dot-app/onyx',
    'google-research/time', 'siddharthvaddem/open', 'dmtrKovalenko/fff.nv',
    'f/prompts.chat', 'sherlock-project/she',
}

# ─── 评分因子 ───────────────────────────────────────────────

def _parse_amount(title):
    """从标题提取金额（单位：M美元），返回浮点数"""
    patterns = [
        (r'\$(\d+(?:\.\d+)?)\s*[Bb](?:illion)?', 1000),
        (r'€(\d+(?:\.\d+)?)\s*[Mm](?:illion)?', 1),
        (r'\$(\d+(?:\.\d+)?)\s*[Mm](?:illion)?', 1),
    ]
    for pat, mult in patterns:
        m = re.search(pat, title, re.I)
        if m:
            return float(m.group(1)) * mult
    return 0

# 金额分段（单位：M美元）→ 基础分 1-6
AMOUNT_BUCKETS = [
    (0,      5,    1),
    (5,      20,   2),
    (20,     100,  3),
    (100,    500,  4),
    (500,    1000, 5),
    (1000,   float('inf'), 6),
]

def _amount_score(amount):
    for lo, hi, pts in AMOUNT_BUCKETS:
        if lo <= amount < hi:
            return pts
    return 0

# 事件类型 → 基础加成（相同金额下，M&A 信号意义更大）
EVT_SCORE = {
    'ma':       2,   # 并购：战略整合信号
    'earnings': 2,   # IPO/财报：市场验证信号
    'funding':  1,   # 融资：最常见
    'strategy': 1,   # 战略：方向性信号
    'other':    0,
}

# 地区 → 权重因子（新兴市场情报价值更高）
REGION_WEIGHT = {
    '非洲': 1.30,
    '中东': 1.25,
    '亚太': 1.20,
    '拉美': 1.15,
    '欧洲': 1.00,
}

# 行业 → 权重因子（热点行业信号更密集）
HOT_INDUSTRIES = {
    'AI', 'ML', '大模型', '大模型', 'LLM',
    '金融科技', 'fintech', 'health', 'healthtech',
    'biotech', 'bio', 'climate', 'agritech',
    '机器人', 'robot', 'edge computing', '半导体',
}

# 顶级 VC 名单（主权基金、顶级机构）
TOP_INVESTORS = {
    'softbank', 'vision fund', 'mubadala', 'ADIA', 'SADIA',
    'sovereign', 'temasek', 'gia', 'coatue', 'a16z',
    'sequoia', 'index', 'accel', 'general Atlantic',
    'thiel', 'founders fund', 'khosla',
}

def calculate_score(event):
    """多因子评分：clamp(1-10)，全部从数据推导，不依赖预设"""
    title = event.get('title', '')
    ev_type = event.get('event_types', ['other'])[0]

    # 维度一：金额规模（对数刻度，分段映射）
    amount = _parse_amount(title)
    amt_pts = _amount_score(amount)
    if amount == 0:
        amt_pts = 1  # 无金额事件最低1分

    # 维度二：事件类型加成
    type_pts = EVT_SCORE.get(ev_type, 0)

    # 维度三：地区权重
    region = event.get('region', '')
    region_mult = REGION_WEIGHT.get(region, 1.0)

    # 维度四：行业热度
    title_lower = title.lower()
    reason_lower = event.get('why_important', '').lower()
    combined = title_lower + ' ' + reason_lower
    industry_pts = 1 if any(k.lower() in combined for k in HOT_INDUSTRIES) else 0

    # 维度五：公司质量
    companies = [c.lower() for c in event.get('companies', [])]
    # 有公司名
    named_pts = 1 if companies else 0
    # 顶级投资人（从标题判断）
    investor_pts = 1 if any(inv in title_lower for inv in TOP_INVESTORS) else 0

    raw = (amt_pts + type_pts + industry_pts + named_pts + investor_pts) * region_mult
    score = round(min(max(raw, 1), 10))
    return max(score, 1)

def enrich(event):
    """统一事件格式 + 自动评分"""
    if 'event_types' not in event:
        cat = event.get('category', '其他')
        event['event_types'] = [CATEGORY_MAP.get(cat, 'other')]

    ev_type = event.get('event_types', ['other'])[0]

    why = event.get('why_important', '')
    if why in TRUNCATED_JUNK or why == '待分析' or len(why) < 10:
        event['reason'] = event.get('title', '')[:50]
    elif why:
        event['reason'] = why
    else:
        event['reason'] = event.get('title', '')[:50]

    event.setdefault('impact', event.get('impact_scope', '未知'))
    event.setdefault('insight_label', INSIGHT_LABEL_MAP.get(ev_type, '背景补充'))
    event.setdefault('region', '未知')
    event.setdefault('companies', [])
    event.setdefault('source', '未知')

    # 自动评分（覆盖任何预设值）
    event['score'] = calculate_score(event)

    for old_key in ('summary', 'category', 'impact_range', 'impact_scope', 'why_important', 'summary_short', 'level'):
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
    """生成周报摘要：headline + summary + region_distribution"""
    all_days = sorted(all_events.keys(), reverse=True)
    total_events = sum(len(v) for v in all_events.values())

    funding = sum(1 for e in signals if e.get('event_types', [''])[0] == 'funding')
    ma = sum(1 for e in signals if e.get('event_types', [''])[0] == 'ma')
    earnings = sum(1 for e in signals if e.get('event_types', [''])[0] == 'earnings')

    # 区域分布
    region_counts = {}
    for e in signals:
        r = e.get('region', '未知')
        region_counts[r] = region_counts.get(r, 0) + 1
    region_counts = {k: v for k, v in region_counts.items() if k != '未知'}
    hot_region = max(region_counts, key=region_counts.get) if region_counts else ''

    # ── Headline：单行判断语 ──────────────────────────────
    top = signals[0] if signals else None
    headline = ""
    if top:
        company = top.get('companies', [''])[0] if top.get('companies') else ''
        top_region = top.get('region', '')  # top 信号的地区
        amount = _parse_amount(top.get('title', ''))
        amount_str = f"${amount:.0f}M" if amount else ''

        ev_type = top.get('event_types', [''])[0]
        if ev_type == 'ma':
            headline = f"{company or top_region}并购加速，{region_counts.get(top_region, '')}起事件折射行业整合趋势" if top_region else "行业整合信号持续"
        elif ev_type == 'earnings':
            headline = f"{company or top_region}市场数据公布，本周财报季值得持续关注" if top_region else "财报季来临"
        elif company and amount_str:
            headline = f"{company} {amount_str}融资刷新记录，{top_region or '新兴市场'}资本热度不减"
        elif company:
            headline = f"{company}成为{top_region or '本周'}最受关注标的，{funding}起融资密集落地"
        elif top_region:
            headline = f"{top_region}领跑本周新兴市场，{region_counts.get(top_region,'')}起事件折射多赛道并进"
        else:
            headline = f"本周{total_events}条动态覆盖{len(region_counts)}个地区，多赛道资本活跃"
    else:
        headline = f"共{total_events}条动态，{', '.join(region_counts.keys()) if region_counts else '各地区'}保持关注"

    # 区域卡片：按事件数量降序排列
    region_distribution = dict(sorted(region_counts.items(), key=lambda x: x[1], reverse=True))

    # ── Summary：今日描述（2-3句话）─────────────────────────
    summary_parts = []

    if hot_region and region_counts.get(hot_region):
        summary_parts.append(f"{hot_region}事件最多（{region_counts[hot_region]}起），占今日大头。")

    if funding >= 3:
        summary_parts.append(f"融资仍是主旋律，共{funding}起，最大单笔来自{top.get('companies', ['未知'])[0] if top else '未知'}。")
    elif funding >= 1:
        summary_parts.append(f"有{funding}起融资落地。")

    if ma >= 1:
        summary_parts.append(f"另有{ma}起并购，显示{hot_region or '该地区'}行业整合加速。")

    if earnings >= 1:
        summary_parts.append(f"本周财报季有{earnings}起值得关注。")

    regions_str = '、'.join(region_counts.keys()) if region_counts else '各地区'
    if not summary_parts:
        summary_parts.append(f"共{total_events}条动态，覆盖{regions_str}。")

    summary = ' '.join(summary_parts)

    return {
        'total_events': total_events,
        'total_signals': len(signals),
        'funding': funding,
        'ma': ma,
        'earnings': earnings,
        'regions': len(region_counts),
        'days': len(all_days),
        'headline': headline,
        'summary': summary,
        'region_distribution': region_distribution,
        'top3': signals[:3],
    }

def generate_html():
    events = load_events()
    sorted_dates = sorted(events.keys(), reverse=True)
    signals = get_signal_events(events)
    latest_date = sorted_dates[0] if sorted_dates else None

    # 全部动态（信号优先，按 score 排序）
    sig_urls = {e['url'] for e in signals}
    other_events = [e for e in events.get(latest_date, []) if e['url'] not in sig_urls]
    all_feed = signals + other_events
    all_feed.sort(key=lambda x: x.get('score', 5), reverse=True)

    # 历史（7天内，除今天）
    cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    history_dates = [d for d in sorted_dates if d >= cutoff and d != latest_date]
    history = [(d, events.get(d, [])) for d in history_dates]

    # 周报摘要
    weekly = build_weekly_summary(signals, events)

    template = Template(open('scripts/template.html', 'r', encoding='utf-8').read())
    html = template.render(
        weekly=weekly,
        all_feed=all_feed,
        history=history,
        update_time=datetime.now().strftime('%Y-%m-%d %H:%M'),
    )

    os.makedirs('docs', exist_ok=True)
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"OK | {len(all_feed)} 条 | {len(history)} 天往期")

if __name__ == '__main__':
    generate_html()
