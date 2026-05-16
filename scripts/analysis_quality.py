"""Event analysis quality helpers.

The collector should not treat template fallback text as finished analysis.
These helpers mark events that still need AI repair before they are trusted.
"""

GENERIC_REASON_PATTERNS = [
    '科技动态',
    '有新动态',
    '战略调整',
    '融资事件',
    '并购/收购',
    '财报披露',
    '金额待确认',
    '完成融资',
    '达成并购',
    '战略新动向',
    '战略动态',
    '科技行业动态',
    '科技公司',
    '科技企业',
    '待确认',
    '待分析',
]

UNKNOWN_IMPACT_VALUES = {
    '',
    '未知',
    '待分析',
    '无法判断',
    '无法确定',
    '相关行业',
    '相关企业',
    '相关公司',
}


def _norm(value):
    return str(value or '').strip()


def get_quality_flags(event):
    """Return quality flags for one event."""
    flags = []
    title = _norm(event.get('title'))
    reason = _norm(event.get('reason'))
    summary = _norm(event.get('summary_short'))
    impact = _norm(event.get('impact'))

    if not summary:
        flags.append('missing_summary')
    elif title and summary == title[:25]:
        flags.append('title_prefix_summary')

    if not reason:
        flags.append('missing_reason')
    elif any(pattern in reason for pattern in GENERIC_REASON_PATTERNS):
        flags.append('generic_reason')

    if impact in UNKNOWN_IMPACT_VALUES:
        flags.append('unknown_impact')

    return flags


def annotate_event_quality(event, source=None, status=None):
    """Add analysis status fields to an event and return it."""
    flags = get_quality_flags(event)
    event['quality_flags'] = flags
    event['needs_repair'] = bool(flags)
    if source:
        event['analysis_source'] = source
    else:
        event.setdefault('analysis_source', 'unknown')

    if status:
        event['analysis_status'] = status
    elif event.get('analysis_status') in ('fallback', 'failed'):
        pass
    elif flags:
        event['analysis_status'] = 'partial'
    else:
        event['analysis_status'] = 'complete'
    return event


def summarize_quality(events):
    total = len(events)
    needs_repair = sum(1 for e in events if e.get('needs_repair') or get_quality_flags(e))
    fallback = sum(1 for e in events if e.get('analysis_status') in ('fallback', 'failed'))
    high_risk = sum(
        1 for e in events
        if (e.get('score') or 0) >= 7 and (e.get('needs_repair') or get_quality_flags(e))
    )
    return {
        'total': total,
        'needs_repair': needs_repair,
        'fallback_or_failed': fallback,
        'high_score_needs_repair': high_risk,
        'repair_ratio': (needs_repair / total) if total else 0,
    }
