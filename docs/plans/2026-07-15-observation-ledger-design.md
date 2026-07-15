# Observation Ledger Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore event-date credibility and make every monitored company expose a credible, explainable observation status.

**Architecture:** Keep `date` as the legacy display bucket, add explicit publication/observation metadata, and reject future publication candidates before storage. Build an observation ledger from the entity pool, source registry, run metrics, and qualified events; the company index consumes this ledger instead of treating zero qualified events as a single undifferentiated empty state.

**Tech Stack:** Python, JSON, Jinja2, existing script-style tests.

---

### Task 1: Date semantics and future-date guard

**Files:**
- Modify: `scripts/fetch_news.py`
- Modify: `scripts/check_data_health.py`
- Modify: `scripts/generate_html.py`
- Test: `scripts/test_fetch_news_source_meta.py`
- Test: `scripts/test_data_health.py`

**Steps:**
1. Add failing tests for dashed URL dates and future body dates.
2. Add publication metadata: `published_at`, `observed_at`, `date_source`, `date_confidence`, and `date_parse_warning`.
3. Reject publication dates later than the observation time tolerance and retain the rejected value as `scheduled_at` for audit.
4. Revalidate dates before event bucketing and exclude future buckets from display/health calculations.
5. Run the focused date and health tests.

### Task 2: Clean polluted history

**Files:**
- Modify: `data/events.json`

**Steps:**
1. Remove the four Cloudflare records stored under `2026-08-10`, `2026-09-15`, and `2026-10-05`.
2. Verify no event bucket or event date is later than the current date.
3. Recompute the `2026-07-01` to `2026-07-15` health baseline.

### Task 3: Observation ledger

**Files:**
- Create: `scripts/entity_observation_ledger.py`
- Create: `scripts/test_entity_observation_ledger.py`
- Modify: `scripts/fetch_news.py`
- Generate: `data/entity_observation_ledger.json`

**Steps:**
1. Add tests covering `active`, `quiet`, `changed_below_threshold`, `failed`, `partial`, and `pending` states.
2. Record fetch success separately from an empty parse result in run metrics.
3. Build per-observation-point and per-entity ledger rows from run metrics and qualified events.
4. Generate the ledger after each collection run without changing workflow files.
5. Run focused ledger tests and inspect the real ledger output.

### Task 4: Company index status

**Files:**
- Modify: `scripts/generate_html.py`
- Modify: `scripts/template.html`
- Test: `scripts/test_data_health.py`

**Steps:**
1. Attach ledger state to each preset company card.
2. Replace the generic empty state with plain-language states: recent action, checked and quiet, changed but below threshold, collection failed, partial coverage, or pending connection.
3. Keep event counts as supporting evidence rather than the card's primary status.
4. Generate the preview and verify the company index markup.

### Task 5: Verification

**Files:**
- Regenerate: `docs/index.html`
- Regenerate: `docs/feed.xml`

**Steps:**
1. Run all focused tests plus existing source, selector, feed, and health tests.
2. Regenerate HTML and RSS using project scripts.
3. Run strict data health and inspect git diff for unrelated changes.
