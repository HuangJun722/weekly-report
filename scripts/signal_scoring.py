"""Shared content typing and multi-axis signal scoring.

The score is intentionally separate from scope admission. Scope decides
whether an item belongs to the station; these scores decide how it should be
ordered and how useful it may be for a later trend view.
"""

import re


CONTENT_TYPES = {
    'company_action',
    'industry_report',
    'model_release',
    'regional_policy',
    'capital_event',
    'generic_industry_change',
}

REPORT_TERMS = {
    'report', 'research', 'forecast', 'market outlook', 'market map',
    'benchmark', 'market share', 'market size', '行业报告', '研报',
    '市场预测', '市场份额', '市场规模', '基准测试',
}

MODEL_TERMS = {
    'foundation model', 'language model', 'large language model',
    'multimodal model', 'ai model', 'model release', 'model launches',
    'open-source model', 'open source model', '模型发布', '大模型',
    '多模态模型', '开源模型',
}

MODEL_ACTION_TERMS = {
    'launch', 'launches', 'released', 'release', 'unveils', 'available',
    '推出', '发布', '上线', '开放',
}

ACTION_TERMS = {
    'launch', 'launches', 'released', 'release', 'expands', 'expansion',
    'enters', 'partnership', 'partners', 'investment', 'invests', 'builds',
    'hiring', 'hires', 'restructures', '推出', '发布', '上线', '扩张',
    '进入', '合作', '投资', '建设', '招聘', '重组',
}

QUANTIFIED_TERMS = {
    'market share', 'market size', 'growth', 'decline', 'forecast',
    'revenue', 'users', 'gmv', 'volume', 'benchmark', 'percent', '%',
    '份额', '规模', '增长', '下降', '预测', '收入', '用户', '交易额',
    '基准',
}


def _text(event):
    return ' '.join([
        event.get('title') or '',
        event.get('display_title') or '',
        event.get('summary_short') or '',
        event.get('source_excerpt') or '',
        event.get('vertical') or '',
        event.get('track') or '',
    ]).lower()


def _has(text, terms):
    for term in terms:
        term = term.lower()
        if term == '%':
            if '%' in text:
                return True
        elif re.search(r'[a-z0-9]', term):
            if re.search(rf'(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])', text):
                return True
        elif term in text:
            return True
    return False


def infer_content_type(event):
    """Return a stable content profile without using generated analysis."""
    explicit = event.get('content_type')
    if explicit in CONTENT_TYPES:
        return explicit

    source_type = (event.get('source_type') or '').lower()
    source_signals = ' '.join(event.get('source_signal_types') or []).lower()
    text = _text(event)
    event_type = (event.get('event_types') or ['other'])[0]

    if source_type in {'research_report', 'research', 'report'}:
        return 'industry_report'
    if 'industry_analysis' in source_signals and _has(text, REPORT_TERMS):
        return 'industry_report'
    if _has(text, MODEL_TERMS) and _has(text, MODEL_ACTION_TERMS):
        return 'model_release'
    if event.get('scope_layer') == 'regional_policy':
        return 'regional_policy'
    if event_type in {'funding', 'ma', 'earnings'}:
        return 'capital_event'
    if event.get('is_company') or event.get('company_name'):
        return 'company_action'
    if event_type in {'strategy', 'partnership'}:
        return 'generic_industry_change'
    return 'generic_industry_change'


def infer_subject_type(event, content_type=None):
    content_type = content_type or infer_content_type(event)
    explicit = event.get('subject_type')
    if explicit:
        return explicit
    if content_type == 'industry_report':
        return 'report'
    if content_type == 'model_release':
        return 'ai_model'
    if content_type == 'regional_policy':
        return 'region_policy'
    if event.get('is_company') or event.get('company_name'):
        return 'company'
    return 'industry'


