"""
全球互联网动态情报站 — 数据采集与 AI 分析
专注非中美地区的互联网/科技公司动态
"""

import json
import os
import time
import re
from datetime import datetime, timedelta

# 加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import warnings
warnings.filterwarnings('ignore')
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml, text/xml, text/html, */*',
    'Accept-Language': 'en-US,en;q=0.9',
}

# ============================================================
# 信源列表（RSS 优先，稳定可靠）
# ============================================================

RSS_FEEDS = [
    # 欧洲
    {'name': 'TechCrunch',       'url': 'https://techcrunch.com/feed/',              'source': 'TechCrunch',        'region_hint': '欧洲',  'max': 15},
    {'name': 'Tech.eu',         'url': 'https://tech.eu/feed/',                       'source': 'Tech.eu',          'region_hint': '欧洲',  'max': 12},
    {'name': 'The Next Web',    'url': 'https://thenextweb.com/feed/',               'source': 'The Next Web',     'region_hint': '欧洲',  'max': 10},
    {'name': 'Sifted',          'url': 'https://sifted.eu/feed/',                     'source': 'Sifted',           'region_hint': '欧洲',  'max': 10},
    # 亚太 / 全球
    {'name': 'Rest of World',   'url': 'https://restofworld.org/feed/',             'source': 'Rest of World',    'region_hint': '亚太',  'max': 15},
    {'name': 'Techpoint Africa','url': 'https://techpoint.africa/feed/',             'source': 'Techpoint Africa', 'region_hint': '非洲',  'max': 10},
    # 中东 / 非洲
    {'name': 'WAMDA',           'url': 'https://www.wamda.com/feed',                'source': 'WAMDA',            'region_hint': '中东',  'max': 15},
    {'name': 'TechCabal',       'url': 'https://techcabal.com/feed',                 'source': 'TechCabal',         'region_hint': '非洲',  'max': 15},
    # 拉美 / 综合
    {'name': 'Bloomberg Tech',  'url': 'https://feeds.bloomberg.com/technology/news.rss', 'source': 'Bloomberg', 'region_hint': '拉美', 'max': 12},
]

HTML_SOURCES = [
    # HTML 备用源（RSS 不可用时）
    {'name': 'TechCrunch Startups','url': 'https://techcrunch.com/category/startups/', 'source': 'TechCrunch', 'region_hint': '欧洲',
     'article_sel': 'article', 'title_sel': 'h2 a, .post-block__title__link', 'max': 10},
    {'name': 'Tech in Asia',       'url': 'https://www.techinasia.com/',              'source': 'Tech in Asia',     'region_hint': '亚太',
     'article_sel': '.stream-item, article', 'title_sel': 'h2 a, .title a', 'max': 10},
    {'name': 'e27',                'url': 'https://e27.co/',                           'source': 'e27',              'region_hint': '亚太',
     'article_sel': 'article, .post', 'title_sel': 'h2 a, h3 a', 'max': 10},
    {'name': 'Disrupt Africa',     'url': 'https://disrupt-africa.com/',              'source': 'Disrupt Africa',    'region_hint': '非洲',
     'article_sel': 'article', 'title_sel': 'h2 a, h3 a', 'max': 10},
    {'name': 'Contxto',            'url': 'https://contxto.com/en/',                  'source': 'Contxto',           'region_hint': '拉美',
     'article_sel': 'article', 'title_sel': 'h2 a, h3 a', 'max': 10},
    {'name': 'LAVCA',              'url': 'https://lavca.org/',                       'source': 'LAVCA',            'region_hint': '拉美',
     'article_sel': 'article, .post', 'title_sel': 'h2 a, h3 a', 'max': 10},
    {'name': 'DealStreetAsia',     'url': 'https://www.dealstreetasia.com/',         'source': 'DealStreetAsia',   'region_hint': '亚太',
     'article_sel': 'article', 'title_sel': 'h2 a, h3 a', 'max': 8},
    {'name': 'Ventureburn',        'url': 'https://ventureburn.com/',                 'source': 'Ventureburn',       'region_hint': '非洲',
     'article_sel': 'article', 'title_sel': 'h2 a, h3 a', 'max': 8},
    {'name': 'MENAbytes',          'url': 'https://menabytes.com/',                    'source': 'MENAbytes',         'region_hint': '中东',
     'article_sel': 'article', 'title_sel': 'h2 a, h3 a', 'max': 8},
]

# 黑名单：只有明确的中美公司/品牌才跳过（避免误杀）
BLACKLIST_PATTERNS = [
    # 中国（只列公司主体，不是提到就算）
    r'\bByteDance\b', r'\bTikTok\b',
    # 美国（只列明确的公司名称整体）
    r'\bOpenAI\b', r'\bAnthropic\b', r'\bSpaceX\b',
    r'\bPalantir\b', r'\bxAI\b',
]

# ============================================================
# 工具函数
# ============================================================

def fetch_with_retry(url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r
        except Exception:
            if i == retries - 1:
                return None
            time.sleep(2 ** i)

def is_blacklisted(title):
    for p in BLACKLIST_PATTERNS:
        if re.search(p, title, re.IGNORECASE):
            return True
    return False

# ============================================================
# RSS 采集
# ============================================================

def fetch_rss_feed(cfg):
    resp = fetch_with_retry(cfg['url'])
    if not resp:
        return []

    text = resp.text.strip()
    # 检查是否有效 RSS/XML
    if not any(text.startswith(x) or x in text[:300] for x in ['<?xml', '<rss', '<feed']):
        return []

    try:
        soup = BeautifulSoup(text, 'xml')
    except Exception:
        return []

    items = soup.select('item') or soup.select('entry')
    results = []

    for item in items[:cfg['max'] * 3]:
        title_el = item.select_one('title')
        link_el = item.select_one('link')
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        # link: 可能是子标签文本，也可能是 href 属性
        link = ''
        if link_el:
            link = (link_el.get('href') or '').strip()
            if not link:
                link = link_el.get_text(strip=True)

        if len(title) < 15 or is_blacklisted(title):
            continue

        # 如果没有 link，用guid
        if not link:
            guid_el = item.select_one('guid')
            if guid_el:
                link = guid_el.get_text(strip=True)

        results.append({
            'title': title,
            'url': link,
            'source': cfg['source'],
            'region_hint': cfg['region_hint'],
        })
        if len(results) >= cfg['max']:
            break

    return results

# ============================================================
# HTML 采集
# ============================================================

def fetch_html_source(cfg):
    resp = fetch_with_retry(cfg['url'])
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    results = []
    seen = set()

    for article in soup.select(cfg['article_sel'])[:cfg['max'] * 4]:
        a = article.select_one(cfg['title_sel'])
        if not a:
            continue
        title = a.get_text(strip=True)
        url = a.get('href', '')
        if not title or len(title) < 15 or title in seen or is_blacklisted(title):
            continue
        if not url:
            continue
        if not url.startswith('http'):
            if url.startswith('/'):
                base = '/'.join(cfg['url'].split('/')[:3])
                url = base + url
            else:
                continue
        seen.add(title)
        results.append({
            'title': title,
            'url': url,
            'source': cfg['source'],
            'region_hint': cfg['region_hint'],
        })
        if len(results) >= cfg['max']:
            break

    return results

# ============================================================
# Gemini AI 分析
# ============================================================

def configure_gemini():
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return False
    genai.configure(api_key=api_key)
    return True

def analyze_events_gemini(items):
    """
    调用 Gemini 批量分析。
    失败时返回 None（触发降级）。
    """
    model = genai.GenerativeModel('gemini-2.0-flash-exp')

    news_list = [{'title': it['title'], 'url': it['url'], 'source': it['source']} for it in items]
    news_json = json.dumps(news_list, ensure_ascii=False)

    prompt = f"""分析以下新闻，筛选非中美互联网科技动态。只返回 JSON 数组（不要 markdown）：

{news_json}

规则：
- keep=true：非中美公司的融资/IPO/并购/重要产品发布/行业趋势/监管政策
- is_china_us=true：新闻主体是美国或中国公司的
- keep=false：新闻主体是美国公司（微软/苹果/谷歌/亚马逊/OpenAI等发布的产品/财报/裁员等）

JSON格式：
[{{"url":"...","keep":true/false,"is_china_us":true/false,"region":"欧洲|亚太|中东|拉美|非洲|未知","companies":["非中美公司"],"why_important":"中文25字以内","impact_scope":"中文20字以内","impact_range":"全球|区域|行业","score":1-10}}]"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # 去掉 markdown 代码块
        for marker in ['```json', '```']:
            if marker in text:
                parts = text.split(marker)
                for p in parts[1:]:
                    text = p.strip()
                    if text.endswith('```'):
                        text = text[:-3].strip()
                    break
        text = re.sub(r'^(json\s*)', '', text, flags=re.IGNORECASE).strip()
        results = json.loads(text)
        return {r['url']: r for r in results if isinstance(r, dict) and 'url' in r}
    except Exception as e:
        print(f"  [Gemini 分析失败: {e}] → 降级为保留全部模式")
        return None

def build_event(item, analysis=None):
    """将原始条目构造为事件对象"""
    score = 5
    if analysis:
        score = analysis.get('score', 5)

    if score >= 8:
        level = 'A'
    elif score >= 6:
        level = 'B'
    elif score >= 4:
        level = 'C'
    else:
        level = 'D'

    why = '待分析'
    impact = '未知'
    companies = []
    region = item.get('region_hint', '未知')

    if analysis:
        why = analysis.get('why_important', '待分析')
        impact = analysis.get('impact_scope', '未知')
        companies = analysis.get('companies', [])
        region = analysis.get('region', region)

    return {
        'title': item['title'],
        'url': item['url'],
        'source': item['source'],
        'level': level,
        'score': score,
        'region': region,
        'companies': companies,
        'why_important': why,
        'impact_scope': impact,
        'impact_range': analysis.get('impact_range', '行业') if analysis else '行业',
        'date': datetime.now().isoformat(),
    }

# ============================================================
# 主函数
# ============================================================

def classify_level(score):
    if score >= 8: return 'A'
    if score >= 6: return 'B'
    if score >= 4: return 'C'
    return 'D'

def main():
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"\n🌍 全球互联网动态情报站")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   模式：RSS采集 {'+ Gemini分析' if configure_gemini() else '(无API，跳过AI分析)'}\n")

    # ---- 加载历史数据 ----
    os.makedirs('data', exist_ok=True)
    try:
        with open('data/events.json', 'r', encoding='utf-8') as f:
            all_events = json.load(f)
        if isinstance(all_events, list):
            all_events = {}
    except Exception:
        all_events = {}

    # ---- Step 1: RSS 采集 ----
    print("📡 采集 RSS 信源...")
    all_items = []
    for cfg in RSS_FEEDS:
        items = fetch_rss_feed(cfg)
        if items:
            print(f"  [{cfg['name']}] {len(items)} 条")
            all_items.extend(items)
        time.sleep(0.3)

    # ---- Step 2: HTML 采集（补充）----
    print("\n📡 采集 HTML 信源（备用）...")
    for cfg in HTML_SOURCES:
        items = fetch_html_source(cfg)
        if items:
            print(f"  [{cfg['name']}] {len(items)} 条")
            all_items.extend(items)
        time.sleep(0.3)

    # ---- Step 3: 去重 ----
    seen_urls = set()
    unique_items = []
    for item in all_items:
        if item['url'] and item['url'] not in seen_urls:
            seen_urls.add(item['url'])
            unique_items.append(item)

    total = len(unique_items)
    print(f"\n📊 合计：{total} 条（去重后）")

    if total == 0:
        print("❌ 未采集到任何内容，检查网络连接")
        return

    # ---- Step 4: Gemini AI 分析 ----
    use_gemini = configure_gemini()
    today_events = []

    if use_gemini:
        print(f"\n🤖 正在调用 Gemini API 分析 {total} 条...")
        batch_size = 8
        for i in range(0, total, batch_size):
            batch = unique_items[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            print(f"  批次 {batch_num}/{total_batches} ...", end='', flush=True)

            result_map = analyze_events_gemini(batch)

            if result_map is None:
                # Gemini 失败 → 降级：保留所有
                print(" Gemini失败，保留全部")
                for item in batch:
                    today_events.append(build_event(item))
            else:
                kept = 0
                for item in batch:
                    r = result_map.get(item['url'], {})
                    if not r.get('is_china_us', False):
                        today_events.append(build_event(item, r))
                        kept += 1
                print(f" 保留 {kept}/{len(batch)} 条")
            time.sleep(0.5)
    else:
        # 无 API → 直接保留所有（不过滤）
        print("\n⚡ 无 Gemini API，直接保留全部采集内容")
        for item in unique_items:
            today_events.append(build_event(item))

    # ---- Step 5: 保存 ----
    # 合并：今天的 + 历史的（不去掉旧日期的数据）
    if today in all_events and all_events[today]:
        # 今天已有数据 → 合并去重
        existing_urls = {e['url'] for e in all_events[today]}
        for e in today_events:
            if e['url'] not in existing_urls:
                all_events[today].append(e)
    else:
        all_events[today] = today_events

    # 清理 8 天前的数据
    cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    all_events = {k: v for k, v in all_events.items() if k >= cutoff}

    with open('data/events.json', 'w', encoding='utf-8') as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    # 统计
    region_stats = {}
    for e in all_events.get(today, []):
        region_stats[e['region']] = region_stats.get(e['region'], 0) + 1

    print(f"\n✅ 完成！{today} 共 {len(all_events.get(today, []))} 条事件")
    if region_stats:
        print(f"   区域：{region_stats}")
    print(f"   总计 {sum(len(v) for v in all_events.values())} 条（{len(all_events)} 天）")

if __name__ == '__main__':
    main()
