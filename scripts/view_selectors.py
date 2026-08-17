"""View-layer selectors for dashboard, RSS, and company surfaces.

Scoring answers "how valuable is this event"; selectors answer "where should
this event appear". Keep these rules explicit so one surface does not inherit
another surface's product contract by accident.
"""

try:
    from event_value import (
        event_score,
        event_filter_reason,
        event_type,
        classify_bd_priority,
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
        event_filter_reason,
        event_type,
        classify_bd_priority,
        is_company_quality_signal,
        is_google_news_event,
        is_high_value_event,
        needs_quality_review,
        should_show_in_main_list,
        should_show_in_review,
    )


MATURE_BATCH_MIN_EVENTS = 3


def derive_view_status(event):
    if should_show_in_main_list(event):
        return 'main'
    if should_show_in_review(event):
        return 'review'
    return 'filtered'


def apply_view_contract(event):
    """Freeze the display decision before presentation enrichment mutates text."""
    status = derive_view_status(event)
    priority = classify_bd_priority(event)
    event['view_status'] = status
    event['view_reason'] = 'qualified_main' if status == 'main' else (
        'qualified_review' if status == 'review' else event_filter_reason(event)
    )
    event['view_priority'] = {
        '高': 'selected',
        '中': 'important',
        '观察': 'watch',
    }.get(priority, 'watch')
    return event


def is_main_view_event(event):
    return event.get('view_status') == 'main' if event.get('view_status') else should_show_in_main_list(event)


def is_review_view_event(event):
    return event.get('view_status') == 'review' if event.get('view_status') else should_show_in_review(event)


def event_date(event):
    return (event.get('date') or '')[:10]


def _signal_change_score(event):
    try:
        return float(event.get('signal_change_score') or 0)
    except (TypeError, ValueError):
        return 0


# 信号类型质量加分：行动性信号（扩张/合作/开发者/AI基建）> 资本与支付 > 组织/合规/无分类。
# 与 signal_change_score 的 action_type 权重互补：后者按动作定值，这里按信号分类在
# 同分事件里再区分"更可能对应商业行动"的，避免只靠单一轴。
TAXONOMY_BONUS = {
    'expansion': 2,
    'partnership': 2,
    'developer_change': 2,
    'ai_infra': 2,
    'payment': 1,
    'commerce': 1,
    'capital': 1,
    'org_change': 0,
    'compliance': 0,
    'general': 0,
}

TIER_BONUS = {
    'L1 官方/IR源': 2,
    'L2 垂直交易源': 1,
    'L3 区域生态源': 1,
    'L4 垂直赛道精品源': 1,
    'L4 深度趋势源': 1,
    'L5 Google News 补漏源': 0,
}


def _signal_quality_bonus(event):
    """来源与信号类型的质量加分，作为同变化分事件内的次级排序。"""
    taxonomies = event.get('signal_taxonomy') or []
    tax_bonus = max((TAXONOMY_BONUS.get(t, 0) for t in taxonomies), default=0)
    tier_bonus = TIER_BONUS.get(event.get('source_tier') or '', 0)
    return tax_bonus + tier_bonus


def signal_sort_key(event):
    """按 日期 → 变化重要性(signal_change_score) → 信号质量 → 事件分 排序。

    signal_change_score 回答"这个变化对行业/区域有多重要"，是产品定位
    （变化发现）的核心排序轴；信号质量加分只在同变化分内区分来源可信度与
    信号行动性；event_score 只回答"公司发生了什么"，降为最次级。
    """
    return (
        event.get('date', ''),
        _signal_change_score(event),
        _signal_quality_bonus(event),
        event_score(event),
    )


def _sort_events(events):
    return sorted(events, key=signal_sort_key, reverse=True)


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

            if is_main_view_event(event) or is_review_view_event(event):
                generic_events.append(event)

    return _sort_events(company_events), _sort_events(generic_events)


def select_mature_main_date(sorted_dates, all_visible_events, events_by_date):
    """Prefer the newest date that has enough visible events for the homepage."""
    counts = {}
    for event in all_visible_events:
        if not is_main_view_event(event):
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
    return [event for event in events if is_main_view_event(event)]


def select_homepage_events(all_visible_events, main_date, fallback_events=None):
    """Select homepage cards for a date, with a caller-provided fallback."""
    selected = [
        event for event in all_visible_events
        if event_date(event) == main_date and is_main_view_event(event)
    ]
    if not selected and fallback_events:
        return list(fallback_events)
    return selected


def is_review_candidate(event):
    """Return whether a visible event belongs in the review drawer."""
    return (
        needs_quality_review(event)
        or not is_main_view_event(event)
        or (is_google_news_event(event) and not is_high_value_event(event))
    )


def select_review_events(events, limit=12):
    review_events = [
        event for event in events
        if is_review_candidate(event) and is_review_view_event(event)
    ]
    review_events.sort(key=signal_sort_key, reverse=True)
    if limit is None:
        return review_events
    return review_events[:limit]


def select_company_quality_events(events):
    return [event for event in events if is_company_quality_signal(event)]


def is_period_high_value_event(event):
    """Return whether an event counts as high priority in period reports."""
    if event.get('view_status'):
        return event.get('view_status') == 'main' and event.get('view_priority') == 'selected'
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


def select_feed_events(today_events, all_visible_events, limit=None):
    """Select RSS entries from homepage first, then latest date with high-value events."""
    high_value = [
        event for event in today_events
        if is_period_high_value_event(event) and not is_google_news_event(event)
    ]
    main_fill = [
        event for event in today_events
        if is_main_view_event(event) and not is_google_news_event(event)
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
