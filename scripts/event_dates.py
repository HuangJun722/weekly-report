"""Shared event-date semantics for collection, storage, and display."""

from datetime import datetime, timedelta, timezone


def _parse_observed_at(value):
    if isinstance(value, datetime):
        return value
    if value:
        try:
            return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _parse_date(value):
    try:
        return datetime.strptime((value or '')[:10], '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def publication_metadata(candidate, source, confidence, observed_at=None):
    observed = _parse_observed_at(observed_at)
    observed_iso = observed.isoformat()
    parsed = _parse_date(candidate)
    metadata = {
        'published_at': '',
        'observed_at': observed_iso,
        'date_source': source or 'observed_at',
        'date_confidence': confidence or 'low',
        'date_parse_warning': '',
    }
    if not candidate:
        metadata.update({
            'date_source': 'observed_at',
            'date_confidence': 'observed',
            'date_parse_warning': 'missing_published_at',
        })
        return metadata
    if not parsed:
        metadata['date_parse_warning'] = 'invalid_published_at'
        return metadata
    if parsed > (observed + timedelta(hours=24)).date():
        metadata['scheduled_at'] = parsed.isoformat()
        metadata['date_confidence'] = 'low'
        metadata['date_parse_warning'] = 'future_published_at_reclassified'
        return metadata
    metadata['published_at'] = parsed.isoformat()
    return metadata


def apply_event_date_metadata(event, fallback_observed_at=None):
    """Normalize one event while preserving `date` as the legacy display bucket."""
    observed_at = event.get('observed_at') or fallback_observed_at
    candidate = event.get('published_at') or event.get('article_date')
    metadata = publication_metadata(
        candidate,
        event.get('date_source') or 'legacy_article_date',
        event.get('date_confidence') or 'medium',
        observed_at=observed_at,
    )
    if not candidate and event.get('scheduled_at'):
        metadata['scheduled_at'] = event['scheduled_at']
        metadata['date_parse_warning'] = event.get('date_parse_warning') or metadata['date_parse_warning']
    event.update(metadata)
    event['article_date'] = metadata['published_at']
    observed_date = metadata['observed_at'][:10]
    event['date'] = metadata['published_at'] or observed_date
    event['date_basis'] = 'published_at' if metadata['published_at'] else 'observed_at'
    return event


def is_display_date(value, now=None):
    parsed = _parse_date(value)
    if not parsed:
        return False
    current = _parse_observed_at(now).date()
    return parsed <= current
