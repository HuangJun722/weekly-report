import json
import re
import unittest.mock as mock

from generate_html import build_period_report
import fetch_news  # noqa: F401 — 确保模块已导入，便于 patch

# 模块级保护：默认不调真实 LLM，避免测试依赖 API key 或污染线上
_patch_api = mock.patch('fetch_news._chat_api_candidates', return_value=[])
_patch_api.start()


def event(**overrides):
    base = {
        'title': 'Example AI infra startup raises funding',
        'display_title': 'Example AI infra startup raises funding',
        'summary_short': '欧洲AI基础设施公司融资扩张',
        'url': 'https://example.com/a',
        'source': 'Tech.eu',
        'source_tier': 'L2 垂直交易源',
        'event_types': ['funding'],
        'score': 7,
        'region': '欧洲',
        'company_name': 'ExampleAI',
        'companies': ['ExampleAI'],
        'reason': '欧洲AI基础设施公司融资，云、数据中心和开发者生态出现预算窗口',
        'impact': '云服务商、AI基础设施供应商',
        'trend_topic': '欧洲AI基础设施',
        'opportunity_direction': '云与AI基础设施',
        'bd_triggers': ['预算窗口'],
        'follow_up_window': '7天内',
        'bd_priority': '高',
        'date': '2026-06-03',
    }
    base.update(overrides)
    return base


def test_weekly_report_builds_focus_windows_from_repeated_signals():
    report = build_period_report([
        event(url='https://example.com/a', company_name='ExampleAI', companies=['ExampleAI']),
        event(url='https://example.com/b', company_name='CloudBox', companies=['CloudBox']),
    ], '2026-06-01', '2026-06-07', '2026年第23周', '2026-W23', 'open', focus_windows_enabled=True)

    assert report['focus_windows']
    window = report['focus_windows'][0]
    assert window['direction'] == 'AI与云基础设施'
    assert window['evidence_count'] == 2
    assert 'ExampleAI' in window['objects']
    assert 'CloudBox' in window['objects']
    assert len(window['evidence']) == 2


def test_monthly_trend_requires_cross_week_evidence_and_comparison():
    report = build_period_report([
        event(date='2026-06-03', url='https://example.com/a', company_name='ExampleAI', companies=['ExampleAI']),
        event(date='2026-06-10', url='https://example.com/b', company_name='CloudBox', companies=['CloudBox']),
        event(date='2026-06-18', url='https://example.com/c', company_name='InfraCo', companies=['InfraCo']),
    ], '2026-06-01', '2026-06-30', '6 月报', '2026-06', 'closed')

    assert report['period_themes']
    trend = report['period_themes'][0]
    assert trend['week_count'] >= 2
    assert trend['count'] >= 3
    assert trend['change'] in {'新增', '升温', '延续', '降温'}


def test_weekly_report_does_not_promote_single_event_to_focus_window():
    report = build_period_report([
        event(url='https://example.com/a'),
    ], '2026-06-01', '2026-06-07', '2026年第23周', '2026-W23', 'open', focus_windows_enabled=True)

    assert report['focus_windows'] == []


def test_monthly_report_does_not_enable_weekly_focus_windows_by_default():
    report = build_period_report([
        event(url='https://example.com/a', company_name='ExampleAI', companies=['ExampleAI']),
        event(url='https://example.com/b', company_name='CloudBox', companies=['CloudBox']),
    ], '2026-06-01', '2026-06-30', '6 月报', '2026-06', 'open')

    assert report['focus_windows'] == []
    assert '周报先看' not in report['summary']


def test_weekly_broad_window_keeps_out_of_scope_events_out():
    report = build_period_report([
        event(
            url='https://example.com/health-a',
            title='Tavo Biotherapeutics raises funding for ophthalmology therapies',
            display_title='Tavo Biotherapeutics raises funding for ophthalmology therapies',
            summary_short='Tavo Biotherapeutics获融资开发眼科疗法',
            reason='眼科疗法和生物制药研发获融资',
            impact='医疗器械供应商、临床试验服务商',
            trend_topic='非洲医疗科技融资',
            region='非洲',
            company_name='Tavo Biotherapeutics',
            companies=['Tavo Biotherapeutics'],
        ),
        event(
            url='https://example.com/health-b',
            title='Secretome Therapeutics raises funding for cardiac therapy',
            display_title='Secretome Therapeutics raises funding for cardiac therapy',
            summary_short='Secretome获融资用于心脏细胞治疗',
            reason='心脏细胞疗法和生物制药融资',
            impact='医疗技术供应商',
            trend_topic='非洲医疗科技融资',
            region='非洲',
            company_name='Secretome Therapeutics',
            companies=['Secretome Therapeutics'],
        ),
    ], '2026-06-01', '2026-06-07', '2026年第23周', '2026-W23', 'open', focus_windows_enabled=True)

    assert report['focus_windows'] == []


