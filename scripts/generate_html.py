"""
生成全球互联网动态情报站 HTML 页面
评分系统：基于 Galtung & Ruge 新闻价值理论 + 金融情报平台通用因子
"""
import argparse
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

# ─── 预设公司名单 ─────────────────────────────────────────────

PRESET_COMPANIES = {
    '中资': ['ByteDance/TikTok', 'Tencent', 'Alibaba', 'JD.com', 'Kuaishou', 'Ant Group', 'Meituan'],
    '亚太': ['Kakao', 'Naver', 'Rakuten', 'Sea Limited', 'Grab', 'Gojek', 'VNG Group', 'Yahoo', 'Cyberagent'],
    '欧洲': ['Adyen', 'Zalando', 'Allegro', 'Trendyol'],
    '中东': ['Noon', 'Careem', 'Tabby', 'Kaspi.kz'],
    '非洲': ['Jumia', 'Konga'],
    '拉美': ['MercadoLibre', 'Rappi'],
}

# ─── Fallback reason 生成 ───────────────────────────────────

# 常见监控公司名（用于从标题提取当事人）
# 标题中包含这些词时直接用作 subject
KNOWN_COMPANIES = {
    'tabby', 'grab', 'gojek', 'noon', 'jumia', 'konga', 'trendyol',
    'rakuten', 'adyen', 'zalando', 'mercado', 'rappi', 'meesho',
    'swiggy', 'zomato', 'deliveroo', 'gorillas', 'getir',
    'ant group', 'alibaba', 'tencent', 'bytedance', 'tiktok',
    'jd.com', 'jd.com', 'kuaishou', 'shein', 'temu',
    'mercadoli', 'nubank', 'dlocal', 'paystack', 'flutterwave',
    'uber', 'lyft', 'grab', 'ola', 'bolt', 'inDrive',
    'flipkart', 'amazon', 'shopee', 'lazada',
    'stc pay', 'urpay', 'tala', 'chime', 'klarna', 'marqeta',
    'allegro', 'olx', 'letgo', '不成',
}

# 中资出海关键词
CHINESE_OUTBOUND = {
    '字节', 'tiktok', 'bytedance', '抖音', 'temu', 'shein',
    '希音', '腾讯', 'tencent', '阿里', 'alibaba', '蚂蚁',
    'ant group', '京东', 'jd.com', '快手', 'kuaishou', '拼多多',
    '美团', 'meituan', '滴滴', 'didi', '百度', 'baidu',
}

def _extract_subject(title):
    """从标题提取当事人公司/产品名，优先级：已知公司 > 正则模式"""
    # 清理标题（去掉来源后缀）
    clean = re.sub(r'\s*[-|]\s*(Forbes|Reuters|TechCrunch|WIRED|BBC|CNBC|Bloomberg|Al Arabiya|cairoscene| african businessNewswire|Business Wire|PRNewswire|Euronews|Arab News).*$', '', title, flags=re.I)
    clean = clean.strip()

    # 策略1：已知名公司匹配（最优先）
    title_lower = clean.lower()
    for kw in sorted(KNOWN_COMPANIES, key=len, reverse=True):  # 长的先匹配
        if kw in title_lower:
            # 从标题中提取原始大小写版本
            idx = title_lower.find(kw)
            # 往回找到词边界（只吃字母不吃数字，避免 "000 MercadoLibre"）
            start = max(0, idx - 1)
            while start > 0 and title[start-1].isalpha():
                start -= 1
            # 往后取词
            end = idx + len(kw)
            while end < len(title) and (title[end].isalnum() or title[end] in ' -'):
                end += 1
            name = title[start:end].strip().rstrip(' -').strip()
            if len(name) >= 2:
                return name

    # 策略2：正则提取
    patterns = [
        # "X Raises/Closes/Secures $NNNM" → X 是主角
        (r'^([A-Z][A-Za-z0-9\s&\.,\'\-\u2019]+?)\s+(?:raises|closes|secures|wins|gets|attracts|draws)\s+', 1),
        # "X Raises $NNNM in/on Y" → X 是主角
        (r'^([A-Z][A-Za-z0-9\s&\.,\'\-\u2019]+?)\s+raises?\s+\$', 1),
        # "X acquires/buys Y" → X 是主角
        (r'^([A-Z][A-Za-z0-9\s&\.,\'\-\u2019]+?)\s+(?:acquires|acquisition|buys|purchases|merges)', 1),
        # "X to acquire Y" → X 是主角
        (r'^([A-Z][A-Za-z0-9\s&\.,\'\-\u2019]+?)\s+to\s+acquire', 1),
        # "X posts/reports QN revenue/profit" → X 是主角
        (r'^([A-Z][A-Za-z0-9\s&\.\-\u2019]+?)[\'’]?(?:\s+\w+)?\s+(?:posts|reports|beats|misses|revenue|profit|earnings)', 1),
        # "X launches/expands into Y" → X 是主角
        (r'^([A-Z][A-Za-z0-9\s&\.\-\u2019]+?)\s+(?:launches|expands|enters|rolls out|partners)', 1),
        # "X valued at $Y" → X 是主角
        (r'^([A-Z][A-Za-z0-9\s&\.\-\u2019]+?)\s+valued\s+at', 1),
        # "X files for IPO" → X 是主角
        (r'^([A-Z][A-Za-z0-9\s&\.\-\u2019]+?)\s+(?:files|plans|ready)\s+(?:for|to)', 1),
    ]
    for pat, group in patterns:
        m = re.search(pat, clean, re.I)
        if m:
            name = m.group(group).strip().rstrip(',;:').strip()
            # 清理常见前缀词
            skip = {'why ', 'how ', 'what ', 'who ', 'where ', 'when ', 'this ', 'the '}
            for s in skip:
                if name.lower().startswith(s):
                    name = name[len(s):].strip()
            if len(name) >= 2 and len(name) <= 40:
                return name

    return None

