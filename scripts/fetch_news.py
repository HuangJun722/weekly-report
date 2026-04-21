"""
全球互联网动态情报站 — 数据采集
目标：融资 | 并购 | 财报披露 | 重大战略 — 发现 ICT 合作机会点
"""

import json, os, time, re, hashlib
from datetime import datetime, timedelta
from pathlib import Path
import feedparser

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import warnings; warnings.filterwarnings('ignore')
import requests
from bs4 import BeautifulSoup

# ============================================================
# 并行采集优化：aiohttp
# ============================================================
try:
    import aiohttp
    import asyncio
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    print("安装 aiohttp（并行采集）...")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp", "-q"])
    import aiohttp
    import asyncio
    HAS_AIOHTTP = True

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36',
    'Referer': 'https://www.google.com/',
}

REQUEST_DELAY = 1.2  # 避免被封（仅用于重试，非采集）
REQUEST_TIMEOUT = 8   # 单次请求超时（秒），降级提速

# ============================================================
# ���源：重点标注是否为融资专属源
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
    {'name': 'TechWire Asia',    'url': 'https://techwireasia.com/feed/',               'source': 'TechWire Asia', 'region': '亚太', 'priority': 2},
    # DealStreetAsia RSS 已停用（"Temporarily Disabled"），改用 HTML 降级采集
    # e27 已移除：Cloudflare 全面拦截，无法绕过
    # Google News RSS 不可用：链接为 Google 内部跳转，非原始来源
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
# 27家重点公司监控 — Google News RSS
# ============================================================

COMPANY_SOURCES = [
    # 中国企业海外
    {'name': 'ByteDance/TikTok', 'query': 'ByteDance overseas', 'region': '中资', 'priority': 3},
    {'name': 'Tencent', 'query': 'Tencent international', 'region': '中资', 'priority': 2},
    {'name': 'Alibaba', 'query': 'Alibaba international overseas', 'region': '中资', 'priority': 2},
    {'name': 'JD.com', 'query': 'JD.com international overseas', 'region': '中资', 'priority': 2},
    {'name': 'Kuaishou', 'query': 'Kuaishou overseas international', 'region': '中资', 'priority': 1},
    {'name': 'Ant Group', 'query': 'Ant Group international overseas', 'region': '中资', 'priority': 2},
    {'name': 'Meituan', 'query': 'Meituan international overseas', 'region': '中资', 'priority': 1},
    # 亚太
    {'name': 'Kakao', 'query': 'Kakao', 'region': '亚太', 'priority': 2},
    {'name': 'Naver', 'query': 'Naver', 'region': '亚太', 'priority': 2},
    {'name': 'Rakuten', 'query': 'Rakuten', 'region': '亚太', 'priority': 2},
    {'name': 'Sea Limited', 'query': 'Sea Limited Shopee', 'region': '亚太', 'priority': 2},
    {'name': 'Grab', 'query': 'Grab holdings Singapore', 'region': '亚太', 'priority': 2},
    {'name': 'Gojek', 'query': 'Gojek', 'region': '亚太', 'priority': 2},
    {'name': 'VNG Group', 'query': 'VNG Group Vietnam', 'region': '亚太', 'priority': 1},
    {'name': 'Yahoo', 'query': 'Yahoo Tech APAC', 'region': '亚太', 'priority': 1},
    {'name': 'Cyberagent', 'query': 'CyberAgent Japan', 'region': '亚太', 'priority': 1},
    # 欧洲
    {'name': 'Adyen', 'query': 'Adyen', 'region': '欧洲', 'priority': 2},
    {'name': 'Zalando', 'query': 'Zalando Germany', 'region': '欧洲', 'priority': 2},
    {'name': 'Allegro', 'query': 'Allegro Polish ecommerce', 'region': '欧洲', 'priority': 2},
    {'name': 'Trendyol', 'query': 'Trendyol', 'region': '欧洲', 'priority': 1},
    # 拉美
    {'name': 'MercadoLibre', 'query': 'MercadoLibre', 'region': '拉美', 'priority': 3},
    {'name': 'Rappi', 'query': 'Rappi Colombia', 'region': '拉美', 'priority': 1},
    # 中东
    {'name': 'Noon', 'query': 'Noon ecommerce UAE Dubai', 'region': '中东', 'priority': 2},
    {'name': 'Careem', 'query': 'Careem UAE', 'region': '中东', 'priority': 2},
    {'name': 'Tabby', 'query': 'Tabby UAE fintech', 'region': '中东', 'priority': 2},
    {'name': 'Kaspi.kz', 'query': 'Kaspi.kz super app', 'region': '中东', 'priority': 2},
    # 非洲
    {'name': 'Jumia', 'query': 'Jumia Africa ecommerce', 'region': '非洲', 'priority': 2},
    {'name': 'Konga', 'query': 'Konga Nigeria', 'region': '非洲', 'priority': 1},
]

