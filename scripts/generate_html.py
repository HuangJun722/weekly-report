"""
生成全球互联网动态情报站 HTML 页面
"""
import json
import os
from datetime import datetime, timedelta
from jinja2 import Template

def load_events():
    with open('data/events.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        # 旧格式：扁平数组 → 按日期分组
        grouped = {}
        for event in data:
            date = event.get('date', datetime.now().isoformat())[:10]
            if date not in grouped:
                grouped[date] = []
            # 补充缺失字段（兼容旧数据）
            event.setdefault('why_important', event.get('summary', '待分析')[:25])
            event.setdefault('impact_scope', '未知')
            event.setdefault('impact_range', '行业')
            event.setdefault('companies', [])
            event.setdefault('level', 'C')
            event.setdefault('score', 5)
            event.setdefault('region', '未知')
            grouped[date].append(event)
        return grouped
    return data

def enrich_event(event):
    """确保每条事件都有必要字段"""
    event.setdefault('why_important', event.get('summary', '待分析')[:25])
    event.setdefault('impact_scope', '未知')
    event.setdefault('impact_range', '行业')
    event.setdefault('companies', [])
    event.setdefault('level', 'C')
    event.setdefault('score', 5)
    event.setdefault('region', '未知')
    return event

def get_top_events(events, max_count=10):
    """获取按 score 排序的所有事件（去重）"""
    seen = set()
    result = []
    dates = sorted(events.keys(), reverse=True)
    for date in dates:
        for event in events[date]:
            enrich_event(event)
            if event['url'] not in seen:
                seen.add(event['url'])
                result.append(event)
    # 按 score 降序
    result.sort(key=lambda x: x.get('score', 5), reverse=True)
    return result

def get_all_companies(events):
    """提取所有公司名"""
    companies = set()
    for date_events in events.values():
        for e in date_events:
            enrich_event(e)
            for c in e.get('companies', []):
                if c:
                    companies.add(c)
    return sorted(companies)

def generate_html():
    events = load_events()
    all_top = get_top_events(events)
    today = datetime.now().strftime('%Y-%m-%d')

    # 今日事件
    today_events = events.get(today, [])
    for e in today_events:
        enrich_event(e)

    # 本周最重要（本周所有去重事件）
    week_events = [e for e in all_top if e.get('date', '').startswith(
        (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')[:7]
    )]
    # 如果本周没有数据，用所有数据
    if not week_events:
        week_events = all_top[:15]

    all_companies = get_all_companies(events)
    sorted_dates = sorted(events.keys(), reverse=True)

    template = Template(open('scripts/template.html', 'r', encoding='utf-8').read())

    html = template.render(
        top_events=today_events + week_events,  # 今日 + 本周
        all_events=events,
        sorted_dates=sorted_dates,
        all_companies=all_companies,
        update_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        today=today,
    )

    os.makedirs('docs', exist_ok=True)
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    total = sum(len(v) for v in events.values())
    print(f"✓ 生成完成：{len(events)} 天数据，共 {total} 条事件")

if __name__ == '__main__':
    generate_html()
