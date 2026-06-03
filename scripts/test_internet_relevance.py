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


def test_biotherapeutics_funding_is_out_of_scope():
    result = assess_internet_relevance(event(
        title='Tavo Biotherapeutics secures $17M for ophthalmology therapies',
        reason='眼科疗法和生物制药研发获融资',
        impact='医疗器械供应商、临床试验服务商',
    ))
    assert result['score'] == 0


def test_defense_tech_is_edge_not_mainline():
    result = assess_internet_relevance(event(
        title='Defense tech startup raises $500M for military drones',
        reason='国防科技和军工AI融资',
    ))
    assert result['score'] == 1
    assert not is_mainline_internet_event(event(title='Defense tech startup raises $500M'))


if __name__ == '__main__':
    test_core_internet_is_mainline()
    test_openai_health_model_is_kept_as_ai_platform_signal()
    test_biotherapeutics_funding_is_out_of_scope()
    test_defense_tech_is_edge_not_mainline()
    print('internet relevance tests passed')
