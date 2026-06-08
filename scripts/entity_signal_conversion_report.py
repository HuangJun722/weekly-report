"""Report entity-pool coverage and current event conversion.

The first version is intentionally observational: it does not crawl new
observation points yet. It shows which entities already receive stored events
and which observation points still lack instrumentation.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from event_value import should_show_in_main_list, should_show_in_review
except ImportError:
    from scripts.event_value import should_show_in_main_list, should_show_in_review


def _safe_print(text):
    print(text.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')) 


def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _flatten_events(data):
    if isinstance(data, list):
        return data
    events = []
    for date_key, items in (data or {}).items():
        for event in items or []:
            if not event.get('date'):
                event = dict(event)
                event['date'] = date_key
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


def _norm(value):
    return re.sub(r'[^a-z0-9]+', '', (value or '').lower())


def _event_company_tokens(event):
    values = []
    for key in ('company_name', 'company'):
        if event.get(key):
            values.append(event[key])
    values.extend(event.get('companies') or [])
    return {_norm(value) for value in values if _norm(value)}


def _event_text_token(event):
    text = ' '.join([
        event.get('title') or '',
        event.get('display_title') or '',
        event.get('summary_short') or '',
        event.get('reason') or '',
    ])
    return _norm(text)


def _entity_alias_tokens(entity):
    aliases = [entity.get('name') or '']
    aliases.extend(entity.get('aliases') or [])
    return {_norm(alias) for alias in aliases if _norm(alias)}


def event_matches_entity(event, entity):
    aliases = _entity_alias_tokens(entity)
    if not aliases:
        return False
    company_tokens = _event_company_tokens(event)
    if aliases & company_tokens:
        return True
    text = _event_text_token(event)
    return any(alias and alias in text for alias in aliases)


def _point_counts(entity):
    counts = {
        'observation_points': 0,
        'active_points': 0,
        'candidate_points': 0,
        'not_instrumented_points': 0,
    }
    for point in entity.get('observation_points') or []:
        counts['observation_points'] += 1
        status = point.get('status') or 'candidate'
        if status == 'active':
            counts['active_points'] += 1
        if status == 'candidate':
            counts['candidate_points'] += 1
        if not point.get('instrumented'):
            counts['not_instrumented_points'] += 1
    return counts


def build_entity_signal_conversion_report(days=30, pool_path='data/entity_pool.json', events_path='data/events.json'):
    pool = _load_json(pool_path)
    events = _flatten_events(_load_json(events_path))
    dates = sorted({_event_date(event) for event in events if _event_date(event)})
    end_date = dates[-1] if dates else ''
    selected_dates = _period_dates(end_date, days)
    selected_events = [event for event in events if _event_date(event) in selected_dates]

    rows = []
    for entity in pool.get('entities') or []:
        matched = [event for event in selected_events if event_matches_entity(event, entity)]
        main = [event for event in matched if should_show_in_main_list(event)]
        review = [event for event in matched if should_show_in_review(event)]
        point_counts = _point_counts(entity)
        row = {
            'entity': entity.get('name') or '',
            'region': entity.get('region') or '',
            'sector': entity.get('sector') or '',
            'priority': entity.get('priority') or '',
            **point_counts,
            'stored_events': len(matched),
            'homepage_events': len(main),
            'review_events': len(review),
            'last_event_date': max((_event_date(event) for event in matched), default=''),
            'instrumentation_status': 'not_instrumented'
            if point_counts['not_instrumented_points'] else 'instrumented',
        }
        rows.append(row)

    rows.sort(
        key=lambda row: (
            row['homepage_events'],
            row['stored_events'],
            row['active_points'],
            row['observation_points'],
        ),
        reverse=True,
    )
    totals = {
        'entities': len(rows),
        'observation_points': sum(row['observation_points'] for row in rows),
        'active_points': sum(row['active_points'] for row in rows),
        'candidate_points': sum(row['candidate_points'] for row in rows),
        'not_instrumented_points': sum(row['not_instrumented_points'] for row in rows),
        'stored_events': sum(row['stored_events'] for row in rows),
        'homepage_events': sum(row['homepage_events'] for row in rows),
        'review_events': sum(row['review_events'] for row in rows),
    }
    return {
        'end_date': end_date,
        'days': days,
        'pool_version': pool.get('version') or '',
        'totals': totals,
        'rows': rows,
    }


def print_report(report, limit=50):
    totals = report['totals']
    _safe_print(
        f"entity signal conversion | pool_version={report['pool_version']} "
        f"end_date={report['end_date']} days={report['days']}"
    )
    _safe_print(
        "totals | entities={entities} points={observation_points} active={active_points} "
        "candidate={candidate_points} not_instrumented={not_instrumented_points} "
        "stored={stored_events} homepage={homepage_events} review={review_events}".format(**totals)
    )
    _safe_print("entity | region | sector | points | active | candidate | stored | homepage | review | last_event | status")
    for row in report['rows'][:limit]:
        _safe_print(
            "{entity} | {region} | {sector} | {observation_points} | {active_points} | "
            "{candidate_points} | {stored_events} | {homepage_events} | {review_events} | "
            "{last_event_date} | {instrumentation_status}".format(**row)
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=30)
    parser.add_argument('--pool-path', default='data/entity_pool.json')
    parser.add_argument('--events-path', default='data/events.json')
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--json-out', help='Optional path to write JSON report')
    args = parser.parse_args()

    report = build_entity_signal_conversion_report(args.days, args.pool_path, args.events_path)
    print_report(report, args.limit)
    if args.json_out:
        path = Path(args.json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == '__main__':
    sys.exit(main())
