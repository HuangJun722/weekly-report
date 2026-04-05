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
    {'name': 'TechCrunch VC',   'url': 'https://techcrunch.com/category/venture/feed/',      'source': 'TechCrunch',    'region': '欧洲', 'priority': 3},
    {'name': 'Tech.eu',          'url': 'https://tech.eu/feed/',                             'source': 'Tech.eu',       'region': '欧洲', 'priority': 3},
    {'name': 'Sifted',           'url': 'https://sifted.eu/feed/',                           'source': 'Sifted',        'region': '欧洲', 'priority': 2},
    {'name': 'EU-Startups',      'url': 'https://www.eu-startups.com/feed/',                 'source': 'EU-Startups',   'region': '欧洲', 'priority': 2},
    # --- 亚太：融资专业源 ---
    {'name': 'Tech in Asia',     'url': 'https://www.techinasia.com/feed/',                 'source': 'Tech in Asia',  'region': '亚太', 'priority': 3},
    {'name': 'DealStreetAsia',  'url': 'https://www.dealstreetasia.com/feed/',             'source': 'DealStreetAsia', 'region': '亚太', 'priority': 3},
    {'name': 'e27',              'url': 'https://e27.co/feed/',                             'source': 'e27',           'region': '亚太', 'priority': 2},
    # --- 中东/非洲 ---
    {'name': 'WAMDA',           'url': 'https://www.wamda.com/feed',                    'source': 'WAMDA',         'region': '中东', 'priority': 3},
    {'name': 'TechCabal',       'url': 'https://techcabal.com/feed',                    'source': 'TechCabal',     'region': '非洲', 'priority': 2},
    # Disrupt Africa RSS 已废弃，只返回2024年旧文，改用 HTML 采集
    {'name': 'Techpoint',       'url': 'https://techpoint.africa/feed/',              'source': 'Techpoint',     'region': '非洲', 'priority': 2},
    {'name': 'Ventureburn',     'url': 'https://ventureburn.com/feed/',               'source': 'Ventureburn',   'region': '非洲', 'priority': 2},
    # --- 拉美 ---
    # 注意：Bloomberg RSS 是全球综合科技，不限于拉美，已移除避免噪声
    {'name': 'LAVCA',           'url': 'https://lavca.org/feed/',                     'source': 'LAVCA',         'region': '拉美', 'priority': 3},
    {'name': 'Contxto',         'url': 'https://contxto.com/en/feed/',               'source': 'Contxto',       'region': '拉美', 'priority': 2},
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
    # Disrupt Africa RSS 已废弃，改用 HTML 采集
    {'name': 'Disrupt Africa', 'url': 'https://disrupt-africa.com/category/funding/', 'source': 'Disrupt Africa', 'region': '非洲', 'priority': 2},
]

def fetch_html(cfg):
    """从 HTML 页面提取文章列表"""
    resp = fetch_url(cfg['url'])
    if not resp: return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    results = []

    # Disrupt Africa 文章列表结构
    articles = soup.select('article') or soup.select('.post') or soup.select('.article')
    if not articles:
        # 通用结构
        articles = soup.select('a[href]')

    for art in articles[:15]:
        # 提取标题和链接
        title_el = art.select_one('h2,h3,h4,.title,.entry-title') or art
        title = title_el.get_text(strip=True)
        if len(title) < 15 or is_blacklisted(title): continue

        link_el = art.select_one('a') or title_el.select_one('a')
        link = ''
        if link_el:
            link = (link_el.get('href') or '').strip()
        if not link or link.startswith('#') or link.startswith('javascript'): continue

        # 过滤非文章链接
        if any(x in link for x in ['/category/', '/tag/', '/author/', '/page/',
                                    'subscribe', 'newsletter', 'contact']): continue

        # 过滤日期太旧的
        date_el = art.select_one('time,.date,.published,.post-date')
        date_str = ''
        if date_el:
            date_str = date_el.get('datetime', '') or date_el.get_text(strip=True)

        types = detect_event_types(title)
        results.append({
            'title': title,
            'url': link,
            'source': cfg['source'],
            'region': cfg['region'],
            'priority': cfg.get('priority', 1),
            'event_types': types,
            '_date_str': date_str,  # 用于调试/日志
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

def analyze_events_gemini(items):
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    news = [{'title': it['title'], 'url': it['url'], 'source': it['source']} for it in items]
    prompt = f"""分析以下科技新闻，返回JSON数组（不要markdown）：

{json.dumps(news, ensure_ascii=False)}

返回格式：
[{{"url":"...","companies":["非中美公司"],"why_important":"中文25字","impact_scope":"谁受影响","score":1-10}}]

规则：非中美公司融资/IPO/并购/新品→score≥7；美国/中国公司新闻→忽略。只返回JSON。"""
    try:
        resp = model.generate_content(prompt)
        text = resp.text.strip()
        for m in ['```json', '```']:
            if m in text:
                parts = text.split(m)
                for p in parts[1:]:
                    text = p.strip()
                    if text.endswith('```'): text = text[:-3].strip()
                    break
        return json.loads(re.sub(r'^json\s*', '', text, flags=re.I))
    except Exception:
        return None

def build_event(item, analysis=None):
    score = (analysis or {}).get('score', 5) if analysis else 5
    level = 'A' if score >= 8 else 'B' if score >= 6 else 'C' if score >= 4 else 'D'
    why = (analysis or {}).get('why_important', '待分析') if analysis else '待分析'
    return {
        'title': item['title'],
        'url': item['url'],
        'source': item['source'],
        'region': item['region'],
        'event_types': item['event_types'],
        'level': level,
        'score': score,
        'why_important': why,
        'impact_scope': (analysis or {}).get('impact_scope', '未知') if analysis else '未知',
        'companies': (analysis or {}).get('companies', []) if analysis else [],
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
