from event_value import (
    classify_bd_priority,
    is_high_value_event,
    should_show_in_main_list,
    should_show_in_review,
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
    }
    event.update(overrides)
    return event


def test_low_score_signal_is_not_high():
    event = base_event(score=2)
    assert classify_bd_priority(event) == '观察'
    assert not is_high_value_event(event)
    assert not should_show_in_main_list(event)


def test_google_news_company_low_signal_stays_out():
    event = base_event(
        title='K-pop singer to star in Rakuten Viki romcom',
        url='https://news.google.com/rss/articles/example',
        source='Google News',
        source_tier='L5 Google News 补漏源',
        company_name='Rakuten',
        is_company=True,
        score=5,
    )
    assert classify_bd_priority(event) == '观察'
    assert not should_show_in_main_list(event)
    assert not should_show_in_review(event)


def test_google_news_real_org_action_can_enter_review_not_main():
    event = base_event(
        title='Naver Eyes Baemin Acquisition to Accelerate Super App Strategy',
        url='https://news.google.com/rss/articles/example',
        source='Google News',
        source_tier='L5 Google News 补漏源',
        company_name='Naver',
        is_company=True,
        event_types=['ma'],
        score=5,
    )
    assert classify_bd_priority(event) == '中'
    assert not should_show_in_main_list(event)
    assert should_show_in_review(event)


def test_non_google_strong_signal_is_high_value():
    event = base_event(score=5)
    assert classify_bd_priority(event) == '高'
    assert is_high_value_event(event)
    assert should_show_in_main_list(event)


if __name__ == '__main__':
    test_low_score_signal_is_not_high()
    test_google_news_company_low_signal_stays_out()
    test_google_news_real_org_action_can_enter_review_not_main()
    test_non_google_strong_signal_is_high_value()
    print('event_value tests passed')
