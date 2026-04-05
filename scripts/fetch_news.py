"""
全球互联网动态情报站 — 数据采集
目标：融资 | 并购 | 财报披露 | 重大战略 — 发现 ICT 合作机会点
"""

import json, os, time, re
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import warnings; warnings.filterwarnings('ignore')
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36',
    'Referer': 'https://www.google.com/',
}

REQUEST_DELAY = 1.2  # 避免被封

# ============================================================
# 信源：重点标注是否为融资专属源
# ============================================================

RSS_SOURCES = [
    # --- 欧洲：融资专业源优先 ---
    {'name': 'TechCrunch',       'url': 'https://techcrunch.com/feed/',                  'source': 'TechCrunch',    'region': '欧洲', 'priority': 3},
    {'name': 'TechCrunch VC',   'url': 'https://techcrunch.com/category/venture/feed/', 'source': 'TechCrunch',    'region': '欧洲', 'priority': 3},
    {'name': 'Tech.eu',          'url': 'https://tech.eu/feed/',                         'source': 'Tech.eu',       'region': '欧洲', 'priority': 3},
    {'name': 'The Next Web',     'url': 'https://thenextweb.com/feed/',                  'source': 'The Next Web',  'region': '欧洲', 'priority': 2},
    # EU-Startups 已移除：Cloudflare 全面拦截（RSS + HTML 均 403）
    # Sifted 已移除：Cloudflare 全面拦截，无法绕过
    # --- 亚太：融资专业源 ---
    {'name': 'Tech in Asia',     'url': 'https://www.techinasia.com/feed/',              'source': 'Tech in Asia',  'region': '亚太', 'priority': 3},
    # DealStreetAsia RSS 已停用（"Temporarily Disabled"），改用 HTML 降级采集
    # e27 已移除：Cloudflare 全面拦截，无法绕过，改用 HTML 降级
    # --- 中东/非洲 ---
    {'name': 'WAMDA',           'url': 'https://www.wamda.com/feed',                     'source': 'WAMDA',         'region': '中东', 'priority': 3},
    {'name': 'MENAbytes',        'url': 'https://www.menabytes.com/feed/',               'source': 'MENAbytes',     'region': '中东', 'priority': 2},
    {'name': 'TechCabal',        'url': 'https://techcabal.com/feed',                   'source': 'TechCabal',     'region': '非洲', 'priority': 2},
    # Disrupt Africa：RSS 恢复，root feed 可用
    {'name': 'Disrupt Africa',   'url': 'https://disrupt-africa.com/feed/',             'source': 'Disrupt Africa', 'region': '非洲', 'priority': 2},
    {'name': 'Techpoint',        'url': 'https://techpoint.africa/feed/',               'source': 'Techpoint',     'region': '非洲', 'priority': 2},
    {'name': 'Ventureburn',      'url': 'https://ventureburn.com/feed/',                'source': 'Ventureburn',   'region': '非洲', 'priority': 2},
    # --- 拉美 ---
    # 注意：Bloomberg RSS 是全球综合科技，不限于拉美，已移除避免噪声
    {'name': 'LAVCA',            'url': 'https://lavca.org/feed/',                        'source': 'LAVCA',         'region': '拉美', 'priority': 3},
    {'name': 'Contxto',          'url': 'https://contxto.com/en/feed/',                  'source': 'Contxto',       'region': '拉美', 'priority': 2},
]

# ============================================================
# 关键词检测（宽松模式，宁多不漏）
# ============================================================

