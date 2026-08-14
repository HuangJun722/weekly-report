"""Evidence-backed weekly themes and cross-week monthly trends."""

import re
from collections import Counter
from datetime import datetime, timedelta

try:
    from evidence_atoms import build_evidence_atoms, can_promote_to_narrative, evidence_independence
    from event_value import classify_bd_priority, event_score, event_type, is_google_news_event, signal_score
    from internet_relevance import is_mainline_internet_event
except ImportError:
    from scripts.evidence_atoms import build_evidence_atoms, can_promote_to_narrative, evidence_independence
    from scripts.event_value import classify_bd_priority, event_score, event_type, is_google_news_event, signal_score
    from scripts.internet_relevance import is_mainline_internet_event


THEMES = {
    'ai_infra': ('AI与云基础设施', ('ai', 'agent', 'model', 'gpu', 'cloud', 'data center', 'datacenter', 'compute', 'inference', '算力', '云', '模型')),
    'payments': ('支付与金融科技', ('payment', 'fintech', 'wallet', 'bank', 'bnpl', 'checkout', 'remittance', '支付', '金融科技', '银行', '钱包')),
    'commerce': ('电商、商户与物流', ('commerce', 'ecommerce', 'marketplace', 'merchant', 'seller', 'logistics', 'fulfillment', '电商', '商户', '物流')),
    'developer': ('开发者与平台生态', ('api', 'sdk', 'developer', 'changelog', 'release note', 'platform', '开发者', '接口', '平台更新')),
    'expansion': ('区域扩张与合作', ('expansion', 'new market', 'launches in', 'partnership', 'partner', 'regional', '扩张', '进入', '合作', '生态')),
    'operations': ('经营与组织变化', ('earnings', 'revenue', 'profit', 'margin', 'hiring', 'jobs', 'layoff', '营收', '利润', '招聘', '组织')),
    'compliance': ('合规与安全', ('compliance', 'regulatory', 'license', 'security', 'privacy', 'risk', '合规', '监管', '牌照', '安全', '风控')),
}

COUNTRY_REGIONS = {
    '亚太': ('india', 'indonesia', 'singapore', 'malaysia', 'thailand', 'vietnam', 'japan', 'korea', '印度', '印尼', '新加坡', '马来西亚', '日本', '韩国'),
    '欧洲': ('europe', 'uk ', 'britain', 'germany', 'france', 'poland', '英国', '德国', '法国', '欧洲'),
    '中东': ('uae', 'dubai', 'saudi', 'qatar', 'middle east', '阿联酋', '迪拜', '沙特', '中东'),
    '非洲': ('africa', 'nigeria', 'kenya', 'egypt', 'south africa', '非洲', '尼日利亚', '肯尼亚', '埃及'),
    '拉美': ('latin america', 'brazil', 'mexico', 'argentina', 'colombia', '拉美', '巴西', '墨西哥', '阿根廷', '哥伦比亚'),
}


def _text(event):
    return ' '.join([
        event.get('title') or '', event.get('summary_short') or '',
        event.get('reason') or '', event.get('trend_topic') or '',
        ' '.join(event.get('signal_taxonomy') or []),
    ]).lower()


def theme_key(event):
    text = _text(event)
    scores = {
        key: sum(1 for term in terms if term in text)
        for key, (_, terms) in THEMES.items()
    }
    best, count = max(scores.items(), key=lambda item: item[1])
    if count:
        return best
    if event_type(event) == 'earnings':
        return 'operations'
    return ''


def resolved_region(event, entity_regions=None):
    entity_regions = entity_regions or {}
    company = event.get('company_name') or ''
    if company in entity_regions:
        return entity_regions[company]
    text = f" {_text(event)} "
    for region, terms in COUNTRY_REGIONS.items():
        if any(term in text for term in terms):
            return region
    if event.get('region_basis') in {'entity', 'title', 'article'}:
        return event.get('region') or '全球'
    return '全球'


def _eligible(events):
    return [
        event for event in events
        if event_type(event) != 'other'
        and is_mainline_internet_event(event)
        and not event.get('needs_repair')
        and not event.get('quality_flags')
    ]


def _event_rank(event):
    return (
        {'高': 3, '中': 2, '观察': 1}.get(classify_bd_priority(event), 0),
        event_score(event),
        signal_score(event, 'attention_score'),
        (event.get('date') or '')[:10],
    )


def _representative_events(atoms, limit=5):
    events = []
    for atom in atoms:
        ranked = sorted(atom.get('events') or [], key=_event_rank, reverse=True)
        if ranked:
            events.append(ranked[0])
    return sorted(events, key=_event_rank, reverse=True)[:limit]


def _evidence(event):
    return {
        'title': event.get('display_title') or event.get('summary_short') or event.get('title') or '',
        'url': event.get('url') or '#',
        'date': (event.get('date') or '')[:10],
        'source': event.get('display_source') or event.get('source') or '公开来源',
        'type': event.get('insight_label') or event_type(event),
    }


