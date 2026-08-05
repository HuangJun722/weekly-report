from fetch_news import _apply_company_scope_contract, _calc_score, detect_event_types
from scope_gate import apply_scope_contract, assess_scope


def event(title, **overrides):
    item = {
        'title': title,
        'event_types': ['strategy'],
        'source': 'Example',
        'region': '全球',
    }
    item.update(overrides)
    return item


def test_ai_policy_is_qualified_as_regional_policy():
    result = assess_scope(event(
        'EU regulator approves new AI model transparency rules',
        region='欧洲',
    ))
    assert result['status'] == 'qualified'
    assert result['layer'] == 'regional_policy'
    assert 'ai_infra' in result['industries']


def test_unrelated_regional_policy_is_filtered():
    result = assess_scope(event(
        'Regional authority updates construction material tax rules',
        region='欧洲',
    ))
    assert result['status'] == 'filtered'
    assert result['reason'] == 'scope_no_target_industry'


def test_vertical_source_contract_recovers_implicit_company_action():
    result = assess_scope(event(
        'eBay to Operate Depop as It Seeks Synergies',
        event_types=['other'],
        source_role='industry_vertical',
        source_tier='L4 垂直赛道精品源',
        vertical='电商',
    ))
    assert result['status'] == 'qualified'
    assert result['match_basis'] == 'source_contract'
    assert 'commerce' in result['industries']


def test_vertical_lifestyle_story_stays_filtered():
    result = assess_scope(event(
        'Food businesses face a summer PR headache',
        event_types=['other'],
        source_role='industry_vertical',
        source_tier='L4 垂直赛道精品源',
        vertical='电商/零售',
    ))
    assert result['status'] == 'filtered'


def test_in_scope_topic_without_change_stays_candidate():
    result = assess_scope(event(
        'A guide to payment infrastructure providers',
        event_types=['other'],
    ))
    assert result['status'] == 'candidate'
    assert result['reason'] == 'scope_editorial_without_explicit_change'


def test_vertical_editorial_stays_candidate_without_explicit_change():
    result = assess_scope(event(
        'Why SoftPOS Is Becoming a Strategic Decision for Merchant Acquiring',
        event_types=['strategy'],
        source_role='industry_vertical',
        source_tier='L4 垂直赛道精品源',
        vertical='Fintech/支付',
    ))
    assert result['status'] == 'candidate'
    assert result['reason'] == 'scope_editorial_without_explicit_change'


def test_editorial_term_anywhere_in_title_stays_candidate():
    result = assess_scope(event(
        'Meta shares holiday 2026 tips for small businesses',
        event_types=['strategy'],
        source_role='industry_vertical',
        source_tier='L4 垂直赛道精品源',
        vertical='广告/社交',
    ))
    assert result['status'] == 'candidate'
    assert result['reason'] == 'scope_editorial_without_explicit_change'


def test_quantified_industry_change_is_not_mistaken_for_editorial():
    result = assess_scope(event(
        'How mobile game revenue rose 25% across Southeast Asia',
        event_types=['earnings'],
        source_role='industry_vertical',
        source_tier='L4 垂直赛道精品源',
        vertical='游戏',
    ))
    assert result['status'] == 'qualified'
    assert result['layer'] == 'industry_change'


def test_scope_contract_is_auditable():
    item = apply_scope_contract(event('Singapore grants a new digital bank license'))
    assert item['scope_status'] == 'qualified'
    assert item['scope_enforced'] is True
    assert item['scope_layer'] == 'regional_policy'
    assert item['scope_reason'] == 'scope_target_change'
    assert item['scope_regions'] == ['全球']


def test_policy_and_industry_changes_do_not_need_capital_amount_to_score():
    policy = event(
        'Singapore regulator introduces new payment license rules',
        region='亚太',
        source_tier='L4 垂直赛道精品源',
        source_role='industry_vertical',
        vertical='Fintech/支付',
    )
    industry = event(
        'Mobile game spending declines across Southeast Asia',
        region='亚太',
        source_tier='L4 垂直赛道精品源',
        source_role='industry_vertical',
        vertical='游戏',
    )
    assert _calc_score(policy) >= 6
    assert _calc_score(industry) >= 5


def test_company_scope_contract_comes_from_existing_entity_pool():
    cfg = _apply_company_scope_contract({'name': 'Grab'})
    assert 'payments' in cfg['scope_industries']
    assert 'local_services_logistics' in cfg['scope_industries']
    assert cfg['scope_regions'] == ['亚太']
    newsroom = _apply_company_scope_contract({
        'name': 'Grab Newsroom',
        'company_name': 'Grab',
    })
    assert 'payments' in newsroom['scope_industries']
    naver = _apply_company_scope_contract({'name': 'Naver'})
    assert 'ai_infra' in naver['scope_industries']
    assert 'cloud_saas_developer' in naver['scope_industries']


def test_report_and_model_are_not_collapsed_into_strategy():
    assert detect_event_types('IDC publishes China cloud market share forecast report') == ['industry_report']
    assert detect_event_types('Open source multimodal model launches with API access') == ['model_release']


if __name__ == '__main__':
    test_ai_policy_is_qualified_as_regional_policy()
    test_unrelated_regional_policy_is_filtered()
    test_vertical_source_contract_recovers_implicit_company_action()
    test_vertical_lifestyle_story_stays_filtered()
    test_in_scope_topic_without_change_stays_candidate()
    test_vertical_editorial_stays_candidate_without_explicit_change()
    test_editorial_term_anywhere_in_title_stays_candidate()
    test_quantified_industry_change_is_not_mistaken_for_editorial()
    test_scope_contract_is_auditable()
    test_policy_and_industry_changes_do_not_need_capital_amount_to_score()
    test_company_scope_contract_comes_from_existing_entity_pool()
    test_report_and_model_are_not_collapsed_into_strategy()
    print('scope gate tests passed')