def detect_event_types(title):
    t = title.lower()
    types = []
    # 融资（最高优先）
    if any(k in t for k in ['raises', 'secures $', 'closes $', 'raises £',
                       'closes funding', 'series ', 'seed round', 'valued at', 'unicorn',
                       'pre-series', 'investment of $', 'received $', 'attracts $',
                       'ltd raises', 'funding of', 'funding to',
                       # 融资金额直接出现
                       '$50m', '$100m', '$200m', '$500m', '$1b', '$1b+', 'bags $',
                       # 融资进展
                       'funding round', 'raises in ', 'closes $', 'm series',
                       'attracts gulf',  # WAMDA 常见格式
                       # 估值相关
                       'valuation', 'valued at', 'eyes $', '$b valuation']):
        types.append('funding')
    # 并购/收购
    if any(k in t for k in ['acquires', 'acquired', 'acquisition', 'merger', 'merges',
                       'takeover', 'takes control', 'stake in', 'buys', 'purchases',
                       'buyout', 'sold to']):
        types.append('ma')
    # 财报/IPO
    if any(k in t for k in ['revenue', 'earnings', 'profit', 'quarterly results',
                       'fiscal year', 'ipo ', 'listing', 'goes public',
                       'files to go public', 'quarterly profit', 'quarterly loss',
                       'Q1 ', 'Q2 ', 'Q3 ', 'Q4 ', 'financial results',
                       'goes live', 'shares ', 'stock ']):
        types.append('earnings')
    # 战略/市场
    if any(k in t for k in ['partners with', 'partnership', 'strategic',
                       'joint venture', 'expands to', 'flagship store',
                       'exits ', 'layoffs', 'shutdown', 'spins off',
                       'disrupts', 'CEO says', 'CEO on', 'ceo on', 'expansion',
                       'launches ', 'rolls out', 'deploys', 'to launch',
                       'launches in', 'listing ', 'eyes $', '$ valuation']):
        types.append('strategy')
    return types if types else ['other']

# 中美公司关键词（匹配标题中出现的公司名，排除不相关内容）
# 用非贪婪匹配 + 上下文判断，避免误杀（如 "DeepMind raises" 才排除，纯叙述不排除）
BLACKLIST_COMPANIES = [
    # 美国公司/产品
    'OpenAI', 'Anthropic', 'xAI', 'x.AI', 'SpaceX', 'Starlink', 'Palantir',
    'ChatGPT', 'GPT-4', 'GPT-5', 'Claude ', 'Perplexity', 'Character.AI',
    'Waymo', 'Cruise',  # 自动驾驶（美）
    # 中国公司/产品
    'ByteDance', 'TikTok', 'Douyin', 'DeepSeek', 'Kimi', 'Qwen',
    # AI 产品名
    'Gemini ', 'Gemini,', 'Gemini.', 'Gemini/',  # Google AI 产品
]
BLACKLIST_PATTERNS = [re.compile(r'\b' + re.escape(c) + r'\b', re.IGNORECASE) for c in BLACKLIST_COMPANIES]

def is_blacklisted(title):
    t = title
    for pat in BLACKLIST_PATTERNS:
        if pat.search(t):
            return True
    # 域名黑名单（URL 中出现这些域名也算排除）
    for dom in ['openai.com', 'anthropic.com', 'x.ai', 'spacex.com', 'byteDance.com',
                'tiktok.com', 'deepmind.google', 'waymo.com']:
        if dom in t.lower():
            return True
    return False

# ============================================================
# HTTP
# ============================================================

