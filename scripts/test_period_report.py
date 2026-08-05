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


if __name__ == '__main__':
    test_weekly_report_builds_focus_windows_from_repeated_signals()
    test_weekly_report_does_not_promote_single_event_to_focus_window()
    test_monthly_report_does_not_enable_weekly_focus_windows_by_default()
    test_monthly_trend_requires_cross_week_evidence_and_comparison()
    test_weekly_broad_window_keeps_out_of_scope_events_out()
    test_weekly_narrative_overrides_mainline_when_llm_succeeds()
    test_weekly_narrative_falls_back_to_template_when_llm_fails()
    print('period report tests passed')
