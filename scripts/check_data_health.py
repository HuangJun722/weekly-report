"""Check dashboard data health after events have been stored.

It verifies the collection metrics -> stored-data -> selector -> display contract.
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta

try:
    from collection_timing_report import build_collection_timing_rows, print_collection_timing_report
    from daily_coverage_report import build_daily_coverage_report
    from event_dates import is_display_date
    from generate_html import build_company_cards, build_display_context
    from run_metrics import latest_run_metrics
    from source_conversion_report import build_source_conversion_report
    from source_quality_report import build_source_quality_report
    from view_selectors import select_feed_events, select_main_list_events, select_review_events
except ImportError:
    from scripts.collection_timing_report import build_collection_timing_rows, print_collection_timing_report
    from scripts.daily_coverage_report import build_daily_coverage_report
    from scripts.event_dates import is_display_date
    from scripts.generate_html import build_company_cards, build_display_context
    from scripts.run_metrics import latest_run_metrics
    from scripts.source_conversion_report import build_source_conversion_report
    from scripts.source_quality_report import build_source_quality_report
    from scripts.view_selectors import select_feed_events, select_main_list_events, select_review_events


def _event_date(event):
    return (event.get('date') or '')[:10]


def _norm_title(event):
    title = (
        event.get('display_title')
        or event.get('summary_short')
        or event.get('title')
        or ''
    ).lower()
    return re.sub(r'[^\w]+', '', title)


def _date_range(end_date, days):
    end = datetime.strptime(end_date, '%Y-%m-%d')
    return [
        (end - timedelta(days=offset)).strftime('%Y-%m-%d')
        for offset in range(days)
    ]


def _source_is_google(event):
    source = (event.get('source') or '').lower()
    tier = event.get('source_tier') or ''
    url = (event.get('url') or '').lower()
    return source == 'google news' or tier == 'L5 Google News 补漏源' or 'news.google.com' in url


def _duplicate_ratio(events):
    keys = [
        _norm_title(event)
        for event in events
        if len(_norm_title(event)) > 10
    ]
    if not keys:
        return 0.0, 0
    counts = Counter(keys)
    duplicate_items = sum(count - 1 for count in counts.values() if count > 1)
    return duplicate_items / len(keys), duplicate_items


def _future_event_count(path='data/events.json', now=None):
    try:
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return 0
    count = 0
    for bucket, events in (data or {}).items():
        for event in events or []:
            value = event.get('published_at') or event.get('article_date') or event.get('date') or bucket
            if value and not is_display_date(value, now=now or datetime.now().astimezone()):
                count += 1
    return count


def build_health_report(days=7):
    context = build_display_context()
    main_date = context['main_date']
    all_visible = context['all_events_for_list']
    today_events = context['today_events']
    raw_today = context['raw_today_events']

    feed_events, fallback_feed_date = select_feed_events(today_events, all_visible)
    company_cards = build_company_cards(
        context['preset_company_list'],
        main_date,
        context.get('entity_observation_ledger'),
    )
    company_quality_nonzero = sum(1 for card in company_cards if card.get('quality_30', 0) > 0)

    dates = _date_range(context['latest_data_date'] or main_date, days)
    daily = []
    recent_events = []
    for date_key in dates:
        raw_day = [event for event in all_visible if _event_date(event) == date_key]
        main_day = select_main_list_events(raw_day)
        review_day = select_review_events(raw_day, limit=None)
        recent_events.extend(raw_day)
        daily.append({
            'date': date_key,
            'visible': len(raw_day),
            'main': len(main_day),
            'review': len(review_day),
            'google': sum(1 for event in raw_day if _source_is_google(event)),
        })

    duplicate_ratio, duplicate_items = _duplicate_ratio(recent_events)
    feed_google = sum(1 for event in feed_events if _source_is_google(event))
    feed_google_ratio = feed_google / len(feed_events) if feed_events else 0.0
    run_metrics = latest_run_metrics()
    collection_timing = build_collection_timing_rows(limit=8)
    source_report = build_source_quality_report(days=days)
    source_conversion = build_source_conversion_report(days=days)
    daily_coverage = build_daily_coverage_report(days=days)
    future_event_count = _future_event_count()

    return {
        'main_date': main_date,
        'latest_data_date': context['latest_data_date'],
        'run_metrics': run_metrics,
        'collection_timing': collection_timing,
        'today_events': len(today_events),
        'raw_today_events': len(raw_today),
        'all_visible_events': len(all_visible),
        'company_quality_nonzero': company_quality_nonzero,
        'feed_entries': len(feed_events),
        'feed_google': feed_google,
        'feed_google_ratio': feed_google_ratio,
        'feed_fallback_date': fallback_feed_date,
        'duplicate_ratio': duplicate_ratio,
        'duplicate_items': duplicate_items,
        'daily': daily,
        'source_quality': source_report,
        'source_conversion': source_conversion,
        'daily_coverage': daily_coverage,
        'future_event_count': future_event_count,
    }


def print_report(report):
    metrics = report.get('run_metrics') or {}
    collection = metrics.get('collection') or {}
    filtering = metrics.get('filtering') or {}
    scoring = metrics.get('scoring') or {}
    storage = metrics.get('storage') or {}
    if metrics:
        print(
            "run | date={date} env={environment} raw={raw} unique={unique} "
            "smart_filtered={smart_filtered} ai_filtered={ai_filtered} "
            "ai_tier={ai_tier} program_tier={program_tier} dropped={dropped} "
            "added={added} duplicate_skipped={duplicate_skipped}".format(
                date=metrics.get('date', ''),
                environment=metrics.get('environment', ''),
                raw=collection.get('raw_count', 0),
                unique=collection.get('unique_count', 0),
                smart_filtered=filtering.get('smart_filtered_count', 0),
                ai_filtered=filtering.get('ai_filtered_count', 0),
                ai_tier=scoring.get('ai_tier_count', 0),
                program_tier=scoring.get('program_tier_count', 0),
                dropped=scoring.get('dropped_count', 0),
                added=storage.get('added_count', 0),
                duplicate_skipped=storage.get('duplicate_skipped', 0),
            )
        )
    else:
        print("run | no run_metrics.json found")
    print(
        "health | main_date={main_date} latest_data_date={latest_data_date} "
        "today={today_events} raw_today={raw_today_events} visible={all_visible_events}".format(**report)
    )
    print(
        "health | company_quality_nonzero={company_quality_nonzero} "
        "feed_entries={feed_entries} feed_google={feed_google} "
        "feed_google_ratio={feed_google_ratio:.1%} duplicate_ratio={duplicate_ratio:.1%} "
        "duplicate_items={duplicate_items}".format(**report)
    )
    print(f"health | future_event_count={report.get('future_event_count', 0)}")
    if report['feed_fallback_date']:
        print(f"health | feed_fallback_date={report['feed_fallback_date']}")
    if report.get('collection_timing'):
        print_collection_timing_report(report['collection_timing'])
    print("date | visible | main | review | google")
    for row in report['daily']:
        print(
            "{date} | {visible} | {main} | {review} | {google}".format(**row)
        )
    source_rows = (report.get('source_quality') or {}).get('rows') or []
    if source_rows:
        print("top sources | source | visible | main | high | rss | google")
        for row in source_rows[:8]:
            print(
                "{source} | {stored_visible} | {main} | {high_value} | {rss} | {google}".format(**row)
                .encode(sys.stdout.encoding or 'utf-8', errors='replace')
                .decode(sys.stdout.encoding or 'utf-8')
            )
    conversion = report.get('source_conversion') or {}
    conversion_totals = conversion.get('totals') or {}
    if conversion_totals:
        print(
            "source conversion | raw={raw} signal={signal} stored={stored} main={main} "
            "review={review} out_of_scope_industry={out_of_scope_industry} "
            "capital_only_low_actionability={capital_only_low_actionability} "
            "quality_review={quality_review} "
            "lost_after_signal≈{lost_after_signal}".format(**conversion_totals)
        )
    high_signal_low_main = (conversion.get('high_signal_low_main') or [])[:5]
    if high_signal_low_main:
        print("source conversion watch | source | signal | stored | main | lost_after_signal≈")
        for row in high_signal_low_main:
            print(
                "{source} | {signal} | {stored} | {main} | {lost_after_signal}".format(**row)
                .encode(sys.stdout.encoding or 'utf-8', errors='replace')
                .decode(sys.stdout.encoding or 'utf-8')
            )
    governance_actions = conversion.get('governance_actions') or {}
    if governance_actions:
        print("source governance actions | action | source | signal | stored | main")
        for action in (
            'audit_raw_signal_quality',
            'instrument_candidate_loss',
            'audit_conversion_loss',
            'downgrade_or_reclassify',
            'promote_weight',
        ):
            for row in governance_actions.get(action, [])[:3]:
                print(
                    f"{action} | {row['source']} | {row['signal']} | "
                    f"{row['stored']} | {row['main']}"
                )
    coverage = report.get('daily_coverage') or {}
    coverage_totals = coverage.get('totals') or {}
    if coverage_totals:
        print(
            "daily coverage | stored={stored_events} main={main_events} review={review_events} "
            "status={status_counts} actions={action_counts}".format(**coverage_totals)
        )
        print("daily coverage rows | date | stored | main | entities | regions | tracks | google | company | status | action")
        for row in (coverage.get('rows') or [])[:8]:
            print(
                "{date} | {stored_events} | {main_events} | {entities} | {regions} | "
                "{tracks} | {google_events} | {company_events} | {status} | {action}".format(**row)
            )


def collect_failures(report, args):
    failures = []
    if report.get('future_event_count', 0):
        failures.append(f"future_event_count {report['future_event_count']} > 0")
    if report['today_events'] < args.min_today:
        failures.append(f"today_events {report['today_events']} < {args.min_today}")
    if report['company_quality_nonzero'] < args.min_company_quality_nonzero:
        failures.append(
            f"company_quality_nonzero {report['company_quality_nonzero']} "
            f"< {args.min_company_quality_nonzero}"
        )
    if report['feed_entries'] < args.min_feed_entries:
        failures.append(f"feed_entries {report['feed_entries']} < {args.min_feed_entries}")
    if report['feed_google_ratio'] > args.max_feed_google_ratio:
        failures.append(
            f"feed_google_ratio {report['feed_google_ratio']:.1%} "
            f"> {args.max_feed_google_ratio:.1%}"
        )
    if report['duplicate_ratio'] > args.max_duplicate_ratio:
        failures.append(
            f"duplicate_ratio {report['duplicate_ratio']:.1%} "
            f"> {args.max_duplicate_ratio:.1%}"
        )
    metrics = report.get('run_metrics') or {}
    if args.require_run_metrics and not metrics:
        failures.append("run_metrics missing")
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--min-today', type=int, default=1)
    parser.add_argument('--min-company-quality-nonzero', type=int, default=1)
    parser.add_argument('--min-feed-entries', type=int, default=1)
    parser.add_argument('--max-feed-google-ratio', type=float, default=0)
    parser.add_argument('--max-duplicate-ratio', type=float, default=0.35)
    parser.add_argument('--require-run-metrics', action='store_true')
    parser.add_argument('--strict', action='store_true', help='Exit non-zero when health checks fail')
    args = parser.parse_args()

    report = build_health_report(args.days)
    print_report(report)
    failures = collect_failures(report, args)
    for failure in failures:
        print(f"WARNING: {failure}")
    if args.strict and failures:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
