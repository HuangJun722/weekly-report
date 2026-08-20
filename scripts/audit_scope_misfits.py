"""只读审计：扫描放行但可能与数字产业无关的事件（scope 越界漏网）。

思路：登记纪律为主、事后审计为辅——泛行业源（如 Retail Dive）若混入
L4 背书，其"合约放行但本质不属数字产业"的事件会在这里被扫出来。
词表不做展示层强过滤（实测 is_mainline_internet_event 误杀 24%、
score=0 剔除会杀掉产品精选的国防 AI 合作），漏网靠此审计人工处置。

用法：python scripts/audit_scope_misfits.py [days=7]
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from internet_relevance import assess_internet_relevance

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 7


def main():
    with open('data/events.json', encoding='utf-8') as f:
        data = json.load(f)

    suspicious = []
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=DAYS)).strftime('%Y-%m-%d')
    for date, events in data.items():
        if not isinstance(events, list):
            continue
        if date < cutoff:
            continue
        for e in events:
            if e.get('scope_status') != 'qualified':
                continue
            rel = assess_internet_relevance(e)
            if rel['score'] >= 2:
                continue
            suspicious.append((date, e.get('source') or '', rel['score'],
                               (e.get('title') or '')[:70], rel['reason']))

    print(f'扫描 {DAYS} 天：scope 放行但互联网相关性 <2 的事件 {len(suspicious)} 条')
    for date, source, score, title, reason in suspicious:
        print(f'{date} | {source} | score={score} | {title} | {reason}')


if __name__ == '__main__':
    main()