def infer_claim_type(event, content_type=None):
    content_type = content_type or infer_content_type(event)
    explicit = event.get('claim_type')
    if explicit:
        return explicit
    if content_type == 'industry_report':
        return 'institutional_assessment'
    if content_type == 'model_release':
        return 'release_fact' if not _has(_text(event), {'benchmark', '领先', 'best'}) else 'performance_claim'
    if content_type == 'regional_policy':
        return 'policy_change'
    if content_type == 'company_action':
        return 'company_action'
    return 'industry_change'


# ─── 阶段3：信号维度 ──────────────────────────────────────
# content_type 回答"这是什么内容"，signal_type 回答"这代表哪类变化"；
# Event Score（现有 score）回答"公司发生了什么"，signal_change_score 回答
# "这个变化对行业/区域有多重要"。两者正交，Signal 是变化轴，不是事件轴。
SIGNAL_TYPES = ('market', 'policy', 'technology', 'capital', 'consumer', 'company')

# 政策信号用阶段1验证过的窄词表（排除 approval/compliance/license/policy 等
# 高频业务词，避免"公司琐事里的用词"误判为政策变化）。
POLICY_SIGNAL_TERMS = {
    'regulation', 'regulatory', 'regulator', 'legislation', 'antitrust',
    'central bank', 'rules', 'fined', 'fines', 'bars', 'bans', 'ban', 'banned',
    'orders', 'tax', 'taxes', 'taxable', 'tariff', 'tariffs', 'sanction',
    'sanctions', 'tribunal', 'ruling',
    '监管', '法规', '法案', '反垄断', '央行', '牌照', '关税', '制裁',
}
TECHNOLOGY_SIGNAL_TERMS = {
    'foundation model', 'language model', 'large language model',
    'multimodal model', 'ai model', 'model release', 'open-source model',
    'llm', 'inference', 'gpu', 'chip', 'chips', 'semiconductor',
    'data center', 'datacenter', 'compute', 'agent', 'algorithm', '5g',
    '6ghz', 'open ran', 'quantum', 'satellite', 'robotaxi', 'autonomous',
    '大模型', '算力', '芯片', '数据中心', '智能体', '算法', '推理',
}
CAPITAL_SIGNAL_TERMS = {
    'funding', 'raises', 'raised', 'raise', 'series ', 'seed round',
    'valuation', 'acquisition', 'acquires', 'acquisitions', 'merger',
    'ipo', 'investment', 'invests', 'earnings', 'net income', 'profit',
    'revenue growth', 'loan',
    '融资', '收购', '并购', '估值', '上市', '投资', '财报', '净利润',
    '营收增长', '贷款',
}
MARKET_SIGNAL_TERMS = {
    'market share', 'market size', 'consolidation', 'competition', 'pricing',
    'forecast', 'outlook', 'benchmark', 'growth', 'decline', 'shift', 'shifts',
    'changing', 'battle', 'surges', 'rises', 'falls',
    '市场份额', '市场规模', '整合', '竞争', '定价', '预测', '展望', '基准',
    '增长', '下降', '转变', '洗牌', '混战',
}
CONSUMER_SIGNAL_TERMS = {
    'users', 'user base', 'adoption', 'consumer', 'consumers', 'demand',
    'spending', 'downloads', 'subscribers', 'engagement', 'shopping',
    '用户', '消费者', '需求', '支出', '下载量', '订阅', '购物',
}
COMPANY_SIGNAL_TERMS = {
    'launch', 'launches', 'launched', 'partnership', 'partners', 'expands',
    'expansion', 'enters', 'hires', 'appoints', 'restructures', 'opens',
    'rolls out', 'available in', 'integration', 'product chief', 'cfo',
    '发布', '上线', '合作', '扩张', '进入', '招聘', '任命', '重组', '开放',
}
# 变化显性词：无这些词的标题 = 没有可感变化 = Signal 分上不去（窄门约束）
CHANGE_EXPLICIT_TERMS = {
    'launch', 'launches', 'launched', 'released', 'releases', 'acquires',
    'acquired', 'raises', 'raised', 'announces', 'announced', 'plans',
    'orders', 'bans', 'banned', 'fines', 'fined', 'shifts', 'shifted',
    'changing', 'changes', 'expands', 'enters', 'surges', 'rises', 'falls',
    'cuts', 'closes', 'partners', 'rolls out', 'appoints', 'hires', 'opens',
    'joins', 'tests', 'unveils', 'debuts', 'ramps up', 'commits', 'pledges',
    'backs', 'weighs', 'extends', 'operationalises',
    '发布', '宣布', '收购', '融资', '责令', '禁令', '罚款', '转变', '扩张',
    '进入', '上涨', '下降', '削减', '合作', '上线', '任命', '招聘',
    '承诺', '启动', '落地', '推进',
}


