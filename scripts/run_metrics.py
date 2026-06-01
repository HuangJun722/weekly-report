"""Persist collection-run metrics for later health checks."""

import json
from pathlib import Path


DEFAULT_PATH = Path('data/run_metrics.json')


def _read_metrics(path):
    if not path.exists():
        return []
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def write_run_metrics(metrics, path=DEFAULT_PATH, keep=30):
    """Append one run metrics record, replacing the same run_id if present."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = _read_metrics(path)
    run_id = metrics.get('run_id')
    if run_id:
        records = [record for record in records if record.get('run_id') != run_id]
    records.append(metrics)
    records = records[-keep:]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    return path


def latest_run_metrics(path=DEFAULT_PATH):
    records = _read_metrics(Path(path))
    return records[-1] if records else {}
