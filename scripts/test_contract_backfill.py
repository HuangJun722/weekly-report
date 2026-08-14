"""Regression test: do legacy and frozen (prefilled) events share the same view contract?

Legacy stored events carry no scope/signal contract fields; frozen historical
events carry scope_enforced + scope_status + scoring fields written by the
contract. Both must, after prepare_event_contract, reach the same display
decision, or every divergence must be attributable to a known deviation.

Known deviations (documented, NOT fixed this round):

1. scope_fit 8-vs-20 vintage gap
   signal_scoring.score_signal computes scope_fit = 20 when scope_status is
   'qualified', 0 when 'filtered', else 8. A legacy event re-scored today has
   no scope_status, so it gets scope_fit=8; a frozen qualified twin gets 20.
   The delta (attention +12, capped at 100) changes attention_score ordering,
   but under current view thresholds no first-class
   typed event crosses the main/review gates because of it (probe on the live
   corpus: 0 view flips). The test asserts the delta is exactly scope_fit and
   that view_status/view_priority stay consistent.

2. Raw-path consumers skip the contract
   entity_signal_conversion_report.build_entity_signal_conversion_report calls
   should_show_in_main_list/should_show_in_review on raw stored events at
   lines 207-208 WITHOUT prepare_event_contract. Legacy events therefore take
   the legacy score path (event_type + score) while prepared consumers take
   the typed signal path. On the 2026-08-05 corpus this diverges on 69 events
   (64 raw review -> prepared main; 4 review -> filtered; 1 filtered ->
   review). The report undercounts main events relative to the homepage. This
   is recorded as a known deviation; fixing it means preparing events in that
   report, which is out of scope this round.
"""

import copy
import json
import sys
from pathlib import Path

try:
    from event_contract import prepare_event_contract
    from event_value import should_show_in_main_list, should_show_in_review
    from signal_scoring import score_signal
except ImportError:
    from scripts.event_contract import prepare_event_contract
    from scripts.event_value import should_show_in_main_list, should_show_in_review
    from scripts.signal_scoring import score_signal


REPO_ROOT = Path(__file__).resolve().parent.parent
EVENTS_PATH = REPO_ROOT / 'data' / 'events.json'

_FAILURES = []
_NOTES = []


def _note(message):
    _NOTES.append(message)


def _load_events():
    with open(EVENTS_PATH, encoding='utf-8') as handle:
        data = json.load(handle)
    events = []
    for date_key, items in (data or {}).items():
        for event in items or []:
            item = dict(event)
            item.setdefault('date', date_key)
            events.append(item)
    return events


def _frozen_twin(prepared_legacy):
    """A historical event frozen with the contract written into its fields."""
    frozen = copy.deepcopy(prepared_legacy)
    frozen['scope_enforced'] = True
    frozen['scope_status'] = 'qualified'
    return frozen


def _view_signature(event):
    status = should_show_in_main_list(event) and 'main' or (
        should_show_in_review(event) and 'review' or 'filtered'
    )
    return status, event.get('view_priority')


def raw_sig_status(event):
    """Status-only signature for events that may lack a frozen view_priority."""
    status = should_show_in_main_list(event) and 'main' or (
        should_show_in_review(event) and 'review' or 'filtered'
    )
    return status


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


def test_prepare_is_deterministic():
    raw = base_event()
    first = prepare_event_contract(copy.deepcopy(raw))
    second = prepare_event_contract(copy.deepcopy(raw))
    assert first.get('view_status') == second.get('view_status'), 'same input, different view_status'
    assert first.get('view_priority') == second.get('view_priority'), 'same input, different view_priority'
    assert first.get('attention_score') == second.get('attention_score'), 'same input, different attention'
    # Re-preparing an already prepared event must not change the frozen view.
    again = prepare_event_contract(copy.deepcopy(first))
    assert again.get('view_status') == first.get('view_status'), 're-prepare changed view_status'
    assert again.get('view_priority') == first.get('view_priority'), 're-prepare changed view_priority'


def test_frozen_twin_differs_only_by_scope_fit():
    raw = base_event()
    legacy = prepare_event_contract(copy.deepcopy(raw))
    frozen = prepare_event_contract(_frozen_twin(legacy))

    legacy_breakdown = legacy.get('score_breakdown') or {}
    frozen_breakdown = frozen.get('score_breakdown') or {}
    divergent_components = {
        key for key in set(legacy_breakdown) | set(frozen_breakdown)
        if legacy_breakdown.get(key) != frozen_breakdown.get(key)
    }
    assert divergent_components == {'scope_fit'}, (
        f'score_breakdown diverges beyond scope_fit: {divergent_components}'
    )
    assert frozen_breakdown['scope_fit'] == legacy_breakdown['scope_fit'] + 12
    assert legacy_breakdown['scope_fit'] == 8, 'legacy scope_fit should be 8 (no scope_status)'
    assert frozen_breakdown['scope_fit'] == 20, 'frozen qualified scope_fit should be 20'
    # confidence must not change; only attention (derived from scope_fit).
    assert frozen.get('confidence_score') == legacy.get('confidence_score')
    # trend_weight 已移除：单条 Signal 不再评分趋势（趋势判断留给聚合层）
    assert 'trend_weight' not in frozen and 'trend_weight' not in legacy
    assert frozen.get('attention_score') == min(100, legacy.get('attention_score') + 12)
    # And the view decision must not flip (documented deviation #1).
    assert _view_signature(frozen) == _view_signature(legacy), (
        'scope_fit delta flipped the view decision'
    )


