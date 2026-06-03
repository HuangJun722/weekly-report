"""Build conservative signal clusters from stored intelligence events.

Signal clusters are a display-layer object: they group evidence around a
watch window without claiming that a commercial opportunity is already proven.
"""

import re
from collections import defaultdict
from datetime import datetime, timedelta

try:
    from event_value import (
        classify_bd_priority,
        event_score,
        event_type,
        is_google_news_event,
        needs_quality_review,
    )
    from internet_relevance import is_mainline_internet_event
except ImportError:
    from scripts.event_value import (
        classify_bd_priority,
        event_score,
        event_type,
        is_google_news_event,
        needs_quality_review,
    )
    from scripts.internet_relevance import is_mainline_internet_event


CLUSTER_TYPE_LABELS = {
    'funding': '资金进入窗口',
    'ma': '整合窗口',
    'earnings': '经营拐点窗口',
    'expansion': '扩张窗口',
    'partnership': '生态合作窗口',
    'payment': '支付升级窗口',
    'ai': 'AI建设窗口',
    'infra': '基础设施建设窗口',
    'compliance': '合规窗口',
    'org': '组织变化窗口',
    'strategy': '战略调整窗口',
}

CLUSTER_KEYWORDS = [
    ('payment', ['支付', 'fintech', 'wallet', 'remittance', 'bank', 'bnpl', 'acquiring']),
    ('ai', ['ai', '人工智能', '模型', 'agent', 'inference', 'gpu']),
    ('infra', ['cloud', '云', 'infra', 'data center', '数据中心', 'chip', '算力']),
    ('compliance', ['监管', '牌照', 'license', 'regulation', '合规']),
    ('expansion', ['扩张', '出海', '市场', 'localization', 'launch', '进入']),
    ('partnership', ['合作', 'partner', '生态', 'alliance', 'integrat']),
    ('org', ['招聘', 'hiring', 'layoff', '高管', 'exec', '组织']),
]

TYPE_TO_CLUSTER = {
    'funding': 'funding',
    'ma': 'ma',
    'earnings': 'earnings',
    'strategy': 'strategy',
}

SOURCE_CONFIDENCE = {
    'L1 官方/IR源': 3,
    'L2 垂直交易源': 2,
    'L3 区域生态源': 2,
    'L4 垂直赛道精品源': 2,
    'L4 深度趋势源': 1,
    'L5 Google News 补漏源': 0,
}


def _event_date(event):
    return (event.get('date') or '')[:10]


def _parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except (TypeError, ValueError):
        return None


def _date_range(end_date, days):
    end = _parse_date(end_date)
    if not end:
        return set()
    return {
        (end - timedelta(days=offset)).strftime('%Y-%m-%d')
        for offset in range(days)
    }


def _flatten_events(events):
    if isinstance(events, dict):
        flattened = []
        for group in events.values():
            flattened.extend(group or [])
        return flattened
    return list(events or [])


def _event_text(event):
    return ' '.join([
        event.get('title') or '',
        event.get('summary_short') or '',
        event.get('reason') or '',
        event.get('impact') or '',
        event.get('opportunity_direction') or '',
        ' '.join(event.get('bd_triggers') or []),
    ]).lower()


def _cluster_type(event):
    hard_type = event_type(event)
    if hard_type in {'funding', 'ma', 'earnings'}:
        return TYPE_TO_CLUSTER[hard_type]
    text = _event_text(event)
    for key, keywords in CLUSTER_KEYWORDS:
        if any(keyword.lower() in text for keyword in keywords):
            return key
    return TYPE_TO_CLUSTER.get(hard_type, 'strategy')


def _event_companies(event):
    companies = []
    if event.get('company_name'):
        companies.append(event['company_name'])
    for company in event.get('companies') or []:
        if company and company not in companies:
            companies.append(company)
    return companies


def _event_subject(event):
    companies = _event_companies(event)
    if companies:
        return companies[0]
    title = event.get('display_title') or event.get('summary_short') or event.get('title') or ''
    cleaned = re.sub(r'[^\w\u4e00-\u9fff]+', ' ', title).strip()
    return ' '.join(cleaned.split()[:4]) or '区域信号'


def _cluster_topic(event):
    topic = (event.get('trend_topic') or '').strip()
    if topic:
        return re.sub(r'\s*[—-]\s*(欧洲|亚太|中东|非洲|拉美|全球|中资).*$', '', topic).strip()
    companies = _event_companies(event)
    if companies:
        return companies[0]
    direction = (event.get('opportunity_direction') or '').split('/')[0].strip()
    if direction and direction != '持续观察':
        return direction
    return _event_subject(event)


def _source_signal_label(event):
    tier = event.get('source_tier') or ''
    if tier == 'L1 官方/IR源':
        return '官方动作'
    if tier == 'L2 垂直交易源':
        return '行业交易'
    if tier == 'L3 区域生态源':
        return '区域生态'
    if tier.startswith('L4'):
        return '垂类信号'
    if is_google_news_event(event):
        return '补漏来源'
    return '公开信号'


def _short_text(text, max_len=62):
    text = re.sub(r'\s+', ' ', (text or '')).strip()
    return text if len(text) <= max_len else text[:max_len].rstrip() + '...'


def _evidence_title(event):
    return _short_text(
        event.get('display_title') or event.get('summary_short') or event.get('reason') or event.get('title') or ''
    )


