from signal_scoring import apply_signal_contract, infer_content_type, infer_action_type, infer_domain, score_signal, signal_change_score


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


def test_action_type_and_domain_are_orthogonal_fields():
    # 公司动作：主体是公司，但动作是产品发布，行业是 AI
    event = base_event(
        title='Stripe launches new payment API for AI agents',
        source_type='newsroom', source_tier='L1 官方/IR源',
        is_company=True, company_name='Stripe', companies=['Stripe'],
        scope_status='qualified', scope_industries=['ai_infra', 'cloud_saas_developer'],
    )
    result = apply_signal_contract(event)
    assert result['action_type'] == 'product_release'
    assert result['domain'] in ('payment', 'ai', 'cloud_saas')
    assert 'signal_type' in result  # 兼容旧字段，但评分已不按它给公司低分


def test_company_action_not_penalized_by_subject():
    # 公司产品发布（高价值动作）不该因"公司主体"天然拿低分：
    # 同样公司，产品发布 > 泛公司动作。用干净文本，避开 base_event 默认摘要污染。
    def clean(title):
        return base_event(
            title=title, display_title=title,
            summary_short='', source_excerpt='', impact='',
            source_type='newsroom', source_tier='L1 官方/IR源',
            is_company=True, company_name='ExampleAI', companies=['ExampleAI'],
            scope_status='qualified', scope_industries=['ai_infra'],
        )
    release = clean('ExampleAI launches new AI inference service')
    generic = clean('ExampleAI reorganizes internal teams')
    r_rel = signal_change_score(release)
    r_gen = signal_change_score(generic)
    assert r_rel['action_type'] == 'product_release'
    assert r_gen['action_type'] == 'other' or r_gen['action_type'] == 'expansion'
    assert r_rel['signal_change_score'] > r_gen['signal_change_score']
    # 公司产品发布至少不低于旧 signal_type 的 company 档（12 分权重）
    assert r_rel['signal_change_breakdown']['action_type_weight'] >= 20


def test_market_impact_uses_company_market_with_confidence():
    # Stripe 在实体池有 primary_markets → 公司市场标注，置信度 20
    event = base_event(
        title='Stripe expands in Southeast Asia',
        source_type='newsroom', source_tier='L1 官方/IR源',
        is_company=True, company_name='Stripe', companies=['Stripe'],
        scope_status='qualified', scope_industries=['payments'],
    )
    r = signal_change_score(event)
    assert r['signal_change_breakdown']['market_impact_confidence'] == 20
    assert r['signal_change_breakdown']['market_impact'] > 0


if __name__ == '__main__':
    test_report_is_a_first_class_content_type()
    test_model_release_has_model_profile()
    test_china_company_uses_company_subject_without_special_bonus()
    test_score_is_not_used_to_admit_out_of_scope_content()
    test_action_type_and_domain_are_orthogonal_fields()
    test_company_action_not_penalized_by_subject()
    test_market_impact_uses_company_market_with_confidence()
    print('signal scoring tests passed')
