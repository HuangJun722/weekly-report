"""变化聚合 MVP 测试：公司/行业维度的跨周变化检测（复用主题趋势的基线+校正）。"""

from period_themes import build_company_changes, build_industry_changes, company_key, industry_key


def event(**overrides):
    base = {
        'title': 'DeepSeek 发布新一代推理模型并扩张算力',
        'display_title': 'DeepSeek 发布新一代推理模型并扩张算力',
        'summary_short': 'DeepSeek 发布新模型并扩张 AI 算力',
        'url': 'https://example.com/deepseek-1',
        'source': 'TechCrunch',
        'source_tier': 'L2 垂直交易源',
        'event_types': ['funding'],
        'score': 7,
        'region': '中资',
        'company_name': 'DeepSeek',
        'companies': ['DeepSeek'],
        'reason': '中国 AI 厂商发布新模型，带动算力与开发者生态变化',
        'impact': '云服务商、AI 基础设施供应商',
        'trend_topic': '中国 AI 大模型',
        'domain': 'ai',
        'scope_industries': ['ai'],
        'date': '2026-08-03',
    }
    base.update(overrides)
    return base


def multi_week_company_events():
    """同一公司在 3 个不同周各有多条事件，形成跨周公司变化。"""
    events = []
    weeks = ['2026-08-03', '2026-08-10', '2026-08-17']
    for i, day in enumerate(weeks):
        for j in range(2):
            events.append(event(
                url=f'https://example.com/deepseek-{i}-{j}',
                company_name='DeepSeek', companies=['DeepSeek'],
                domain='ai', scope_industries=['ai'],
                title=f'DeepSeek 第{i}周发布模型迭代（{j}）',
                date=day,
            ))
    return events


def test_company_key_prefers_company_name():
    assert company_key({'company_name': 'Grab', 'companies': ['Grab', 'GoTo']}) == 'Grab'
    assert company_key({'companies': ['GoTo']}) == 'GoTo'
    assert company_key({}) == ''


def test_industry_key_falls_through_domain_to_vertical():
    assert industry_key({'domain': 'payments', 'scope_industries': ['payments']}) == 'payments'
    assert industry_key({'scope_industries': ['commerce']}) == 'commerce'
    assert industry_key({'vertical': 'Fintech/支付'}) == 'Fintech/支付'


def test_company_changes_detects_cross_week_company():
    """同一公司跨多周持续出信号 → 返回公司变化。"""
    rows = build_company_changes(multi_week_company_events(), '2026-08-01', '2026-08-31')
    assert rows, 'DeepSeek 跨 3 周应形成公司变化'
    row = rows[0]
    assert row['dimension'] == 'company'
    assert 'DeepSeek' in row['title']
    assert row['week_count'] >= 2
    assert row['count'] >= 3
    assert row['evidence']


def test_company_changes_empty_without_cross_week():
    """单周事件不足跨周 → 不返回。"""
    single_week = [event(date=d, company_name='DeepSeek') for d in ('2026-08-03', '2026-08-04', '2026-08-05')]
    assert build_company_changes(single_week, '2026-08-01', '2026-08-31') == []


def test_industry_changes_detects_cross_week_industry():
    """某行业跨周多事件 → 返回行业变化。"""
    events = []
    for i, day in enumerate(['2026-08-03', '2026-08-10', '2026-08-17']):
        for j in range(2):
            events.append(event(
                url=f'https://example.com/pay-{i}-{j}',
                company_name=f'Fintech{i}{j}', companies=[f'Fintech{i}{j}'],
                domain='payments', scope_industries=['payments'],
                title=f'支付行业第{i}周融资与产品更新（{j}）',
                reason='支付基础设施获融资并推出新能力',
                date=day,
            ))
    rows = build_industry_changes(events, '2026-08-01', '2026-08-31')
    assert rows, '支付行业跨 3 周应形成行业变化'
    row = rows[0]
    assert row['dimension'] == 'industry'
    assert '支付' in row['title'] or 'payments' in row['title']
    assert row['week_count'] >= 2


def test_industry_changes_empty_input():
    assert build_industry_changes([], '2026-08-01', '2026-08-31') == []
    assert build_company_changes([], '2026-08-01', '2026-08-31') == []
