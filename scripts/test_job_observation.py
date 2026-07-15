from job_observation import diff_job_snapshots, extract_job_links


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


if __name__ == '__main__':
    test_extract_job_links_for_three_pilot_shapes()
    test_snapshot_diff_clusters_structure_changes()
    test_snapshot_diff_detects_contraction_cluster()
    print('job observation tests passed')
