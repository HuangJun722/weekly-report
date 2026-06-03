"""Product-boundary rules for a global internet industry intelligence site.

This is not a source-quality filter. It answers whether an event belongs to
the site's identity: internet platforms, digital infrastructure, and software-
driven business opportunities.
"""

import re


CORE_INTERNET_TERMS = {
    'ecommerce', 'e-commerce', 'marketplace', 'merchant', 'seller',
    'payment', 'payments', 'fintech', 'wallet', 'bnpl', 'remittance',
    'acquiring', 'banking app', 'digital bank', 'checkout',
    'saas', 'software-as-a-service', 'enterprise software', 'crm', 'erp',
    'cloud', 'ai infrastructure', 'ai infra', 'data center', 'datacenter',
    'gpu', 'openai', 'anthropic', 'nvidia', 'developer', 'api', 'changelog', 'serverless', 'database',
    'cybersecurity', 'security platform', 'identity', 'ads', 'advertising',
    'adtech', 'marketing automation', 'social media', 'creator platform',
    'gaming', 'game', 'games', 'streaming', 'app store', 'super app',
    'ride-hailing', 'mobility platform', 'delivery platform', 'food delivery',
    'logistics platform', 'fulfillment', 'last-mile',
    '电商', '支付', '金融科技', '钱包', '跨境汇款', '商户', '收单',
    '云', '云服务', '数据中心', '算力', '开发者', '接口', '数据库',
    '网络安全', '身份认证', '广告', '营销自动化', '游戏', '流媒体',
    '超级app', '本地生活', '外卖', '出行平台', '物流平台', '履约',
}

ADJACENT_INTERNET_TERMS = {
    'platform', 'software', 'app', 'digital', 'data', 'analytics', 'automation',
    'ai platform', 'ai app', 'ai application', 'model', 'llm', 'agent', 'inference', 'workflow', 'notetaker',
    'ehr', 'emr', 'telehealth', 'health it', 'medical it', 'patient support',
    'clinical data', 'medical data', 'digital health', 'healthcare saas',
    '平台', '软件', '应用', '数字化', '数据', '分析', '自动化',
    'ai平台', 'ai应用', '模型', '智能体', '推理', '工作流', '医疗it', '医疗数据',
    '电子病历', '远程医疗', '数字医疗', '医疗saas', '患者支持',
}

STRONG_ADJACENT_HEALTH_IT_TERMS = {
    'ehr', 'emr', 'telehealth', 'health it', 'medical it', 'patient support',
    'clinical data platform', 'medical data platform', 'healthcare saas',
    'ai notetaker', 'notetaker', 'revenue cycle management',
    '电子病历', '远程医疗', '医疗it', '医疗数据平台', '医疗saas',
    '患者支持平台', 'ai病历', '收入周期管理',
}

EDGE_TERMS = {
    'industrial software', 'robotics', 'robot', 'energy software',
    'climate software', 'manufacturing software', 'supply chain software',
    '工业软件', '机器人', '能源软件', '制造软件', '供应链软件',
}

OUT_OF_SCOPE_TERMS = {
    'defense', 'defence', 'military', 'weapon', 'missile', 'ammunition',
    'army', 'battlefield', 'palantir-style',
    'biotech', 'biotherapeutics', 'therapeutics', 'pharma', 'pharmaceutical',
    'drug', 'drug discovery', 'therapy', 'therapies', 'clinical trial',
    'ophthalmology', 'glaucoma', 'retinal', 'cardiac', 'oncology', 'cancer',
    'diagnostics', 'disease diagnosis', 'healthcare fund', 'medical device',
    'ct scanner', 'agriculture', 'agritech', 'construction material', 'mining',
    '国防', '军工', '军事', '武器', '导弹', '弹药', '战场',
    '生物科技', '生物制药', '制药', '药物', '疗法', '治疗', '临床试验',
    '眼科', '青光眼', '视网膜', '心脏', '肿瘤', '癌症', '诊断',
    '医疗基金', '医疗器械', '农业', '建筑材料', '矿业',
}