def _build_reason(title, ev_type, region, company_name=None):
    """生成 fallback reason：必须包含当事人 + 事件 + 金额（从标题提取）"""
    subject = _extract_subject(title) or company_name
    r = region or ''

    # 金额提取
    amt = _parse_amount(title)
    amt_str = _format_amount(amt) if amt > 0 else ''

    # 中资出海检测
    is_chinese = any(kw.lower() in title.lower() for kw in CHINESE_OUTBOUND)

    if subject:
        # 包含公司名的 reason
        if ev_type == 'funding':
            if amt_str:
                reason = f"{subject}获{amt_str}融资"
            else:
                reason = f"{subject}完成融资"
        elif ev_type == 'ma':
            # 尝试提取收购对象
            m = re.search(r'(?:acquires?|buys|purchases)\s+([A-Z][A-Za-z0-9\s&\-]+?)(?:\s+for|\s+in|\s*$|\.)', title, re.I)
            target = m.group(1).strip() if m else None
            if target and len(target) < 30:
                reason = f"{subject}收购{target}"
            else:
                reason = f"{subject}达成并购"
        elif ev_type == 'earnings':
            # 尝试提取增长数字
            m = re.search(r'(up|down|growth|jumped|rose|fell|slumped)\s+(\d+(?:\.\d+)?%?)', title, re.I)
            if m:
                reason = f"{subject}营收{m.group(1)} {m.group(2)}"
            else:
                reason = f"{subject}发布财报"
        elif ev_type == 'strategy':
            m = re.search(r'(?:launches|expands|enters|partners|files for IPO|plans to go)', title, re.I)
            if m:
                reason = f"{subject}战略新动向"
            else:
                reason = f"{subject}战略调整"
        else:
            # 从标题提取首段代替"有新动态"（零成本提高信息量）
            title_short = re.split(r'[,;、。.!！?？]', title)[0].strip()
            if len(title_short) > 40:
                title_short = title_short[:40] + '…'
            if len(title_short) >= 10:
                if title_short.startswith(subject) and len(title_short) > len(subject):
                    reason = title_short  # 标题以公司名开头，直接用标题
                elif title_short != subject:
                    reason = f"{subject}：{title_short}"
                else:
                    reason = f"{subject}有新动态"
            else:
                reason = f"{subject}有新动态"
    else:
        # 没有任何信息时的最后兜底：用标题前段代替泛化模板
        # 取第一个句子（句号/问号/叹号前），最长 35 字
        title_short = re.split(r'[.。!！?？]', title)[0].strip()
        if len(title_short) > 35:
            title_short = title_short[:35] + '…'
        if len(title_short) >= 8:
            reason = f"{r or '全球'}：{title_short}"
        elif is_chinese:
            for kw in ['tiktok', 'shein', 'temu', 'bytedance', 'alibaba', 'tencent', 'ant', 'jd.com', 'kuaishou']:
                if kw in title.lower():
                    reason = f"{kw.capitalize()}有新动态"
                    break
            else:
                reason = "中资科技公司动态"
        elif r:
            templates = {
                'funding': f"{r}科技公司融资{amt_str}落地" if amt_str else f"{r}科技公司融资",
                'ma':      f"{r}科技公司并购",
                'earnings':f"{r}科技公司财报",
                'strategy':f"{r}科技公司战略",
                'other':   f"{r}科技动态",
            }
            reason = templates.get(ev_type, f"{r}科技动态")
        else:
            reason = "全球科技动态"

    return reason

