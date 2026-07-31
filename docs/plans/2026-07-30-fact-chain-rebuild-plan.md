# Fact Chain Rebuild Implementation Plan

> **For Claude:** Execute this plan task-by-task and keep changes scoped to the listed files.

**Goal:** Make the observation-to-report chain auditable and ensure daily, weekly, monthly, company, RSS, and governance views share one truth.

**Architecture:** Add a deterministic event contract and a persistent Jobs candidate layer. Replace source-based period aggregation with evidence-based weekly themes and cross-week monthly trends, while keeping the existing static HTML stack.

**Tech Stack:** Python 3.11, JSON, Jinja2, pytest, static HTML.

---

### Task 1: Freeze Event View Decisions

**Files:**
- Create: `scripts/event_contract.py`
- Modify: `scripts/view_selectors.py`
- Modify: `scripts/generate_html.py`
- Modify: `scripts/source_conversion_report.py`
- Modify: `scripts/daily_coverage_report.py`
- Test: `scripts/test_view_selectors.py`
- Test: `scripts/test_source_conversion_report.py`

Derive `view_status`, `view_reason`, and `view_priority` before presentation enrichment. All selectors and reports must use those fields when present.

### Task 2: Preserve Source Lineage

**Files:**
- Modify: `scripts/fetch_news.py`
- Modify: `scripts/source_conversion_report.py`
- Test: `scripts/test_fetch_news_source_meta.py`
- Test: `scripts/test_source_conversion_report.py`

Keep entity query and discovery source through storage so Naver/Kakao company queries do not disappear into the Google News aggregate.

### Task 3: Persist Jobs Candidates

**Files:**
- Modify: `scripts/job_observation.py`
- Modify: `scripts/fetch_news.py`
- Modify: `scripts/entity_observation_ledger.py`
- Create: `data/signal_candidates.json`
- Test: `scripts/test_job_observation.py`
- Test: `scripts/test_entity_observation_ledger.py`

Store candidate IDs, evidence references, status and rejection reasons. Detect source resets and only promote clear added-role clusters.

### Task 4: Rebuild Period Themes

**Files:**
- Create: `scripts/period_themes.py`
- Modify: `scripts/evidence_atoms.py`
- Modify: `scripts/generate_html.py`
- Modify: `scripts/template.html`
- Test: `scripts/test_evidence_atoms.py`
- Test: `scripts/test_period_report.py`

Collapse duplicate reports into one fact, infer geography from the event rather than publisher, and render editorial themes backed by evidence. Monthly trends must span weeks and compare with the previous period.

### Task 5: Make Entity Pool the Company SSOT

**Files:**
- Modify: `data/entity_pool.json`
- Modify: `scripts/generate_html.py`
- Modify: `scripts/entity_observation_ledger.py`
- Modify: `scripts/template.html`
- Test: `scripts/test_data_health.py`

Generate all company cards from the 32 entities in the pool and display separate coverage and activity labels.

### Task 6: Extend Health and Documentation

**Files:**
- Modify: `scripts/check_data_health.py`
- Modify: `docs/SYSTEM_OVERVIEW.md`
- Modify: `docs/VIEW_CONTRACT.md`
- Modify: `data/site_updates.json`
- Test: `scripts/test_data_health.py`

Report must-tier coverage, failed observation points, candidate backlog and Jobs failures. Run the focused tests, full tests, HTML generation and visual checks before commit.

