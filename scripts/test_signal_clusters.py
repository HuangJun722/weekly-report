from signal_clusters import build_signal_clusters


def event(**overrides):
    base = {
        'title': 'Careem expands mobility platform after Uber deal',
        'url': 'https://example.com/careem',
        'source': 'TechCrunch',
        'source_tier': 'L2 垂直交易源',
        'event_types': ['ma'],
        'score': 7,
        'region': '中东',
        'company_name': 'Careem',
        'companies': ['Careem', 'Uber'],
        'reason': '中东出行平台整合，第三方服务和支付合作入口可能变化',
        'impact': '中东出行技术供应商、本地化服务商',
        'summary_short': 'Careem控制权变化带来生态整合信号',
        'trend_topic': '中东出行平台整合',
        'date': '2026-06-01',
    }
    base.update(overrides)
    return base


def test_builds_signal_cluster_from_repeated_regional_signals():
    events = [
        event(url='https://example.com/a'),
        event(
            url='https://example.com/b',
            company_name='e&',
            companies=['e&', 'Uber'],
            title='e& sells Careem stake to Uber',
        ),
    ]
    clusters = build_signal_clusters(events, '2026-06-01')
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster['region'] == '中东'
    assert cluster['type_label'] == '整合窗口'
    assert '多个事件' in cluster['eligibility']
    assert '多个对象' in cluster['eligibility']


def test_single_event_is_not_promoted_to_cluster():
    clusters = build_signal_clusters([event()], '2026-06-01')
    assert clusters == []


def test_google_only_cluster_requires_more_evidence():
    google_events = [
        event(
            source='Google News',
            source_tier='L5 Google News 补漏源',
            url='https://news.google.com/rss/articles/a',
        ),
        event(
            source='Google News',
            source_tier='L5 Google News 补漏源',
            url='https://news.google.com/rss/articles/b',
            company_name='Uber',
            companies=['Uber', 'Careem'],
        ),
    ]
    clusters = build_signal_clusters(google_events, '2026-06-01')
    assert clusters == []


if __name__ == '__main__':
    test_builds_signal_cluster_from_repeated_regional_signals()
    test_single_event_is_not_promoted_to_cluster()
    test_google_only_cluster_requires_more_evidence()
    print('signal cluster tests passed')
