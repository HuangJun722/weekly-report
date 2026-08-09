"""一次性工具：为历史事件补齐 AI 扩写的 content_overview 字段。
只写入 content_overview，其余字段一律不动；已有 content_overview 的事件跳过。
用法:
    python scripts/backfill_content_overview.py                       # 默认补最近 7 天到今天
    python scripts/backfill_content_overview.py --days 14             # 补最近 14 天
    python scripts/backfill_content_overview.py --start 2026-08-01 --end 2026-08-09
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
os.chdir(ROOT)  # fetch_news 的 load_dotenv() 按当前工作目录找 .env

from fetch_news import analyze_events_deepseek  # noqa: E402

EVENTS_PATH = ROOT / 'data' / 'events.json'


def norm_url(u):
    return (u or '').strip().rstrip('/')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=7)
    ap.add_argument('--start', default=None)
    ap.add_argument('--end', default=date.today().isoformat())
    ap.add_argument('--batch', type=int, default=12)
    args = ap.parse_args()

    end = date.fromisoformat(args.end)
    start = date.fromisoformat(args.start) if args.start else end - timedelta(days=args.days - 1)
    days = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]

    data = json.load(open(EVENTS_PATH, encoding='utf-8'))

    targets = []
    for d in days:
        for ev in data.get(d, []):
            if not (ev.get('content_overview') or '').strip():
                targets.append(ev)
    print(f'range {start} ~ {end}, to-fill {len(targets)}', flush=True)
    if not targets:
        print('nothing to fill, exit', flush=True)
        return

    backup_dir = Path(os.environ.get('TEMP', str(ROOT))) / 'weekly-report-backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f'events.backup-{end.isoformat()}.json'
    json.dump(data, open(backup, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'backup -> {backup}', flush=True)

    by_url = {norm_url(ev.get('url')): ev for ev in targets}
    items = [{'title': ev.get('title', ''), 'url': ev.get('url', ''),
              'source': ev.get('source', ''), 'region': ev.get('region', '')} for ev in targets]

    updated = 0
    total_batches = (len(items) + args.batch - 1) // args.batch
    for i in range(0, len(items), args.batch):
        chunk = items[i:i + args.batch]
        result = analyze_events_deepseek(chunk)
        if not result:
            print(f'  [{(i // args.batch) + 1}/{total_batches}] ai fail, skip batch', flush=True)
            continue
        for r in result:
            ev = by_url.get(norm_url(r.get('url')))
            if ev is None:
                continue
            ov = (r.get('content_overview') or '').strip()
            if not ov or ov == (ev.get('summary_short') or '').strip():
                continue  # 空或与一句话摘要相同视为扩写失败
            ev['content_overview'] = ov
            updated += 1
        print(f'  [{(i // args.batch) + 1}/{total_batches}] updated {updated}', flush=True)

    json.dump(data, open(EVENTS_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'done: updated {updated} content_overview', flush=True)


if __name__ == '__main__':
    main()
