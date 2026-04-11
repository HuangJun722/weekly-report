"""
生成全球互联网动态情报站 HTML 页面
评分系统：基于 Galtung & Ruge 新闻价值理论 + 金融情报平台通用因子
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
        (r'\$([0-9,]+(?:\.\d+)?)\s*[Bb](?:illion)?', 1000),
        (r'€([0-9,]+(?:\.\d+)?)\s*[Mm](?:illion)?', 1),
        (r'\$([0-9,]+(?:\.\d+)?)\s*[Mm](?:illion)?', 1),
    ]
    for pat, mult in patterns:
        m = re.search(pat, title, re.I)
        if m:
            val = float(m.group(1).replace(',', '')) * mult
            return val
    return 0

def _format_amount(amount):
    """金额格式化，统一显示为 $XM 或 $XB"""
    if amount >= 1000:
        return f"${amount/1000:.0f}B"
    return f"${amount:.0f}M"

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

EVT_SCORE = {
    'ma':       2,
    'earnings': 2,
    'funding':  1,
    'strategy': 1,
    'other':    0,
}

REGION_WEIGHT = {
    '非洲': 1.30,
    '中东': 1.25,
    '亚太': 1.20,
    '拉美': 1.15,
    '欧洲': 1.00,
    '中资': 1.25,  # 中国科技巨头海外扩张，高情报价值
}

# 中资出海公司名单（用于识别"中资"区域）
CHINESE_CAPITAL_COMPANIES = {
    '字节', 'tiktok', 'byteDance', 'bytedance', '抖音',
    '腾讯', 'tencent', '微信',
    '阿里巴巴', 'alibaba', 'aliyun', 'lazada',
    '京东', 'jd.com', 'jd retail',
    '快手', 'kuaishou',
    '美团', 'meituan',
    '蚂蚁', 'ant group', 'antgroup', '支付宝', 'alipay',
    '拼多多', 'pinduoduo',
    '百度', 'baidu',
    '小米', 'xiaomi',
    '滴滴', 'didi',
    'shein', '希音',
    'temu',
    'oppo', 'vivo', 'realme',
    '传音', 'transsion', 'tecno',
    '比亚迪', 'byd',
}

# 亚太新增公司（提升区域关联性）
REGION_COMPANIES = {
    '亚太': {'cyberagent', 'square enix', 'vng', 'vnggroup', 'grab', 'gojek', 'sea group', 'shopee'},
    '欧洲': {'trendyol', 'hepsiburada', 'kaspi', 'olx', ' Allegro'},
}

# 用 \b 词边界避免子串误匹配
def _is_hot_industry(title_lower, reason_lower=''):
    combined = (title_lower + ' ' + reason_lower).lower()
    hot = {
        r'\bai\b', r'\bml\b', r'\bllm\b', r'\bgpt\b',
        r'\bfintech\b', r'\bfintech\b', r'\bhealth ?tech\b',
        r'\bbiotech\b', r'\bhealth ?tech\b',
        r'\bagritech\b', r'\bagri ?tech\b',
        r'\brobot\b', r'\bclimate ?tech\b',
        r'\bchips?\b', r'\bchipset\b',
    }
    hot.update({'AI', 'ML', '大模型', '金融科技', '机器人', '农业科技'})
    for kw in hot:
        if kw in combined:
            return True
    return False

def _has_top_investor(title_lower):
    investors = [
        'softbank', 'vision fund', 'mubadala', 'adia', 'temasek',
        'coatue', 'a16z', 'sequoia', 'index ventures',
        'thiel', 'founders fund', 'khosla', 'general atlantic',
    ]
    return any(inv in title_lower for inv in investors)

def _is_chinese_capital(event):
    """检测事件是否涉及中资出海公司"""
    title_lower = event.get('title', '').lower()
    reason_lower = event.get('why_important', '').lower()
    companies_lower = [c.lower() for c in event.get('companies', [])]
    combined = ' '.join([title_lower, reason_lower] + companies_lower)
    return any(kw.lower() in combined for kw in CHINESE_CAPITAL_COMPANIES)

def calculate_score(event):
    """多因子评分，clamp(1-10)，全部从数据推导"""
    title = event.get('title', '')
    title_lower = title.lower()
    ev_type = event.get('event_types', ['other'])[0]

    amount = _parse_amount(title)
    amt_pts = _amount_score(amount) if amount > 0 else 1
    type_pts = EVT_SCORE.get(ev_type, 0)
    region = event.get('region', '')
    region_mult = REGION_WEIGHT.get(region, 1.0)
    industry_pts = 1 if _is_hot_industry(title_lower, event.get('why_important', '')) else 0
    named_pts = 1 if event.get('companies') else 0
    investor_pts = 1 if _has_top_investor(title_lower) else 0

    raw = (amt_pts + type_pts + industry_pts + named_pts + investor_pts) * region_mult
    return max(round(min(raw, 10)), 1)

def enrich(event):
    """统一事件格式 + 自动评分"""
    if 'event_types' not in event:
        event['event_types'] = [CATEGORY_MAP.get(event.get('category', '其他'), 'other')]

    ev_type = event['event_types'][0]
    why = event.get('why_important', '')
    if why in TRUNCATED_JUNK or why == '待分析' or len(why) < 10:
        existing_reason = event.get('reason', '')
        if existing_reason and len(existing_reason) >= 10 and '⚠️' not in existing_reason and '待分析' not in existing_reason:
            pass
        else:
            # 生成中文 fallback
            fallback = {
                'funding': f"{event.get('region','该地区')}科技公司融资事件",
                'ma': f"{event.get('region','该地区')}科技公司并购/收购",
                'earnings': f"{event.get('region','该地区')}科技公司财报披露",
                'strategy': f"{event.get('region','该地区')}科技公司战略动态",
            }.get(ev_type, f"{event.get('region','该地区')}科技行业动态")
            event['reason'] = fallback
    else:
        event['reason'] = why

    event.setdefault('impact', event.get('impact_scope', '未知'))
    event.setdefault('insight_label', INSIGHT_LABEL_MAP.get(ev_type, '其他'))
    event.setdefault('region', '未知')
    event.setdefault('companies', [])
    event.setdefault('source', '未知')
    event['score'] = calculate_score(event)
    # 用于 Market Pulse 突出展示
    amt = _parse_amount(event.get('title', ''))
    event['display_amount'] = _format_amount(amt) if amt > 0 else ''

    # 检测中资出海：若涉及中国科技公司出海，追加"中资"标签
    is_chinese = _is_chinese_capital(event)
    event['is_chinese_capital'] = is_chinese
    if is_chinese:
        ev_type = event.get('event_types', ['other'])[0]
        event['insight_label'] = '中资出海'

    for old_key in ('summary', 'category', 'impact_range', 'impact_scope', 'why_important', 'summary_short', 'level'):
        event.pop(old_key, None)
    # 保留 date 字段用于 Market Pulse 日期权重
    if not event.get('date'):
        event['date'] = datetime.now().strftime('%Y-%m-%d')

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


def split_company_events(events):
    """将事件拆分为公司动态和通用热点"""
    company_events = []
    generic_events = []
    for date_str, evs in events.items():
        for e in evs:
            if e.get('is_company'):
                company_events.append(e)
            else:
                generic_events.append(e)
    # 分别按 score 排序
    company_events.sort(key=lambda x: x.get('score', 5), reverse=True)
    generic_events.sort(key=lambda x: x.get('score', 5), reverse=True)
    return company_events, generic_events

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
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    def _recency_boost(e):
        score = e.get('score', 5)
        d = e.get('date') or ''
        if d == today:
            return score + 4
        elif d == yesterday:
            return score + 3
        elif d >= week_ago:
            return score + 1
        return score
    result.sort(key=_recency_boost, reverse=True)
    return result[:20]

def build_weekly_summary(all_feed, signals, latest_date_events, all_events):
    """生成周报摘要：所有数字从 all_feed（今日全部）计算"""
    # ── 数字统计（从全部事件算，不只是高分信号）──────────────
    funding = sum(1 for e in all_feed if e.get('event_types', [''])[0] == 'funding')
    ma      = sum(1 for e in all_feed if e.get('event_types', [''])[0] == 'ma')
    earnings= sum(1 for e in all_feed if e.get('event_types', [''])[0] == 'earnings')
    strategy= sum(1 for e in all_feed if e.get('event_types', [''])[0] == 'strategy')
    total   = len(all_feed)

    # ── type_counts：动态生成筛选按钮用 ───────────────────
    type_counts = {
        '融资': funding, '并购': ma, '财报': earnings, '战略': strategy,
    }

    # 区域分布
    region_counts = {}
    for e in all_feed:
        r = e.get('region', '未知')
        if r != '未知':
            region_counts[r] = region_counts.get(r, 0) + 1
    region_counts = dict(sorted(region_counts.items(), key=lambda x: x[1], reverse=True))
    hot_region = max(region_counts, key=region_counts.get) if region_counts else ''

    # ── 金额计算（用于 headline）────────────────────���──────
    # 找最大融资事件
    funding_events = [e for e in all_feed if e.get('event_types', [''])[0] == 'funding']
    top_funding = max(funding_events, key=lambda x: x.get('score', 0), default=None)
    max_ma = next((e for e in all_feed if e.get('event_types', [''])[0] == 'ma'), None)

    # ── Headline ────────────────────────────────────────
    top = all_feed[0] if all_feed else None
    headline = ""
    if top:
        ev_type = top.get('event_types', [''])[0]
        company = top.get('companies', [''])[0] if top.get('companies') else ''
        top_region = top.get('region', '')
        amount = _parse_amount(top.get('title', ''))

        if ev_type == 'ma' and max_ma:
            amt_str = _format_amount(_parse_amount(max_ma.get('title', '')))
            mCompany = max_ma.get('companies', [''])[0] if max_ma.get('companies') else ''
            headline = f"{mCompany or top_region}达成{amt_str}并购，{region_counts.get(top_region, '')}起事件折射整合加速" if top_region else f"并购整合加速，本周至少{ma}起"
        elif ev_type == 'earnings':
            headline = f"{company or top_region or '本周'}财报数据公布，{earnings}起值得持续关注"
        elif amount > 0 and company:
            headline = f"{company} {_format_amount(amount)}融资刷新记录，{top_region or '新兴市场'}资本热度不减"
        elif amount > 0:
            headline = f"{_format_amount(amount)}融资领跑，{hot_region or '新兴市场'}资本保持活跃"
        elif company:
            headline = f"{company}成{hot_region or '本周'}焦点，{total}起事件折射多赛道并进"
        elif hot_region:
            headline = f"{hot_region}领跑本周新兴市场，{region_counts.get(hot_region,'')}起事件折射多赛道并进"
        else:
            headline = f"本周{total}条动态覆盖{len(region_counts)}个地区，多赛道资本活跃"
    else:
        headline = f"共{total}条动态"

    # ── Summary ─────────────────────────────────────────
    parts = []
    if hot_region and region_counts.get(hot_region):
        parts.append(f"{hot_region}事件最多（{region_counts[hot_region]}起），占今日大头。")
    if funding >= 3:
        tf = top_funding
        top_co = tf.get('companies', [''])[0] if tf and tf.get('companies') else ''
        top_amt = _format_amount(_parse_amount(tf.get('title', ''))) if tf else ''
        if top_co and top_amt:
            parts.append(f"融资仍是主旋律，共{funding}起，最大单笔{top_co} {top_amt}。")
        elif top_co:
            parts.append(f"融资仍是主旋律，共{funding}起，最大单笔来自{top_co}。")
        else:
            parts.append(f"融资仍是主旋律，共{funding}起。")
    elif funding >= 1:
        parts.append(f"有{funding}起融资落地。")
    if ma >= 1:
        parts.append(f"另有{ma}起并购，显示{hot_region or '该地区'}行业整合加速。")
    if earnings >= 1:
        parts.append(f"本周财报季有{earnings}起值得关注。")
    if strategy >= 1:
        parts.append(f"另有{strategy}起战略动态值得关注。")
    if not parts:
        parts.append(f"共{total}条动态，覆盖{', '.join(region_counts.keys()) if region_counts else '各地区'}。")
    summary = ' '.join(parts)

    # ── Market Pulse：始终取所有信号事件中评分最高的3条─────
    # Hero区域不变，始终显示TOP3（与主tab内容解耦）
    today_s = datetime.now().strftime('%Y-%m-%d')
    yesterday_s = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    week_ago_s = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    def _recency_boost_s(e):
        score = e.get('score', 0)
        d = e.get('date') or ''
        if d == today_s:
            return score + 4
        elif d == yesterday_s:
            return score + 3
        elif d >= week_ago_s:
            return score + 1
        return score
    sorted_signals = sorted(signals, key=_recency_boost_s, reverse=True) if signals else []
    mp_events = sorted_signals[:3]

    return {
        'total_events': total,
        'total_signals': len(signals),
        'funding': funding,
        'ma': ma,
        'earnings': earnings,
        'strategy': strategy,
        'regions': len(region_counts),
        'region_distribution': region_counts,
        'type_counts': type_counts,
        'headline': headline,
        'summary': summary,
        'top3': mp_events[:3],
    }

def generate_html():
    events = load_events()
    sorted_dates = sorted(events.keys(), reverse=True)

    # 主tab：最近一次有内容的采集批次（回退到昨天兜底）
    # 历史tab：除主tab批次之外的所有日期
    today_str = datetime.now().strftime('%Y-%m-%d')
    main_date = None
    main_events = []

    # 找最近一个有内容的批次
    for d in sorted_dates:
        evs = events.get(d, [])
        if evs:
            main_date = d
            main_events = evs
            break

    # 今天批次为空 → 回退到昨天
    if main_date == today_str and not main_events:
        for d in sorted_dates:
            if d != today_str:
                evs = events.get(d, [])
                if evs:
                    main_date = d
                    main_events = evs
                    break

    # 标题去重 + 按评分排序
    seen_titles = set()
    deduped = []
    for e in main_events:
        norm = re.sub(r'[^\w]', '', e.get('title', '').lower())
        if norm not in seen_titles and len(norm) > 10:
            seen_titles.add(norm)
            deduped.append(e)
    deduped.sort(key=lambda x: x.get('score', 5), reverse=True)
    all_feed = deduped

    # 公司动态单独处理
    company_events, generic_events = split_company_events(events)
    company_by_company = {}
    for e in company_events:
        name = e.get('company_name', '其他')
        company_by_company.setdefault(name, []).append(e)
    company_list = sorted(company_by_company.items(), key=lambda x: len(x[1]), reverse=True)

    # 历史tab：15天内除主tab批次之外的所有有内容日期
    cutoff = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
    history_dates = [d for d in sorted_dates if d >= cutoff and d != main_date]
    history = [(d, events.get(d, [])) for d in history_dates if events.get(d, [])]

    signals = get_signal_events(events)
    weekly = build_weekly_summary(all_feed, signals, main_events, events)
    # 公司动态也加入周报摘要
    weekly['company_count'] = len(company_events)
    weekly['company_list'] = company_list

    template = Template(open('scripts/template.html', 'r', encoding='utf-8').read())
    html = template.render(
        weekly=weekly,
        all_feed=all_feed,
        history=history,
        main_date=main_date,
        company_events=company_events,
        company_list=company_list,
        update_time=(datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M') + ' 北京时间',
    )

    os.makedirs('docs', exist_ok=True)
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"OK | 通用{len(generic_events)} 条 | 公司{len(company_events)} 条 | {len(history)} 天往期")

if __name__ == '__main__':
    generate_html()