# Google News RSS 关键词黑名单（公司新闻噪音）
COMPANY_BLACKLIST = [
    'show hn:', 'launch HN', 'Ask HN:', 'Hiring ',
    'Introducing Claude', 'Introducing GPT', 'Introducing Gemini',
    'openai launches', 'anthropic announces', 'google announces',
    'apple announces', 'meta announces', 'microsoft announces',
    'weekly newsletter', 'daily newsletter',
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
    # 战略/市场（出海、全球化、产品发布）
    if any(k in t for k in ['partners with', 'partnership', 'strategic',
                       'joint venture', 'expands to', 'flagship store',
                       'exits ', 'layoffs', 'shutdown', 'spins off',
                       'disrupts', 'CEO says', 'CEO on', 'ceo on', 'expansion',
                       'launches ', 'rolls out', 'deploys', 'to launch',
                       'launches in', 'listing ', 'eyes $', '$ valuation',
                       # 出海/国际化关键词（扩充）
                       'overseas', 'offshore', 'abroad', 'foreign market',
                       'international', 'global launch', 'global push', 'global ambition',
                       'enter', 'enters', 'entering', 'to expand', 'expanding',
                       'global expansion', 'international expansion',
                       'digital hub', 'digital status', 'digital economy',
                       'tech hub', 'tech investment', 'AI investment',
                       # 产品/市场动作（扩充）
                       'debut', 'debuts', 'debuting', 'launch', 'launched',
                       'available in', 'rollout', 'available internationally',
                       'files for IPO', 'goes public', 'listing',
                       'turnaround', 'restructure', 'reorganization',
                       'cloud service', 'cloud expansion', 'data center',
                       'partners with', 'signs MOU', 'joint venture']):
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

# --- 缓存（仅用于单次运行内去重，不跨天保留）---
CACHE_DIR = Path('data/.cache')
CACHE_TTL = 60 * 60 * 24  # 24小时

def _cache_key(url):
    return hashlib.md5(url.encode()).hexdigest()

def _cache_get(url):
    """返回 (body, age_seconds)，无缓存或过期返回 (None, None)"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / _cache_key(url)
    if not f.exists(): return None, None
    age = time.time() - f.stat().st_mtime
    if age > CACHE_TTL:
        f.unlink()
        return None, None
    return f.read_text(encoding='utf-8', errors='ignore'), age

def _cache_set(url, body):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / _cache_key(url)
    f.write_text(body, encoding='utf-8')


def _clear_old_cache():
    """每次运行前清理旧缓存，确保抓取最新内容"""
    import shutil
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  🗑  已清理历史缓存（{CACHE_DIR}）")


def fetch_url(url, retries=1):
    """
    快速失败策略：
    - 只重试1次（之前重试3次无意义，失败通常是网络/CF，超时后立即失败更好）
    - 超时8s（之前20s太长，RSS本身5s内必返回）
    - 优先读缓存，缓存命中则跳过网络请求
    """
    # 1. 缓存命中
    body, age = _cache_get(url)
    if body:
        print(f"  [CACHE] {url[:50]}... ({age:.0f}s old)")
        return body  # 返回文本，调用方用同样方式解析

    # 2. 网络请求（最多重试1次）
    for i in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code in (403, 429):
                if i < retries:
                    time.sleep(2 * (i + 1)); continue
                return None
            r.raise_for_status()
            body = r.text
            _cache_set(url, body)  # 写缓存
            return body
        except Exception:
            if i < retries:
                time.sleep(2 ** i); continue
            return None
    return None


async def fetch_url_async(session, url, semaphore):
    """异步单 URL 抓取（带信号量控制并发）"""
    async with semaphore:
        # 检查缓存
        body, age = _cache_get(url)
        if body:
            return url, body, age, True  # cache_hit

        try:
            async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as r:
                if r.status in (403, 429):
                    return url, None, 0, False
                body = await r.text()
                _cache_set(url, body)
                return url, body, 0, False
        except Exception as e:
            return url, None, 0, False


async def fetch_all_parallel(urls):
    """
    并行抓取所有 URL。
    返回 {url: (body_or_None, from_cache)}
    """
    semaphore = asyncio.Semaphore(8)  # 最多8个并发
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url_async(session, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    out = {}
    for item in results:
        if isinstance(item, Exception):
            continue
        url, body, age, cached = item
        out[url] = (body, cached)
    return out

# ============================================================
# 工具函数
# ============================================================

def _parse_rss_date(item):
    """从 RSS/Atom 条目提取文章发布日期，返回 ISO 格式字符串，失败返回 None"""
    # 已废弃：feedparser 自动标准化日期，保留接口兼容
    return None

# ============================================================
# 采集
# ============================================================

def _parse_rss_text(cfg, text):
    """解析 RSS/Atom 文本，返回事件列表。feedparser 自动处理编码/日期标准化。"""
    if not text: return []
    text = text.strip()
    if not any(text.startswith(x) or x in text[:300] for x in ['<?xml', '<rss', '<feed']):
        return []

    try:
        parsed = feedparser.parse(text)
    except Exception:
        return []

    results = []
    max_items = cfg.get('max', 8)

    for entry in parsed.entries:
        if len(results) >= max_items: break

        # 标题
        title = (entry.get('title') or '').strip()
        if len(title) < 15 or is_blacklisted(title):
            continue

        # 链接：优先 href 属性，其次纯文本 link
        link = ''
        link_val = entry.get('link', '')
        if isinstance(link_val, dict):
            link = (link_val.get('href') or '').strip()
        else:
            link = (link_val or '').strip()
        if not link:
            link = (entry.get('id') or '').strip()
        if not link:
            continue

        # 日期：feedparser 标准化时间，URL 日期兜底
        article_date = None
        tp = entry.get('published_parsed') or entry.get('updated_parsed')
        if tp:
            article_date = datetime(*tp[:3]).strftime('%Y-%m-%d')
        if not article_date:
            article_date = _extract_date_from_url(link)

        types = detect_event_types(title)
        results.append({
            'title': title,
            'url': link,
            'source': cfg.get('source', cfg.get('name', 'Google News')),
            'region': cfg['region'],
            'priority': cfg.get('priority', 1),
            'event_types': types,
            'article_date': article_date,
        })
    return results


def fetch_rss(cfg):
    """顺序抓取（兼容旧接口，保留给 fetch_html 等调用方使用）"""
    text = fetch_url(cfg['url'])
    return _parse_rss_text(cfg, text)

# ============================================================
# HTML 备用采集（RSS 失效时的降级方案）
# ============================================================

# HTML 降级采集时过滤报告/评论类 URL（这类链接无情报价值）
HTML_SKIP_URL_PATTERNS = [
    '/reports/',          # 报告类
    '/review/',           # 回顾类
    'funding-review',     # 融资回顾
    'women-founders',     # 女性创始人报告
    'greater-china',      # 大中华区报告
    'southeast-asia',    # 东南亚报告
    'private-equity',     # PE 基金报告
    'lp-view',           # LP 视角（评论，非新闻）
    'startup-watch',     # 创业观察（长列表，非新闻）
]

HTML_SKIP_TITLE_PATTERNS = [
    'review', 'roundup', 'weekly recap', 'monthly recap',
    '2025 ', '2024 ', '2023 ',  # 历史回顾类标题
    ' Q4 ', ' Q1 ', ' Q2 ', ' Q3 ',  # 季度报告
]

HTML_SOURCES = [
    # DealStreetAsia RSS 停用（"Temporarily Disabled"），主站为 JS SPA
    # 低频尝试：只采集新闻类页面，报告/评论页已过滤
    {'name': 'DealStreetAsia', 'url': 'https://dealstreetasia.com/', 'source': 'DealStreetAsia', 'region': '亚太', 'priority': 1},
    # e27：Angular JS + Cloudflare 双层保护，RSS + HTML 均无法采集，已移除
]

def _extract_date_from_url(url):
    """从 URL 提取日期兜底，如 /2026/04/15/"""
    m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def fetch_company_news(cfg):
    """
    从 Google News RSS 抓取特定公司的新闻
    只取当天/昨天的 + 有信号的事件 + 每公司最多3条
    """
    import urllib.parse
    query = urllib.parse.quote(cfg['query'])
    url = f'https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en'
    body = fetch_url(url)
    if not body: return []

    if not any(body.strip().startswith(x) or x in body[:300] for x in ['<?xml', '<rss', '<feed']):
        return []

    try:
        parsed = feedparser.parse(body)
    except Exception:
        return []

    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    allowed_dates = {today, yesterday}

    results = []
    seen_titles = set()  # 标题归一化去重（多家报道同一事件只取第一条）

    for entry in parsed.entries:
        if len(results) >= 3: break  # 每公司最多3条

        title = (entry.get('title') or '').strip()
        if len(title) < 15: continue

        # 标题归一化去重
        norm = re.sub(r'[^\w]', '', title.lower())[:40]
        if norm in seen_titles:
            continue
        seen_titles.add(norm)

        # 基础噪音过滤
        title_lower = title.lower()
        if any(kw in title_lower for kw in COMPANY_BLACKLIST): continue

        link = ''
        link_val = entry.get('link', '')
        if isinstance(link_val, dict):
            link = (link_val.get('href') or '').strip()
        else:
            link = (link_val or '').strip()
        if not link:
            link = (entry.get('id') or '').strip()
        if not link: continue

        # 日期过滤：RSS日期优先，URL日期兜底
        article_date = None
        tp = entry.get('published_parsed') or entry.get('updated_parsed')
        if tp:
            article_date = datetime(*tp[:3]).strftime('%Y-%m-%d')
        if not article_date:
            article_date = _extract_date_from_url(link)
        if article_date and article_date not in allowed_dates:
            continue

        types = detect_event_types(title)
        # 公司动态只要有company_name就保留，不再过滤other类型
        # 因为扩充关键词后other类型减少，且other中也有有价值的出海新闻

        results.append({
            'title': title,
            'url': link,
            'source': 'Google News',
            'region': cfg['region'],
            'priority': cfg.get('priority', 1),
            'event_types': types,
            'article_date': article_date,
            'is_company': True,
            'company_name': cfg['name'],
        })
    return results


def fetch_html(cfg):
    """从 HTML 页面提取文章列表（降级方案，针对各站点结构定制）"""
    body = fetch_url(cfg['url'])
    if not body: return []

    soup = BeautifulSoup(body, 'html.parser')
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
        # 过滤报告/评论类 URL
        if any(p in link.lower() for p in HTML_SKIP_URL_PATTERNS): continue
        # 过滤报告类标题
        title_lower = title.lower()
        if any(p.lower() in title_lower for p in HTML_SKIP_TITLE_PATTERNS): continue
        # 只保留绝对 URL 或同源链接
        if not link.startswith('http'):
            if link.startswith('/'):
                base = cfg['url'].split('/')[2]  # 提取域名
                link = 'https://' + base + link

        types = detect_event_types(title)
        results.append({
            'title': title,
            'url': link,
            'source': cfg.get('source', cfg.get('name', 'Google News')),
            'region': cfg['region'],
            'priority': cfg.get('priority', 1),
            'event_types': types,
            'article_date': None,  # HTML 无 pubDate，归入运行日
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
    2. 公司监控事件全部保留（is_company=True）
    3. 其他事件按 priority 排序，每天最多 40 条（通用部分）
    """
    # 信号事件（全部保留）
    signal = [it for it in items if it['event_types'][0] != 'other']
    # 公司监控事件（全部保留，不管 event_types 是什么）
    company = [it for it in items if it.get('is_company')]
    # 非信号、非公司事件（按 priority 排序，取剩余名额）
    others = [it for it in items if it['event_types'][0] == 'other' and not it.get('is_company')]
    others.sort(key=lambda x: x.get('priority', 1), reverse=True)

    result = []
    used_urls = set()
    used_title_norm = set()  # 标题归一化去重（前60字符）

    def _norm_title(title):
        return re.sub(r'[^\w]', '', title.lower())[:60]

    def _add_unique(it):
        norm = _norm_title(it['title'])
        if it['url'] not in used_urls and norm not in used_title_norm:
            result.append(it)
            used_urls.add(it['url'])
            used_title_norm.add(norm)
            return True
        return False

    # 1. 公司监控事件（全部保留）
    for it in company:
        _add_unique(it)

    # 2. 全部信号事件
    for it in signal:
        _add_unique(it)

    # 3. 非信号事件补足到 MAX_DAILY，每个区域最多 MAX_PER_REGION 条
    regions = list(dict.fromkeys(it['region'] for it in items))  # 保持原始顺序
    for region in regions:
        remaining = MAX_DAILY - len(result)
        if remaining <= 0: break
        region_others = [it for it in others if it['region'] == region and it['url'] not in used_urls]
        signal_in_region = sum(1 for it in result if it['region'] == region)
        max_other_for_region = max(0, MAX_PER_REGION - signal_in_region)
        for it in region_others[:max_other_for_region]:
            _add_unique(it)
            if len(result) >= MAX_DAILY: break

    return result

# ============================================================
# MiniMax API（主力）
# ============================================================

def configure_minimax():
    """配置 MiniMax API，优先使用"""
    key = os.environ.get('MINIMAX_API_KEY')
    model = os.environ.get('MINIMAX_MODEL', 'MiniMax-M2.7')
    print(f"  🔑 MINIMAX_API_KEY: {'已设置 (' + str(len(key)) + ' 字符)' if key else '未设置 ❌'}")
    if not key:
        print("  ⚠️  未设置 MINIMAX_API_KEY，将降级使用豆包")
        return False
    if len(key) < 10:
        print(f"  ❌ MINIMAX_API_KEY 长度异常（{len(key)} 字符），降级使用豆包")
        return False
    print(f"  ✅ MiniMax API 配置检查通过，模型: {model}")
    return True


def analyze_events_minimax(items):
    """
    使用 MiniMax 大模型分析新闻事件（OpenAI 兼容格式）
    模型: MiniMax-Text-01
    """
    import os
    api_key = os.environ.get('MINIMAX_API_KEY')
    if not api_key:
        print("  ⚠️  未设置 MINIMAX_API_KEY")
        return None

    url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    model = os.environ.get('MINIMAX_MODEL', 'MiniMax-M2.7')
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json"
    }

    news = [{'title': it['title'], 'url': it['url'], 'source': it['source'], 'region': it.get('region','')} for it in items]
    prompt = AI_SYSTEM_PROMPT + "\n" + AI_EXAMPLES + "\n\n分析以下事件，返回JSON数组：\n" + json.dumps(news, ensure_ascii=False) + "\n\n返回JSON："

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.1
    }

    # 创建不使用代理的session（MiniMax不需要代理）
    session = requests.Session()
    session.trust_env = False  # 禁用环境变量代理

    for attempt in range(3):
        try:
            resp = session.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 429:
                wait = (attempt + 1) * 10
                print(f"  ⚠️  MiniMax API 配额耗尽（429），等待 {wait}s 后重试...")
                time.sleep(wait)
                continue
            if resp.status_code == 400:
                print(f"  ⚠️  MiniMax API 请求错误（400）: {resp.text[:200]}，尝试降级...")
                return None
            if resp.status_code != 200:
                print(f"  ❌ MiniMax API HTTP {resp.status_code}: {resp.text[:300]}")
                return None
            data = resp.json()
            text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if not text:
                print("  ⚠️  MiniMax 返回空内容: " + str(data))
                return None
            for m in ['```json', '```']:
                if m in text:
                    parts = text.split(m)
                    for p in parts[1:]:
                        text = p.strip()
                        if text.endswith('```'):
                            text = text[:-3].strip()
                        break
                    break
            result = json.loads(re.sub(r'^json\s*', '', text, flags=re.I))
            if isinstance(result, list):
                result = [r for r in result if r.get('url') and r.get('summary_short')]
            print(f"  ✅ MiniMax 分析成功，{len(result) if isinstance(result, list) else 0} 条")
            return result
        except requests.exceptions.Timeout:
            print(f"  ⚠️  MiniMax API 超时（60s），快速失败，跳过该批次")
            return None
        except json.JSONDecodeError as e:
            if attempt < 2:
                wait = (attempt + 1) * 5
                print(f"  ⚠️  MiniMax 返回非JSON，尝试修正解析...")
                import re as re2
                match = re2.search(r'\[[\s\S]*\]', text if 'text' in dir() else '')
                if match:
                    try:
                        result = json.loads(match.group())
                        result = [r for r in result if isinstance(r, dict) and r.get('url')]
                        if result:
                            print(f"  ✅ 修正解析成功，提取 {len(result)} 条")
                            return result
                    except: pass
                print(f"  解析失败，等待 {wait}s 后重试...")
                time.sleep(wait)
                continue
            print(f"  ❌ MiniMax JSON 解析最终失败")
            return None
        except Exception as e:
            if attempt < 2:
                wait = (attempt + 1) * 5
                print(f"  ⚠️  MiniMax API 调用失败（{type(e).__name__}），等待 {wait}s 后重试...")
                time.sleep(wait)
                continue
            print(f"  ❌ MiniMax API 最终失败: {type(e).__name__} {str(e)[:200]}")
            return None
    return None


