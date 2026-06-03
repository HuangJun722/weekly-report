from narratives import build_narrative


def cluster(**overrides):
    base = {
        'title': 'Careem / Uber整合窗口',
        'region': '中东',
        'topic': '中东出行平台整合',
        'cluster_type': 'ma',
        'type_label': '整合窗口',
        'companies': ['Careem', 'Uber'],
        'signals': ['行业交易'],
        'confidence': '高',
        'action': '加入观察名单，跟踪整合后的合作入口',
        'evidence': [
            {
                'title': 'Uber收购Careem控股权',
                'url': 'https://example.com/a',
                'date': '2026-06-01',
                'source': 'The National',
                'type': '资金流向',
            },
            {
                'title': 'e&出售Careem部分股份',
                'url': 'https://example.com/b',
                'date': '2026-06-01',
                'source': 'ZAWYA',
                'type': '资金流向',
            },
        ],
        'evidence_events': [
            {
                'display_title': 'Uber收购Careem控股权',
                'url': 'https://example.com/a',
                'date': '2026-06-01',
                'source': 'The National',
                'source_tier': 'L2 垂直交易源',
                'region': '中东',
                'company_name': 'Careem',
                'event_types': ['ma'],
                'trend_topic': '中东出行平台整合',
                'reason': '中东出行平台整合',
            },
            {
                'display_title': 'Careem开放支付合作',
                'url': 'https://example.com/b',
                'date': '2026-06-02',
                'source': 'Careem Press',
                'source_tier': 'L1 官方/IR源',
                'region': '中东',
                'company_name': 'Careem',
                'event_types': ['partnership'],
                'trend_topic': '中东出行平台整合',
                'reason': '中东出行生态出现官方合作信号',
            },
        ],
    }
    base.update(overrides)
    return base


def test_narrative_binds_judgment_clusters_and_evidence():
    narrative = build_narrative([cluster()])
    assert narrative['clusters']
    assert narrative['evidence']
    assert narrative['evidence_events'][0]['display_title'] == 'Uber收购Careem控股权'
    assert narrative['judgment']
    assert narrative['consistency']['evidence_coverage'] == 1.0
    assert narrative['mode'] == 'narrative'


def test_dedupes_clusters_with_same_company():
    narrative = build_narrative([
        cluster(title='Careem整合窗口'),
        cluster(title='Careem生态开放窗口', cluster_type='partnership', type_label='生态合作窗口'),
    ])
    assert len(narrative['clusters']) == 1


def test_downgrades_when_evidence_is_not_independent():
    narrative = build_narrative([
        cluster(evidence_events=[
            {
                'display_title': '非洲医疗科技公司A融资',
                'url': 'https://example.com/health-a',
                'date': '2026-06-01',
                'source': 'Ventureburn',
                'source_tier': 'L2 垂直交易源',
                'region': '非洲',
                'company_name': 'HealthA',
                'event_types': ['funding'],
                'trend_topic': '非洲医疗科技融资',
            },
            {
                'display_title': '非洲医疗科技公司B融资',
                'url': 'https://example.com/health-b',
                'date': '2026-06-01',
                'source': 'Ventureburn',
                'source_tier': 'L2 垂直交易源',
                'region': '非洲',
                'company_name': 'HealthB',
                'event_types': ['funding'],
                'trend_topic': '非洲医疗科技融资',
            },
        ])
    ])
    assert narrative['mode'] == 'daily_brief'
    assert narrative['clusters'] == []
    assert not narrative['consistency']['promoted']


def test_keeps_narrative_clusters_coherent():
    narrative = build_narrative([
        cluster(title='中东出行整合窗口', region='中东', type_label='整合窗口'),
        cluster(
            title='欧洲旅游融资窗口',
            region='欧洲',
            type_label='资金进入窗口',
            companies=['TravelCo'],
            evidence=[
                {
                    'title': 'TravelCo获融资',
                    'url': 'https://example.com/c',
                    'date': '2026-06-01',
                    'source': 'Tech.eu',
                    'type': '资金流向',
                }
            ],
            evidence_events=[
                {
                    'display_title': 'TravelCo获融资',
                    'url': 'https://example.com/c',
                    'date': '2026-06-01',
                    'source': 'Tech.eu',
                    'region': '欧洲',
                }
            ],
        ),
    ])
    assert len(narrative['clusters']) == 1
    assert narrative['clusters'][0]['region'] == '中东'


def test_falls_back_to_daily_brief_without_clusters():
    narrative = build_narrative([], fallback_events=[
        {
            'display_title': '韩国AI中心建设',
            'url': 'https://example.com/c',
            'date': '2026-06-01',
            'display_source': 'Tech in Asia',
            'insight_label': '资金流向',
        }
    ])
    assert narrative['mode'] == 'daily_brief'
    assert narrative['title'] == '今日要点'
    assert narrative['evidence'][0]['title'] == '韩国AI中心建设'


if __name__ == '__main__':
    test_narrative_binds_judgment_clusters_and_evidence()
    test_dedupes_clusters_with_same_company()
    test_downgrades_when_evidence_is_not_independent()
    test_keeps_narrative_clusters_coherent()
    test_falls_back_to_daily_brief_without_clusters()
    print('narrative tests passed')
