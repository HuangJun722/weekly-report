"""Build narrative objects that bind judgment, windows, and evidence.

The narrative layer sits above signal clusters. It keeps the homepage and
future period reports from composing separate summaries, windows, and evidence
lists that do not prove each other.
"""

try:
    from evidence_atoms import build_evidence_atoms, can_promote_to_narrative, evidence_independence
except ImportError:
    from scripts.evidence_atoms import build_evidence_atoms, can_promote_to_narrative, evidence_independence


def _event_key(event):
    if not event:
        return ''
    return event.get('url') or '|'.join([
        event.get('date') or '',
        event.get('display_title') or event.get('title') or '',
    ])


def _cluster_companies(cluster):
    return [company for company in cluster.get('companies') or [] if company]


def _cluster_key(cluster):
    companies = tuple(sorted(_cluster_companies(cluster)))
    if companies:
        return ('companies', companies)
    return (
        'topic',
        cluster.get('region') or '',
        cluster.get('topic') or cluster.get('title') or '',
        cluster.get('cluster_type') or cluster.get('type_label') or '',
    )


def _dedupe_clusters(clusters):
    deduped = []
    seen = set()
    used_companies = set()
    for cluster in clusters or []:
        companies = set(_cluster_companies(cluster))
        key = _cluster_key(cluster)
        if key in seen:
            continue
        if companies and used_companies & companies:
            continue
        seen.add(key)
        used_companies.update(companies)
        deduped.append(cluster)
    return deduped


def _coherent_clusters(clusters):
    clusters = _dedupe_clusters(clusters)
    if not clusters:
        return []
    anchor = clusters[0]
    anchor_region = anchor.get('region') or ''
    anchor_theme = anchor.get('type_label') or anchor.get('cluster_type') or ''
    coherent = [anchor]
    for cluster in clusters[1:]:
        region = cluster.get('region') or ''
        theme = cluster.get('type_label') or cluster.get('cluster_type') or ''
        if (anchor_region and region == anchor_region) or (anchor_theme and theme == anchor_theme):
            coherent.append(cluster)
    return coherent


def _unique_evidence(clusters, limit=8):
    evidence = []
    seen = set()
    for cluster in clusters:
        for item in cluster.get('evidence') or []:
            key = item.get('url') or '|'.join([item.get('date') or '', item.get('title') or ''])
            if not key or key in seen:
                continue
            seen.add(key)
            evidence.append(item)
            if len(evidence) >= limit:
                return evidence
    return evidence


def _unique_evidence_events(clusters, limit=8):
    evidence_events = []
    seen = set()
    for cluster in clusters:
        for event in cluster.get('evidence_events') or []:
            key = _event_key(event)
            if not key or key in seen:
                continue
            seen.add(key)
            evidence_events.append(event)
            if len(evidence_events) >= limit:
                return evidence_events
    return evidence_events


def _coverage(clusters, evidence):
    cluster_keys = {
        item.get('url') or '|'.join([item.get('date') or '', item.get('title') or ''])
        for cluster in clusters
        for item in cluster.get('evidence') or []
    }
    cluster_keys = {key for key in cluster_keys if key}
    evidence_keys = {
        item.get('url') or '|'.join([item.get('date') or '', item.get('title') or ''])
        for item in evidence
    }
    evidence_keys = {key for key in evidence_keys if key}
    if not cluster_keys:
        return 0.0
    return len(cluster_keys & evidence_keys) / len(cluster_keys)


def _dominant_region(clusters):
    counts = {}
    for cluster in clusters:
        region = cluster.get('region') or ''
        if not region:
            continue
        counts[region] = counts.get(region, 0) + 1
    if not counts:
        return ''
    return max(counts.items(), key=lambda item: item[1])[0]


def _dominant_theme(clusters):
    counts = {}
    for cluster in clusters:
        theme = cluster.get('type_label') or cluster.get('topic') or ''
        if not theme:
            continue
        counts[theme] = counts.get(theme, 0) + 1
    if not counts:
        return ''
    return max(counts.items(), key=lambda item: item[1])[0]