# ─── Enrich ─────────────────────────────────────────────────

def enrich(event):
    """统一事件格式 + 自动评分"""
    if 'event_types' not in event:
        event['event_types'] = [CATEGORY_MAP.get(event.get('category', '其他'), 'other')]

    ev_type = event['event_types'][0]
    region = event.get('region', '')
    title = event.get('title', '')

    # 判断 reason 是否有效（通用模板也算无效，必须重新生成）
    why = event.get('why_important', '')
    existing_reason = event.get('reason', '')
    # 通用模板 reason 列表——这些是 AI 生成的烂 reason，必须重新生成
    GENERIC_REASONS = {
        # 短模式（子串匹配 — 覆盖 "亚太科技公司财报披露" 等程序生成变体）
        '科技动态', '财报披露', '融资事件', '战略动态', '并购/收购', '金额待确认',
        '战略调整', '有新动态', '科技公司融资', '科技公司并购', '科技公司战略',
        '科技行业动态', '的高估值',
        # 完整短语保留兼容
        '中东科技公司融资事件，金额待确认',
        '中资科技动态', '亚太科技动态', '欧洲科技动态', '中东科技动态',
        '非洲科技动态', '拉美科技动态',
        '中资科技公司战略动态',
        '中资科技公司财报披露',
        '中资科技公司并购/收购',
        '中资科技巨头持续增长，巩固行业地位，吸引更多合作资源',
        '中资电商巨头海外拓展成功，为国际市场ICT合作带来新机遇',
        '中资视频平台增长强劲提升行业影响力，吸引资金和合作关注',
        '中资金融科技巨头战略布局，吸引资金流入，提升行业关注度',
        '亚太地区出行平台拓展外卖业务版图，加强本地服务能力',
    }
    is_generic = any(p in existing_reason for p in GENERIC_REASONS)
    reason_ok = (existing_reason
                 and len(existing_reason) >= 10
                 and '⚠️' not in existing_reason
                 and '待分析' not in existing_reason
                 and existing_reason not in TRUNCATED_JUNK
                 and not is_generic)
    why_ok = why and len(why) >= 10 and why not in TRUNCATED_JUNK

    if why_ok:
        event['reason'] = why
    elif reason_ok:
        pass  # 保留 AI 生成的 reason
    else:
        # 生成有信息量的 fallback：提取公司名 + 事件类型
        event['reason'] = _build_reason(title, ev_type, region, event.get('company_name'))

    # summary_short fallback：AI 没生成时用 reason 兜底
    ss = event.get('summary_short', '')
    if not ss or len(ss) < 8 or ss[:25] == title[:25]:
        event['summary_short'] = event.get('reason', '')

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

    for old_key in ('summary', 'category', 'impact_range', 'impact_scope', 'why_important', 'level'):
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
    """
    将事件拆分为公司动态和通用热点
    - 公司动态只保留7天内，不过滤
    - 通用热点：排除other类型和评分<5的事件
    """
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    company_events = []
    generic_events = []

    for date_str, evs in events.items():
        for e in evs:
            if e.get('is_company') and date_str >= week_ago:
                # 公司动态：只保留7天内的，不过滤
                company_events.append(e)
            elif not e.get('is_company'):
                # 通用事件：排除other类型和低评分
                score = e.get('score', 0)
                ev_type = e.get('event_types', ['other'])[0]
                if ev_type == 'other' or score < 5:
                    continue
                generic_events.append(e)

    # 按时间倒序，同一天按评分排序
    company_events.sort(key=lambda x: (x.get('date', ''), x.get('score', 0)), reverse=True)
    generic_events.sort(key=lambda x: (x.get('date', ''), x.get('score', 0)), reverse=True)
    return company_events, generic_events