# ============================================================
# 豆包分析（备份）
# ============================================================

def configure_doubao():
    key = os.environ.get('DOUBAO_API_KEY')
    model = os.environ.get('DOUBAO_MODEL', 'ep-20260409223830-dnt5b')
    print(f"  🔑 DOUBAO_API_KEY: {'已设置 (' + str(len(key)) + ' 字符)' if key else '未设置 ❌'}")
    if not key:
        print("  ❌ 未找到 DOUBAO_API_KEY，跳过 AI 分析")
        return False
    if len(key) < 10:
        print(f"  ❌ DOUBAO_API_KEY 长度异常（{len(key)} 字符），跳过 AI 分析")
        return False
    print(f"  ✅ 豆包 API 配置检查通过，模型: {model}")
    return True

# ============================================================
# AI 分析 Prompt 模板（Few-shot，输出稳定）
# ============================================================

AI_SYSTEM_PROMPT = """你是全球互联网科技情报分析师。受众是ICT从业者，关注：合作机会、供应链变化、预算流向。
每条事件输出4个字段：summary_short（事实）、reason（为什么重要，ICT视角）、impact（影响谁）、insight_label（资金流向/合作机会/警示信号/背景补充）。

reason 要求：必须从标题提取公司名/产品名/技术名，组合地区+行业+具体机会描述，格式固定为"[地区][行业]具体描述"。禁止出现"无法判断""无法确定""待确认""相关"等模糊词。
impact 要求：指明具体受益方或受损方，如"东南亚电商平台""海湾主权基金""非洲移动支付商"，禁止"相关行业"。
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
输出: {"url":"","summary_short":"意大利电信裁员2000人","reason":"���统运营商压缩成本，转向网络外包，ICT服务商机会增加","impact":"IT外包商、网络设备供应商","insight_label":"警示信号","score":7}

示例6（财报盈利）：
标题: "Nubank Q1 revenue up 34% to $2.8B"
输出: {"url":"","summary_short":"Nubank营收$2.8B，同比+34%","reason":"拉美数字银行持续高增长，东南亚复制模式具有参考价值","impact":"拉美金融科技合作方、银行科技供应商","insight_label":"背景补充","score":6}

示例7（财报亏损）：
标题: "Gorillas files for insolvency amid funding crunch"
输出: {"url":"","summary_short":"欧洲快送平台Gorillas申请破产保护","reason":"即时配送赛道资金耗尽，同类公司需警惕融资环境恶化信号","impact":"同类快送平台、物流技术供应商","insight_label":"警示信号","score":8}
"""

