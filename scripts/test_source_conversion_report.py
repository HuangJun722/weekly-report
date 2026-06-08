from source_conversion_report import build_source_conversion_report, classify_filter_reason


def _event(**overrides):
    base = {
        'date': '2026-06-08',
        'title': 'European fintech startup raises funding for payment platform',
        'summary_short': 'European fintech startup raises funding for payment platform.',
        'reason': '支付平台融资会影响商户收单和跨境支付合作窗口。',
        'impact': '支付服务商、跨境电商商户',
        'source': 'TechCrunch',
        'source_tier': 'L2 垂直交易源',
        'event_types': ['funding'],
        'score': 7,
        'url': 'https://example.com/a',
    }
    base.update(overrides)
    return base


def test_filter_reason_main():
    assert classify_filter_reason(_event()) == 'main'


def test_filter_reason_out_of_scope_before_quality():
    event = _event(
        title='Biotech company raises funding for clinical trial',
        summary_short='Biotech company raises funding for clinical trial.',
        reason='临床试验融资。',
        impact='未知',
    )
    assert classify_filter_reason(event) == 'out_of_scope'


def test_filter_reason_quality_review():
    event = _event(summary_short='', event_types=['other'], score=2)
    assert classify_filter_reason(event) == 'quality_review'


def test_conversion_aggregates_run_and_event_stats(tmp_path):
    data_path = tmp_path / 'data'
    data_path.mkdir()
    events_path = data_path / 'events.json'
    metrics_path = data_path / 'run_metrics.json'
    registry_path = data_path / 'source_registry.json'
    events_path.write_text(
        """
        {
          "2026-06-08": [
            {
              "date": "2026-06-08",
              "title": "European fintech startup raises funding for payment platform",
              "summary_short": "European fintech startup raises funding for payment platform.",
              "reason": "支付平台融资会影响商户收单和跨境支付合作窗口。",
              "impact": "支付服务商、跨境电商商户",
              "source": "TechCrunch",
              "source_tier": "L2 垂直交易源",
              "event_types": ["funding"],
              "score": 7,
              "url": "https://example.com/a"
            }
          ]
        }
        """,
        encoding='utf-8',
    )
    metrics_path.write_text(
        """
        [
          {
            "date": "2026-06-08",
            "rss": {
              "source_stats": {
                "TechCrunch": {"count": 10, "signal_count": 4, "status": "ok", "method": "rss"}
              }
            }
          }
        ]
        """,
        encoding='utf-8',
    )
    registry_path.write_text('{"sources": []}', encoding='utf-8')

    old_cwd = __import__('os').getcwd()
    try:
        __import__('os').chdir(tmp_path)
        report = build_source_conversion_report(days=1)
    finally:
        __import__('os').chdir(old_cwd)

    row = report['rows'][0]
    assert row['source'] == 'TechCrunch'
    assert row['raw'] == 10
    assert row['signal'] == 4
    assert row['stored'] == 1
    assert row['main'] == 1
    assert row['lost_after_signal'] == 3


if __name__ == '__main__':
    test_filter_reason_main()
    test_filter_reason_out_of_scope_before_quality()
    test_filter_reason_quality_review()
    from tempfile import TemporaryDirectory
    from pathlib import Path
    with TemporaryDirectory() as temp_dir:
        test_conversion_aggregates_run_and_event_stats(Path(temp_dir))
    print('source conversion tests passed')