def get_signal_events(events):
    """
    获取信号事件：
    1. 只取最近7天内的信号事件
    2. 排除中资出海
    3. 排除other类型
    4. 排除低评分（<5）事件
    5. 按日期倒序排序
    """
    seen = set()
    result = []

    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    for date in sorted(events.keys(), reverse=True):
        # 只处理最近7天内的日期
        if date < week_ago:
            continue

        for event in events[date]:
            if event['url'] in seen:
                continue
            seen.add(event['url'])

            # 排除中资出海
            if event.get('is_chinese_capital'):
                continue

            # 只取信号事件（排除other类型）
            ev_type = event.get('event_types', ['other'])[0]
            if ev_type == 'other':
                continue

            # 排除低评分事件（评分<5视为低质量）
            score = event.get('score', 0)
            if score < 5:
                continue

            result.append(event)

    return result  # 已经在日期倒序遍历，返回即有序

def build_weekly_summary(all_feed, signals, latest_date_events, all_events):
    """生成周报摘要：排除中资出海，只展示真正的"非中美"动态"""
    # 排除中资出海（中资有独立标签页）
    non_chinese = [e for e in all_feed if not e.get('is_chinese_capital')]
    # ── 数字统计 ───────────────────────────────────────────
    funding = sum(1 for e in non_chinese if e.get('event_types', [''])[0] == 'funding')
    ma      = sum(1 for e in non_chinese if e.get('event_types', [''])[0] == 'ma')
    earnings= sum(1 for e in non_chinese if e.get('event_types', [''])[0] == 'earnings')
    strategy= sum(1 for e in non_chinese if e.get('event_types', [''])[0] == 'strategy')
    total   = len(non_chinese)

    # ── type_counts：动态生成筛选按钮用 ───────────────────
    type_counts = {
        '融资': funding, '并购': ma, '财报': earnings, '战略': strategy,
    }

    # 区域分布
    region_counts = {}
    for e in non_chinese:
        r = e.get('region', '未知')
        if r != '未知':
            region_counts[r] = region_counts.get(r, 0) + 1
    region_counts = dict(sorted(region_counts.items(), key=lambda x: x[1], reverse=True))
    hot_region = max(region_counts, key=region_counts.get) if region_counts else ''

    # ── 金额计算（用于 headline）───────────────────────
    # 找最大融资事件
    funding_events = [e for e in non_chinese if e.get('event_types', [''])[0] == 'funding']
    top_funding = max(funding_events, key=lambda x: x.get('score', 0), default=None)
    max_ma = next((e for e in non_chinese if e.get('event_types', [''])[0] == 'ma'), None)

    # ── Headline ────────────────────────────────────────
    # 用趋势描述，不用单一事件（避免"说亚太最强但Top3全是欧洲"的尴尬）
    parts_hl = []
    if funding > 0:
        parts_hl.append(f"融资{int(funding)}起")
    if ma > 0:
        parts_hl.append(f"并购{int(ma)}起")
    if earnings > 0:
        parts_hl.append(f"财报{int(earnings)}起")
    if hot_region and region_counts.get(hot_region):
        parts_hl.append(f"{hot_region}{region_counts[hot_region]}起")
    headline = "、".join(parts_hl) if parts_hl else f"共{int(total)}条动态"
    if len(region_counts) > 1:
        headline += f"覆盖{len(region_counts)}地区"

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

    # ── Market Pulse：最近3天的优质信号事件─────
    # 优先今天 > 昨天 > 前天，按评分排序
    today_s = datetime.now().strftime('%Y-%m-%d')
    yesterday_s = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    two_days_ago_s = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')

    # 按优先级分组
    today_signals = [e for e in signals if e.get('date') == today_s]
    yesterday_signals = [e for e in signals if e.get('date') == yesterday_s]
    two_days_ago_signals = [e for e in signals if e.get('date') == two_days_ago_s]

    # 今天优先，然后昨天，然后前天
    mp_events = today_signals[:7]
    if len(mp_events) < 7:
        need = 7 - len(mp_events)
        mp_events.extend(yesterday_signals[:need])
    if len(mp_events) < 7:
        need = 7 - len(mp_events)
        mp_events.extend(two_days_ago_signals[:need])

    mp_events = mp_events[:7]

    # ── P0 Agent：读取 AI 趋势分析，覆盖程序摘要 ──
    try:
        summary_path = 'data/summary.json'
        if os.path.exists(summary_path):
            with open(summary_path, 'r', encoding='utf-8') as sf:
                ai_summaries = json.load(sf)
            today_s = datetime.now().strftime('%Y-%m-%d')
            if today_s in ai_summaries:
                ai_text = ai_summaries[today_s].strip()
                if len(ai_text) >= 20:
                    summary = ai_text  # 用 AI 生成的趋势分析代替程序摘要
    except Exception:
        pass  # 降级：保留程序生成摘要

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
        'top3': mp_events[:3],  # 保持兼容
        'top7': mp_events,  # 新增：今日要点7条
    }