HEALTH_BIO_OUT_OF_SCOPE_TERMS = {
    'healthtech', 'health tech', 'healthcare', 'medical',
    'biotech', 'biotherapeutics', 'therapeutics', 'pharma', 'pharmaceutical',
    'drug', 'therapy', 'therapies', 'clinical trial', 'ophthalmology',
    'glaucoma', 'retinal', 'cardiac', 'oncology', 'cancer', 'diagnostics',
    'disease diagnosis', 'healthcare fund', 'medical device',
    '医疗科技', '医疗健康', '医疗行业', '生物科技', '生物制药', '制药', '药物', '疗法', '治疗', '临床试验',
    '眼科', '青光眼', '视网膜', '心脏', '肿瘤', '癌症', '诊断',
    '医疗基金', '医疗器械',
}

OUT_OF_SCOPE_CAP_TO_EDGE_TERMS = {
    'defense', 'defence', 'military', '国防', '军工', '军事',
}


def _event_text(event):
    parts = [
        event.get('title') or '',
        event.get('display_title') or '',
        event.get('summary_short') or '',
        event.get('reason') or '',
        event.get('trend_topic') or '',
        event.get('source') or '',
        event.get('company_name') or '',
        ' '.join(event.get('companies') or []),
    ]
    return ' '.join(parts).lower()


def _contains_any(text, terms):
    for term in terms:
        term = term.lower()
        if re.search(r'[a-z0-9]', term):
            if re.search(rf'(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])', text):
                return True
            continue
        if term in text:
            return True
    return False


def assess_internet_relevance(event):
    """Return score/label/reason for the site's product boundary.

    score:
    - 3: core internet
    - 2: adjacent but clearly software/platform/infrastructure related
    - 1: edge observation only
    - 0: out of scope for the main internet intelligence product
    """
    text = _event_text(event)
    has_core = _contains_any(text, CORE_INTERNET_TERMS)
    has_adjacent = _contains_any(text, ADJACENT_INTERNET_TERMS)
    has_strong_health_it = _contains_any(text, STRONG_ADJACENT_HEALTH_IT_TERMS)
    has_edge = _contains_any(text, EDGE_TERMS)
    has_out = _contains_any(text, OUT_OF_SCOPE_TERMS)
    has_health_bio_out = _contains_any(text, HEALTH_BIO_OUT_OF_SCOPE_TERMS)
    capped_edge = _contains_any(text, OUT_OF_SCOPE_CAP_TO_EDGE_TERMS)

    if capped_edge and not has_core:
        return {
            'score': 1,
            'label': 'edge_observation',
            'reason': '军工/国防相关事件默认不进入主展示，只保留观察价值',
        }

    if has_core:
        score = 3
        label = 'core_internet'
        reason = '核心互联网平台、软件或数字基础设施信号'
    elif has_adjacent:
        score = 2
        label = 'adjacent_internet'
        reason = '相邻行业事件，但明确指向软件、平台、数据或AI能力'
    elif has_edge:
        score = 1
        label = 'edge_observation'
        reason = '边缘产业数字化信号，只适合观察层'
    else:
        score = 0 if has_out else 1
        label = 'out_of_scope' if has_out else 'edge_observation'
        reason = '不属于本站主赛道' if has_out else '互联网相关性不足，先作为边缘观察'

    if has_out and score >= 2:
        if capped_edge:
            return {
                'score': 1,
                'label': 'edge_observation',
                'reason': '军工/国防相关事件默认不进入主展示，只保留观察价值',
            }
        if has_core:
            return {
                'score': 2,
                'label': 'adjacent_internet',
                'reason': '相邻行业事件，因包含互联网平台、软件或AI基础设施能力而保留',
            }
        if has_health_bio_out and not has_strong_health_it:
            return {
                'score': 0,
                'label': 'out_of_scope',
                'reason': '生物制药、疗法、诊断或医疗器械事件默认不属于本站主赛道',
            }
        if has_adjacent:
            return {
                'score': 2,
                'label': 'adjacent_internet',
                'reason': '相邻行业事件，因明确指向软件、数据或AI应用而保留',
            }

    return {'score': score, 'label': label, 'reason': reason}


def internet_relevance_score(event):
    return assess_internet_relevance(event)['score']


def is_mainline_internet_event(event):
    return internet_relevance_score(event) >= 2


def is_edge_internet_event(event):
    return internet_relevance_score(event) == 1
