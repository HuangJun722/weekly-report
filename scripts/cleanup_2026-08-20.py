# -*- coding: utf-8 -*-
"""一次性存量清理（2026-08-20 止血方案）：
1. 检出并删除越界事件（泛零售 Retail Dive/Modern Retail 报道 + 非数字产业内容）
2. 合并同事件重复（Navi / Kakao Mobility / Kanana-2），被合并源记入 merged_from
匹配一律用标题关键词 + 来源，逐条打印被处理条目，写回 data/events.json。
"""
import json

with open('data/events.json', encoding='utf-8') as f:
    data = json.load(f)

# ── 删除规则：标题关键词（小写）+ 来源限定 ─────────────────────────
wearhouse_noise_keywords = ['under armour', 'the rock']
retail_dive_keywords = {
    'home depot', 'ulta', 'nike', 'foot locker', "lowe", "lowes",
    'ted by ted baker', "macys", "macy", 'target', 'back-to-school',
    'anthropologie', 'chobani', 'fabletics', 'h&m', 'h&m', 'partnership strategies',
}
other_noise_keywords = {
    'msci', 'thanh thanh cong', 'dubai international airport',
    'wrangler', 'gojek clone', 'korea labor foundation', 'catalog house',
}
RETAIL_ONLY_SOURCES = {'Retail Dive', 'Modern Retail'}


def is_noise(e):
    src = (e.get('source') or '')
    t = (e.get('title') or '').lower()
    if src in RETAIL_ONLY_SOURCES:
        return any(k in t for k in retail_dive_keywords)
    return any(k in t for k in other_noise_keywords)


# ── 合并规则 ────────────────────────────────────────────────
def find(day, key, val):
    for e in data.get(day, []):
        if (e.get(key) or '').lower().find(val.lower()) >= 0:
            return e
    return None


removed = []
merged_log = []


def merge_into(keep, drop, why):
    if not keep or not drop:
        return False
    keep.setdefault('merged_from', [])
    if drop['url'] not in keep['merged_from']:
        keep['merged_from'].append(drop['url'])
    # 删掉被并入条（同 day 用 remove）
    for day in list(data.keys()):
        if not isinstance(data.get(day), list):
            continue
        if drop in data[day]:
            data[day].remove(drop)
    merged_log.append((why, keep.get('title'), drop.get('url')))
    return True


# Kanana-2（08-18）：保留 Koreabizwire 条（title 指 Kanana-2 Tops）
kanana_keep = next((e for e in data.get('2026-08-18', []) if (e.get('title') or '').lower().find('kanana-2 tops') >= 0), None)
kanana_drop = next((e for e in data.get('2026-08-18', []) if (e is not kanana_keep and 'kanana' in (e.get('title') or '').lower())), None)
merge_into(kanana_keep, kanana_drop, 'kanana-2')

# Kakao Mobility（08-19 biggo 保留 ← 조선일보；08-20 Yonhap ← 并入 08-19）
kakao19_keep = next((e for e in data.get('2026-08-19', []) if (e.get('title') or '').lower().find('confidential ipo registration') >= 0), None)
kakao19_drop = next((e for e in data.get('2026-08-19', []) if (e is not kakao19_keep and 'kakao mobility' in (e.get('title') or '').lower())), None)
merge_into(kakao19_keep, kakao19_drop, 'kakao-mobility-08-19')
kakao20 = next((e for e in data.get('2026-08-20', []) if 'kakao mobility' in (e.get('title') or '').lower()), None)
merge_into(kakao19_keep, kakao20, 'kakao-mobility-08-20')

# Navi（08-19 TechCrunch 保留 ← Inc42；08-20 DSA ← 并入 08-19）
navi_keep = next((e for e in data.get('2026-08-19', []) if 'techcrunch' in (e.get('url') or '') and 'navi' in (e.get('title') or '').lower()), None)
navi_inc42 = next((e for e in data.get('2026-08-19', []) if (e is not navi_keep and 'inc42' in (e.get('url') or '') and 'navi' in (e.get('title') or '').lower())), None)
merge_into(navi_keep, navi_inc42, 'navi-08-19')
navi_dsa = next((e for e in data.get('2026-08-20', []) if 'dealstreetasia' in (e.get('url') or '')), None)
merge_into(navi_keep, navi_dsa, 'navi-08-20')

# ── 执行删除 ───────────────────────────────────────────────
for day in list(data.keys()):
    if not isinstance(data.get(day), list):
        continue
    kept = []
    for e in data[day]:
        if is_noise(e):
            removed.append((day, e.get('source') or '', (e.get('title') or '')[:70]))
            continue
        kept.append(e)
    data[day] = kept

with open('data/events.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

print(f'删除 {len(removed)} 条：')
for r in removed:
    print('  -', r)
print(f'合并 {len(merged_log)} 组：')
for why, title, url in merged_log:
    print(f'  - [{why}] {title} | 并入 {url[:60]}...')