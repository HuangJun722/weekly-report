import io
import json
import os
import unittest.mock as mock

from generate_html import build_period_report, _load_aihot_archive

# 归档数据：不同日期文件内容（basename -> 文件内容 JSON 字符串）
ARCHIVE_FILES = {
    '2026-08-10.json': json.dumps({
        'items': [
            {'rank': 1, 'title': 'DeepSeek 发布 DeepSeek V4 Pro', 'heat': 245,
             'original_links': [{'url': 'https://example.com/dsv4'}], 'story_url': 'https://example.com/s1'},
        ]
    }, ensure_ascii=False),
    '2026-08-14.json': json.dumps({
        'items': [
            {'rank': 1, 'title': 'Google 发布 Gemini 3.7 Flash', 'heat': 211,
             'original_links': [{'url': 'https://example.com/gemini'}], 'story_url': 'https://example.com/s2'},
            {'rank': 2, 'title': 'DeepSeek 发布 DeepSeek V4 Pro', 'heat': 162,
             'original_links': [{'url': 'https://example.com/dsv4-2'}], 'story_url': 'https://example.com/s3'},
        ]
    }, ensure_ascii=False),
    '2026-08-20.json': json.dumps({
        'items': [
            {'rank': 1, 'title': 'xAI 发布 Grok 4.6', 'heat': 92,
             'original_links': [], 'story_url': 'https://example.com/s4'},
        ]
    }, ensure_ascii=False),
}


def _patch_archive(available_files=None, isdir=True):
    """Mock _load_aihot_archive 依赖的文件访问，按文件名提供不同内容。"""
    files = dict(available_files) if available_files else dict(ARCHIVE_FILES)

    def fake_open(path, *args, **kwargs):
        name = os.path.basename(str(path))
        return io.StringIO(files.get(name, '{}'))

    return (
        mock.patch('generate_html.os.listdir', return_value=sorted(files.keys())),
        mock.patch('generate_html.os.path.isdir', return_value=isdir),
        mock.patch('generate_html.open', side_effect=fake_open),
    )


def test_weekly_mode_includes_current_day_beyond_event_end_date():
    """周报模式按自然周归属：本周内（含当天）归档应被包含，即使站内事件截止日更早。"""
    patches = _patch_archive()
    for p in patches:
        p.start()
    try:
        items = _load_aihot_archive('2026-08-10', '2026-08-13', weekly=True)
    finally:
        for p in reversed(patches):
            p.stop()
    titles = [it['title'] for it in items]
    # 8/14 是本周（8/10-8/16）内，必须被包含
    assert 'Google 发布 Gemini 3.7 Flash' in titles
    # 8/10 在 start 内
    assert 'DeepSeek 发布 DeepSeek V4 Pro' in titles
    # 8/20 超出自然周（下周），不包含
    assert 'xAI 发布 Grok 4.6' not in titles


def test_monthly_mode_includes_current_day_beyond_event_end_date():
    """月报模式按自然月归属：本月内归档应被包含，不受站内事件截止日限制。"""
    patches = _patch_archive()
    for p in patches:
        p.start()
    try:
        items = _load_aihot_archive('2026-08-01', '2026-08-13', weekly=False)
    finally:
        for p in reversed(patches):
            p.stop()
    titles = [it['title'] for it in items]
    assert 'Google 发布 Gemini 3.7 Flash' in titles  # 8/14 本月内
    assert 'xAI 发布 Grok 4.6' in titles             # 8/20 本月内
    # 跨文件去重：DeepSeek 标题在 8/10 和 8/14 都出现，只留一条
    assert titles.count('DeepSeek 发布 DeepSeek V4 Pro') == 1


def test_archive_builds_fields_and_dedupes():
    """返回字段（title/heat/url/date）正确，跨文件同标题去重，url 优先 original_links。"""
    patches = _patch_archive({'2026-08-14.json': ARCHIVE_FILES['2026-08-14.json']})
    for p in patches:
        p.start()
    try:
        items = _load_aihot_archive('2026-08-01', '2026-08-14', weekly=False)
    finally:
        for p in reversed(patches):
            p.stop()
    assert len(items) == 2
    gemini = next(it for it in items if it['title'].startswith('Google'))
    assert gemini['heat'] == 211
    assert gemini['url'] == 'https://example.com/gemini'   # 优先 original_links
    assert gemini['date'] == '2026-08-14'
    assert items[0]['rank'] == 1


def test_archive_missing_dir_returns_empty():
    """归档目录不存在时返回空列表，页面隐藏小节。"""
    patches = _patch_archive(isdir=False)
    for p in patches:
        p.start()
    try:
        assert _load_aihot_archive('2026-08-01', '2026-08-14', weekly=False) == []
    finally:
        for p in reversed(patches):
            p.stop()


def test_build_period_report_carries_aihot_hot():
    """build_period_report 返回 aihot_hot 字段，透传归档内容。"""
    patches = _patch_archive()
    for p in patches:
        p.start()
    try:
        report = build_period_report([], '2026-08-01', '2026-08-13', '2026年8月', '2026-08', 'mature')
    finally:
        for p in reversed(patches):
            p.stop()
    assert 'aihot_hot' in report
    titles = [it['title'] for it in report['aihot_hot']]
    assert 'Google 发布 Gemini 3.7 Flash' in titles
    # 最多 10 条
    assert len(report['aihot_hot']) <= 10