def _event_type(event):
    types = event.get('event_types') or ['other']
    return types[0] if types else 'other'


def infer_signal_type(event, content_type=None):
    """Return the kind of change an event represents (6-way taxonomy).

    policy 判定不以 content_type/scope_layer 标签为准，必须命中窄词表：
    scope_layer='regional_policy' 可能是旧数据或宽词表误标（如 B2B 观点文），
    词表命中了才是真政策变化。
    """
    explicit = event.get('signal_type')
    if explicit in SIGNAL_TYPES:
        return explicit
    content_type = content_type or infer_content_type(event)
    text = _text(event)
    ev_type = _event_type(event)
    if _has(text, POLICY_SIGNAL_TERMS):
        return 'policy'
    if content_type == 'model_release' or _has(text, TECHNOLOGY_SIGNAL_TERMS):
        return 'technology'
    if ev_type in {'funding', 'ma', 'earnings'} or content_type == 'capital_event':
        return 'capital'
    if _has(text, MARKET_SIGNAL_TERMS):
        return 'market'
    if _has(text, CONSUMER_SIGNAL_TERMS):
        return 'consumer'
    if event.get('is_company') or event.get('company_name') or content_type == 'company_action':
        return 'company'
    return 'market'


def signal_change_score(event, content_type=None):
    """Score how significant the CHANGE an event represents is (0-100).

    窄门约束：Signal 层不得把 scope 已过滤的噪声拉高。
    - 不在目标行业内（scope_status 非 qualified、无 scope_industries）→ 0 分。
    - 在行业内但无明确变化证据（无变化词/量化）→ 0 分。
    只有"行业内 + 有变化"的事件才进入分量打分。
    """
    content_type = content_type or infer_content_type(event)
    signal_type = infer_signal_type(event, content_type)
    scope_status = event.get('scope_status')
    in_scope = (
        scope_status == 'qualified'
        or bool(event.get('scope_industries'))
        or bool(event.get('vertical'))
    )
    if not in_scope:
        return {
            'signal_type': signal_type,
            'signal_change_score': 0,
            'signal_change_blocked': 'out_of_target_industry',
            'signal_change_breakdown': {},
        }

    text = _text(event)
    # "有变化"门槛与 scope_gate 同口径：scope 层用 ACTION_TERMS/INDUSTRY_CHANGE_TERMS/
    # QUANTIFIED_CHANGE_TERMS 判定 qualified，Signal 层复用同一批词面，避免因词表
    # 不同步而误杀（央行测试代币化、区域融资这类 scope 判过的变化在 Signal 层 0 分）。
    # 区别在打分：scope 只判"是不是变化"，Signal 层再判"变化有多重要"。
    try:
        from scope_gate import (
            ACTION_TERMS as SCOPE_ACTION_TERMS,
            INDUSTRY_CHANGE_TERMS as SCOPE_INDUSTRY_TERMS,
            QUANTIFIED_CHANGE_TERMS as SCOPE_QUANTIFIED_TERMS,
            REGIONAL_POLICY_TITLE_TERMS as SCOPE_POLICY_TERMS,
        )
    except ImportError:
        from scripts.scope_gate import (
            ACTION_TERMS as SCOPE_ACTION_TERMS,
            INDUSTRY_CHANGE_TERMS as SCOPE_INDUSTRY_TERMS,
            QUANTIFIED_CHANGE_TERMS as SCOPE_QUANTIFIED_TERMS,
            REGIONAL_POLICY_TITLE_TERMS as SCOPE_POLICY_TERMS,
        )
    # 事件类型本身代表强变化的，Signal 层直接视为"有变化"，不靠标题词：
    # funding/ma/earnings（融资并购财报）、regional_policy（政策层）天然是变化。
    # strategy/partnership 最泛（含人事任命、观点文），需词表判定。
    strong_change_types = {'funding', 'ma', 'earnings', 'regional_policy'}
    has_explicit_change = (
        _event_type(event) in strong_change_types
        or bool(
            _has(text, SCOPE_POLICY_TERMS)
            or _has(text, SCOPE_ACTION_TERMS)
            or _has(text, SCOPE_INDUSTRY_TERMS)
            or _has(text, SCOPE_QUANTIFIED_TERMS)
            or _has(text, CHANGE_EXPLICIT_TERMS)
            or _has(text, QUANTIFIED_TERMS)
            or bool(re.search(r'\d+(?:\.\d+)?\s*%', text))
            or bool(re.search(r'[$€£]\s?\d', text))
            or bool(re.search(r'\d+\s*(?:million|billion|亿|万|万亿|亿美元)', text))
        )
    )
    if not has_explicit_change:
        return {
            'signal_type': signal_type,
            'signal_change_score': 0,
            'signal_change_blocked': 'no_explicit_change',
            'signal_change_breakdown': {},
        }

    # 量化加分只认数字+单位/金额模式；B2B/B2C/5G/Web3 这类缩写里的数字不算。
    quantified = (
        _has(text, QUANTIFIED_TERMS)
        or bool(re.search(r'\d+(?:\.\d+)?\s*%', text))
        or bool(re.search(r'[$€£]\s?\d', text))
        or bool(re.search(r'\d+\s*(?:million|billion|亿|万|万亿|亿美元)', text))
    )
    change_explicit = 35 if quantified else 20

    type_weight = {
        'policy': 25, 'technology': 22, 'market': 20,
        'capital': 18, 'consumer': 16, 'company': 12,
    }[signal_type]
    scope_fit = 20 if event.get('scope_industries') else 12
    region_specific = 10 if (event.get('region') or '').strip() not in ('', '全球', 'global') else 5
    trend_potential = 15 if signal_type in {'policy', 'technology', 'market'} else 8
    if event.get('scope_regions') and len(event.get('scope_regions')) > 1:
        trend_potential = min(20, trend_potential + 5)

    total = min(100, change_explicit + type_weight + scope_fit + region_specific + trend_potential)
    return {
        'signal_type': signal_type,
        'signal_change_score': total,
        'signal_change_blocked': '',
        'signal_change_breakdown': {
            'change_explicit': change_explicit,
            'signal_type_weight': type_weight,
            'scope_fit': scope_fit,
            'region_specific': region_specific,
            'trend_potential': trend_potential,
        },
    }