def build_trend_groups(events):
    """将事件按趋势主题分组，如果没有 trend_topic 则按 company_name / insight_label 降级"""
    groups = {}
    for e in events:
        topic = e.get('trend_topic')
        if not topic:
            region = e.get('region', '')
            company = e.get('company_name', '')
            if company:
                topic = f"{company}动态 — {region}" if region else f"{company}动态"
            else:
                label = e.get('insight_label', '其他')
                topic = f"{label} — {region}" if region else label
        groups.setdefault(topic, []).append(e)
    result = [{'topic': k, 'events': v} for k, v in groups.items()]
    result.sort(key=lambda x: len(x['events']), reverse=True)
    return result


def build_date_panel(date_str, day_events, all_events):
    """预计算某日期的今日面板数据（趋势分组 + 判断 + 统计），供 JS 翻页切换"""
    signals = get_signal_events(all_events)
    weekly = build_weekly_summary(day_events, signals, day_events, all_events)
    trend_groups = build_trend_groups(day_events)

    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return {
        'trend_groups': trend_groups,
        'judgment': weekly.get('summary', ''),
        'top3': weekly.get('top3', []),
        'total_stories': len(day_events),
        'vol_label': f"VOL.{date_str}",
        'cn_date': f"{dt.year}年{dt.month}月{dt.day}日 星期{CHINESE_WEEKDAYS[dt.weekday()]}",
        'headline': weekly.get('headline', ''),
        'funding': weekly.get('funding', 0),
        'ma': weekly.get('ma', 0),
        'earnings': weekly.get('earnings', 0),
        'regions': weekly.get('regions', 0),
    }


def group_events_by_date(events):
    """将事件按日期分组，按时间倒序"""
    groups = {}
    for e in events:
        d = (e.get('date') or '')[:10]
        groups.setdefault(d, []).append(e)
    result = [{'date': k, 'events': v} for k, v in sorted(groups.items(), reverse=True)]
    return result


def build_period_report(events, start_date, end_date, label):
    """聚合周报/月报入口所需的轻量统计和趋势。"""
    period_events = [
        e for e in events
        if start_date <= (e.get('date') or '')[:10] <= end_date
    ]
    regions = sorted({e.get('region') for e in period_events if e.get('region')})
    companies = sorted({
        e.get('company_name') for e in period_events
        if e.get('is_company') and e.get('company_name')
    })

    trend_counts = {}
    trend_regions = {}
    for e in period_events:
        topic = _front_trend_topic(e)
        trend_counts[topic] = trend_counts.get(topic, 0) + 1
        region = e.get('region') or '未知'
        trend_regions.setdefault(topic, {})
        trend_regions[topic][region] = trend_regions[topic].get(region, 0) + 1

    trends = []
    for topic, count in sorted(trend_counts.items(), key=lambda x: x[1], reverse=True):
        region_map = trend_regions.get(topic, {})
        top_region = max(region_map.items(), key=lambda x: x[1])[0] if region_map else '多地区'
        trends.append({'topic': topic, 'count': count, 'region': top_region})

    if trends:
        title = f"{label}主线：{trends[0]['topic']}"
        summary = f"{label}共收录 {len(period_events)} 条事件，覆盖 {len(regions)} 个地区、{len(companies)} 家重点公司。"
    else:
        title = f"{label}暂无足够事件形成趋势"
        summary = "当前周期事件数量较少，先保留为观察入口。"

    return {
        'start': start_date,
        'end': end_date,
        'month': start_date[:7],
        'title': title,
        'summary': summary,
        'total': len(period_events),
        'companies': len(companies),
        'regions': len(regions),
        'trends': trends or [{'topic': '暂无趋势', 'count': 0, 'region': '无'}],
    }


def clean_display_title(title):
    title = (title or '').strip()
    title = re.sub(r'^(背景补充|合作机会|资金流向|警示信号|中资出海|观察)[：:]\s*', '', title)
    return title