def _fake_apis():
    return [{'id': 'test', 'name': 'Test', 'url': 'http://fake', 'key': 'k' * 10, 'model': 'm'}]


def test_weekly_narrative_overrides_mainline_when_llm_succeeds():
    def fake_post_chat(api, prompt, **kw):
        keys = [m.group(1) for m in re.finditer(r'"key": "([^"]+)"', prompt)] or ['ai_infra']
        content = json.dumps({
            'mainline': '本周AI与云基础设施成为主线，资本同步加码算力与支付赛道。',
            'themes': [{'key': k, 'narrative': f'{k}主题的叙事导读'} for k in keys],
        }, ensure_ascii=False)
        return mock.Mock(status_code=200, json=lambda: {'choices': [{'message': {'content': content}}]})

    ctx_api = mock.patch('fetch_news._chat_api_candidates', return_value=_fake_apis())
    ctx_llm = mock.patch('fetch_news._post_chat', side_effect=fake_post_chat)
    ctx_api.start()
    ctx_llm.start()
    try:
        report = build_period_report([
            event(url='https://example.com/a', company_name='ExampleAI', companies=['ExampleAI']),
            event(url='https://example.com/b', company_name='CloudBox', companies=['CloudBox']),
        ], '2026-06-01', '2026-06-07', '2026年第23周', '2026-W23', 'open', focus_windows_enabled=True)
    finally:
        ctx_llm.stop()
        ctx_api.stop()

    assert '叙事导读' in report['summary'] or 'AI' in report['summary']
    assert all(w.get('narrative') for w in report['focus_windows'])


def test_weekly_narrative_falls_back_to_template_when_llm_fails():
    ctx_api = mock.patch('fetch_news._chat_api_candidates', return_value=_fake_apis())
    ctx_llm = mock.patch('fetch_news._post_chat', side_effect=Exception('boom'))
    ctx_api.start()
    ctx_llm.start()
    try:
        report = build_period_report([
            event(url='https://example.com/a', company_name='ExampleAI', companies=['ExampleAI']),
            event(url='https://example.com/b', company_name='CloudBox', companies=['CloudBox']),
        ], '2026-06-01', '2026-06-07', '2026年第23周', '2026-W23', 'open', focus_windows_enabled=True)
    finally:
        ctx_llm.stop()
        ctx_api.stop()

    assert '本周期从' in report['summary']
    assert not any('narrative' in w for w in report['focus_windows'])


def test_weekly_editorial_failure_blocks_production_output():
    ctx_api = mock.patch('fetch_news._chat_api_candidates', return_value=_fake_apis())
    ctx_llm = mock.patch('fetch_news._post_chat', side_effect=Exception('boom'))
    ctx_api.start()
    ctx_llm.start()
    try:
        try:
            build_period_report([
                event(url='https://example.com/a', company_name='ExampleAI', companies=['ExampleAI']),
                event(url='https://example.com/b', company_name='CloudBox', companies=['CloudBox']),
            ], '2026-06-01', '2026-06-07', '2026年第23周', '2026-W23', 'open',
                focus_windows_enabled=True, require_editorial=True)
        except RuntimeError as exc:
            assert '拒绝发布降级版' in str(exc)
        else:
            raise AssertionError('生产周报在 AI 编辑失败时必须终止生成')
    finally:
        ctx_llm.stop()
        ctx_api.stop()


