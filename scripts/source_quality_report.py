"""Summarize source contribution quality from stored events and latest run metrics."""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

try:
    from event_value import is_google_news_event, is_high_value_event
    from generate_html import build_display_context
    from run_metrics import latest_run_metrics
    from view_selectors import select_feed_events, select_main_list_events
except ImportError:
    from scripts.event_value import is_google_news_event, is_high_value_event
    from scripts.generate_html import build_display_context
    from scripts.run_metrics import latest_run_metrics
    from scripts.view_selectors import select_feed_events, select_main_list_events


def _event_date(event):
    return (event.get('date') or '')[:10]


def _source_name(event):
    return event.get('display_source') or event.get('source_detail') or event.get('source') or '未知来源'


def _date_range(end_date, days):
    end = datetime.strptime(end_date, '%Y-%m-%d')
    return {
        (end - timedelta(days=offset)).strftime('%Y-%m-%d')
        for offset in range(days)
    }


def _latest_run_source_stats():
    metrics = latest_run_metrics()
    result = {}
    for group in ('rss', 'html', 'company'):
        for name, stats in (metrics.get(group, {}).get('source_stats') or {}).items():
            result[name] = {
                'raw': stats.get('count', 0),
                'signals': stats.get('signal_count', 0),
                'method': stats.get('method') or group,
                'status': stats.get('status', ''),
            }
    return result


def build_source_quality_report(days=7):
    context = build_display_context()
    end_date = context['latest_data_date'] or context['main_date']
    selected_dates = _date_range(end_date, days)
    all_visible = [
        event for event in context['all_events_for_list']
        if _event_date(event) in selected_dates
    ]
    main_events = select_main_list_events(all_visible)
    feed_events, _ = select_feed_events(context['today_events'], context['all_events_for_list'])
    feed_urls = {event.get('url') for event in feed_events}

    rows = defaultdict(lambda: {
        'source': '',
        'tier': '',
        'role': '',
        'stored_visible': 0,
        'main': 0,
        'high_value': 0,
        'rss': 0,
        'google': 0,
        'company': 0,
    })

    main_urls = {event.get('url') for event in main_events}
    for event in all_visible:
        name = _source_name(event)
        row = rows[name]
        row['source'] = name
        row['tier'] = event.get('source_tier') or row['tier']
        row['role'] = event.get('source_role') or row['role']
        row['stored_visible'] += 1
        if event.get('url') in main_urls:
            row['main'] += 1
        if is_high_value_event(event):
            row['high_value'] += 1
        if event.get('url') in feed_urls:
            row['rss'] += 1
        if is_google_news_event(event):
            row['google'] += 1
        if event.get('is_company'):
            row['company'] += 1

    run_sources = _latest_run_source_stats()
    for name, stats in run_sources.items():
        row = rows[name]
        row['source'] = name
        row['raw'] = stats['raw']
        row['signals'] = stats['signals']
        row['method'] = stats['method']
        row['status'] = stats['status']

    report_rows = []
    for row in rows.values():
        row.setdefault('raw', 0)
        row.setdefault('signals', 0)
        row.setdefault('method', '')
        row.setdefault('status', '')
        raw = row.get('raw') or 0
        visible = row.get('stored_visible') or 0
        row['signal_ratio'] = (row['signals'] / raw) if raw else 0
        row['main_ratio'] = (row['main'] / visible) if visible else 0
        row['rss_ratio'] = (row['rss'] / visible) if visible else 0
        report_rows.append(row)

    report_rows.sort(
        key=lambda row: (
            row.get('rss', 0),
            row.get('high_value', 0),
            row.get('main', 0),
            row.get('stored_visible', 0),
            row.get('raw', 0),
        ),
        reverse=True,
    )
    return {
        'end_date': end_date,
        'days': days,
        'rows': report_rows,
    }


def print_report(report, limit=30):
    print(f"source quality | end_date={report['end_date']} days={report['days']}")
    print("source | raw | signals | visible | main | high | rss | google | company | tier")
    for row in report['rows'][:limit]:
        line = (
            "{source} | {raw} | {signals} | {stored_visible} | {main} | {high_value} | "
            "{rss} | {google} | {company} | {tier}".format(**row)
        )
        print(line.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--limit', type=int, default=30)
    parser.add_argument('--json-out', help='Optional path to write JSON report')
    args = parser.parse_args()

    report = build_source_quality_report(args.days)
    print_report(report, args.limit)
    if args.json_out:
        path = Path(args.json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == '__main__':
    sys.exit(main())
