"""
测试：GitHub Actions 能否访问 Google News RSS
"""
import requests
import json
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36',
    'Referer': 'https://www.google.com/',
}

# 测试几家有代表性的公司
TEST_URLS = [
    'https://news.google.com/rss/search?q=ByteDance',
    'https://news.google.com/rss/search?q=MercadoLibre',
    'https://news.google.com/rss/search?q=Kaspi.kz',
]

def test_google_news():
    results = {}
    for url in TEST_URLS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            results[url] = {'status': r.status_code, 'length': len(r.text)}
            print(f"✅ {url}: HTTP {r.status_code}, {len(r.text)} bytes")
        except Exception as e:
            results[url] = {'error': str(e)}
            print(f"❌ {url}: {e}")
    # 输出结果供 Actions 日志查看
    print("\n--- SUMMARY ---")
    print(json.dumps(results, indent=2))
    return results

if __name__ == '__main__':
    test_google_news()