def test_monthly_comparison_counts_atoms_in_both_periods():
    # 上月 5 条原始事件中 4 条是同事实转载（压成 1 个 atom），修正后按 atom 口径 = 2
    previous_events = [
        event(url='https://example.com/p1', company_name='ExampleAI', companies=['ExampleAI'],
              title='Global AI startup closes funding round', display_title='Global AI startup closes funding round',
              summary_short='ExampleAI完成新一轮融资', date='2026-06-05'),
        event(url='https://example.com/p2', company_name='ExampleAI', companies=['ExampleAI'],
              title='Global AI startup closes funding round', display_title='Global AI startup closes funding round',
              summary_short='ExampleAI完成新一轮融资', date='2026-06-06'),
        event(url='https://example.com/p3', company_name='ExampleAI', companies=['ExampleAI'],
              title='Global AI startup closes funding round', display_title='Global AI startup closes funding round',
              summary_short='ExampleAI完成新一轮融资', date='2026-06-06'),
        event(url='https://example.com/p4', company_name='ExampleAI', companies=['ExampleAI'],
              title='Global AI startup closes funding round', display_title='Global AI startup closes funding round',
              summary_short='ExampleAI完成新一轮融资', date='2026-06-07'),
        event(url='https://example.com/p5', company_name='CloudBox', companies=['CloudBox'],
              title='CloudBox raises for AI data center expansion', display_title='CloudBox raises for AI data center expansion',
              summary_short='CloudBox为AI数据中心扩张融资', date='2026-06-15'),
    ]
    current_events = [
        event(url='https://example.com/c1', company_name='ExampleAI', companies=['ExampleAI'],
              title='ExampleAI expands AI inference capacity', display_title='ExampleAI expands AI inference capacity',
              summary_short='ExampleAI扩大推理算力', date='2026-07-03'),
        event(url='https://example.com/c2', company_name='CloudBox', companies=['CloudBox'],
              title='CloudBox launches regional data center', display_title='CloudBox launches regional data center',
              summary_short='CloudBox启动区域数据中心', date='2026-07-10'),
        event(url='https://example.com/c3', company_name='InfraCo', companies=['InfraCo'],
              title='InfraCo secures GPU supply for inference', display_title='InfraCo secures GPU supply for inference',
              summary_short='InfraCo锁定推理GPU供应', date='2026-07-18'),
    ]
    report = build_period_report(previous_events + current_events, '2026-07-01', '2026-07-31', '7 月报', '2026-07', 'mature')
    assert report['period_themes']
    trend = report['period_themes'][0]
    assert trend['key'] == 'ai_infra'
    assert trend['previous_count'] == 2
    assert trend['change'] == '延续'


def test_monthly_trend_requires_min_absolute_delta():
    previous_events = [
        event(url='https://example.com/a1', company_name='ExampleAI', companies=['ExampleAI'],
              title='ExampleAI expands AI capacity', display_title='ExampleAI expands AI capacity', date='2026-06-04'),
        event(url='https://example.com/a2', company_name='CloudBox', companies=['CloudBox'],
              title='CloudBox expands AI capacity', display_title='CloudBox expands AI capacity', date='2026-06-11'),
        event(url='https://example.com/a3', company_name='InfraCo', companies=['InfraCo'],
              title='InfraCo expands AI capacity', display_title='InfraCo expands AI capacity', date='2026-06-18'),
    ]
    current_events = [
        event(url='https://example.com/b1', company_name='ExampleAI', companies=['ExampleAI'],
              title='ExampleAI adds regional inference nodes', display_title='ExampleAI adds regional inference nodes', date='2026-07-02'),
        event(url='https://example.com/b2', company_name='CloudBox', companies=['CloudBox'],
              title='CloudBox adds regional inference nodes', display_title='CloudBox adds regional inference nodes', date='2026-07-09'),
        event(url='https://example.com/b3', company_name='InfraCo', companies=['InfraCo'],
              title='InfraCo adds regional inference nodes', display_title='InfraCo adds regional inference nodes', date='2026-07-16'),
        event(url='https://example.com/b4', company_name='NebulaAI', companies=['NebulaAI'],
              title='NebulaAI adds regional inference nodes', display_title='NebulaAI adds regional inference nodes', date='2026-07-23'),
    ]
    report = build_period_report(previous_events + current_events, '2026-07-01', '2026-07-31', '7 月报', '2026-07', 'mature')
    assert report['period_themes']
    trend = report['period_themes'][0]
    # 4 相对 3 增幅 33%，但未达到 +2 绝对门槛，应判延续而非升温
    assert trend['previous_count'] == 3
    assert trend['change'] == '延续'