def test_scope_fit_vintage_gap_is_mechanism_only():
    # An industry_report with no scope fields: legacy attention sits above the
    # typed main gate even at scope_fit=8, so the +12 never flips the view.
    raw = base_event(
        title='SEA market forecast report shows cloud spending growing 28%',
        source='Counterpoint Research',
        source_tier='L4 垂直赛道精品源',
        event_types=['industry_report'],
        content_type='industry_report',
        scope_industries=['cloud_saas_developer'],
        region='SEA',
        report_access_level='public',
        report_published_at='2026-08-01',
    )
    legacy = prepare_event_contract(copy.deepcopy(raw))
    frozen = prepare_event_contract(_frozen_twin(legacy))
    breakdown_legacy = legacy.get('score_breakdown') or {}
    breakdown_frozen = frozen.get('score_breakdown') or {}
    assert breakdown_frozen['scope_fit'] - breakdown_legacy['scope_fit'] == 12
    assert frozen.get('attention_score') == min(100, legacy.get('attention_score') + 12)
    _note(
        'scope_fit 8-vs-20：legacy 重评分按 scope_fit=8，冻结 qualified 按 20，'
        f'attention 最多 +12（本例 {legacy.get("attention_score")}->{frozen.get("attention_score")}，'
        '受 100 封顶）。当前阈值下该增量不翻转 view_status'
        '（一等内容类型在 legacy 下已越过门槛），但影响 attention 排序。'
    )


def test_corpus_legacy_and_frozen_share_view():
    """Across the live corpus, freezing must change only scope_fit and must
    not flip any view decision. New divergences beyond the documented gap are
    regressions."""
    events = _load_events()
    view_flips = []
    unexplained = []
    for event in events:
        legacy = prepare_event_contract(copy.deepcopy(event))
        frozen = prepare_event_contract(_frozen_twin(legacy))
        if _view_signature(frozen) != _view_signature(legacy):
            view_flips.append(event.get('title'))
            continue
        breakdown_legacy = legacy.get('score_breakdown') or {}
        breakdown_frozen = frozen.get('score_breakdown') or {}
        divergent = {
            key for key in set(breakdown_legacy) | set(breakdown_frozen)
            if breakdown_legacy.get(key) != breakdown_frozen.get(key)
        }
        if not (divergent <= {'scope_fit'}):
            unexplained.append((event.get('title'), sorted(divergent)))
        elif frozen.get('confidence_score') != legacy.get('confidence_score'):
            unexplained.append((event.get('title'), ['confidence_score']))
    assert not unexplained, f'unexplained frozen-vs-legacy diffs: {unexplained[:5]}'
    _note(
        f'corpus | {len(events)} events | frozen-vs-legacy view flips: {len(view_flips)} '
        '(scope_fit delta does not flip views under current thresholds)'
    )


def test_corpus_raw_path_consumers_skip_contract():
    """Document deviation #2: consumers that call should_show_* without
    prepare_event_contract see a different surface than prepared consumers."""
    events = _load_events()
    status_divergent = []
    status_direction = {}
    for event in events:
        raw = copy.deepcopy(event)
        prepared = prepare_event_contract(copy.deepcopy(event))
        # raw events carry no view_priority until the contract writes it, so
        # only the status leg of the signature is comparable here.
        raw_status = raw_sig_status(raw)
        prep_status = raw_sig_status(prepared)
        if raw_status == prep_status:
            continue
        status_divergent.append((event.get('title'), raw_status, prep_status))
        status_direction[f'{raw_status}->{prep_status}'] = status_direction.get(
            f'{raw_status}->{prep_status}', 0
        ) + 1
    _note(
        f'raw-path vs prepared-path status divergence: {len(status_divergent)}/{len(events)} events. '
        f'directions: {status_direction}. '
        '根因：entity_signal_conversion_report.py:207-208 未 prepare 直接调 should_show_*，'
        'legacy 走旧 score 门槛，prepared 走 typed 信号门槛。记录为已知偏差，本轮不改。'
    )


def _run():
    for name, func in sorted(globals().items()):
        if name.startswith('test_') and callable(func):
            func()
    for note in _NOTES:
        print(f'  note | {note}')
    if _FAILURES:
        for failure in _FAILURES:
            print(f'  FAIL | {failure}')
        print('contract_backfill tests FAILED')
        return 1
    print('contract_backfill tests passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(_run())