def _all_companies(clusters):
    companies = []
    for cluster in clusters:
        for company in _cluster_companies(cluster):
            if company not in companies:
                companies.append(company)
    return companies


def _confidence(clusters, evidence_coverage):
    atoms = build_evidence_atoms(_unique_evidence_events(clusters))
    if clusters and not can_promote_to_narrative(atoms):
        return '观察'
    high = sum(1 for cluster in clusters if cluster.get('confidence') == '高')
    if len(clusters) >= 2 and high >= 1 and evidence_coverage >= 0.75:
        return '高'
    if clusters and evidence_coverage >= 0.5:
        return '中'
    return '观察'


def _title(region, theme, clusters):
    if not clusters:
        return '今日要点'
    if len(clusters) == 1:
        return clusters[0].get('title') or '今日关注窗口'
    if region and theme:
        return f'{region}{theme}出现连续信号'
    if region:
        return f'{region}出现连续信号'
    return '今日关注窗口出现连续信号'


def _judgment(title, clusters, evidence_count, downgraded):
    if not clusters:
        return '今日尚未形成稳定关注窗口，先查看已入库事件和需复核线索。'
    if downgraded:
        return '今日独立证据密度不足，尚未形成稳定关注窗口，先按要点跟踪。'
    return f'{title}，由{len(clusters)}个关注窗口和{evidence_count}条证据事件支撑。'


def _recommended_action(clusters):
    for cluster in clusters:
        action = cluster.get('action')
        if action:
            return action
    return '加入观察名单，等待二次确认信号'


def build_narrative(clusters, fallback_events=None, limit_clusters=3):
    """Return one conservative narrative for the current display surface."""
    clusters = _coherent_clusters(clusters)[:limit_clusters]
    evidence = _unique_evidence(clusters)
    evidence_events = _unique_evidence_events(clusters)
    evidence_coverage = _coverage(clusters, evidence)
    evidence_atoms = build_evidence_atoms(evidence_events)
    independence = evidence_independence(evidence_atoms)
    region = _dominant_region(clusters)
    theme = _dominant_theme(clusters)
    confidence = _confidence(clusters, evidence_coverage)
    promoted = can_promote_to_narrative(evidence_atoms)
    downgraded = bool(clusters) and (evidence_coverage < 0.5 or not promoted)
    title = '今日要点' if downgraded else _title(region, theme, clusters)
    display_clusters = [] if downgraded else clusters

    if not clusters and fallback_events:
        fallback_evidence = []
        fallback_evidence_events = []
        seen = set()
        for event in fallback_events[:5]:
            key = _event_key(event)
            if not key or key in seen:
                continue
            seen.add(key)
            fallback_evidence_events.append(event)
            fallback_evidence.append({
                'title': event.get('display_title') or event.get('summary_short') or event.get('title') or '',
                'url': event.get('url') or '#',
                'date': event.get('date') or '',
                'source': event.get('display_source') or event.get('source') or '公开来源',
                'type': event.get('insight_label') or '',
            })
        evidence = fallback_evidence
        evidence_events = fallback_evidence_events

    return {
        'title': title,
        'theme': theme,
        'region': region,
        'companies': _all_companies(display_clusters),
        'judgment': _judgment(title, clusters, len(evidence), downgraded),
        'clusters': display_clusters,
        'evidence': evidence,
        'evidence_events': evidence_events,
        'recommended_action': _recommended_action(clusters),
        'confidence': confidence,
        'mode': 'narrative' if clusters and not downgraded else 'daily_brief',
        'consistency': {
            'region_match': 1.0 if region and all((c.get('region') or '') == region for c in clusters) else 0.0,
            'company_match': 1.0,
            'evidence_coverage': round(evidence_coverage, 2),
            'evidence_atoms': independence,
            'promoted': promoted,
        },
    }