def _source_authority(event):
    credibility = event.get('credibility_score')
    try:
        credibility_score = float(credibility)
    except (TypeError, ValueError):
        credibility_score = 0
    if credibility_score > 0:
        return min(35, max(8, credibility_score * 3.5))
    tier_points = {
        'L1 官方/IR源': 33,
        'L4 垂直赛道精品源': 29,
        'L3 区域生态源': 23,
        'L2 垂直交易源': 20,
        'L5 Google News 补漏源': 10,
    }
    return tier_points.get(event.get('source_tier'), 16)


def _confidence_score(event, content_type):
    traceability = 0
    if event.get('source_excerpt') or event.get('original_title'):
        traceability += 10
    if event.get('evidence_refs'):
        traceability += 8
    if event.get('url'):
        traceability += 7

    recency = 15 if event.get('published_at') or event.get('article_date') else 7
    specificity = 10 if event.get('scope_industries') or event.get('vertical') else 5
    if _has(_text(event), QUANTIFIED_TERMS):
        specificity += 5
    if content_type == 'industry_report' and event.get('report_methodology_visible'):
        specificity += 5
    if content_type == 'model_release' and event.get('model_card_url'):
        specificity += 5
    return min(100, round(_source_authority(event) + traceability + recency + specificity))


def _materiality_score(event, content_type):
    text = _text(event)
    if content_type == 'industry_report':
        score = 20
        if _has(text, {'market share', 'market size', 'forecast', '份额', '规模', '预测'}):
            score += 15
        if _has(text, QUANTIFIED_TERMS):
            score += 10
        if event.get('report_published_at') or event.get('published_at'):
            score += 5
        return score
    if content_type == 'model_release':
        score = 25
        if _has(text, {'open source', 'open-source', 'api', 'pricing', 'context', '开放', '价格'}):
            score += 15
        if _has(text, {'multimodal', 'reasoning', 'agent', '多模态', '推理', '智能体'}):
            score += 10
        return score
    if content_type == 'regional_policy':
        score = 25
        if _has(text, {'law', 'regulation', 'license', 'effective', '法规', '法案', '牌照', '生效'}):
            score += 15
        return score
    score = 15
    if _has(text, ACTION_TERMS):
        score += 15
    if event.get('companies') or event.get('company_name'):
        score += 5
    return score


