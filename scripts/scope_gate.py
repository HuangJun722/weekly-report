"""Scope-first admission rules for the intelligence pipeline.

Source credibility and event importance are separate concerns. This module
answers the earlier question: does the fact belong to one of the configured
AI/internet industries, and does it describe a meaningful change?
"""

import re


TARGET_INDUSTRIES = {
    'ai_infra': {
        'ai', 'artificial intelligence', 'llm', 'model', 'inference', 'agent',
        'gpu', 'compute', 'data center', 'datacenter', 'ai infrastructure',
        'ai infra', 'machine learning', '人工智能', '大模型', '模型', '推理',
        '智能体', '算力', '数据中心',
    },
    'payments': {
        'payment', 'payments', 'fintech', 'wallet', 'bnpl', 'remittance',
        'acquiring', 'checkout', 'digital bank', 'banking app', 'card network',
        '支付', '金融科技', '钱包', '跨境汇款', '收单', '数字银行',
    },
    'commerce': {
        'ecommerce', 'e-commerce', 'commerce', 'marketplace', 'merchant',
        'seller', 'retail platform', 'shopping platform', '电商', '商户',
        '卖家', '零售平台', '交易平台',
    },
    'cloud_saas_developer': {
        'saas', 'enterprise software', 'cloud', 'developer', 'api', 'sdk',
        'database', 'serverless', 'changelog', 'software platform',
        '企业软件', '云服务', '开发者', '接口', '数据库',
    },
    'security': {
        'cybersecurity', 'security platform', 'identity', 'authentication',
        'fraud prevention', '网络安全', '身份认证', '风控平台',
    },
    'ads_social': {
        'advertising', 'adtech', 'ads platform', 'social media',
        'creator platform', 'marketing automation', '广告', '广告技术',
        '社交平台', '创作者平台', '营销自动化',
    },
    'gaming_content': {
        'gaming', 'video game', 'mobile game', 'games industry', 'game studio',
        'streaming platform', 'app store', '游戏', '手游', '流媒体', '应用商店',
    },
    'local_services_logistics': {
        'super app', 'ride-hailing', 'mobility platform', 'food delivery',
        'delivery platform', 'logistics platform', 'fulfillment', 'last-mile',
        '超级app', '本地生活', '出行平台', '外卖', '物流平台', '履约',
    },
}

POLICY_TERMS = {
    'regulation', 'regulatory', 'regulator', 'policy', 'law', 'legislation',
    'rules', 'license', 'licence', 'approval', 'ban', 'antitrust', 'privacy',
    'data protection', 'compliance', 'central bank', 'competition authority',
    'tax rule', 'tariff', '监管', '政策', '法规', '法案', '牌照', '许可',
    '反垄断', '隐私', '数据保护', '合规', '央行', '税收', '关税',
}

INDUSTRY_CHANGE_TERMS = {
    'market', 'market share', 'revenue', 'gmv', 'volume', 'users', 'user base',
    'adoption', 'growth', 'grows', 'decline', 'forecast', 'benchmark', 'report',
    'spending', 'downloads', 'pricing', 'fee', 'fees', 'commission', 'standard',
    'supply', 'demand', '行业', '市场', '份额', '收入', '交易额', '用户',
    '增长', '下降', '预测', '报告', '支出', '下载量', '定价', '费率', '标准',
}

ACTION_TERMS = {
    'launch', 'launches', 'rolls out', 'introduces', 'changes', 'updates',
    'expands', 'enters', 'partners', 'partnership', 'acquires', 'acquisition',
    'merger', 'invests', 'investment', 'raises', 'funding', 'builds', 'opens',
    'hires', 'appoints', 'restructures', 'shuts down', 'will no longer',
    'restricts', 'requires', 'operates', 'operate', 'integration', 'synergies',
    '发布', '上线', '推出', '调整', '更新', '扩张', '进入', '合作', '收购',
    '并购', '投资', '融资', '建设', '招聘', '任命', '重组', '关闭', '限制',
}

STRONG_EVENT_TYPES = {
    'funding', 'ma', 'earnings', 'strategy', 'partnership',
    'industry_report', 'model_release', 'regional_policy',
}

EDITORIAL_TITLE_PATTERNS = (
    r'^why\b', r'^how\b', r'^what\b', r'^a guide\b', r'^guide\b',
    r'^tips?\b', r'^opinion\b', r'^podcast\b', r'^week in\b',
    r'^review\b', r'^inside\b',
)

EDITORIAL_TITLE_TERMS = {
    'tip', 'tips', 'advice', 'best practice', 'best practices',
}

QUANTIFIED_CHANGE_TERMS = {
    'revenue', 'gmv', 'market share', 'payment volume', 'users', 'user base',
    'subscribers', 'downloads', 'spending', 'growth', 'decline', 'grows',
    'falls', 'rises', 'surpasses', 'hits', 'reaches',
    '收入', '交易额', '市场份额', '支付量', '用户', '订阅', '下载量',
    '支出', '增长', '下降', '突破',
}


def _contains(text, term):
    term = term.lower()
    if re.search(r'[a-z0-9]', term):
        return bool(re.search(rf'(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])', text))
    return term in text


