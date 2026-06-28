"""View-layer selectors for dashboard, RSS, and company surfaces.

Scoring answers "how valuable is this event"; selectors answer "where should
this event appear". Keep these rules explicit so one surface does not inherit
another surface's product contract by accident.
"""

try:
    from event_value import (
        event_score,
        event_type,
        is_company_quality_signal,
        is_google_news_event,
        is_high_value_event,
        needs_quality_review,
        should_show_in_main_list,
        should_show_in_review,
    )
except ImportError:
    from scripts.event_value import (
        event_score,
        event_type,
        is_company_quality_signal,
        is_google_news_event,
        is_high_value_event,
        needs_quality_review,
        should_show_in_main_list,
        should_show_in_review,
    )


MATURE_BATCH_MIN_EVENTS = 3


def event_date(event):
    return (event.get('date') or '')[:10]


def _sort_events(events):
    return sorted(events, key=lambda x: (x.get('date', ''), event_score(x)), reverse=True)


def select_company_events(events_by_date, week_ago):
    """Return recent company events and visible generic events for dashboard use."""
    company_events = []
    generic_events = []

    for date_str, events in events_by_date.items():
        for event in events:
            if event.get('is_company') and date_str >= week_ago:
                company_events.append(event)
                continue

            if event.get('is_company'):
                continue

            if should_show_in_main_list(event) or should_show_in_review(event):
                generic_events.append(event)

    return _sort_events(company_events), _sort_events(generic_events)


def select_mature_main_date(sorted_dates, all_visible_events, events_by_date):
    """Prefer the newest date that has enough visible events for the homepage."""
    counts = {}
    for event in all_visible_events:
        if not should_show_in_main_list(event):
            continue
        date_key = event_date(event)
        if date_key:
            counts[date_key] = counts.get(date_key, 0) + 1

    latest_date = next((d for d in sorted_dates if events_by_date.get(d)), None)
    main_date = latest_date
    for date_key in sorted_dates:
        if counts.get(date_key, 0) >= MATURE_BATCH_MIN_EVENTS:
            main_date = date_key
            break

    latest_count = len(events_by_date.get(latest_date, [])) if latest_date else 0
    notice = ''
    if latest_date and main_date and latest_date != main_date:
        notice = f'最新批次仅 {latest_count} 条，当前展示最近一个信息量更完整的批次'
    return main_date, latest_date, latest_count, notice


def select_main_list_events(events):
    """Select events that can appear as normal dashboard cards."""
    return [event for event in events if should_show_in_main_list(event)]


def select_homepage_events(all_visible_events, main_date, fallback_events=None):
    """Select homepage cards for a date, with a caller-provided fallback."""
    selected = [
        event for event in all_visible_events
        if event_date(event) == main_date and should_show_in_main_list(event)
    ]
    if not selected and fallback_events:
        return list(fallback_events)
    return selected


def is_review_candidate(event):
    """Return whether a visible event belongs in the review drawer."""
    return (
        needs_quality_review(event)
        or not should_show_in_main_list(event)
        or (is_google_news_event(event) and not is_high_value_event(event))
    )


def select_review_events(events, limit=12):
    review_events = [
        event for event in events
        if is_review_candidate(event) and should_show_in_review(event)
    ]
    review_events.sort(key=lambda x: (event_score(x), x.get('date', '')), reverse=True)
    if limit is None:
        return review_events
    return review_events[:limit]


def select_company_quality_events(events):
    return [event for event in events if is_company_quality_signal(event)]


def is_period_high_value_event(event):
    """Return whether an event counts as high priority in period reports."""
    return is_high_value_event(event)


def select_period_high_value_events(events):
    """Select high-priority events for weekly/monthly opportunity summaries."""
    return [event for event in events if is_period_high_value_event(event)]


def _unique_events(events, limit=None):
    selected = []
    seen = set()
    for event in events:
        key = event.get('url') or event.get('title') or id(event)
        if key in seen:
            continue
        seen.add(key)
        selected.append(event)
        if limit is not None and len(selected) >= limit:
            break
    return selected


def select_feed_events(today_events, all_visible_events, limit=5):
    """Select RSS entries from homepage first, then latest date with high-value events."""
    high_value = [
        event for event in today_events
        if is_high_value_event(event) and not is_google_news_event(event)
    ]
    main_fill = [
        event for event in today_events
        if should_show_in_main_list(event) and not is_google_news_event(event)
    ]
    feed_events = _unique_events(high_value + main_fill, limit=limit)
    if feed_events:
        return feed_events, ''

    by_date = {}
    for event in all_visible_events:
        if not is_high_value_event(event) or is_google_news_event(event):
            continue
        date_key = event_date(event)
        if date_key:
            by_date.setdefault(date_key, []).append(event)

    if not by_date:
        return [], ''

    feed_date = sorted(by_date.keys(), reverse=True)[0]
    return _unique_events(by_date[feed_date], limit=limit), feed_date