def build_weekly_themes(events, entity_regions=None, limit=6):
    grouped = {}
    for event in _eligible(events):
        key = theme_key(event)
        if key:
            grouped.setdefault(key, []).append(event)
    themes = []
    for key, grouped_events in grouped.items():
        atoms = build_evidence_atoms(grouped_events)
        if len(atoms) < 2 or not can_promote_to_narrative(atoms):
            continue
        stats = evidence_independence(atoms)
        representatives = _representative_events(atoms)
        regions = Counter(resolved_region(event, entity_regions) for event in representatives)
        region = regions.most_common(1)[0][0] if regions else '全球'
        companies = []
        for atom in atoms:
            for company in atom.get('companies') or []:
                if company not in companies:
                    companies.append(company)
        label = THEMES[key][0]
        why = representatives[0].get('reason') or representatives[0].get('summary_short') or ''
        change_brief = [
            {
                'title': e.get('display_title') or e.get('title') or '',
                'date': (e.get('date') or '')[:10],
                'type': e.get('insight_label') or event_type(e),
            }
            for e in representatives[:4]
        ]
        themes.append({
            'key': key,
            'title': label,
            'region': region,
            'objects': '、'.join(companies[:4]) if companies else '多个市场对象',
            'direction': label,
            'confidence': '高' if stats['atom_count'] >= 4 and stats['source_count'] >= 2 else '中',
            'evidence_count': stats['atom_count'],
            'action': '继续跟踪对象动作和第二来源确认',
            'why': why,
            'change_brief': change_brief,
            'evidence': [_evidence(event) for event in representatives[:4]],
            'score': stats['atom_count'] * 4 + stats['source_count'] * 2 + stats['company_count'],
        })
    themes.sort(key=lambda row: row['score'], reverse=True)
    return themes[:limit]


def _week_key(event):
    try:
        date_value = datetime.strptime((event.get('date') or '')[:10], '%Y-%m-%d')
    except ValueError:
        return ''
    year, week, _ = date_value.isocalendar()
    return f'{year}-W{week:02d}'


def _window_stats(all_events, start, end, key):
    """窗口内某主题的 Evidence Atom 数与合格事件总数（覆盖率代理）。

    total_eligible 反映该窗口采集/覆盖了多少合格事实：窗口间总事件数差异
    主要来自信源增减或采集波动，用它做覆盖率校正，避免"新增信源"被误判为
    行业升温，也避免"信源失效"掩盖真实增长。
    """
    in_window = [
        event for event in _eligible(all_events)
        if start <= (event.get('date') or '')[:10] <= end
    ]
    total_eligible = len(in_window)
    if total_eligible == 0:
        return 0, 0
    theme_events = [event for event in in_window if theme_key(event) == key]
    atoms = build_evidence_atoms(theme_events)
    return len(atoms), total_eligible


def build_monthly_trends(all_events, start_date, end_date, entity_regions=None, limit=6):
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    span = (end - start).days + 1
    # 基线 = 当前窗口之前 3 个同长度窗口（足够判断"相对过去是否真的变化"）
    prior_windows = []
    window_end = start - timedelta(days=1)
    for _ in range(3):
        wstart = window_end - timedelta(days=span - 1)
        prior_windows.append((wstart.strftime('%Y-%m-%d'), window_end.strftime('%Y-%m-%d')))
        window_end = wstart - timedelta(days=1)

    current_groups = {}
    current_eligible = [
        event for event in _eligible(all_events)
        if start_date <= (event.get('date') or '')[:10] <= end_date
    ]
    current_total = len(current_eligible)
    for event in current_eligible:
        key = theme_key(event)
        if key:
            current_groups.setdefault(key, []).append(event)
    trends = []
    for key, grouped_events in current_groups.items():
        weeks = {_week_key(event) for event in grouped_events if _week_key(event)}
        atoms = build_evidence_atoms(grouped_events)
        if len(weeks) < 2 or len(atoms) < 3 or not can_promote_to_narrative(atoms):
            continue
        current_count = len(atoms)

        # 基线：有数据的先前窗口均值（覆盖率为 0 的窗口跳过，无法归一化）
        base_entries = [
            _window_stats(all_events, ws, we, key)
            for ws, we in prior_windows
        ]
        base_entries = [(c, t) for c, t in base_entries if t > 0]
        has_baseline = bool(base_entries)
        if has_baseline:
            avg_total = sum(t for _, t in base_entries) / len(base_entries)
            baseline_count = sum(c for c, _ in base_entries) / len(base_entries)
            coverage_ratio = current_total / avg_total if avg_total else 1.0
            # 覆盖率校正：只在当前窗口总事件量相对基线明显变化（信源增减/采集波动）
            # 时校正，并钳制修正幅度，避免小样本被过度放大。
            if coverage_ratio < 0.8 or coverage_ratio > 1.25:
                correction = min(max(avg_total / current_total, 0.75), 1.30) if current_total else 1.0
            else:
                correction = 1.0
            current_adj = current_count * correction
            if current_adj >= baseline_count + 2 and (current_adj / baseline_count if baseline_count else 2) >= 1.25:
                change = '升温'
            elif current_adj <= baseline_count - 2 and (current_adj / baseline_count if baseline_count else 0) <= 0.75:
                change = '降温'
            else:
                change = '延续'
        else:
            baseline_count = 0
            coverage_ratio = 1.0
            current_adj = current_count
            change = '新增'

        representatives = _representative_events(atoms)
        regions = Counter(resolved_region(event, entity_regions) for event in representatives)
        region = regions.most_common(1)[0][0] if regions else '全球'
        label = THEMES[key][0]
        delta = round(current_adj - baseline_count, 1)
        comparison = f'较基线 {delta:+.1f} 个事实' if has_baseline else '前一周期未形成同类证据'
        trends.append({
            'key': key,
            'name': f'{label}{change}',
            'title': f'{label}{change}',
            'region': region,
            'change': change,
            'count': current_count,
            'week_count': len(weeks),
            'previous_count': round(baseline_count, 1),
            'baseline_count': round(baseline_count, 1),
            'coverage_ratio': round(coverage_ratio, 3),
            'summary': f'本月在 {len(weeks)} 个周次持续出现，共 {current_count} 个独立事实；{comparison}。',
            'evidence': [_evidence(event) for event in representatives[:4]],
            'score': current_count * 4 + len(weeks) * 3 + max(round(current_adj - baseline_count), 0),
        })
    trends.sort(key=lambda row: row['score'], reverse=True)
    return trends[:limit]

