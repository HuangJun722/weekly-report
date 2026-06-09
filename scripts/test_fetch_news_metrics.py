from fetch_news import (
    _merge_source_funnel,
    _source_funnel_stage,
    dedupe_events_by_day,
)


def test_source_funnel_counts_by_source_id():
    items = [
        {'source_id': 'stripe-changelog', 'source': 'Stripe', 'title': 'A'},
        {'source_id': 'stripe-changelog', 'source': 'Stripe', 'title': 'B'},
        {'source': 'TechCrunch', 'title': 'C'},
    ]
    funnel = {}
    _merge_source_funnel(funnel, _source_funnel_stage(items, 'raw'))
    _merge_source_funnel(funnel, _source_funnel_stage(items[:2], 'smart_kept'))

    assert funnel['stripe-changelog']['raw'] == 2
    assert funnel['stripe-changelog']['smart_kept'] == 2
    assert funnel['TechCrunch']['raw'] == 1


def test_dedupe_events_by_day_returns_reason_counts():
    events = {
        '2026-06-08': [
            {
                'date': '2026-06-08',
                'title': 'Financial Results for Fiscal Year',
                'url': 'https://example.com/a',
                'is_company': True,
                'company_name': 'Square Enix',
            },
            {
                'date': '2026-06-08',
                'title': 'Square Enix Financial Results for Fiscal Year',
                'url': 'https://example.com/b',
                'is_company': True,
                'company_name': 'Square Enix',
            },
            {
                'date': '2026-06-08',
                'title': 'Square Enix Financial Results for Fiscal Year',
                'url': 'https://example.com/b',
                'is_company': True,
                'company_name': 'Square Enix',
            },
        ]
    }
    cleaned, removed, reasons = dedupe_events_by_day(events)

    assert removed == 2
    assert len(cleaned['2026-06-08']) == 1
    assert reasons['missing_company_alias'] == 1
    assert reasons['same_day_duplicate'] == 1


if __name__ == '__main__':
    test_source_funnel_counts_by_source_id()
    test_dedupe_events_by_day_returns_reason_counts()
    print('fetch news metrics tests passed')
