import json

from daily_coverage_report import build_daily_coverage_report


def _event(**overrides):
    base = {
        'date': '2026-06-08',
        'title': 'Fintech startup raises funding for payment platform',
        'summary_short': 'Fintech startup raises funding for payment platform.',
        'reason': '支付平台融资会影响跨境支付合作窗口。',
        'impact': '支付服务商、跨境商户',
        'source': 'TechCrunch',
        'source_tier': 'L2 垂直交易源',
        'region': '欧洲',
        'company_name': 'PayCo',
        'event_types': ['funding'],
        'score': 7,
        'url': 'https://example.com/payco',
    }
    base.update(overrides)
    return base


def test_daily_coverage_counts_objects_regions_and_groups(tmp_path):
    events_path = tmp_path / 'events.json'
    events = {
        '2026-06-08': [
            _event(company_name='PayCo', region='欧洲', url='https://example.com/1'),
            _event(company_name='ShopCo', region='亚太', url='https://example.com/2', score=5),
            _event(company_name='CloudCo', region='拉美', url='https://example.com/3', score=4),
        ]
    }
    events_path.write_text(json.dumps(events, ensure_ascii=False), encoding='utf-8')

    report = build_daily_coverage_report(days=1, events_path=str(events_path))
    row = report['rows'][0]
    assert row['stored_events'] == 3
    assert row['entities'] == 3
    assert row['regions'] == 3
    assert row['selected'] + row['important'] + row['watch'] == 3
    assert row['selected'] >= 1
    assert row['status'] == 'thin'


def test_daily_coverage_flags_google_heavy_day(tmp_path):
    events_path = tmp_path / 'events.json'
    events = {
        '2026-06-08': [
            _event(
                source='Google News',
                source_tier='L5 Google News 补漏源',
                company_name='MercadoLibre',
                is_company=True,
                url='https://news.google.com/a',
                score=3,
            ),
            _event(
                source='Google News',
                source_tier='L5 Google News 补漏源',
                company_name='Naver',
                is_company=True,
                url='https://news.google.com/b',
                score=3,
            ),
            _event(company_name='Grab', is_company=True, url='https://example.com/grab', score=2),
        ]
    }
    events_path.write_text(json.dumps(events, ensure_ascii=False), encoding='utf-8')

    report = build_daily_coverage_report(days=1, events_path=str(events_path))
    row = report['rows'][0]
    assert row['google_ratio'] > 0.4
    assert row['action'] == 'check_source_mix'


if __name__ == '__main__':
    from tempfile import TemporaryDirectory
    from pathlib import Path
    with TemporaryDirectory() as temp_dir:
        test_daily_coverage_counts_objects_regions_and_groups(Path(temp_dir))
    with TemporaryDirectory() as temp_dir:
        test_daily_coverage_flags_google_heavy_day(Path(temp_dir))
    print('daily coverage tests passed')