def analyze_events_doubao(items):
    """
    使用豆包大模型分析新闻事件（OpenAI 兼容 API）
    模型：doubao-pro-32k
    """
    import os
    api_key = os.environ.get('DOUBAO_API_KEY')
    if not api_key:
        print("  ⚠️  未设置 DOUBAO_API_KEY，降级跳过 AI 分析")
        return None

    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    model = os.environ.get('DOUBAO_MODEL', 'ep-20260409223830-dnt5b')
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json"
    }

    news = [{'title': it['title'], 'url': it['url'], 'source': it['source'], 'region': it.get('region','')} for it in items]
    prompt = AI_SYSTEM_PROMPT + "\n" + AI_EXAMPLES + "\n\n分析以下事件，返回JSON数组：\n" + json.dumps(news, ensure_ascii=False) + "\n\n返回JSON："

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.1
    }

    for attempt in range(3):  # 最多重试3次
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)  # 30s timeout，快速失败
            if resp.status_code == 429:
                wait = (attempt + 1) * 10
                print("  ⚠️  豆包 API 配额耗尽（429），等待 " + str(wait) + "s 后重试...")
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                print(f"  ❌ 豆包 API HTTP {resp.status_code}: {resp.text[:300]}")
                return None
            data = resp.json()
            text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if not text:
                print("  ⚠️  豆包返回空内容: " + str(data))
                return None
            for m in ['```json', '```']:
                if m in text:
                    parts = text.split(m)
                    for p in parts[1:]:
                        text = p.strip()
                        if text.endswith('```'):
                            text = text[:-3].strip()
                        break
                    break
            result = json.loads(re.sub(r'^json\s*', '', text, flags=re.I))
            if isinstance(result, list):
                result = [r for r in result if r.get('url') and r.get('summary_short')]
            return result
        except requests.exceptions.Timeout:
            print(f"  ⚠️  豆包 API 超时（30s），快速失败，跳过该批次")
            return None  # 超时直接跳过，不重试
        except json.JSONDecodeError as e:
            if attempt < 2:
                wait = (attempt + 1) * 5
                print(f"  ⚠️  豆包返回非JSON，尝试修正解析...")
                import re as re2
                match = re2.search(r'\[[\s\S]*\]', text if 'text' in dir() else '')
                if match:
                    try:
                        result = json.loads(match.group())
                        result = [r for r in result if isinstance(r, dict) and r.get('url')]
                        if result:
                            print(f"  ✅ 修正解析成功，提取 {len(result)} 条")
                            return result
                    except: pass
                print(f"  解析失败，等待 {wait}s 后重试...")
                time.sleep(wait)
                continue
            print(f"  ❌ 豆包 JSON 解析最终失败")
            return None
        except Exception as e:
            if attempt < 2:
                wait = (attempt + 1) * 5
                print(f"  ⚠️  豆包 API 调用失败（{type(e).__name__}），等待 {wait}s 后重试...")
                time.sleep(wait)
                continue
            print(f"  ❌ 豆包 API 最终失败: {type(e).__name__} {str(e)[:200]}")
            return None
    return None


