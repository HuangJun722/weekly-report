from job_observation import (
    build_job_candidate,
    diff_job_snapshots,
    extract_job_links,
    merge_candidate_pool,
    source_reset_suspected,
)


def test_extract_job_links_for_three_pilot_shapes():
    cases = [
        ('Grab', 'https://www.grab.careers/en/jobs/', '<a href="/en/jobs/7440001/senior-software-engineer-backend-ai/">Senior Software Engineer, Backend AI</a>'),
        ('Stripe', 'https://stripe.com/jobs/search', '<a href="/jobs/listing/account-executive-ai-sales/7954688">Account Executive, AI Sales</a>'),
        ('Shopify', 'https://www.shopify.com/careers', '<a href="/careers/product-partner-manager-shopify-payments_12345678-1234-1234-1234-123456789abc">Product Partner Manager, Shopify Payments</a>'),
    ]
    for entity, base_url, html in cases:
        jobs = extract_job_links(entity, base_url, html)
        assert len(jobs) == 1
        assert jobs[0]['url'].startswith('https://')
        assert jobs[0]['title']


def test_snapshot_diff_clusters_structure_changes():
    previous = [{'id': 'old', 'title': 'Operations Analyst', 'url': 'https://example.com/old', 'function_tags': ['operations']}]
    current = [
        {'id': 'ai-1', 'title': 'Senior AI Engineer', 'url': 'https://example.com/ai-1', 'function_tags': ['ai', 'engineering']},
        {'id': 'ai-2', 'title': 'AI Platform Engineer', 'url': 'https://example.com/ai-2', 'function_tags': ['ai', 'engineering']},
        {'id': 'sales', 'title': 'Partner Sales Lead', 'url': 'https://example.com/sales', 'function_tags': ['partnerships', 'sales']},
    ]
    diff = diff_job_snapshots(previous, current)
    assert diff['added_count'] == 3
    assert diff['removed_count'] == 1
    assert diff['clusters']['ai'] == 2
    assert diff['candidate_signal'] is True


def test_snapshot_diff_detects_contraction_cluster():
    previous = [
        {'id': f'ops-{index}', 'title': f'Operations role {index}', 'url': f'https://example.com/{index}', 'function_tags': ['operations']}
        for index in range(3)
    ]
    diff = diff_job_snapshots(previous, [])
    assert diff['removed_count'] == 3
    assert diff['removed_clusters']['operations'] == 3
    assert diff['candidate_signal'] is True


def test_full_board_refresh_is_rejected_as_source_reset():
    previous = [
        {'id': f'old-{index}', 'title': f'AI Engineer {index}', 'url': f'https://example.com/old/{index}', 'function_tags': ['ai']}
        for index in range(20)
    ]
    current = [
        {'id': f'new-{index}', 'title': f'AI Engineer {index}', 'url': f'https://example.com/new/{index}', 'function_tags': ['ai']}
        for index in range(20)
    ]
    diff = diff_job_snapshots(previous, current)
    assert source_reset_suspected(previous, current, diff)
    candidate = build_job_candidate(
        {'id': 'example', 'name': 'Example', 'region': '全球', 'sector': 'ai_platform'},
        diff, previous, current, '2026-07-30T12:00:00+08:00',
    )
    assert candidate['status'] == 'rejected'
    assert candidate['rejection_reason'] == 'source_reset_suspected'


def test_qualified_candidate_is_persisted_and_promoted_with_evidence():
    previous = []
    current = [
        {'id': f'ai-{index}', 'title': f'AI Platform Engineer {index}', 'url': f'https://example.com/{index}', 'function_tags': ['ai', 'engineering']}
        for index in range(3)
    ]
    diff = diff_job_snapshots(previous, current)
    candidate = build_job_candidate(
        {'id': 'stripe', 'name': 'Stripe', 'region': '全球', 'sector': 'payment_developer_platform'},
        diff, previous, current, '2026-07-30T12:00:00+08:00',
    )
    pool, events = merge_candidate_pool({'candidates': []}, [candidate], '2026-07-30T12:00:00+08:00')
    assert pool['candidates'][0]['status'] == 'promoted'
    assert len(pool['candidates'][0]['evidence_refs']) == 3
    assert events[0]['candidate_id'] == candidate['candidate_id']
    assert events[0]['source'] == 'Stripe Jobs'


if __name__ == '__main__':
    test_extract_job_links_for_three_pilot_shapes()
    test_snapshot_diff_clusters_structure_changes()
    test_snapshot_diff_detects_contraction_cluster()
    test_full_board_refresh_is_rejected_as_source_reset()
    test_qualified_candidate_is_persisted_and_promoted_with_evidence()
    print('job observation tests passed')
