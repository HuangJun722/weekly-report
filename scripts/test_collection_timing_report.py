from collection_timing_report import build_collection_timing_rows


def test_builds_collection_timing_rows():
    rows = build_collection_timing_rows([
        {
            'run_id': '20260603-052000',
            'date': '2026-06-03',
            'started_at': '2026-06-03T05:20:00+08:00',
            'environment': 'github_actions',
            'collection': {'raw_count': 10, 'unique_count': 8},
            'filtering': {'smart_filtered_count': 6, 'ai_filtered_count': 5},
            'storage': {
                'added_count': 3,
                'generic_added': 2,
                'company_added': 1,
                'duplicate_skipped': 4,
                'added_event_dates': {'2026-06-02': 2, '2026-06-03': 1},
                'added_source_tiers': {'L2 垂直交易源': 2, 'L1 官方/IR源': 1},
            },
        }
    ])
    assert rows[0]['run_id'] == '20260603-052000'
    assert rows[0]['raw'] == 10
    assert rows[0]['event_dates']['2026-06-02'] == 2
    assert rows[0]['source_tiers']['L2 垂直交易源'] == 2


if __name__ == '__main__':
    test_builds_collection_timing_rows()
    print('collection timing tests passed')
