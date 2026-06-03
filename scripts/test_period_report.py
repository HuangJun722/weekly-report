from generate_html import build_period_report


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
    assert window['direction'] == '资金进入窗口'
    assert window['evidence_count'] == 2
    assert 'ExampleAI' in window['objects']
    assert 'CloudBox' in window['objects']
    assert len(window['evidence']) == 2


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


if __name__ == '__main__':
    test_weekly_report_builds_focus_windows_from_repeated_signals()
    test_weekly_report_does_not_promote_single_event_to_focus_window()
    test_monthly_report_does_not_enable_weekly_focus_windows_by_default()
    test_weekly_broad_window_keeps_out_of_scope_events_out()
    print('period report tests passed')
