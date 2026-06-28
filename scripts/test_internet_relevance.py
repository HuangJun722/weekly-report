from internet_relevance import assess_internet_relevance, is_mainline_internet_event


def event(**overrides):
    base = {
        'title': 'Example raises funding',
        'summary_short': 'Example获融资',
        'reason': '融资事件',
        'impact': '相关供应商',
        'source': 'TechCrunch',
        'source_tier': 'L2 垂直交易源',
    }
    base.update(overrides)
    return base


def test_core_internet_is_mainline():
    result = assess_internet_relevance(event(
        title='Stripe launches new payments API for global merchants',
        reason='支付API更新影响跨境商户和开发者生态',
    ))
    assert result['score'] == 3
    assert is_mainline_internet_event(event(title='Stripe launches payments API'))


def test_openai_health_model_is_kept_as_ai_platform_signal():
    result = assess_internet_relevance(event(
        title='OpenAI launches healthcare model API',
        reason='OpenAI医疗模型通过API进入企业AI平台生态',
    ))
    assert result['score'] >= 2


def test_healthcare_saas_exception_is_kept():
    result = assess_internet_relevance(event(
        title='Healthcare SaaS platform launches AI notetaker API',
        reason='医疗SaaS通过API和AI病历能力服务企业客户',
    ))
    assert result['score'] >= 2


def test_biotherapeutics_funding_is_out_of_scope():
    result = assess_internet_relevance(event(
        title='Tavo Biotherapeutics secures $17M for ophthalmology therapies',
        reason='眼科疗法和生物制药研发获融资',
        impact='医疗器械供应商、临床试验服务商',
    ))
    assert result['score'] == 0


def test_therapeutics_is_not_rescued_by_analysis_api_wording():
    result = assess_internet_relevance(event(
        title='LTZ Therapeutics Raises $38M to Advance Immunotherapy Pipeline',
        summary_short='LTZ Therapeutics获融资推进免疫疗法管线',
        reason='分析称可能带来API、生态和合作机会',
        impact='临床试验服务商',
    ))
    assert result['score'] == 0


def test_space_capital_event_is_out_of_scope_without_internet_infra():
    result = assess_internet_relevance(event(
        title='HawkEye 360 Raises $416M in Landmark Space IPO',
        summary_short='HawkEye 360通过太空IPO筹集资金',
        reason='资本进入空间科技',
    ))
    assert result['score'] == 0


def test_biotech_construction_materials_are_out_of_scope():
    result = assess_internet_relevance(event(
        title='Biotech startup Mykor raises €4.6M for low-carbon construction materials',
        summary_short='Mykor获融资，用废料生产低碳建材',
        reason='生物制造和建筑科技融资',
        impact='生物制造设备供应商、建筑科技集成商',
    ))
    assert result['score'] == 0


def test_defense_tech_is_edge_not_mainline():
    result = assess_internet_relevance(event(
        title='Defense tech startup raises $500M for military drones',
        reason='国防科技和军工AI融资',
    ))
    assert result['score'] == 0
    assert not is_mainline_internet_event(event(title='Defense tech startup raises $500M'))


def test_defense_ai_is_hard_out_of_scope():
    result = assess_internet_relevance(event(
        title='Military AI cloud platform raises $100M for battlefield drones',
        reason='军工AI云平台融资扩张',
    ))
    assert result['score'] == 0


if __name__ == '__main__':
    test_core_internet_is_mainline()
    test_openai_health_model_is_kept_as_ai_platform_signal()
    test_healthcare_saas_exception_is_kept()
    test_biotherapeutics_funding_is_out_of_scope()
    test_therapeutics_is_not_rescued_by_analysis_api_wording()
    test_space_capital_event_is_out_of_scope_without_internet_infra()
    test_biotech_construction_materials_are_out_of_scope()
    test_defense_tech_is_edge_not_mainline()
    test_defense_ai_is_hard_out_of_scope()
    print('internet relevance tests passed')