def _action_for_cluster(cluster_type):
    if cluster_type == 'funding':
        return '观察后续采购、扩张和合作信号'
    if cluster_type == 'ma':
        return '加入观察名单，跟踪整合后的合作入口'
    if cluster_type == 'earnings':
        return '观察预算变化和管理层表态'
    if cluster_type == 'payment':
        return '梳理支付、商户和合规合作链路'
    if cluster_type == 'ai':
        return '关注AI基础设施、模型部署和安全治理需求'
    if cluster_type == 'infra':
        return '跟踪云、数据中心和供应链建设信号'
    if cluster_type == 'compliance':
        return '观察牌照、监管和本地合规服务需求'
    if cluster_type == 'expansion':
        return '关注本地化、渠道和伙伴招募信号'
    if cluster_type == 'partnership':
        return '观察生态伙伴、API和联合方案入口'
    return '加入观察名单，等待二次确认信号'


def _eligibility_flags(events):
    companies = {company for event in events for company in _event_companies(event)}
    dates = {_event_date(event) for event in events if _event_date(event)}
    regions = {event.get('region') for event in events if event.get('region')}
    high_sources = [
        event for event in events
        if SOURCE_CONFIDENCE.get(event.get('source_tier') or '', 0) >= 2
    ]
    types = {event_type(event) for event in events}
    text = ' '.join(_event_text(event) for event in events)
    flags = []
    if len(events) >= 2:
        flags.append('多个事件')
    if len(companies) >= 2:
        flags.append('多个对象')
    if len(dates) >= 2:
        flags.append('连续出现')
    if len(regions) == 1 and len(events) >= 2:
        flags.append('影响区域')
    if types & {'funding', 'earnings'} or any(term in text for term in ['budget', '预算', '融资', '$']):
        flags.append('影响预算')
    if types & {'ma', 'strategy', 'earnings'} or any(term in text for term in ['招聘', 'hiring', '高管', '整合']):
        flags.append('影响组织')
    if len(high_sources) >= 1:
        flags.append('可信信源')
    return flags


def _confidence(flags, events):
    high_priority = sum(1 for event in events if classify_bd_priority(event) == '高')
    non_google = sum(1 for event in events if not is_google_news_event(event))
    if len(flags) >= 4 and (high_priority or non_google >= 2):
        return '高'
    if len(flags) >= 3:
        return '中'
    return '观察'


def _cluster_event_rank(event):
    priority_rank = {'高': 3, '中': 2, '观察': 1}
    return (
        priority_rank.get(classify_bd_priority(event), 0),
        event_score(event),
        _event_date(event),
    )


def _cluster_title(region, cluster_type, events, topic):
    label = CLUSTER_TYPE_LABELS.get(cluster_type, '关注窗口')
    companies = []
    for event in events:
        for company in _event_companies(event):
            if company not in companies:
                companies.append(company)
    if len(companies) >= 2:
        subject = ' / '.join(companies[:3])
    elif companies:
        subject = companies[0]
    elif topic:
        subject = topic
    else:
        subject = region or '多地区'
    return f"{subject}{label}"


def _build_cluster(region, cluster_type, topic, events, focus_date):
    events = sorted(events, key=_cluster_event_rank, reverse=True)
    flags = _eligibility_flags(events)
    companies = []
    for event in events:
        for company in _event_companies(event):
            if company not in companies:
                companies.append(company)
    source_labels = []
    for event in events:
        label = _source_signal_label(event)
        if label not in source_labels:
            source_labels.append(label)
    evidence = [
        {
            'title': _evidence_title(event),
            'url': event.get('url') or '#',
            'date': _event_date(event),
            'source': event.get('display_source') or event.get('source') or '公开来源',
            'type': event.get('insight_label') or event_type(event),
        }
        for event in events[:3]
    ]
    cluster = {
        'title': _cluster_title(region, cluster_type, events, topic),
        'region': region or '多地区',
        'topic': topic,
        'cluster_type': cluster_type,
        'type_label': CLUSTER_TYPE_LABELS.get(cluster_type, '关注窗口'),
        'companies': companies[:5],
        'signals': source_labels[:4],
        'evidence': evidence,
        'evidence_events': events[:3],
        'evidence_count': len(events),
        'watch_window': '未来7天' if any(_event_date(e) == focus_date for e in events) else '未来30天',
        'confidence': _confidence(flags, events),
        'why': _short_text(events[0].get('reason') or events[0].get('summary_short') or events[0].get('title') or ''),
        'action': _action_for_cluster(cluster_type),
        'eligibility': flags,
        'has_focus_date': any(_event_date(e) == focus_date for e in events),
        'score': (
            len(flags) * 10
            + len(events) * 2
            + sum(event_score(event) for event in events[:3])
            + (8 if any(_event_date(e) == focus_date for e in events) else 0)
        ),
    }
    return cluster


def build_signal_clusters(events, focus_date, days=7, limit=3):
    events = _flatten_events(events)
    selected_dates = _date_range(focus_date, days)
    candidates = [
        event for event in events
        if _event_date(event) in selected_dates
        and event_type(event) != 'other'
        and not needs_quality_review(event)
        and is_mainline_internet_event(event)
    ]

    grouped = defaultdict(list)
    for event in candidates:
        region = event.get('region') or '多地区'
        topic = _cluster_topic(event)
        grouped[(region, _cluster_type(event), topic)].append(event)

    clusters = []
    for (region, cluster_type, topic), grouped_events in grouped.items():
        if len(grouped_events) < 2:
            continue
        flags = _eligibility_flags(grouped_events)
        if len(flags) < 2:
            continue
        if all(is_google_news_event(event) for event in grouped_events):
            continue
        clusters.append(_build_cluster(region, cluster_type, topic, grouped_events, focus_date))

    clusters.sort(
        key=lambda cluster: (
            cluster['has_focus_date'],
            cluster['confidence'] == '高',
            cluster['score'],
            cluster['evidence_count'],
        ),
        reverse=True,
    )
    return clusters[:limit]
