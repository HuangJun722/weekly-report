#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线权重校准：用真实历史事件对比当前与备选权重配置。

只读诊断，不写任何库。思路：signal_change_score 的 breakdown 已给出
change_explicit/action_type_weight/scope_fit/market_impact 分量，备选配置只换
action_type_weight，其余分量保持不变，即可在同一事件集上对比两种权重的总分
分布与排序差异。

用法:
    /c/Users/16120/AppData/Local/Python/bin/python scripts/calibrate_weights.py
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 仓库根目录
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))  # scripts

from signal_scoring import apply_signal_contract, signal_change_score
from collections import Counter, defaultdict
import statistics

# 备选配置：只调 action_type_weight（主差异轴）。earnings 是财报/经营拐点独立档。
CONFIGS = {
    'current': {
        'policy_change': 25, 'product_release': 22, 'funding': 22,
        'earnings': 20, 'expansion': 18, 'hiring': 12, 'other': 15,
    },
    # 财报不该与融资同权：财报是"经营拐点"但非资本最强信号，降档
    'alt_a': {
        'policy_change': 25, 'product_release': 24, 'funding': 22,
        'earnings': 18, 'expansion': 18, 'hiring': 12, 'other': 15,
    },
    # 产品/扩张拉高（机会发现导向），财报进一步降
    'alt_b': {
        'policy_change': 22, 'product_release': 25, 'funding': 22,
        'earnings': 16, 'expansion': 20, 'hiring': 14, 'other': 15,
    },
}


def load_flat_events(limit=3000):
    raw = json.load(open('data/events.json', encoding='utf-8'))
    flat = []
    for k, v in raw.items():
        flat.extend(v if isinstance(v, list) else [])
    return flat[:limit]


def collect(events):
    """用当前权重跑一遍，收集每条的 breakdown 与元信息。"""
    rows = []
    for e in events:
        c = apply_signal_contract(e)
        r = signal_change_score(c)
        sc = r.get('signal_change_score', 0)
        if sc <= 0:
            continue
        bd = r.get('signal_change_breakdown') or {}
        rows.append({
            'action_type': r.get('action_type') or 'other',
            'change_explicit': bd.get('change_explicit', 0),
            'atw': bd.get('action_type_weight', 0),
            'scope_fit': bd.get('scope_fit', 0),
            'market_impact': bd.get('market_impact', 0),
            'current_total': sc,
            'title': (c.get('display_title') or c.get('title') or '')[:35],
            'region': c.get('region') or '未知',
            'date': (c.get('date') or '')[:10],
        })
    return rows


def rescore(rows, weights):
    out = []
    for r in rows:
        atw = weights.get(r['action_type'], 15)
        total = min(100, r['change_explicit'] + atw + r['scope_fit'] + r['market_impact'])
        out.append((total, r))
    out.sort(key=lambda x: x[0], reverse=True)
    return out


def report(name, ranked, rows):
    vals = [s for s, _ in ranked]
    at = Counter(r['action_type'] for _, r in ranked[:20])
    print(f'  {name}: 有效 {len(vals)} | 平均 {round(statistics.mean(vals),1)} | 中位 {statistics.median(vals)}')
    dist = {
        '0-40': sum(1 for v in vals if v <= 40),
        '41-60': sum(1 for v in vals if 40 < v <= 60),
        '61-80': sum(1 for v in vals if 60 < v <= 80),
        '81+': sum(1 for v in vals if v > 80),
    }
    print(f'    分布: {dist}')
    print(f'    Top20 类型: {dict(at.most_common())}')
    top10 = [(s, r['action_type'], r['region'], r['title']) for s, r in ranked[:10]]
    print('    Top10:')
    for s, at_t, rg, t in top10:
        print(f'      {s:>3} [{at_t:<14}] {rg:<4} {t}')


def main():
    events = load_flat_events()
    print(f'加载事件: {len(events)} 条')
    rows = collect(events)
    print(f'有效分事件: {len(rows)} 条')
    print('== 各配置对比（同一事件集，仅换 action_type_weight） ==\n')
    current_ranked = rescore(rows, CONFIGS['current'])
    report('current', current_ranked, rows)
    print()
    # 对比重排：各配置 Top10 是否不同、分布是否更分散
    for name in ('alt_a', 'alt_b'):
        ranked = rescore(rows, CONFIGS[name])
        report(name, ranked, rows)
        # 与 current 的重合度
        cur_top = {r['title'] for _, r in current_ranked[:15]}
        alt_top = {r['title'] for _, r in ranked[:15]}
        overlap = len(cur_top & alt_top)
        print(f'    Top15 与 current 重合: {overlap}/15')
        print()


if __name__ == '__main__':
    main()
