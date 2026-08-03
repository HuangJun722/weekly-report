"""Deterministic event normalization before any view consumes an event."""

try:
    from view_selectors import apply_view_contract
    from scope_gate import apply_scope_contract
except ImportError:
    from scripts.view_selectors import apply_view_contract
    from scripts.scope_gate import apply_scope_contract


OFFICIAL_BEHAVIOR_TYPES = {'changelog', 'developer_docs', 'product_update'}


def _official_behavior_type(event):
    source_type = (event.get('source_type') or '').lower()
    source_id = (event.get('source_id') or '').lower()
    source = (event.get('source') or '').lower()
    if source_type in OFFICIAL_BEHAVIOR_TYPES:
        return source_type
    if 'changelog' in source_id or 'changelog' in source:
        return 'changelog'
    if 'developer' in source_id or 'docs' in source_id:
        return 'developer_docs'
    return ''


def normalize_official_behavior_event(event):
    """Turn a directly observed product change into an explainable fact.

    This only applies to first-party changelog/docs/product sources. It does
    not repair generic newsroom, IR, or media events.
    """
    point_type = _official_behavior_type(event)
    if not point_type:
        return event
    if (event.get('source_tier') or '') != 'L1 官方/IR源' and not event.get('is_company'):
        return event

    title = (event.get('title') or '').strip()
    if not title:
        return event
    company = event.get('company_name') or (event.get('source') or '').replace(' Changelog', '').strip()
    subject = company or '官方产品'
    labels = {
        'changelog': ('产品更新', '开发者、集成商和生态合作伙伴'),
        'developer_docs': ('开发者能力更新', '开发者、技术集成商和平台合作伙伴'),
        'product_update': ('产品能力更新', '客户、渠道伙伴和生态合作伙伴'),
    }
    topic, impact = labels[point_type]
    if (event.get('event_types') or ['other'])[0] == 'other':
        event['event_types'] = ['strategy']
    event['summary_short'] = event.get('summary_short') or title
    event['reason'] = f'{subject}发布{topic}，可验证其产品、平台或生态能力发生变化'
    event['impact'] = impact
    event['trend_topic'] = event.get('trend_topic') or f'{subject}{topic}'
    event['insight_label'] = event.get('insight_label') or '合作机会'
    event['analysis_status'] = 'complete'
    event['analysis_source'] = event.get('analysis_source') or 'deterministic_official'
    event['needs_repair'] = False
    event['quality_flags'] = []
    event['observation_type'] = point_type
    return event


def prepare_event_contract(event):
    """Normalize a stored event and freeze its product-view decision."""
    normalize_official_behavior_event(event)
    if event.get('scope_enforced') and not event.get('scope_status'):
        apply_scope_contract(event)
    apply_view_contract(event)
    return event
