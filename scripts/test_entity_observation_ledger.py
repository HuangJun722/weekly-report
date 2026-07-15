import json

from entity_observation_ledger import build_entity_observation_ledger


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


def test_observation_ledger_distinguishes_quiet_failed_changed_and_pending(tmp_path):
    pool_path = tmp_path / 'entity_pool.json'
    registry_path = tmp_path / 'source_registry.json'
    metrics_path = tmp_path / 'run_metrics.json'
    events_path = tmp_path / 'events.json'

    _write(pool_path, {
        'entities': [{
            'id': 'example',
            'name': 'Example',
            'aliases': ['Example Inc'],
            'region': '全球',
            'sector': 'platform',
            'observation_points': [
                {'type': 'newsroom', 'url': 'https://example.com/news', 'status': 'active', 'instrumented': True},
                {'type': 'changelog', 'url': 'https://example.com/changelog', 'status': 'active', 'instrumented': True},
                {'type': 'ir', 'url': 'https://example.com/ir', 'status': 'active', 'instrumented': True},
                {'type': 'jobs', 'url': 'https://example.com/jobs', 'status': 'candidate', 'instrumented': False},
            ],
        }],
    })
    _write(registry_path, {'sources': [
        {'id': 'example-news', 'name': 'Example News', 'url': 'https://example.com/news', 'source_type': 'newsroom'},
        {'id': 'example-changelog', 'name': 'Example Changelog', 'url': 'https://example.com/changelog', 'source_type': 'changelog'},
        {'id': 'example-ir', 'name': 'Example IR', 'url': 'https://example.com/ir', 'source_type': 'ir'},
    ]})
    _write(metrics_path, [{
        'run_id': '20260715-120000',
        'date': '2026-07-15',
        'started_at': '2026-07-15T12:00:00+08:00',
        'html': {'source_stats': {
            'Example News': {'status': 'empty', 'fetch_status': 'success', 'count': 0},
            'Example Changelog': {'status': 'ok', 'fetch_status': 'success', 'count': 2},
            'Example IR': {'status': 'failed', 'fetch_status': 'failed', 'count': 0},
        }},
    }])
    _write(events_path, {})

    report = build_entity_observation_ledger(
        pool_path=str(pool_path),
        registry_path=str(registry_path),
        metrics_path=str(metrics_path),
        events_path=str(events_path),
        as_of='2026-07-15',
    )
    points = {row['point_type']: row for row in report['entities'][0]['observation_points']}
    assert points['newsroom']['status'] == 'quiet'
    assert points['changelog']['status'] == 'changed_below_threshold'
    assert points['ir']['status'] == 'failed'
    assert points['jobs']['status'] == 'pending'
    assert report['entities'][0]['status'] == 'partial'


def test_observation_ledger_marks_qualified_entity_active(tmp_path):
    pool_path = tmp_path / 'entity_pool.json'
    registry_path = tmp_path / 'source_registry.json'
    metrics_path = tmp_path / 'run_metrics.json'
    events_path = tmp_path / 'events.json'
    _write(pool_path, {'entities': [{
        'id': 'stripe', 'name': 'Stripe', 'aliases': [], 'region': '全球', 'sector': 'payments',
        'observation_points': [{'type': 'changelog', 'url': 'https://stripe.com/changelog', 'status': 'active', 'instrumented': True}],
    }]})
    _write(registry_path, {'sources': [{
        'id': 'stripe-changelog', 'name': 'Stripe Changelog', 'url': 'https://stripe.com/changelog', 'source_type': 'changelog',
    }]})
    _write(metrics_path, [{
        'run_id': '20260715-120000', 'date': '2026-07-15', 'started_at': '2026-07-15T12:00:00+08:00',
        'html': {'source_stats': {'Stripe Changelog': {'status': 'ok', 'fetch_status': 'success', 'count': 1}}},
    }])
    _write(events_path, {'2026-07-15': [{
        'date': '2026-07-15', 'source_id': 'stripe-changelog', 'source': 'Stripe Changelog',
        'company_name': 'Stripe', 'title': 'Stripe adds a payment API capability',
        'event_types': ['strategy'], 'score': 7, 'url': 'https://stripe.com/changelog/a',
        'summary_short': 'Stripe adds a payment API capability.',
        'reason': 'The API change expands payment integration options.',
        'impact': 'Payment developers and enterprise integration partners.',
        'analysis_status': 'complete',
        'source_tier': 'L1 官方/IR源',
        'is_company': True,
        'internet_relevance_score': 3,
    }]})
    report = build_entity_observation_ledger(
        pool_path=str(pool_path), registry_path=str(registry_path),
        metrics_path=str(metrics_path), events_path=str(events_path), as_of='2026-07-15',
    )
    entity = report['entities'][0]
    assert entity['status'] == 'active'
    assert entity['qualified_event_count_30d'] == 1
    assert entity['observation_points'][0]['last_qualified_event_at'] == '2026-07-15'


if __name__ == '__main__':
    from pathlib import Path
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as temp_dir:
        test_observation_ledger_distinguishes_quiet_failed_changed_and_pending(Path(temp_dir))
    with TemporaryDirectory() as temp_dir:
        test_observation_ledger_marks_qualified_entity_active(Path(temp_dir))
    print('entity observation ledger tests passed')
