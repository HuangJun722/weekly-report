from fetch_news import (
    _merge_source_funnel,
    _select_rss_entry_link,
    _source_funnel_stage,
    apply_event_storage_policy,
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


def test_event_storage_policy_keeps_complete_history():
    events = {
        '2020-01-01': [{'title': 'old'}],
        '2026-08-04': [{'title': 'new'}],
    }

    assert apply_event_storage_policy(events) == events


def test_rss_link_repair_prefers_matching_guid():
    title = 'Citadel sees $500b in AI chip debt issuance by 2028'
    entry = {
        'link': 'https://example.com/nvidia-ceo-chinas-chip-market',
        'id': 'https://example.com/citadel-ai-chip-debt-issuance',
    }

    link, repair = _select_rss_entry_link(entry, title)

    assert link.endswith('/citadel-ai-chip-debt-issuance')
    assert repair['source_url_original'].endswith('/nvidia-ceo-chinas-chip-market')
    assert repair['source_url_repaired'] is True


if __name__ == '__main__':
    test_source_funnel_counts_by_source_id()
    test_dedupe_events_by_day_returns_reason_counts()
    test_event_storage_policy_keeps_complete_history()
    test_rss_link_repair_prefers_matching_guid()
    print('fetch news metrics tests passed')
