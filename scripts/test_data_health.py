from pathlib import Path

from check_data_health import build_health_report, collect_failures
from run_metrics import latest_run_metrics, write_run_metrics


class Args:
    min_today = 1
    min_company_quality_nonzero = 1
    min_feed_entries = 1
    max_feed_google_ratio = 0
    max_duplicate_ratio = 0.35
    require_run_metrics = False


def test_current_data_health_contract():
    report = build_health_report(days=7)
    failures = collect_failures(report, Args)
    assert failures == []


def test_run_metrics_roundtrip():
    path = Path('data/test_run_metrics.json')
    if path.exists():
        path.unlink()
    write_run_metrics({
        'run_id': 'test-run',
        'date': '2026-06-01',
        'collection': {'raw_count': 10, 'unique_count': 8},
        'filtering': {'smart_filtered_count': 6, 'ai_filtered_count': 5},
        'storage': {'added_count': 3, 'duplicate_skipped': 2},
    }, path=path, keep=5)
    latest = latest_run_metrics(path)
    assert latest['run_id'] == 'test-run'
    assert latest['collection']['raw_count'] == 10
    path.unlink()


if __name__ == '__main__':
    test_current_data_health_contract()
    test_run_metrics_roundtrip()
    print('data health tests passed')