def split_judgment(text, fallback='今日非中美互联网动态更新'):
    """把长判断拆成适合头版展示的标题和正文。"""
    text = (text or '').strip()
    if not text:
        return fallback, ''
    title = ''
    lead = ''
    sentence_parts = re.split(r'(?<=[。！？])', text, maxsplit=1)
    first_sentence = (sentence_parts[0] or text).strip()
    rest = (sentence_parts[1] if len(sentence_parts) > 1 else '').strip()
    if len(first_sentence) > 42:
        clause_parts = re.split(r'[，,；;]', first_sentence, maxsplit=1)
        title = clause_parts[0].strip()
        lead = text
    else:
        title = first_sentence
        lead = rest
    if not re.search(r'[。！？]$', title):
        title = title.rstrip('，,；;') + '。'
    return clean_display_title(title), lead


def _has_cjk(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text or ''))


def _is_good_summary(summary, title, reason):
    summary = (summary or '').strip()
    if not summary or len(summary) < 8:
        return False
    if summary == (reason or '').strip():
        return False
    if summary[:25] == (title or '')[:25]:
        return False
    if not _has_cjk(summary):
        return False
    return True


def _front_trend_topic(event):
    """把后台分类转换成前台可读的趋势名，避免“背景补充”露出。"""
    region = event.get('region') or '多地区'
    event_types = event.get('event_types') or []
    event_type = event_types[0] if event_types else 'other'
    raw_topic = (event.get('trend_topic') or '').strip()
    if raw_topic and not raw_topic.startswith(('背景补充', '合作机会')) and raw_topic not in {'背景补充', '合作机会', '其他'}:
        return raw_topic
    if event_type == 'funding':
        return f'{region}资金流向'
    if event_type == 'ma':
        return f'{region}并购整合'
    if event_type == 'earnings':
        return f'{region}盈利与财报观察'
    if event_type == 'strategy':
        return f'{region}战略扩张'
    company = event.get('company_name')
    if company:
        return f'{company}连续动态'
    label = event.get('insight_label')
    if label and label not in {'背景补充', '其他'}:
        return f'{region}{label}'
    return f'{region}区域动态'


def enrich_frontend_fields(events):
    """补齐前台专用字段，让模板少做判断。"""
    for event in events:
        title = event.get('title', '')
        summary = event.get('summary_short', '')
        reason = event.get('reason', '')
        if _is_good_summary(summary, title, reason):
            display_title = summary.strip()
            original_title = title
        elif _has_cjk(reason) and reason.strip() not in {'未知', '科技动态'}:
            display_title = reason.strip()
            original_title = title
        else:
            display_title = title
            original_title = ''
        event['display_title'] = clean_display_title(display_title)
        event['original_title'] = original_title if original_title and original_title != display_title else ''
        event['front_trend_topic'] = _front_trend_topic(event)
        event['display_impact'] = '' if event.get('impact') == '未知' else event.get('impact', '')
    return events


def refine_daily_headline(headline, lead, trend_groups):
    """避免把统计句当作第一屏判断。"""
    weak = bool(re.search(r'事件最多|占今日大头|共\d+条动态|覆盖\d+地区', headline or ''))
    if not weak:
        return headline, lead
    top_topic = ''
    for group in trend_groups:
        events = group.get('events') or []
        if events:
            top_topic = events[0].get('front_trend_topic') or _front_trend_topic(events[0])
            break
    if top_topic:
        return f'{top_topic}成为今日主线。', lead or headline
    return headline, lead


def build_company_cards(company_list, now_date):
    """生成公司索引里的追踪摘要。"""
    start_7 = (datetime.strptime(now_date, '%Y-%m-%d') - timedelta(days=6)).strftime('%Y-%m-%d')
    start_30 = (datetime.strptime(now_date, '%Y-%m-%d') - timedelta(days=29)).strftime('%Y-%m-%d')
    result = []
    for company in company_list:
        events = company.get('events') or []
        events = sorted(events, key=lambda x: (x.get('date', ''), x.get('score', 0)), reverse=True)
        recent_7 = [e for e in events if (e.get('date') or '')[:10] >= start_7]
        recent_30 = [e for e in events if (e.get('date') or '')[:10] >= start_30]
        latest = events[0] if events else {}
        latest_title = clean_display_title(latest.get('display_title') or latest.get('summary_short') or latest.get('title') or '暂无近期事件')
        signal = latest.get('insight_label') or '观察'
        if signal in {'背景补充', '其他'}:
            signal = '观察'
        result.append({
            **company,
            'recent_7': len(recent_7),
            'recent_30': len(recent_30),
            'latest_title': latest_title,
            'latest_date': (latest.get('date') or '')[:10],
            'signal': signal,
        })
    return result