def score_signal(event):
    """Return auditable confidence, attention and trend scores."""
    content_type = infer_content_type(event)
    confidence = _confidence_score(event, content_type)
    materiality = min(45, _materiality_score(event, content_type))
    decision_relevance = 20 if event.get('scope_industries') or event.get('vertical') else 10
    if event.get('impact') and event.get('impact') != '未知':
        decision_relevance += 5
    scope_status = event.get('scope_status')
    scope_fit = 20 if scope_status == 'qualified' else 0 if scope_status == 'filtered' else 8
    novelty = 15 if content_type in {'industry_report', 'model_release', 'regional_policy'} else 10
    if scope_status == 'filtered':
        novelty = 0
    urgency = 10 if event.get('published_at') or event.get('scheduled_at') else 5
    attention = min(100, materiality + decision_relevance + scope_fit + novelty + urgency)

    trend = 20 if content_type in {'industry_report', 'regional_policy', 'model_release'} else 12
    if _has(_text(event), QUANTIFIED_TERMS):
        trend += 20
    if event.get('scope_industries') or event.get('scope_regions'):
        trend += 20
    if event.get('evidence_refs') and len(event.get('evidence_refs')) > 1:
        trend += 20
    if event.get('published_at') or event.get('article_date'):
        trend += 10

    return {
        'content_type': content_type,
        'subject_type': infer_subject_type(event, content_type),
        'claim_type': infer_claim_type(event, content_type),
        'confidence_score': min(100, confidence),
        'attention_score': min(100, attention),
        'trend_weight': min(100, trend),
        'score_breakdown': {
            'source_authority': round(_source_authority(event)),
            'materiality': materiality,
            'decision_relevance': decision_relevance,
            'scope_fit': scope_fit,
            'novelty': novelty,
            'urgency': urgency,
        },
    }


def apply_signal_contract(event):
    result = score_signal(event)
    event.update(result)
    event['evidence_grade'] = (
        'A' if result['confidence_score'] >= 80 else
        'B' if result['confidence_score'] >= 65 else
        'C' if result['confidence_score'] >= 50 else 'D'
    )
    # 阶段3：信号维度（变化轴）。signal_type 分类 + signal_change_score 打分。
    signal = signal_change_score(event, result['content_type'])
    event['signal_type'] = signal['signal_type']
    event['signal_change_score'] = signal['signal_change_score']
    event['signal_change_blocked'] = signal['signal_change_blocked']
    event['signal_change_breakdown'] = signal['signal_change_breakdown']
    return event
