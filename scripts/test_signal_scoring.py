from signal_scoring import apply_signal_contract, infer_content_type, score_signal


def base_event(**overrides):
    event = {
        'title': 'IDC publishes China cloud market share forecast report',
        'url': 'https://example.com/idc-report',
        'source': 'IDC Research',
        'source_type': 'research_report',
        'source_tier': 'L4 垂直赛道精品源',
        'source_excerpt': 'China cloud market share and regional distribution forecast',
        'scope_status': 'qualified',
        'scope_layer': 'industry_change',
        'scope_industries': ['ai_infra', 'cloud_saas_developer'],
        'published_at': '2026-08-05',
        'report_methodology_visible': True,
        'report_published_at': '2026-08-05',
        'impact': '云服务商、数据中心和企业软件供应商',
        'summary_short': 'IDC发布中国云计算市场分布预测',
    }
    event.update(overrides)
    return event


def test_report_is_a_first_class_content_type():
    result = apply_signal_contract(base_event())
    assert result['content_type'] == 'industry_report'
    assert result['subject_type'] == 'report'
    assert result['claim_type'] == 'institutional_assessment'
    assert result['confidence_score'] >= 65
    assert result['attention_score'] >= 70


def test_model_release_has_model_profile():
    result = apply_signal_contract(base_event(
        title='Open source multimodal model launches with API pricing',
        source_type='newsroom',
        source_tier='L1 官方/IR源',
        scope_layer='company_action',
        scope_industries=['ai_infra'],
        model_card_url='https://example.com/model-card',
        report_methodology_visible=False,
    ))
    assert result['content_type'] == 'model_release'
    assert result['subject_type'] == 'ai_model'
    assert result['claim_type'] == 'release_fact'
    assert result['attention_score'] >= 70


def test_china_company_uses_company_subject_without_special_bonus():
    event = base_event(
        title='Chinese AI company expands cloud services in Southeast Asia',
        source_type='newsroom',
        source_tier='L1 官方/IR源',
        is_company=True,
        company_name='Example China AI',
        origin_region='中国',
        impact_regions=['亚太'],
        event_types=['strategy'],
        scope_layer='company_action',
        scope_industries=['ai_infra', 'cloud_saas_developer'],
    )
    result = apply_signal_contract(event)
    assert result['content_type'] == 'company_action'
    assert result['subject_type'] == 'company'
    assert result['claim_type'] == 'company_action'
    assert result['origin_region'] == '中国'


def test_score_is_not_used_to_admit_out_of_scope_content():
    event = base_event(scope_status='filtered', scope_layer='unclassified', scope_industries=[])
    result = score_signal(event)
    assert result['attention_score'] < 80


if __name__ == '__main__':
    test_report_is_a_first_class_content_type()
    test_model_release_has_model_profile()
    test_china_company_uses_company_subject_without_special_bonus()
    test_score_is_not_used_to_admit_out_of_scope_content()
    print('signal scoring tests passed')
