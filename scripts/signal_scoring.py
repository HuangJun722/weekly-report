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
    return event
