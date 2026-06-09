import json

from entity_signal_conversion_report import build_entity_signal_conversion_report, event_matches_entity


def test_event_matches_entity_by_alias():
    entity = {'name': 'MercadoLibre', 'aliases': ['Mercado Libre', 'Mercado Pago']}
    event = {'company_name': 'Mercado Pago', 'title': 'Payment product update'}
    assert event_matches_entity(event, entity)


def test_entity_signal_report_counts_points_and_events(tmp_path):
    pool_path = tmp_path / 'entity_pool.json'
    events_path = tmp_path / 'events.json'
    pool_path.write_text(
        json.dumps({
            'version': 'test',
            'entities': [{
                'name': 'Grab',
                'aliases': ['Grab Holdings', 'GrabPay'],
                'region': '亚太',
                'sector': 'mobility_payment',
                'priority': 'core',
                'observation_points': [
                    {'type': 'newsroom', 'status': 'active', 'instrumented': True},
                    {'type': 'jobs', 'status': 'candidate', 'instrumented': False},
                ],
            }],
        }, ensure_ascii=False),
        encoding='utf-8',
    )
    events_path.write_text(
        json.dumps({
            '2026-06-08': [{
                'date': '2026-06-08',
                'title': 'Grab launches payment platform partnership',
                'summary_short': 'Grab launches payment platform partnership.',
                'reason': '支付平台合作会影响东南亚商户服务链路。',
                'impact': '支付服务商、商户服务伙伴',
                'company_name': 'Grab',
                'companies': ['Grab'],
                'source': 'Grab IR',
                'source_tier': 'L1 官方/IR源',
                'event_types': ['strategy'],
                'score': 6,
                'url': 'https://example.com/grab',
            }],
        }, ensure_ascii=False),
        encoding='utf-8',
    )

    report = build_entity_signal_conversion_report(
        days=1,
        pool_path=str(pool_path),
        events_path=str(events_path),
    )
    row = report['rows'][0]
    assert row['entity'] == 'Grab'
    assert row['observation_points'] == 2
    assert row['active_points'] == 1
    assert row['candidate_points'] == 1
    assert row['not_instrumented_points'] == 1
    assert row['stored_events'] == 1
    assert row['homepage_events'] == 1
    assert row['instrumentation_status'] == 'not_instrumented'
    assert row['governance_action'] == 'observe'
    point_rows = {row['point_type']: row for row in report['point_rows']}
    assert point_rows['newsroom']['active_points'] == 1
    assert point_rows['jobs']['candidate_points'] == 1
    assert point_rows['newsroom']['stored_events'] == 1


if __name__ == '__main__':
    test_event_matches_entity_by_alias()
    from tempfile import TemporaryDirectory
    from pathlib import Path
    with TemporaryDirectory() as temp_dir:
        test_entity_signal_report_counts_points_and_events(Path(temp_dir))
    print('entity signal conversion tests passed')