def test_monthly_preview_outputs_observation_summary():
    events = [
        event(url='https://example.com/c1', company_name='ExampleAI', companies=['ExampleAI'], date='2026-07-03'),
        event(url='https://example.com/c2', company_name='CloudBox', companies=['CloudBox'], date='2026-07-10'),
        event(url='https://example.com/c3', company_name='InfraCo', companies=['InfraCo'], date='2026-07-18'),
    ]
    report = build_period_report(events, '2026-07-01', '2026-07-31', '7 月报', '2026-07', 'preview')
    assert '观察期' in report['summary']
    assert '本月主线是' not in report['summary']
    assert report['status_label'] == '观察中'
    assert report['period_themes']


def test_monthly_editorial_overrides_mainline_when_llm_succeeds():
    def fake_post_chat(api, prompt, **kw):
        keys = [m.group(1) for m in re.finditer(r'"key": "([^"]+)"', prompt)] or ['ai_infra']
        content = json.dumps({
            'editorial_title': '算力转向推理部署',
            'mainline': '本月AI基础设施资本转向推理与区域节点，支付行业同步进入商户入口争夺。',
            'themes': [
                {'key': k, 'narrative': f'{k}趋势本月向推理部署转向',
                 'drivers': ['区域数据中心扩张', '推理算力采购'],
                 'uncertainty': '部分扩张仍处规划阶段',
                 'next_validation': '观察数据中心是否进入运营披露'}
                for k in keys
            ],
        }, ensure_ascii=False)
        return mock.Mock(status_code=200, json=lambda: {'choices': [{'message': {'content': content}}]})

    ctx_api = mock.patch('fetch_news._chat_api_candidates', return_value=_fake_apis())
    ctx_llm = mock.patch('fetch_news._post_chat', side_effect=fake_post_chat)
    ctx_api.start()
    ctx_llm.start()
    try:
        report = build_period_report([
            event(url='https://example.com/c1', company_name='ExampleAI', companies=['ExampleAI'], date='2026-07-03'),
            event(url='https://example.com/c2', company_name='CloudBox', companies=['CloudBox'], date='2026-07-10'),
            event(url='https://example.com/c3', company_name='InfraCo', companies=['InfraCo'], date='2026-07-18'),
        ], '2026-07-01', '2026-07-31', '7 月报', '2026-07', 'mature')
    finally:
        ctx_llm.stop()
        ctx_api.stop()

    assert report['editorial_title'] == '算力转向推理部署'
    assert '本月AI基础设施资本转向' in report['summary']
    trend = report['period_themes'][0]
    assert trend.get('drivers') == ['区域数据中心扩张', '推理算力采购']
    assert trend.get('next_validation') == '观察数据中心是否进入运营披露'


def test_monthly_editorial_falls_back_to_template_when_llm_fails():
    ctx_api = mock.patch('fetch_news._chat_api_candidates', return_value=_fake_apis())
    ctx_llm = mock.patch('fetch_news._post_chat', side_effect=Exception('boom'))
    ctx_api.start()
    ctx_llm.start()
    try:
        report = build_period_report([
            event(url='https://example.com/c1', company_name='ExampleAI', companies=['ExampleAI'], date='2026-07-03'),
            event(url='https://example.com/c2', company_name='CloudBox', companies=['CloudBox'], date='2026-07-10'),
            event(url='https://example.com/c3', company_name='InfraCo', companies=['InfraCo'], date='2026-07-18'),
        ], '2026-07-01', '2026-07-31', '7 月报', '2026-07', 'mature')
    finally:
        ctx_llm.stop()
        ctx_api.stop()

    assert '本周期从' in report['summary']
    assert not report['period_themes'][0].get('drivers')
    assert not report['editorial_title']


if __name__ == '__main__':
    test_weekly_report_builds_focus_windows_from_repeated_signals()
    test_weekly_report_does_not_promote_single_event_to_focus_window()
    test_monthly_report_does_not_enable_weekly_focus_windows_by_default()
    test_monthly_trend_requires_cross_week_evidence_and_comparison()
    test_weekly_broad_window_keeps_out_of_scope_events_out()
    test_weekly_narrative_overrides_mainline_when_llm_succeeds()
    test_weekly_narrative_falls_back_to_template_when_llm_fails()
    test_weekly_editorial_failure_blocks_production_output()
    test_monthly_comparison_counts_atoms_in_both_periods()
    test_monthly_trend_requires_min_absolute_delta()
    test_monthly_preview_outputs_observation_summary()
    test_monthly_editorial_overrides_mainline_when_llm_succeeds()
    test_monthly_editorial_falls_back_to_template_when_llm_fails()
    print('period report tests passed')