def analyze_single_event_minimax(item):
    """单条事件分析（MiniMax批次失败时的兜底）"""
    try:
        result = analyze_events_minimax([item])
        return result
    except Exception:
        return None


def analyze_single_event_doubao(item):
    """单条事件分析（豆包批次失败时的兜底）"""
    # 单条分析也有30s timeout，不等待
    try:
        result = analyze_events_doubao([item])
        return result
    except Exception:
        return None

def _calc_score(item):
    """程序评分：基于金额、事件类型、区域权重计算确定性分数"""
    title = item.get('title', '')
    ev_type = item.get('event_types', ['other'])[0]

    # 金额解析
    amount = 0
    for pat, mult in [
        (r'\$([0-9,]+(?:\.\d+)?)\s*[Bb](?:illion)?', 1000),
        (r'€([0-9,]+(?:\.\d+)?)\s*[Mm](?:illion)?', 1),
        (r'\$([0-9,]+(?:\.\d+)?)\s*[Mm](?:illion)?', 1),
    ]:
        m = re.search(pat, title, re.I)
        if m:
            amount = float(m.group(1).replace(',', '')) * mult
            break

    # 融资金额分
    if amount >= 1000: amt_pts = 5
    elif amount >= 500: amt_pts = 4
    elif amount >= 100: amt_pts = 3
    elif amount >= 20: amt_pts = 2
    elif amount >= 5: amt_pts = 1
    else: amt_pts = 0

    # 事件类型分
    type_pts = {'ma': 2, 'earnings': 2, 'funding': 1, 'strategy': 1, 'other': 0}.get(ev_type, 0)

    # 区域权重
    region_mult = {'非洲': 1.3, '中东': 1.25, '亚太': 1.2, '拉美': 1.15, '欧洲': 1.0}.get(item.get('region', ''), 1.0)

    # 有公司名
    named_pts = 1 if item.get('companies') else 0

    raw = (amt_pts + type_pts + named_pts) * region_mult
    return max(min(int(raw), 10), 1)


