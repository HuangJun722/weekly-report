#!/usr/bin/env python3
"""Test Google News RSS accessibility from GitHub Actions"""
import requests, sys, re

companies = [
    'ByteDance', 'TikTok', 'Tencent', 'Alibaba', 'JD.com', 'Kuaishou', 'Ant Group',
    'Meituan', 'Kakao', 'Naver', 'Rakuten', 'Sea Limited', 'Grab', 'Gojek',
    'VNG Group', 'Yahoo', 'Cyberagent', 'Adyen', 'Zalando', 'Allegro', 'Trendyol',
    'MercadoLibre', 'Rappi', 'Noon', 'Careem', 'Tabby', 'Kaspi.kz', 'Jumia', 'Konga',
]
ok, fail = 0, []
for name in companies:
    url = 'https://news.google.com/rss/search?q=' + requests.utils.quote(name) + '&hl=en-US&gl=US&ceid=US:en'
    try:
        r2 = requests.get(url, timeout=15)
        if r2.status_code == 200 and '<rss' in r2.text:
            items = re.findall(r'<title>(.*?)</title>', r2.text)
            print('OK  ' + name.ljust(15) + ' | ' + str(len(items)-1) + ' titles')
            ok += 1
        else:
            print('FAIL ' + name + ' | HTTP ' + str(r2.status_code))
            fail.append(name)
    except Exception as e:
        print('FAIL ' + name + ' | ' + type(e).__name__)
        fail.append(name)

print('Result: ' + str(ok) + '/' + str(len(companies)) + ' accessible from GitHub Actions')
if fail:
    print('Failed: ' + str(fail))
    sys.exit(1)
