"""阶段3 Signal Score 审计验证（离线重放）

红线约束：Signal 层是"更聪明的窄门"，不得把 scope 已过滤的 70% 噪声拉高。
断言：
1. misclassification_audit 的 77 条被砍噪声 → signal_change_score 全为 0（blocked 非空）。
2. events.json 全量事件：scope_status == 'filtered' 的事件不得出现 signal_change_score > 0。
3. events.json 中 qualified 的真实信号（regional_policy / industry_change）应得正分，
   抽查若干高分信号确认分类合理。
"""
import json
import sys
from collections import Counter

sys.path.insert(0, 'scripts')
from signal_scoring import signal_change_score, apply_signal_contract

PASS = []
FAIL = []


def check(name, cond, detail):
    (PASS if cond else FAIL).append((name, detail))
    print(f"  {'OK ' if cond else 'FAIL'} {name}: {detail}")


# ── 1) 审计 77 条噪声 → 必须全 0 ──────────────────────────
audit = json.load(open('data/misclassification_audit.json', encoding='utf-8'))
samples = audit['by_reason']['scope_no_target_industry']
noise_scores = []
for s in samples:
    event = {
        'title': s.get('title', ''),
        'region': s.get('region', ''),
        'source': s.get('source', ''),
        'url': s.get('url', ''),
        'scope_status': 'filtered',
        'scope_reason': 'scope_no_target_industry',
    }
    r = signal_change_score(event)
    noise_scores.append(r['signal_change_score'])
nonzero = [n for n in noise_scores if n > 0]
check(
    '审计77条噪声 Signal 分全为0',
    len(nonzero) == 0,
    f'噪声 {len(noise_scores)} 条，得分>0 的 {len(nonzero)} 条'
)

# ── 2) events.json 全量：filtered 事件不得有正 Signal 分 ──
data = json.load(open('data/events.json', encoding='utf-8'))
rows = [e for day in data.values() for e in (day or [])]
filtered_pos = []
qualified_zero = []
signal_by_layer = Counter()
for e in rows:
    apply_signal_contract(e)  # 幂等：事件本身若已有信号字段会覆盖，无影响
    sc = e['signal_change_score']
    layer = e.get('scope_layer', '?')
    status = e.get('scope_status', '?')
    if status == 'filtered' and sc > 0:
        filtered_pos.append((e.get('title'), sc, e.get('scope_reason')))
    if status == 'qualified' and sc == 0:
        qualified_zero.append((e.get('title'), e.get('scope_reason')))
    signal_by_layer[(status, layer)] += 1

check(
    'events.json 无 filtered 事件得分>0',
    len(filtered_pos) == 0,
    f'filtered 事件得分>0 的 {len(filtered_pos)} 条'
)
for t, sc, reason in filtered_pos[:5]:
    print(f'    VIOLATION: {t[:70]} score={sc} reason={reason}')

# ── 3) qualified 信号分布 + 抽查高分 ──────────────────────
n_qualified = sum(c for (s, _), c in signal_by_layer.items() if s == 'qualified')
n_zero = len(qualified_zero)
n_positive = n_qualified - n_zero
check(
    'qualified 事件大部分得正分（真实信号）',
    n_positive > n_qualified * 0.5,
    f'qualified {n_qualified} 条，正分 {n_positive}，0分 {n_zero}'
)

# 层分布
print('  signal 层分布(前10):', dict(list(signal_by_layer.most_common(10))))

# 抽查 qualified 高分信号（去掉 review 区，只看主线）
high = sorted(
    [e for e in rows if e.get('scope_status') == 'qualified' and e['signal_change_score'] >= 55],
    key=lambda x: x['signal_change_score'], reverse=True,
)
print(f'  qualified 且 signal_change_score>=55 的信号 {len(high)} 条，抽前10:')
for e in high[:10]:
    print(f"    [{e['signal_change_score']:3d}] {e.get('signal_type','?'):10s} {e.get('scope_layer','?'):16s} | {(e.get('title') or '')[:72]}")

# ── 汇总 ─────────────────────────────────────────────────
print()
print(f'PASS {len(PASS)} | FAIL {len(FAIL)}')
if FAIL:
    for name, detail in FAIL:
        print(f'  FAIL {name}: {detail}')
    sys.exit(1)
print('审计约束全部满足：Signal 层未把噪声拉高。')
