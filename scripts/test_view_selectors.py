from view_selectors import (
    select_company_quality_events,
    select_feed_events,
    select_homepage_events,
    select_mature_main_date,
    select_review_events,
)


def base_event(**overrides):
    event = {
        'title': 'Example raises $100M to expand AI infrastructure',
        'url': 'https://example.com/article',
        'source': 'TechCrunch',
        'source_tier': 'L2 垂直交易源',
        'event_types': ['funding'],
        'score': 7,
        'reason': '大额融资显示AI基础设施预算窗口打开',
        'impact': '云服务商、AI基础设施供应商',
        'summary_short': 'Example获$100M融资扩张AI基础设施',
        'date': '2026-05-31',
    }
    event.update(overrides)
    return event


def test_homepage_selector_allows_low_score_non_google_signal():
    event = base_event(score=2)
    selected = select_homepage_events([event], '2026-05-31')
    assert selected == [event]


def test_feed_selector_falls_back_to_latest_high_value_date():
    low_today = base_event(score=2, date='2026-06-01')
    high_yesterday = base_event(score=7, date='2026-05-31')
    feed_events, feed_date = select_feed_events([low_today], [low_today, high_yesterday])
    assert feed_events == [high_yesterday]
    assert feed_date == '2026-05-31'


def test_company_quality_selector_is_independent_from_rss_high_value():
    company_signal = base_event(
        source='Google News',
        source_tier='L5 Google News 补漏源',
        url='https://news.google.com/rss/articles/example',
        company_name='U-NEXT',
        is_company=True,
        event_types=['ma'],
        score=3,
    )
    assert select_company_quality_events([company_signal]) == [company_signal]


def test_mature_date_selector_skips_thin_latest_batch():
    events_by_date = {
        '2026-06-01': [base_event(date='2026-06-01')],
        '2026-05-31': [
            base_event(date='2026-05-31', url='https://example.com/a'),
            base_event(date='2026-05-31', url='https://example.com/b'),
            base_event(date='2026-05-31', url='https://example.com/c'),
        ],
    }
    visible = events_by_date['2026-06-01'] + events_by_date['2026-05-31']
    main_date, latest_date, latest_count, notice = select_mature_main_date(
        ['2026-06-01', '2026-05-31'],
        visible,
        events_by_date,
    )
    assert main_date == '2026-05-31'
    assert latest_date == '2026-06-01'
    assert latest_count == 1
    assert notice


def test_review_selector_keeps_real_google_org_action_out_of_main():
    event = base_event(
        title='Naver Eyes Baemin Acquisition to Accelerate Super App Strategy',
        source='Google News',
        source_tier='L5 Google News 补漏源',
        url='https://news.google.com/rss/articles/example',
        company_name='Naver',
        is_company=True,
        event_types=['ma'],
        score=5,
    )
    assert select_review_events([event]) == [event]


if __name__ == '__main__':
    test_homepage_selector_allows_low_score_non_google_signal()
    test_feed_selector_falls_back_to_latest_high_value_date()
    test_company_quality_selector_is_independent_from_rss_high_value()
    test_mature_date_selector_skips_thin_latest_batch()
    test_review_selector_keeps_real_google_org_action_out_of_main()
    print('view selector tests passed')
