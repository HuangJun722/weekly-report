"""只读误杀审计：抓取 RSS，对每条事件跑 scope 过滤，收集被砍(filted)的原文，不写任何库。"""
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8')
# 本机有 socks5 代理但 requests 缺 socks 依赖，诊断需直连（与 GitHub Actions 环境一致）
for _v in ('all_proxy', 'ALL_PROXY', 'http_proxy', 'HTTP_PROXY', 'https_proxy', 'HTTPS_PROXY'):
    os.environ.pop(_v, None)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 引入采集模块（保持和 fetch_news.py 一致的 import 路径）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_news
from fetch_news import RSS_SOURCES, _parse_rss_text, apply_scope_contract, _is_vertical_source

def main():
    print("=" * 70)
    print("误杀审计：只读诊断，不写任何库")
    print("=" * 70)
    all_filtered = []      # 被 scope 砍掉的事件
    all_qualified = []     # 过闸事件（对照用）
    per_source = {}

    for cfg in RSS_SOURCES:
        name = cfg.get('name', '?')
        try:
            text = fetch_news.fetch_url(cfg['url'], retries=1)
        except Exception as e:
            print(f"  ✗ {name}: 抓取失败 {type(e).__name__}")
            continue
        if not text:
            print(f"  ✗ {name}: 空内容")
            continue
        # 复刻 _parse_rss_text 的循环，但保留被砍事件
        results = _parse_rss_text(cfg, text)  # 这条会丢 filtered，仅用于拿过闸的
        # 重新完整解析一遍，收集被砍事件
        import feedparser
        from bs4 import BeautifulSoup
        from fetch_news import (
            detect_event_types, _select_rss_entry_link, _rss_date_metadata,
            _recent_article_date, _with_source_meta, is_blacklisted,
        )
        parsed = feedparser.parse(text.strip())
        scope_managed = _is_vertical_source(cfg) or cfg.get('source_role') == 'deep_trend'
        src_filtered, src_qualified = [], []
        max_scan = cfg.get('max_scan', cfg.get('max', 8))
        scanned = 0
        for entry in parsed.entries:
            if scanned >= max_scan:
                break
            scanned += 1
            title = (entry.get('title') or '').strip()
            if len(title) < 15 or is_blacklisted(title):
                continue
            link, link_repair = _select_rss_entry_link(entry, title)
            if not link:
                continue
            date_meta = _rss_date_metadata(entry, link)
            article_date = date_meta['published_at'] or None
            if article_date and not _recent_article_date(article_date, days=2):
                continue
            types = detect_event_types(title)
            summary_html = entry.get('summary') or entry.get('description') or ''
            source_excerpt = BeautifulSoup(summary_html, 'html.parser').get_text(' ', strip=True)[:600]
            item = _with_source_meta({
                'title': title, 'url': link,
                'source': cfg.get('source', cfg.get('name', 'Google News')),
                'region': cfg['region'], 'priority': cfg.get('priority', 1),
                'event_types': types, 'article_date': article_date,
                'is_company': cfg.get('is_company', False),
                'company_name': cfg.get('company_name', ''),
                'source_excerpt': source_excerpt,
                **link_repair, **date_meta,
            }, cfg)
            apply_scope_contract(item)
            status = item.get('scope_status')
            if status == 'qualified':
                src_qualified.append(item)
            elif status == 'candidate':
                src_qualified.append(item)  # candidate 也当"过闸"（未进库但未丢弃）
            else:
                src_filtered.append(item)
        per_source[name] = {
            'raw_scan': scanned,
            'qualified': len(src_qualified),
            'filtered': len(src_filtered),
        }
        all_filtered.extend(src_filtered)
        all_qualified.extend(src_qualified)
        print(f"  {name:28s} 扫描{scanned:3d} | 过闸{len(src_qualified):3d} | 被砍{len(src_filtered):3d}")

    print()
    print("=" * 70)
    print(f"总计：扫描 RSS {len(RSS_SOURCES)} 源 | 被砍 {len(all_filtered)} 条")
    print("=" * 70)

    # 按原因分组
    reasons = {}
    for item in all_filtered:
        r = item.get('scope_reason') or 'unknown'
        reasons.setdefault(r, []).append(item)
    for r, items in sorted(reasons.items(), key=lambda x: -len(x[1])):
        print(f"\n### {r} ({len(items)} 条) ###")
        for it in items[:25]:
            title = it.get('title', '')[:70]
            src = it.get('source', '')
            reg = it.get('region', '')
            print(f"  [{reg}] {title} | {src}")

    # 输出到文件（方便发给参谋）
    out = {
        'generated_at': time.strftime('%Y-%m-%d %H:%M'),
        'per_source': per_source,
        'filtered_count': len(all_filtered),
        'qualified_count': len(all_qualified),
        'by_reason': {
            r: [{'title': it.get('title',''), 'source': it.get('source',''), 'region': it.get('region',''), 'url': it.get('url','')} for it in items]
            for r, items in reasons.items()
        },
    }
    outfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'misclassification_audit.json')
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n明细已存到: {outfile}")

if __name__ == '__main__':
    main()