def fetch_url(url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code in (403, 429):
                time.sleep(5 * (i + 1)); continue
            r.raise_for_status()
            return r
        except Exception:
            if i == retries - 1: return None
            time.sleep(2 ** i)
    return None

# ============================================================
# 采集
# ============================================================

def fetch_rss(cfg):
    resp = fetch_url(cfg['url'])
    if not resp: return []

    text = resp.text.strip()
    if not any(text.startswith(x) or x in text[:300] for x in ['<?xml', '<rss', '<feed']):
        return []

    try:
        soup = BeautifulSoup(text, 'xml')
    except Exception:
        return []

    items = soup.select('item') or soup.select('entry')
    results = []
    max_items = cfg.get('max', 8)  # 每个源最多保留这么多

    for item in items:
        if len(results) >= max_items: break
        title_el = item.select_one('title')
        link_el  = item.select_one('link')
        if not title_el: continue
        title = title_el.get_text(strip=True)
        if len(title) < 15 or is_blacklisted(title): continue

        link = ''
        if link_el:
            link = (link_el.get('href') or '').strip()
            if not link: link = link_el.get_text(strip=True)
        if not link:
            guid_el = item.select_one('guid')
            if guid_el: link = guid_el.get_text(strip=True)
        if not link: continue

        types = detect_event_types(title)
        results.append({
            'title': title,
            'url': link,
            'source': cfg['source'],
            'region': cfg['region'],
            'priority': cfg.get('priority', 1),
            'event_types': types,
        })

    return results

# ============================================================
# HTML 备用采集（RSS 失效时的降级方案）
# ============================================================

HTML_SOURCES = [
    # DealStreetAsia RSS 停用（"Temporarily Disabled"），主站为 JS SPA
    # 低频尝试：大部分时间为 JS 空壳，偶尔可能含静态内容
    {'name': 'DealStreetAsia', 'url': 'https://dealstreetasia.com/', 'source': 'DealStreetAsia', 'region': '亚太', 'priority': 1},
    # e27：Angular JS + Cloudflare 双层保护，RSS + HTML 均无法采集，已移除
]

def fetch_html(cfg):
    """从 HTML 页面提取文章列表（降级方案，针对各站点结构定制）"""
    resp = fetch_url(cfg['url'])
    if not resp: return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    results = []

    # 根据来源选择器定制
    source = cfg['source']
    if source == 'DealStreetAsia':
        # DealStreetAsia: JS SPA，文章在特定 div 结构中
        # 尝试多种文章容器选择器
        selectors = [
            'article', '.post-card', '.deal-card', '.startup-card',
            '[class*=card]', '[class*=item]', '[class*=post]',
            '.listing article', '.archive article',
        ]
        articles = []
        for sel in selectors:
            found = soup.select(sel)
            if found:
                articles = found
                break
        # 也尝试从链接模式找文章：/2026/ 或包含 deal/startup/invest
        if not articles:
            all_links = soup.select('a[href]')
            art_links = []
            for a in all_links:
                href = a.get('href', '')
                if '/202' in href and any(x in href for x in ['/deals/', '/startups/', '/funding/', '/invest/']):
                    parent = a.find_parent()
                    if parent:
                        art_links.append(parent)
            if art_links:
                articles = art_links
    elif source == 'e27':
        # e27: 文章在特定列表结构中
        selectors = [
            'article', '.post', '.listing-item', '.article-item',
            '[class*=article]', '[class*=post]',
        ]
        articles = []
        for sel in selectors:
            found = soup.select(sel)
            if found:
                articles = found
                break
        # 也从链接中提取：e27.co/20xx/ 模式
        if not articles:
            all_links = soup.select('a[href]')
            art_links = []
            for a in all_links:
                href = a.get('href', '')
                if '/20' in href and ('startup' in href or 'funding' in href or 'investment' in href or 'series' in href):
                    parent = a.find_parent()
                    if parent:
                        art_links.append(parent)
            if art_links:
                articles = art_links
    else:
        # 通用回退
        articles = soup.select('article') or soup.select('.post') or soup.select('.article')
        if not articles:
            articles = soup.select('a[href]')

    for art in articles[:15]:
        # 提取标题和链接
        title_el = art.select_one('h2,h3,h4,h5,.title,.entry-title,.post-title,.article-title') or art
        title = title_el.get_text(strip=True)
        if len(title) < 15 or is_blacklisted(title): continue

        link_el = art.select_one('a') or (title_el if isinstance(title_el, object) else None)
        link = ''
        if link_el:
            link = (link_el.get('href') or '').strip()
        if not link or link.startswith('#') or link.startswith('javascript'): continue

        # 过滤非文章链接
        if any(x in link for x in ['/category/', '/tag/', '/author/', '/page/',
                                    'subscribe', 'newsletter', 'contact', '/cdn-cgi/']): continue
        # 只保留绝对 URL 或同源链接
        if not link.startswith('http'):
            if link.startswith('/'):
                base = cfg['url'].split('/')[2]  # 提取域名
                link = 'https://' + base + link

        types = detect_event_types(title)
        results.append({
            'title': title,
            'url': link,
            'source': cfg['source'],
            'region': cfg['region'],
            'priority': cfg.get('priority', 1),
            'event_types': types,
        })

    return results

# ============================================================
# 智能过滤：控制每天总条数，优先保留高价值事件
# ============================================================

MAX_DAILY = 40      # 每天最多保留 40 条
MAX_PER_REGION = 12  # 每个区域最多保留多少条

def smart_filter(items):
    """
    策略：
    1. 所有融资/并购/财报事件全部保留
    2. 其他事件按 priority 排序，每天最多 40 条
    3. 每天至少覆盖所有区域
    """
    # 信号事件（全部保留）
    signal = [it for it in items if it['event_types'][0] != 'other']
    # 非信号事件（按 priority 排序，取剩余名额）
    others = [it for it in items if it['event_types'][0] == 'other']
    others.sort(key=lambda x: x.get('priority', 1), reverse=True)

    # 优先确保每个区域至少有 2 条
    by_region = {}
    for it in items:
        by_region.setdefault(it['region'], []).append(it)

    result = []
    used_urls = set()

    # 1. 全部信号事件
    for it in signal:
        if it['url'] not in used_urls:
            result.append(it); used_urls.add(it['url'])

    # 2. 非信号事件补足到 MAX_DAILY，每个区域最多 MAX_PER_REGION 条
    regions = list(dict.fromkeys(it['region'] for it in items))  # 保持原始顺序
    region_count = {}
    for region in regions:
        remaining = MAX_DAILY - len(result)
        if remaining <= 0: break
        region_others = [it for it in others if it['region'] == region and it['url'] not in used_urls]
        # 每个区域最多补 MAX_PER_REGION - signal_count_for_this_region 条非信号
        signal_in_region = sum(1 for it in result if it['region'] == region)
        max_other_for_region = max(0, MAX_PER_REGION - signal_in_region)
        for it in region_others[:max_other_for_region]:
            if it['url'] not in used_urls:
                result.append(it); used_urls.add(it['url'])
                if len(result) >= MAX_DAILY: break

    return result

# ============================================================
# Gemini 分析（可选）
# ============================================================

def configure_gemini():
    key = os.environ.get('GEMINI_API_KEY')
    if not key: return False
    genai.configure(api_key=key); return True

# ============================================================
# AI 分析 Prompt 模板（Few-shot，输出稳定）
# ============================================================

AI_SYSTEM_PROMPT = """你是全球互联网科技情报分析师。受众是ICT从业者，关注：合作机会、供应链变化、预算流向。
每条事件输出4个字段：summary_short（事实）、reason（为什么重要，ICT视角）、impact（影响谁）、insight_label（资金流向/合作机会/警示信号/背景补充）。
非中美公司融资≥$100M → score 9；融资≥$20M → score 7-8；并购 → score 7-8；财报盈利稳定 → score 5-6；亏损/下滑 → score 7-9；战略扩张 → score 6-7；裁员/关停 → score 6-8。
只返回JSON数组，不要解释。"""

AI_EXAMPLES = """
示例1（融资大额）：
标题: "Mistral raises $830M, 9fin hits unicorn status"
输出: {"url":"","summary_short":"Mistral获$830M融资，9fin晋级独角兽","reason":"欧洲AI独角兽获顶级融资，后续可能开放生态合作和API采购","impact":"AI基础设施供应商、云服务商、API集成商","insight_label":"资金流向","score":9}

示例2（融资中等）：
标题: "Wearable Robotics closes €5M Series A"
输出: {"url":"","summary_short":"可穿戴机器人公司获€5M A轮","reason":"欧洲硬科技早期融资，B2B机器人赛道持续有资金流入","impact":"机器人供应链、工业软件合作方","insight_label":"资金流向","score":6}

示例3（并购）：
标题: "Cafeyn acquires Readly non-Nordic operations"
输出: {"url":"","summary_short":"Cafeyn收购Readly非北欧业务","reason":"欧洲数字出版整合加速，中小媒体可能面临挤压或被整合","impact":"数字媒体公司、内容分发合作方","insight_label":"资金流向","score":7}

示例4（战略合作）：
标题: "Arabic.AI partners with Qistas to deliver sovereign Arabic legal AI"
输出: {"url":"","summary_short":"Arabic.AI与Qistas合作推阿拉伯语法务AI","reason":"中东主权AI战略落地，法律科技出现新的ICT集成机会","impact":"法律科技集成商、中东政府IT合作方","insight_label":"合作机会","score":6}

示例5（战略裁员）：
标题: "Telecom Italia cuts 2000 jobs amid network upgrade"
输出: {"url":"","summary_short":"意大利电信裁员2000人","reason":"传统运营商压缩成本，转向网络外包，ICT服务商机会增加","impact":"IT外包商、网络设备供应商","insight_label":"警示信号","score":7}

示例6（财报盈利）：
标题: "Nubank Q1 revenue up 34% to $2.8B"
输出: {"url":"","summary_short":"Nubank营收$2.8B，同比+34%","reason":"拉美数字银行持续高增长，东南亚复制模式具有参考价值","impact":"拉美金融科技合作方、银行科技供应商","insight_label":"背景补充","score":6}

示例7（财报亏损）：
标题: "Gorillas files for insolvency amid funding crunch"
输出: {"url":"","summary_short":"欧洲快送平台Gorillas申请破产保护","reason":"即时配送赛道资金耗尽，同类公司需警惕融资环境恶化信号","impact":"同类快送平台、物流技术供应商","insight_label":"警示信号","score":8}
"""

def analyze_events_gemini(items):
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    news = [{'title': it['title'], 'url': it['url'], 'source': it['source']} for it in items]
    prompt = f"{AI_SYSTEM_PROMPT}\n{AI_EXAMPLES}\n\n分析以下事件，返回JSON数组：\n{json.dumps(news, ensure_ascii=False)}\n\n返回JSON："
    try:
        resp = model.generate_content(prompt)
        text = resp.text.strip()
        # 去掉 markdown 代码块
        for m in ['```json', '```']:
            if m in text:
                parts = text.split(m)
                for p in parts[1:]:
                    text = p.strip()
                    if text.endswith('```'): text = text[:-3].strip()
                    break
        result = json.loads(re.sub(r'^json\s*', '', text, flags=re.I))
        # 验证结果：过滤掉无效条目
        if isinstance(result, list):
            result = [r for r in result if r.get('url') and r.get('summary_short')]
        return result
    except Exception:
        return None

def build_event(item, analysis=None):
    """构建事件对象，兼容有/无 AI 分析两种情况"""
    score = (analysis or {}).get('score', 5) if analysis else 5
    level = 'A' if score >= 8 else 'B' if score >= 6 else 'C' if score >= 4 else 'D'
    # 有 AI 分析时
    if analysis:
        return {
            'title': item['title'],
            'url': item['url'],
            'source': item['source'],
            'region': item['region'],
            'event_types': item['event_types'],
            'level': level,
            'score': score,
            'summary_short': analysis.get('summary_short', item['title'][:25]),
            'reason': analysis.get('reason', '待分析'),
            'impact': analysis.get('impact', '未知'),
            'insight_label': analysis.get('insight_label', '背景补充'),
            'companies': (analysis or {}).get('companies', []) or [],
            'date': datetime.now().isoformat(),
        }
    # 无 AI 分析时的 fallback
    ev_type = item.get('event_types', ['other'])[0]
    default_label = {
        'funding': '资金流向',
        'ma': '资金流向',
        'earnings': '背景补充',
        'strategy': '合作机会',
    }.get(ev_type, '背景补充')
    return {
        'title': item['title'],
        'url': item['url'],
        'source': item['source'],
        'region': item['region'],
        'event_types': item['event_types'],
        'level': level,
        'score': score,
        'summary_short': item['title'][:25],
        'reason': '待分析',
        'impact': '未知',
        'insight_label': default_label,
        'companies': [],
        'date': datetime.now().isoformat(),
    }

# ============================================================
# 主函数
# ============================================================

def main():
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"\n🌍 全球互联网动态情报站")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')} | 目标：融资/并购/财报/战略\n")

    os.makedirs('data', exist_ok=True)
    try:
        with open('data/events.json', 'r', encoding='utf-8') as f:
            all_events = json.load(f)
        if isinstance(all_events, list): all_events = {}
    except: all_events = {}

    # 采集
    print("📡 采集 RSS 信源...")
    raw = []
    for cfg in RSS_SOURCES:
        items = fetch_rss(cfg)
        if items:
            print(f"  [{cfg['name']}] {len(items)} 条")
            raw.extend(items)
        time.sleep(REQUEST_DELAY)

    # HTML 备用采集（RSS 失效时的降级方案）
    if HTML_SOURCES:
        print("🌐 HTML 备用采集...")
        for cfg in HTML_SOURCES:
            items = fetch_html(cfg)
            if items:
                print(f"  [{cfg['name']}] {len(items)} 条")
                raw.extend(items)
            time.sleep(REQUEST_DELAY)

    # 按 URL 去重
    seen, unique = set(), []
    for it in raw:
        if it['url'] and it['url'] not in seen:
            seen.add(it['url']); unique.append(it)

    # 统计
    types = {'funding':0,'ma':0,'earnings':0,'strategy':0,'other':0}
    for it in unique: types[it['event_types'][0]] += 1
    regions = {}
    for it in unique: regions[it['region']] = regions.get(it['region'],0) + 1

    print(f"\n📊 采集：{len(unique)} 条（融资{types['funding']} | 并购{types['ma']} | 财报{types['earnings']} | 战略{types['strategy']} | 其他{types['other']}）")
    print(f"   区域：{regions}")

    # 智能过滤
    filtered = smart_filter(unique)
    types2 = {'funding':0,'ma':0,'earnings':0,'strategy':0,'other':0}
    for it in filtered: types2[it['event_types'][0]] += 1
    print(f"   过滤后：{len(filtered)} 条（融资{types2['funding']} | 并购{types2['ma']} | 财报{types2['earnings']} | 战略{types2['strategy']} | 其他{types2['other']}）")

    # Gemini 分析
    use_gemini = configure_gemini()
    today_events = []
    if use_gemini:
        print(f"\n🤖 Gemini 分析...")
        for i in range(0, len(filtered), 8):
            batch = filtered[i:i+8]
            results = analyze_events_gemini(batch) or []
            for item in batch:
                r = next((x for x in results if x.get('url') == item['url']), {})
                today_events.append(build_event(item, r))
            print(f"  批次 {(i//8)+1}/{(len(filtered)+7)//8}")
            time.sleep(0.5)
    else:
        for item in filtered:
            today_events.append(build_event(item))

    # 直接用过滤后的数据替换今日（不复写历史）
    all_events[today] = today_events

    # 清理 7 天前
    cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    all_events = {k: v for k, v in all_events.items() if k >= cutoff}

    with open('data/events.json', 'w', encoding='utf-8') as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    final_regions = {}
    for e in all_events.get(today, []):
        final_regions[e['region']] = final_regions.get(e['region'], 0) + 1
    print(f"\n✅ {today} 完成：{len(all_events.get(today,[]))} 条 | 区域：{final_regions}")

if __name__ == '__main__':
    main()
