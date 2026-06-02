from collections import Counter

from source_health_report import _action, _lifecycle, _source_stats_from_events


def row(**overrides):
    base = {
        'source': 'TechCrunch',
        'tier': 'L2',
        'source_type': 'media',
        'recent_raw': 10,
        'recent_signals': 4,
        'recent_runs': 4,
        'recent_nonzero_runs': 4,
        'recent_statuses': Counter({'ok': 4}),
        'stored': 12,
        'high': 6,
        'google': 0,
        'zero_reason': '',
    }
    base.update(overrides)
    return base


def test_stable_source_lifecycle():
    item = row()
    assert _lifecycle(item) == 'stable'
    item['lifecycle'] = 'stable'
    assert _action(item) == '保留/调权'


def test_zero_failed_source_lifecycle():
    item = row(
        recent_raw=0,
        recent_signals=0,
        recent_nonzero_runs=0,
        recent_statuses=Counter({'failed': 4}),
        stored=0,
        high=0,
        tier='L4',
        source_type='industry_media',
        zero_reason='zero and broken',
    )
    assert _lifecycle(item) == 'failed'
    item['lifecycle'] = 'failed'
    assert _action(item) == '优先修复'


def test_google_action_is_fallback_not_weighting():
    item = row(source='Google News', stored=100, high=10, google=100)
    item['lifecycle'] = _lifecycle(item)
    assert _action(item) == '保留补漏/继续降权'


def test_registry_id_alias_merges_event_source():
    events = [{
        'date': '2026-06-01',
        'source_id': 'grab-newsroom',
        'source': 'Grab',
        'event_types': ['strategy'],
        'score': 5,
    }]
    stats = _source_stats_from_events(
        events,
        {'2026-06-01'},
        {'grab-newsroom': 'Grab Newsroom'},
    )
    assert set(stats.keys()) == {'Grab Newsroom'}
    assert stats['Grab Newsroom']['stored'] == 1


if __name__ == '__main__':
    test_stable_source_lifecycle()
    test_zero_failed_source_lifecycle()
    test_google_action_is_fallback_not_weighting()
    test_registry_id_alias_merges_event_source()
    print('source health tests passed')