def group_company_cards(company_list):
    """按预设区域顺序组织公司索引，避免全局排序后用户找不到区域。"""
    grouped = []
    for region in PRESET_COMPANIES.keys():
        companies = [c for c in company_list if c.get('region') == region]
        if not companies:
            continue
        companies.sort(key=lambda x: (x.get('count', 0), x.get('recent_30', 0), x.get('recent_7', 0)), reverse=True)
        grouped.append({
            'region': region,
            'total': len(companies),
            'active': sum(1 for c in companies if c.get('count', 0) > 0),
            'recent_30': sum(c.get('recent_30', 0) for c in companies),
            'companies': companies,
        })
    return grouped

def load_site_updates():
    """读取网站更新日志。"""
    path = os.path.join('data', 'site_updates.json')
    fallback = [{
        'date': datetime.now().strftime('%Y-%m-%d'),
        'version': 'v0.1',
        'type': '系统',
        'status': '已上线',
        'title': '网站初始化',
        'summary': '全球互联网百晓生开始自动生成情报简报。',
        'changes': ['自动采集事件', '生成静态情报页面'],
    }]
    if not os.path.exists(path):
        return fallback
    try:
        with open(path, 'r', encoding='utf-8') as f:
            updates = json.load(f)
    except (json.JSONDecodeError, OSError):
        return fallback
    if not isinstance(updates, list):
        return fallback
    cleaned = []
    for item in updates:
        if not isinstance(item, dict):
            continue
        changes = item.get('changes') if isinstance(item.get('changes'), list) else []
        cleaned.append({
            'date': item.get('date') or '',
            'version': item.get('version') or '',
            'type': item.get('type') or '更新',
            'status': item.get('status') or '已记录',
            'title': item.get('title') or '未命名更新',
            'summary': item.get('summary') or '',
            'changes': [str(c) for c in changes if str(c).strip()],
        })
    return sorted(cleaned or fallback, key=lambda x: x.get('date', ''), reverse=True)

CHINESE_WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']

