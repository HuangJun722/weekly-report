"""Snapshot and diff job boards without turning individual jobs into events."""

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; WeeklyReportObserver/1.0)'}

JOB_PATHS = {
    'Grab': re.compile(r'/en/jobs/\d+/[^/?#]+/?$', re.I),
    'Stripe': re.compile(r'/jobs/listing/[^/?#]+/\d+/?$', re.I),
    'Shopify': re.compile(r'/careers/[^/?#]+_[0-9a-f-]{36}/?$', re.I),
}

FUNCTION_KEYWORDS = {
    'ai': (' ai ', 'machine learning', 'artificial intelligence', 'data science'),
    'engineering': ('engineer', 'developer', 'platform', 'infrastructure', 'architect'),
    'payments': ('payment', 'fintech', 'financial services', 'treasury'),
    'compliance': ('compliance', 'risk', 'privacy', 'legal', 'regulatory'),
    'partnerships': ('partner', 'partnership', 'ecosystem'),
    'sales': ('sales', 'account executive', 'business development', 'growth'),
    'operations': ('operations', 'ops ', 'support', 'people'),
}


def _job_id(url):
    path = urlparse(url).path.rstrip('/')
    tail = path.rsplit('/', 1)[-1]
    match = re.search(r'([0-9a-f]{8}-[0-9a-f-]{27}|\d{6,})', path, re.I)
    return match.group(1).lower() if match else tail.lower()


def _function_tags(title):
    text = f" {(title or '').lower()} "
    return [tag for tag, keywords in FUNCTION_KEYWORDS.items() if any(keyword in text for keyword in keywords)]


def extract_job_links(entity, base_url, html, limit=120):
    pattern = JOB_PATHS.get(entity)
    if not pattern or not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    jobs = []
    seen = set()
    for link in soup.select('a[href]'):
        absolute = urljoin(base_url, link.get('href') or '')
        if not pattern.search(urlparse(absolute).path):
            continue
        identifier = _job_id(absolute)
        if identifier in seen:
            continue
        title = ' '.join(link.get_text(' ', strip=True).split())
        if not title:
            title = urlparse(absolute).path.rstrip('/').rsplit('/', 1)[-1].replace('-', ' ')
        seen.add(identifier)
        jobs.append({
            'id': identifier,
            'title': title,
            'url': absolute,
            'function_tags': _function_tags(title),
        })
        if len(jobs) >= limit:
            break
    return jobs


def diff_job_snapshots(previous, current):
    previous_by_id = {job['id']: job for job in previous or []}
    current_by_id = {job['id']: job for job in current or []}
    added = [job for identifier, job in current_by_id.items() if identifier not in previous_by_id]
    removed = [job for identifier, job in previous_by_id.items() if identifier not in current_by_id]
    clusters = Counter(tag for job in added for tag in job.get('function_tags') or [])
    removed_clusters = Counter(tag for job in removed for tag in job.get('function_tags') or [])
    return {
        'added_count': len(added),
        'removed_count': len(removed),
        'clusters': dict(clusters),
        'removed_clusters': dict(removed_clusters),
        'candidate_signal': (
            len(added) >= 3
            or len(removed) >= 3
            or any(count >= 2 for count in clusters.values())
            or any(count >= 2 for count in removed_clusters.values())
        ),
        'added': added,
        'removed': removed,
    }


def _load(path, default):
    try:
        with open(path, encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def collect_job_observations(pool_path='data/entity_pool.json', snapshot_path='data/job_snapshots.json', observed_at=None):
    pool = _load(pool_path, {})
    previous = _load(snapshot_path, {'entities': {}})
    observed_at = observed_at or datetime.now().astimezone().isoformat()
    snapshots = dict(previous.get('entities') or {})
    source_stats = {}
    candidates = []
    for entity in pool.get('entities') or []:
        jobs_point = next(
            (
                point for point in entity.get('observation_points') or []
                if point.get('type') == 'jobs' and point.get('instrumented') and point.get('url')
            ),
            None,
        )
        if not jobs_point:
            continue
        name = entity.get('name') or ''
        source_name = f'{name} Jobs'
        try:
            response = requests.get(jobs_point['url'], headers=HEADERS, timeout=15)
            response.raise_for_status()
            jobs = extract_job_links(name, response.url, response.text)
            fetch_status = 'success' if jobs else 'parse_failed'
        except requests.RequestException:
            jobs = []
            fetch_status = 'failed'
        snapshot_key = entity.get('id') or name.lower()
        has_baseline = snapshot_key in snapshots
        previous_jobs = (snapshots.get(snapshot_key) or {}).get('jobs') or []
        diff = diff_job_snapshots(previous_jobs, jobs) if fetch_status == 'success' and has_baseline else {
            'added_count': 0, 'removed_count': 0, 'clusters': {}, 'removed_clusters': {}, 'candidate_signal': False,
        }
        if fetch_status == 'success':
            snapshots[snapshot_key] = {
                'entity': name,
                'observed_at': observed_at,
                'jobs': jobs,
            }
        source_stats[source_name] = {
            'method': 'jobs_snapshot',
            'region': entity.get('region') or '',
            'status': 'ok' if fetch_status == 'success' else 'failed',
            'fetch_status': fetch_status,
            'count': diff.get('added_count', 0) + diff.get('removed_count', 0),
            'inventory_count': len(jobs),
            'signal_count': 1 if diff.get('candidate_signal') else 0,
            'added_count': diff.get('added_count', 0),
            'removed_count': diff.get('removed_count', 0),
            'clusters': diff.get('clusters', {}),
            'removed_clusters': diff.get('removed_clusters', {}),
        }
        if diff.get('candidate_signal'):
            candidates.append({
                'entity': name,
                'observed_at': observed_at,
                'added_count': diff['added_count'],
                'removed_count': diff['removed_count'],
                'clusters': diff['clusters'],
                'removed_clusters': diff.get('removed_clusters', {}),
            })
    return {
        'observed_at': observed_at,
        'source_count': len(source_stats),
        'raw_count': sum(row['inventory_count'] for row in source_stats.values()),
        'source_stats': source_stats,
        'candidate_signals': candidates,
    }, {'version': 1, 'generated_at': observed_at, 'entities': snapshots}


def write_job_snapshots(snapshot, path='data/job_snapshots.json'):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, 'w', encoding='utf-8') as handle:
        json.dump(snapshot, handle, ensure_ascii=False, indent=2)
    return target


def write_job_observation_metrics(metrics, path='data/job_observation_metrics.json'):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, 'w', encoding='utf-8') as handle:
        json.dump(metrics, handle, ensure_ascii=False, indent=2)
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pool-path', default='data/entity_pool.json')
    parser.add_argument('--snapshot-path', default='data/job_snapshots.json')
    parser.add_argument('--metrics-path', default='data/job_observation_metrics.json')
    args = parser.parse_args()
    metrics, snapshot = collect_job_observations(args.pool_path, args.snapshot_path)
    write_job_snapshots(snapshot, args.snapshot_path)
    write_job_observation_metrics(metrics, args.metrics_path)
    print(
        f"jobs observation | sources={metrics['source_count']} jobs={metrics['raw_count']} "
        f"candidates={len(metrics['candidate_signals'])}"
    )
    for source, row in metrics['source_stats'].items():
        print(
            f"{source} | fetch={row['fetch_status']} inventory={row['inventory_count']} changes={row['count']} "
            f"added={row['added_count']} removed={row['removed_count']} clusters={row['clusters']}"
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
