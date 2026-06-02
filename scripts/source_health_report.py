"""Report source lifecycle health from registry, run metrics, and stored events.

The goal is source governance, not another event ranking table:
- stable: proven useful recently or over the stored-event window
- partial: some evidence of working, but not yet stable
- zero-hit: no recent raw items and no stored contribution
- failed: recent collection reports failures
"""

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def _safe_print(text):
    print(text.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8'))


def _load_json(path, git_ref=None):
    if git_ref:
        raw = subprocess.check_output(['git', 'show', f'{git_ref}:{path}'])
        return json.loads(raw.decode('utf-8'))
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _flatten_events(data):
    if isinstance(data, list):
        return data
    events = []
    for date, items in (data or {}).items():
        for event in items or []:
            if not event.get('date'):
                event = dict(event)
                event['date'] = date
            events.append(event)
    return events


def _event_date(event):
    return (event.get('date') or '')[:10]


def _parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d')
    except (TypeError, ValueError):
        return None


def _period_dates(end_date, days):
    end = _parse_date(end_date)
    if not end:
        return set()
    return {
        (end - timedelta(days=offset)).strftime('%Y-%m-%d')
        for offset in range(days)
    }


def _source_names(event, aliases=None):
    aliases = aliases or {}
    source_id = event.get('source_id')
    if source_id and source_id in aliases:
        return [aliases[source_id]]
    source = event.get('source')
    if source and source in aliases:
        return [aliases[source]]
    if _is_google(event):
        return ['Google News']
    names = []
    for key in ('source_id', 'source', 'display_source', 'source_detail'):
        value = event.get(key)
        value = aliases.get(value, value)
        if value and value not in names:
            names.append(value)
    return names or ['未知来源']


def _event_score(event):
    try:
        return float(event.get('score') or 0)
    except (TypeError, ValueError):
        return 0


def _is_high_value(event):
    return event.get('bd_priority') == '高' or _event_score(event) >= 7


def _is_google(event):
    source = (event.get('source') or '').lower()
    url = (event.get('url') or '').lower()
    tier = event.get('source_tier') or ''
    return source == 'google news' or 'news.google.com' in url or tier == 'L5 Google News 补漏源'


def _event_type(event):
    types = event.get('event_types') or ['other']
    return types[0] if types else 'other'


def _source_stats_from_runs(metrics):
    rows = defaultdict(lambda: {
        'raw': 0,
        'signals': 0,
        'runs': 0,
        'nonzero_runs': 0,
        'methods': Counter(),
        'statuses': Counter(),
        'dates': set(),
    })
    records = metrics if isinstance(metrics, list) else ([metrics] if metrics else [])
    for run in records:
        run_date = (run.get('date') or run.get('started_at') or '')[:10]
        for group in ('rss', 'html', 'company'):
            for name, stats in ((run.get(group) or {}).get('source_stats') or {}).items():
                row = rows[name]
                count = stats.get('count') or 0
                signals = stats.get('signal_count') or 0
                row['raw'] += count
                row['signals'] += signals
                row['runs'] += 1
                if count:
                    row['nonzero_runs'] += 1
                row['methods'][stats.get('method') or group] += 1
                row['statuses'][stats.get('status') or 'unknown'] += 1
                if run_date:
                    row['dates'].add(run_date)
    return rows, records


def _source_stats_from_events(events, selected_dates, aliases=None):
    rows = defaultdict(lambda: {
        'stored': 0,
        'high': 0,
        'google': 0,
        'company': 0,
        'dates': set(),
        'types': Counter(),
        'tiers': Counter(),
    })
    for event in events:
        date = _event_date(event)
        if date not in selected_dates:
            continue
        for name in _source_names(event, aliases):
            row = rows[name]
            row['stored'] += 1
            if _is_high_value(event):
                row['high'] += 1
            if _is_google(event):
                row['google'] += 1
            if event.get('is_company'):
                row['company'] += 1
            if date:
                row['dates'].add(date)
            row['types'][_event_type(event)] += 1
            if event.get('source_tier'):
                row['tiers'][event['source_tier']] += 1
    return rows


def _registry_rows(registry):
    rows = []
    for source in registry.get('sources') or []:
        rows.append({
            'name': source.get('name') or source.get('id') or '',
            'id': source.get('id') or '',
            'status': source.get('status') or '',
            'tier': source.get('tier') or '',
            'source_type': source.get('source_type') or '',
            'access_method': source.get('access_method') or '',
            'region': source.get('region') or '',
            'track': source.get('track') or '',
            'signal_density': source.get('signal_density') or '',
            'noise_level': source.get('noise_level') or '',
        })
    return rows


def _registry_aliases(registry_sources):
    aliases = {}
    for source in registry_sources:
        name = source.get('name') or source.get('id') or ''
        if not name:
            continue
        aliases[name] = name
        if source.get('id'):
            aliases[source['id']] = name
    return aliases


def _counter_keys(counter):
    return ','.join(name for name, _ in counter.most_common()) if counter else ''


def _zero_reason(statuses):
    if statuses.get('failed'):
        return 'zero and broken'
    if statuses.get('empty') or statuses.get('ok'):
        return 'zero but healthy'
    return 'unknown'


def _lifecycle(row):
    raw = row['recent_raw']
    signals = row['recent_signals']
    stored = row['stored']
    high = row['high']
    runs = row['recent_runs']
    nonzero = row['recent_nonzero_runs']
    statuses = row['recent_statuses']

    if raw == 0 and stored == 0 and statuses.get('failed'):
        return 'failed'
    if raw == 0 and stored == 0:
        return 'zero-hit'
    if (runs and nonzero >= max(2, runs // 2) and signals > 0) or high >= 5 or stored >= 20:
        return 'stable'
    return 'partial'


def _action(row):
    lifecycle = row['lifecycle']
    zero_reason = row['zero_reason']
    tier = row['tier']
    source_type = row['source_type']
    if row['source'] == 'Google News' or row['google']:
        return '保留补漏/继续降权'
    if lifecycle == 'stable':
        return '保留/调权'
    if lifecycle == 'partial':
        return '观察/小修'
    if lifecycle == 'failed':
        return '优先修复' if tier in {'L1', 'L4'} or source_type in {'changelog', 'newsroom'} else '降级观察'
    if lifecycle == 'zero-hit':
        if zero_reason == 'zero and broken':
            return '修复抓取'
        if tier == 'L1' or source_type in {'changelog', 'newsroom'}:
            return '低频观察'
        return '降级/暂停'
    return '人工判断'


def build_source_health_report(days=30, git_ref=None):
    events_data = _load_json('data/events.json', git_ref)
    metrics = _load_json('data/run_metrics.json', git_ref)
    registry = _load_json('data/source_registry.json', git_ref)

    events = _flatten_events(events_data)
    dates = sorted({_event_date(event) for event in events if _event_date(event)})
    end_date = dates[-1] if dates else ''
    selected_dates = _period_dates(end_date, days)
    metric_rows, runs = _source_stats_from_runs(metrics)
    registry_sources = _registry_rows(registry)
    aliases = _registry_aliases(registry_sources)
    event_rows = _source_stats_from_events(events, selected_dates, aliases)

    all_names = set(event_rows) | set(metric_rows) | {source['name'] for source in registry_sources if source['name']}
    registry_by_name = {source['name']: source for source in registry_sources}
    rows = []
    for name in sorted(all_names):
        canonical_name = aliases.get(name, name)
        reg = registry_by_name.get(canonical_name, {})
        events_row = event_rows.get(name, {})
        metrics_row = metric_rows.get(name, {})
        statuses = metrics_row.get('statuses', Counter())
        row = {
            'source': canonical_name,
            'registry_status': reg.get('status', ''),
            'tier': reg.get('tier', '') or _counter_keys(events_row.get('tiers', Counter())).split(',')[0],
            'source_type': reg.get('source_type', ''),
            'access_method': reg.get('access_method', '') or _counter_keys(metrics_row.get('methods', Counter())),
            'region': reg.get('region', ''),
            'track': reg.get('track', ''),
            'recent_raw': metrics_row.get('raw', 0),
            'recent_signals': metrics_row.get('signals', 0),
            'recent_runs': metrics_row.get('runs', 0),
            'recent_nonzero_runs': metrics_row.get('nonzero_runs', 0),
            'recent_statuses': statuses,
            'stored': events_row.get('stored', 0),
            'high': events_row.get('high', 0),
            'google': events_row.get('google', 0),
            'company': events_row.get('company', 0),
            'stored_days': len(events_row.get('dates', set())),
            'top_type': events_row.get('types', Counter()).most_common(1)[0][0] if events_row.get('types') else '',
        }
        row['zero_reason'] = _zero_reason(statuses) if row['recent_raw'] == 0 and row['stored'] == 0 else ''
        row['lifecycle'] = _lifecycle(row)
        row['action'] = _action(row)
        rows.append(row)

    lifecycle_counts = Counter(row['lifecycle'] for row in rows)
    action_counts = Counter(row['action'] for row in rows)
    rows.sort(
        key=lambda row: (
            {'stable': 4, 'partial': 3, 'failed': 2, 'zero-hit': 1}.get(row['lifecycle'], 0),
            row['high'],
            row['stored'],
            row['recent_signals'],
            row['recent_raw'],
        ),
        reverse=True,
    )
    return {
        'end_date': end_date,
        'days': days,
        'git_ref': git_ref or '',
        'run_count': len(runs),
        'run_dates': sorted({(run.get('date') or '') for run in runs if run.get('date')}),
        'lifecycle_counts': dict(lifecycle_counts),
        'action_counts': dict(action_counts),
        'rows': rows,
    }


def _format_statuses(statuses):
    if not statuses:
        return ''
    return ','.join(f'{name}:{count}' for name, count in statuses.most_common())


def print_report(report, limit=80):
    _safe_print(
        f"source health | ref={report['git_ref'] or 'working-tree'} "
        f"end_date={report['end_date']} days={report['days']} runs={report['run_count']} "
        f"run_dates={','.join(report['run_dates'])}"
    )
    _safe_print(f"lifecycle | {json.dumps(report['lifecycle_counts'], ensure_ascii=False)}")
    _safe_print(f"actions | {json.dumps(report['action_counts'], ensure_ascii=False)}")
    _safe_print("source | lifecycle | action | recent_raw | recent_signals | stored | high | zero_reason | status | tier | type | method")
    for row in report['rows'][:limit]:
        line = (
            f"{row['source']} | {row['lifecycle']} | {row['action']} | "
            f"{row['recent_raw']} | {row['recent_signals']} | {row['stored']} | {row['high']} | "
            f"{row['zero_reason']} | {_format_statuses(row['recent_statuses'])} | "
            f"{row['tier']} | {row['source_type']} | {row['access_method']}"
        )
        _safe_print(line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=30)
    parser.add_argument('--git-ref', help='Read data files from a git ref, e.g. origin/main')
    parser.add_argument('--limit', type=int, default=80)
    parser.add_argument('--json-out', help='Optional path to write JSON report')
    args = parser.parse_args()

    report = build_source_health_report(days=args.days, git_ref=args.git_ref)
    print_report(report, args.limit)
    if args.json_out:
        path = Path(args.json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        serializable = dict(report)
        serializable['rows'] = [
            {**row, 'recent_statuses': dict(row['recent_statuses'])}
            for row in report['rows']
        ]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == '__main__':
    sys.exit(main())