def generate_html(force=False, preview_mode=False):
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

    # 标题去重 + 质量过滤 + 按时间排序
    # 1. 排除other类型和低评分事件
    # 2. 按时间倒序（最新的在前）
    seen_titles = set()
    deduped = []
    for e in main_events:
        norm = re.sub(r'[^\w]', '', e.get('title', '').lower())
        if norm in seen_titles or len(norm) <= 10:
            continue
        seen_titles.add(norm)

        # 排除other类型事件（低质量）
        ev_type = e.get('event_types', ['other'])[0]
        if ev_type == 'other':
            continue

        # 排除低评分事件（评分<5视为低质量）
        score = e.get('score', 0)
        if score < 5:
            continue

        deduped.append(e)

    # 按时间倒序，同一天按评分排序
    deduped.sort(key=lambda x: (x.get('date', ''), x.get('score', 0)), reverse=True)
    all_feed = deduped

    # 公司动态单独处理
    company_events, generic_events = split_company_events(events)

    # 收集每家公司所有事件（时间窗口内，不过滤数量上限）
    company_by_company = {}
    for e in company_events:
        name = e.get('company_name', '其他')
        company_by_company.setdefault(name, []).append(e)

    # 按事件数量排序，有事件的排前面
    preset_company_list = []
    for region, companies in PRESET_COMPANIES.items():
        for company_name in companies:
            evs = company_by_company.get(company_name, [])
            preset_company_list.append({
                'name': company_name,
                'region': region,
                'count': len(evs),
                'events': evs
            })

    # 按事件数量排序，有事件的排前面
    preset_company_list.sort(key=lambda x: x['count'], reverse=True)

    # 全部事件 = 通用热点 + 公司动态（筛选后），统一按时间排序
    company_events_filtered = [e for evs in company_by_company.values() for e in evs]
    all_events_for_list = list(generic_events) + company_events_filtered
    all_events_for_list.sort(key=lambda x: (x.get('date', ''), x.get('score', 0)), reverse=True)
    enrich_frontend_fields(all_events_for_list)
    preset_company_list = build_company_cards(preset_company_list, main_date)
    company_groups = group_company_cards(preset_company_list)

    # 历史tab：90天内除主tab批次之外的所有有内容日期
    cutoff = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    history_dates = [d for d in sorted_dates if d >= cutoff and d != main_date]
    history = [(d, events.get(d, [])) for d in history_dates if events.get(d, [])]

    # 今日要点 = what'll be displayed — 从 all_events_for_list 中取今天事件
    today_events = [e for e in all_events_for_list if (e.get('date') or '')[:10] == main_date]
    if not today_events:
        today_events = all_feed

    signals = get_signal_events(events)
    # ⚠️ 关键：weekly 必须从 today_events 计数，不是 all_feed
    # all_feed 过滤了 other 类型和低分事件，但页面上展示的是 today_events
    # 两个数据源不一致导致"共0条动态"而实际有 9 条的矛盾
    weekly = build_weekly_summary(today_events, signals, main_events, events)
    # 公司动态也加入周报摘要
    weekly['company_count'] = len(company_events_filtered)
    weekly['company_list'] = preset_company_list

    trend_groups = build_trend_groups(today_events)
    daily_trend_judgment = weekly.get('summary', '')
    daily_headline, daily_lead = split_judgment(daily_trend_judgment, weekly.get('headline', '今日非中美互联网动态更新'))
    daily_headline, daily_lead = refine_daily_headline(daily_headline, daily_lead, trend_groups)
    daily_trend_signals = weekly.get('top3', [])
    total_stories = len(today_events)
    dt = datetime.strptime(main_date, '%Y-%m-%d')
    vol_label = f"VOL.{main_date}"
    cn_date = f"{dt.year}年{dt.month}月{dt.day}日 星期{CHINESE_WEEKDAYS[dt.weekday()]}"

    # 全部事件按日期分组
    date_grouped_events = group_events_by_date(all_events_for_list)

    # 预计算各日期面板数据（供 JS 翻页切换）
    date_panels = {}
    available_dates = []
    for d in sorted_dates:
        if d < cutoff:
            continue
        day_evs = [e for e in all_events_for_list if (e.get('date') or '')[:10] == d]
        if not day_evs:
            continue
        available_dates.append(d)
        date_panels[d] = build_date_panel(d, day_evs, events)
    date_panels_json = json.dumps(date_panels, ensure_ascii=False)
    main_dt = datetime.strptime(main_date, '%Y-%m-%d')
    weekly_start = (main_dt - timedelta(days=6)).strftime('%Y-%m-%d')
    monthly_start = main_dt.replace(day=1).strftime('%Y-%m-%d')
    weekly_report = build_period_report(all_events_for_list, weekly_start, main_date, '本周')
    monthly_report = build_period_report(all_events_for_list, monthly_start, main_date, '本月')
    site_updates = load_site_updates()

    template = Template(open('scripts/template.html', 'r', encoding='utf-8').read())
    html = template.render(
        weekly=weekly,
        weekly_report=weekly_report,
        monthly_report=monthly_report,
        all_feed=all_feed,
        all_events_for_list=all_events_for_list,
        date_grouped_events=date_grouped_events,
        history=history,
        main_date=main_date,
        company_events=company_events,
        company_list=preset_company_list,
        company_groups=company_groups,
        update_time=main_date + ' 数据（每日02:00北京时间自动更新）',
        trend_groups=trend_groups,
        daily_trend_judgment=daily_trend_judgment,
        daily_headline=daily_headline,
        daily_lead=daily_lead,
        daily_trend_signals=daily_trend_signals,
        total_stories=total_stories,
        vol_label=vol_label,
        cn_date=cn_date,
        date_panels=date_panels,
        date_panels_json=date_panels_json,
        available_dates_json=json.dumps(available_dates),
        available_dates=available_dates,
        site_updates=site_updates,
        site_updates_json=json.dumps(site_updates, ensure_ascii=False),
        feedback_issue_url='https://github.com/HuangJun722/weekly-report/issues/new?template=feedback.yml',
    )

    os.makedirs('docs', exist_ok=True)
    index_path = 'docs/preview.html' if preview_mode else 'docs/index.html'

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)

    mode = '预览' if preview_mode else '生产'
    print(f"OK | {mode}模式 | 通用{len(generic_events)}条 | 公司{len(company_events)}条 | {len(history)}天往期")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='生成全球互联网动态情报站 HTML')
    parser.add_argument('--force', action='store_true', help='强制重写 index.html（跳过内容对比）')
    parser.add_argument('--preview', action='store_true', help='生成本地预览文件 preview.html（不覆盖 index.html）')
    args = parser.parse_args()

    if args.preview:
        # 预览模式：生成到 preview.html
        generate_html(preview_mode=True)
    else:
        # 默认模式：生成到 index.html
        generate_html(force=args.force)