def build_event(item, analysis=None):
    """构建事件对象：程序评分始终生效，AI 只补充 reason/impact/insight_label"""
    # 程序评分（确定性，始终运行）
    score = _calc_score(item)
    level = 'A' if score >= 8 else 'B' if score >= 6 else 'C' if score >= 4 else 'D'
    # 有 AI 分析时（必须是 dict 类型，防止列表或其他异常类型）
    if analysis and isinstance(analysis, dict):
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
            'companies': analysis.get('companies', []) or [],
            'is_company': item.get('is_company', False),
            'company_name': item.get('company_name', ''),
            'date': item.get('article_date', datetime.now().isoformat()[:10]),
        }
    # 无 AI 分析时的 fallback
    ev_type = item.get('event_types', ['other'])[0]
    default_label = {
        'funding': '资金流向',
        'ma': '资金流向',
        'earnings': '背景补充',
        'strategy': '合作机会',
    }.get(ev_type, '背景补充')
    why_fallback = {
        'funding': f"{item['region']}科技公司融资事件，金额待确认",
        'ma': f"{item['region']}科技公司并购/收购",
        'earnings': f"{item['region']}科技公司财报披露",
        'strategy': f"{item['region']}科技公司战略动态",
    }.get(ev_type, f"{item['region']}科技行业动态")
    return {
        'title': item['title'],
        'url': item['url'],
        'source': item['source'],
        'region': item['region'],
        'event_types': item['event_types'],
        'level': level,
        'score': score,
        'summary_short': item['title'][:25],
        'reason': why_fallback,
        'impact': '未知',
        'insight_label': default_label,
        'companies': [],
        'is_company': item.get('is_company', False),
        'company_name': item.get('company_name', ''),
        'date': item.get('article_date', datetime.now().isoformat()[:10]),
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

    # 采集（并行优化）
    _clear_old_cache()  # 清理旧缓存，确保���次都真实抓取
    print("📡 采集 RSS 信源（并行）...")
    t0 = time.time()

    # Step 1: 并行抓取所有 RSS 源文本
    rss_urls = [cfg['url'] for cfg in RSS_SOURCES]
    fetched = asyncio.run(fetch_all_parallel(rss_urls))

    # Step 2: 解析每个返回的文本
    raw = []
    cache_hits = sum(1 for _, (_, cached) in fetched.items() if cached)
    source_stats = {}  # {name: (success, failed)}
    for cfg in RSS_SOURCES:
        body, cached = fetched.get(cfg['url'], (None, False))
        if not body:
            print(f"  ✗ [{cfg['name']}] 失败（{cfg['region']}）")
            source_stats[cfg['name']] = '✗'
            continue
        cfg_copy = cfg.copy()
        items = _parse_rss_text(cfg_copy, body)
        mark = "📦" if cached else "🌐"
        sig = sum(1 for it in items if it['event_types'][0] != 'other')
        print(f"  {mark} [{cfg['name']}] {len(items)} 条（信号{sig} | {cfg['region']}）")
        source_stats[cfg['name']] = f'{len(items)} 条'
        raw.extend(items)

    print(f"\n  ⏱  采集耗时 {time.time()-t0:.1f}s | 缓存命中 {cache_hits}/{len(rss_urls)}")
    print(f"  📊 信源统计（{len(raw)} 条）：{' | '.join(f'{k}: {v}' for k, v in source_stats.items() if v != '✗')}")

    # HTML 备用采集（降级方案）
    if HTML_SOURCES:
        print("\n🌐 HTML 降级采集...")
        for cfg in HTML_SOURCES:
            items = fetch_html(cfg)
            sig = sum(1 for it in items if it['event_types'][0] != 'other')
            if items:
                print(f"  ⚡ [{cfg['name']}] {len(items)} 条（信号{sig} | 亚太）")
            else:
                print(f"  – [{cfg['name']}] 无内容")
            raw.extend(items)
            time.sleep(REQUEST_DELAY)

    # 27家公司监控（直接用 requests，不用 aiohttp，因为 aiohttp 不走系统代理）
    print("\n🏢 采集公司动态...")
    t1 = time.time()
    import urllib.parse
    company_raw = []
    for cfg in COMPANY_SOURCES:
        q = urllib.parse.quote(cfg['query'])
        url = f'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'
        body = fetch_url(url)  # fetch_url 内部会用 requests（支持代理）
        if not body:
            print(f"  ✗ [{cfg['name']}] 失败")
            continue
        items = _parse_rss_text(cfg.copy(), body)
        # 噪音过滤
        filtered = []
        for item in items:
            title_lower = item['title'].lower()
            if any(kw in title_lower for kw in COMPANY_BLACKLIST): continue
            filtered.append(item)
        sig = sum(1 for it in filtered if it['event_types'][0] != 'other')
        print(f"  🌐 [{cfg['name']}] {len(filtered)} 条（信号{sig}）")
        for item in filtered:
            item['is_company'] = True
            item['company_name'] = cfg['name']
        company_raw.extend(filtered)
        time.sleep(0.5)  # 避免请求过快

    # 公司新闻单独去重
    seen_company, company_unique = set(), []
    for it in company_raw:
        if it['url'] and it['url'] not in seen_company:
            seen_company.add(it['url'])
            company_unique.append(it)
    print(f"  ⏱  公司采集耗时 {time.time()-t1:.1f}s | {len(company_unique)} 条（去重后）")

    # 合并：公司新闻 + 通用新闻（分别去重）
    all_raw = company_unique + raw
    seen_all, unique = set(), []
    for it in all_raw:
        if it['url'] and it['url'] not in seen_all:
            seen_all.add(it['url'])
            unique.append(it)

    # 统计
    types = {'funding':0,'ma':0,'earnings':0,'strategy':0,'other':0}
    for it in unique: types[it['event_types'][0]] += 1
    regions = {}
    for it in unique: regions[it['region']] = regions.get(it['region'],0) + 1
    company_count = sum(1 for it in unique if it.get('is_company'))

    print(f"\n📊 采集：{len(unique)} 条（融资{types['funding']} | 并购{types['ma']} | 财报{types['earnings']} | 战略{types['strategy']} | 其他{types['other']}）")
    print(f"   区域：{regions} | 公司动态：{company_count} 条")

    # 智能过滤（公司新闻单独处理，不做 smart_filter）
    filtered = smart_filter(unique)
    types2 = {'funding':0,'ma':0,'earnings':0,'strategy':0,'other':0}
    for it in filtered: types2[it['event_types'][0]] += 1
    print(f"   过滤后：{len(filtered)} 条（融资{types2['funding']} | 并购{types2['ma']} | 财报{types2['earnings']} | 战略{types2['strategy']} | 其他{types2['other']}）")

    # AI 分析：MiniMax 优先，豆包降级
    use_minimax = configure_minimax()
    use_doubao_fallback = False
    today_events = []

    if use_minimax:
        print(f"\n🤖 MiniMax AI 分析（主力）...")
        for i in range(0, len(filtered), 8):
            batch = filtered[i:i+8]
            results = analyze_events_minimax(batch)
            if results is None:
                # MiniMax 批次失败 → 尝试豆包兜底
                print(f"  批次 {(i//8)+1} MiniMax 失败，尝试豆包降级...")
                if not use_doubao_fallback:
                    use_doubao_fallback = configure_doubao()
                if use_doubao_fallback:
                    results = analyze_events_doubao(batch)
                if results is None:
                    print(f"  批次 {(i//8)+1} 豆包也失败，跳过（程序生成reason）...")
                    for item in batch:
                        today_events.append(build_event(item))
                else:
                    for item in batch:
                        r = next((x for x in results if x.get('url') == item['url']), {})
                        today_events.append(build_event(item, r))
            else:
                for item in batch:
                    r = next((x for x in results if x.get('url') == item['url']), {})
                    today_events.append(build_event(item, r))
            print(f"  批次 {(i//8)+1}/{(len(filtered)+7)//8} 完成（{len(batch)}条）")
            time.sleep(0.5)
    elif configure_doubao():
        # MiniMax 未配置，降级使用豆包
        print(f"\n🤖 豆包 AI 分析（降级）...")
        for i in range(0, len(filtered), 8):
            batch = filtered[i:i+8]
            results = analyze_events_doubao(batch)
            if results is None:
                # 批次失败 → 逐条兜底
                print(f"  批次 {(i//8)+1} 批次API失败，跳过（程序生成reason）...")
                for item in batch:
                    today_events.append(build_event(item))
            else:
                for item in batch:
                    r = next((x for x in results if x.get('url') == item['url']), {})
                    today_events.append(build_event(item, r))
            print(f"  批次 {(i//8)+1}/{(len(filtered)+7)//8} 完成（{len(batch)}条）")
            time.sleep(0.5)
    else:
        # 两者都未配置，使用程序生成reason
        for item in filtered:
            today_events.append(build_event(item))

    # 按文章实际发布日期分组（而非脚本运行时间）
    # 同一批次抓到的文章可能有不同的发布日期
    # 全局去重：同一 URL 在整个文件里只保留一条（避免多次运行重复追加）
    existing_urls = {e['url'] for events in all_events.values() for e in events}
    pubdate_ok, pubdate_fallback = 0, 0
    for event in today_events:
        if event['url'] in existing_urls:
            continue  # 跨批次去重
        existing_urls.add(event['url'])  # 同批次内也去重
        date_key = event.pop('article_date', None)  # 取出，写入 event 的 date 字段
        event['date'] = date_key or today  # 保留 date 供 Market Pulse 使用
        if date_key:
            pubdate_ok += 1
            all_events.setdefault(date_key, []).append(event)
        else:
            pubdate_fallback += 1
            # 没有 pubDate 的文章（如 HTML 降级采集），归入运行日
            all_events.setdefault(today, []).append(event)
    # 确保今日槽位存在（即使 0 条也记录空日期，保持历史完整性）
    all_events.setdefault(today, [])

    # 输出统计
    company_added = sum(1 for e in today_events if e.get('is_company'))
    generic_added = len(today_events) - company_added
    print(f"  📅 pubDate 解析：{pubdate_ok} 条有日期 | {pubdate_fallback} 条无日期（归入今日）")
    print(f"  🏢 公司动态：{company_added} 条 | 通用热点：{generic_added} 条")

    # 清理 15 天前（避免数据无限膨胀）
    cutoff = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
    all_events = {k: v for k, v in all_events.items() if k >= cutoff}

    with open('data/events.json', 'w', encoding='utf-8') as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    # 输出每个日期的分桶统计
    for date_key in sorted(all_events.keys(), reverse=True):
        events = all_events[date_key]
        regions = {}
        company_n = 0
        for e in events:
            regions[e['region']] = regions.get(e['region'], 0) + 1
            if e.get('is_company'): company_n += 1
        print(f"  ✅ {date_key}：{len(events)} 条（公司{company_n}）| 区域：{regions}")
    total = sum(len(v) for v in all_events.values())
    company_total = sum(1 for v in all_events.values() for e in v if e.get('is_company'))
    print(f"\n  共 {total} 条历史事件（公司 {company_total} 条），跨 {len(all_events)} 天）")

if __name__ == '__main__':
    main()
