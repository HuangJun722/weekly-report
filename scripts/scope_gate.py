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

# 阶段1 窄通道词表（仅在行业词缺失时启用，详见 assess_scope 注释）
# Leg A：标题级强政策/监管动作词。刻意窄于 POLICY_TERMS：排除 approval/compliance/license/
# policy 这类高频业务词，避免把"公司琐事里的用词"误当政策事件放行。
REGIONAL_POLICY_TITLE_TERMS = {
    'regulation', 'regulatory', 'regulator', 'legislation', 'antitrust',
    'central bank', 'rules', 'fined', 'fines', 'bars', 'bans', 'ban', 'banned',
    'orders', 'tax', 'taxes', 'taxable', 'tariff', 'tariffs', 'sanction',
    'sanctions', 'tribunal', 'ruling',
    '监管', '法规', '法案', '反垄断', '央行', '牌照', '关税', '制裁',
}
# Leg B：区域性结构/行业变化词。需配合"信源区域可判"（非全球综合源）判定。
REGIONAL_STRUCTURAL_TITLE_TERMS = {
    'changing', 'shift', 'shifts', 'shifted', 'battle', 'consolidation',
    '变革', '转变', '洗牌',
}
# 全球综合源标签：此类信源的标题无法判定具体区域影响，Leg B 不放行。
GLOBAL_REGION_LABELS = {'全球', 'global'}

# 数字产业相关性词。窄通道的保险闸：政策/结构变化事件必须命中这些词才放行，
# 防止"建筑建材税率调整""油气价格战"这类与互联网/AI 产业无关的政策被误收。
DIGITAL_RELEVANCE_TERMS = {
    # 技术/平台
    'tech', 'technology', 'internet', 'online', 'platform', 'app', 'apps',
    'software', 'digital', 'data', 'cloud', 'ai', 'artificial intelligence',
    'model', 'algorithm', 'developer', 'api',
    # 金融科技/支付/数字金融
    'fintech', 'payment', 'payments', 'bank', 'banks', 'banking', 'lending',
    'loan', 'loans', 'credit', 'crypto', 'cryptocurrency', 'blockchain',
    'stablecoin', 'token', 'wallet', 'financial', 'e-wallet', 'neobank',
    # 通信/数字基础设施
    'telecom', 'telecommunications', 'mobile', 'network', 'carrier', '5g',
    'data center', 'datacenter', 'semiconductor', 'chip', 'chips',
    # 电商/内容/游戏
    'ecommerce', 'e-commerce', 'commerce', 'retail', 'marketplace', 'seller',
    'gaming', 'game', 'streaming', 'social', 'creator', 'merchant',
    # 安全/设备
    'cyber', 'cybersecurity', 'cybercrime', 'hacker', 'hackers', 'spyware',
    'device', 'devices', 'gadget', 'smartphone',
    # 初创/风险资本生态
    'startup', 'startups', 'start-up', 'start-ups', 'venture', 'unicorn',
    'esop', 'ipo', 'investor', 'investors', 'funding', 'vc', 'capital gains',
    # 平台治理/用户保护（监管对象多指向平台）
    'teen', 'teens', 'minor', 'minors', 'children', 'online safety',
    'digital payments', 'digital economy',
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
        role in {'official_ir', 'developer_change'}
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
    title_has_policy_action = _matches(title_text, REGIONAL_POLICY_TITLE_TERMS)
    title_has_structural_change = _matches(title_text, REGIONAL_STRUCTURAL_TITLE_TERMS)
    title_has_digital_relevance = _matches(title_text, DIGITAL_RELEVANCE_TERMS)
    title_has_action = _matches(title_text, ACTION_TERMS)
    title_has_quantified_change = (
        _matches(title_text, QUANTIFIED_CHANGE_TERMS)
        or bool(re.search(r'\b\d+(?:\.\d+)?%\b', title_text))
        or bool(re.search(r'[$€£]\s?\d', title_text))
    )
    # 信源合约不做数字产业词复核：对 L4 泛行业源（如 Retail Dive）的防御
    # 在登记层（source_tier 背书 + scope_industries 必须真实垂直），不在闸门叠
    # 词表——实测 digital 词表复核一周误杀 46 条（Grab/SEA/Adyen 财报、Kakao
    # IPO 等合法信号标题无 digital 词），宽词表同样漏（'spending''retail' 会让
    # 传统零售混入）。混入的泛行业源由周度审计扫出（contract 放行 + 内容与
    # 数字产业无关 → 告警），登记纪律 + 事后审计优于闸门猜词。
    source_confirmed = (
        not direct_industries
        and bool(contracted_industries)
        and _source_contract_can_confirm(event)
        and (has_action or has_industry_change or bool(event.get('is_company')))
    )

    industries = direct_industries or (contracted_industries if source_confirmed else [])
    if not industries:
        # 阶段1 窄通道：行业词缺失时抢救区域政策/监管/结构变化信号。
        # 两条腿都必须命中数字产业相关性词（DIGITAL_RELEVANCE_TERMS），
        # 防"建筑建材税率调整"这类与互联网/AI 产业无关的政策被误收。
        # Leg A：标题命中强政策/监管动作词 → 政策变化事件。
        #   政策词本身足够强，不作区域限定（"欧盟出台 AI 新规"这类全球源报道也值得保留）。
        # Leg B：标题命中结构/行业变化词，且信源区域可判（非全球综合源）→ 行业变化事件。
        if (title_has_policy_action and title_has_digital_relevance) or event_type == 'regional_policy':
            return {
                'status': 'qualified',
                'reason': 'scope_regional_policy_title',
                'layer': 'regional_policy',
                'industries': [],
                'match_basis': 'regional_policy_title',
            }
        region = (event.get('region') or '').strip()
        if (
            region
            and region not in GLOBAL_REGION_LABELS
            and title_has_structural_change
            and title_has_digital_relevance
        ):
            return {
                'status': 'qualified',
                'reason': 'scope_regional_structural_change',
                'layer': 'industry_change',
                'industries': [],
                'match_basis': 'regional_structural_title',
            }
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