def _matches(text, terms):
    return any(_contains(text, term) for term in terms)


def _fact_text(event):
    parts = [
        event.get('title') or '',
        event.get('display_title') or '',
        event.get('summary_short') or '',
        event.get('source_excerpt') or '',
        event.get('company_name') or '',
        ' '.join(event.get('companies') or []),
    ]
    return ' '.join(parts).lower()


def _title_text(event):
    return ' '.join([
        event.get('title') or '',
        event.get('display_title') or '',
    ]).lower().strip()


def _contract_text(event):
    parts = [
        event.get('vertical') or '',
        event.get('track') or '',
        event.get('entity_focus') or '',
        ' '.join(event.get('scope_industries') or []),
        ' '.join(event.get('signal_types') or []),
        ' '.join(event.get('source_signal_types') or []),
    ]
    return ' '.join(parts).lower()


def matched_industries(event, include_source_contract=False):
    text = _fact_text(event)
    if include_source_contract:
        text = f'{text} {_contract_text(event)}'
    matches = [
        industry
        for industry, terms in TARGET_INDUSTRIES.items()
        if _matches(text, terms)
    ]
    if include_source_contract:
        for industry in event.get('scope_industries') or []:
            if industry in TARGET_INDUSTRIES and industry not in matches:
                matches.append(industry)
    return matches


def _event_type(event):
    types = event.get('event_types') or ['other']
    return types[0] if types else 'other'


def _source_contract_can_confirm(event):
    role = event.get('source_role') or ''
    tier = event.get('source_tier') or ''
    return (
        role in {'industry_vertical', 'official_ir', 'developer_change'}
        or tier in {'L1 官方/IR源', 'L4 垂直赛道精品源'}
        or bool(event.get('is_company'))
    )


def assess_scope(event):
    """Return a deterministic scope decision without using generated analysis."""
    text = _fact_text(event)
    title_text = _title_text(event)
    direct_industries = matched_industries(event)
    contracted_industries = matched_industries(event, include_source_contract=True)
    event_type = _event_type(event)
    has_policy = _matches(text, POLICY_TERMS)
    has_industry_change = _matches(text, INDUSTRY_CHANGE_TERMS)
    has_action = _matches(text, ACTION_TERMS) or event_type in STRONG_EVENT_TYPES
    title_has_policy = _matches(title_text, POLICY_TERMS)
    title_has_action = _matches(title_text, ACTION_TERMS)
    title_has_quantified_change = (
        _matches(title_text, QUANTIFIED_CHANGE_TERMS)
        or bool(re.search(r'\b\d+(?:\.\d+)?%\b', title_text))
        or bool(re.search(r'[$€£]\s?\d', title_text))
    )
    source_confirmed = (
        not direct_industries
        and bool(contracted_industries)
        and _source_contract_can_confirm(event)
        and (has_action or has_industry_change)
    )

    industries = direct_industries or (contracted_industries if source_confirmed else [])
    if not industries:
        return {
            'status': 'filtered',
            'reason': 'scope_no_target_industry',
            'layer': 'unclassified',
            'industries': [],
            'match_basis': 'none',
        }

    is_editorial = (
        any(re.search(pattern, title_text) for pattern in EDITORIAL_TITLE_PATTERNS)
        or _matches(title_text, EDITORIAL_TITLE_TERMS)
    )
    if is_editorial and not (title_has_policy or title_has_action or title_has_quantified_change):
        return {
            'status': 'candidate',
            'reason': 'scope_editorial_without_explicit_change',
            'layer': 'industry_change',
            'industries': industries,
            'match_basis': 'fact' if direct_industries else 'source_contract',
        }

    if not (has_policy or has_industry_change or has_action):
        return {
            'status': 'candidate',
            'reason': 'scope_change_not_explicit',
            'layer': 'industry_change',
            'industries': industries,
            'match_basis': 'fact' if direct_industries else 'source_contract',
        }

    if has_policy:
        layer = 'regional_policy'
    elif has_industry_change and not event.get('is_company'):
        layer = 'industry_change'
    else:
        layer = 'company_action'

    return {
        'status': 'qualified',
        'reason': 'scope_target_change',
        'layer': layer,
        'industries': industries,
        'match_basis': 'fact' if direct_industries else 'source_contract',
    }


def apply_scope_contract(event):
    assessment = assess_scope(event)
    event['scope_enforced'] = True
    event['scope_status'] = assessment['status']
    event['scope_reason'] = assessment['reason']
    event['scope_layer'] = assessment['layer']
    event['scope_industries'] = assessment['industries']
    event['scope_match_basis'] = assessment['match_basis']
    if event.get('region'):
        event['scope_regions'] = [event['region']]
    return event


def scope_filter_reason(event):
    if not event.get('scope_enforced') or not event.get('scope_status'):
        return ''
    if event['scope_status'] == 'qualified':
        return ''
    return event.get('scope_reason') or 'scope_not_qualified'


def is_scope_qualified(event):
    """Legacy events remain compatible until they are explicitly reprocessed."""
    return not event.get('scope_enforced') or event.get('scope_status') == 'qualified'
