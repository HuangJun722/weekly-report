import json
from datetime import datetime
from jinja2 import Template

def load_events():
    with open('data/events.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_html(events):
    template = Template('''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>全球互联网热点周报</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
               background: #f5f5f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: white;
                     padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 10px; }
        .update-time { color: #666; font-size: 14px; margin-bottom: 30px; }
        .level-section { margin-bottom: 40px; }
        .level-title { font-size: 20px; color: #333; margin-bottom: 15px;
                       padding-bottom: 10px; border-bottom: 2px solid #eee; }
        .event { padding: 15px; margin-bottom: 10px; background: #fafafa;
                 border-radius: 4px; transition: background 0.2s; }
        .event:hover { background: #f0f0f0; }
        .event-title { font-size: 16px; color: #1a73e8; text-decoration: none;
                       font-weight: 500; }
        .event-title:hover { text-decoration: underline; }
        .event-meta { font-size: 12px; color: #999; margin-top: 5px; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 3px;
                 font-size: 11px; margin-right: 8px; }
        .badge-A { background: #e8f5e9; color: #2e7d32; }
        .badge-B { background: #e3f2fd; color: #1565c0; }
        .badge-C { background: #fff3e0; color: #e65100; }
        .badge-D { background: #fce4ec; color: #c2185b; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 全球互联网热点周报</h1>
        <div class="update-time">最后更新：{{ update_time }}</div>

        {% for level in ['A', 'B', 'C', 'D'] %}
        {% set level_events = events_by_level.get(level, []) %}
        {% if level_events %}
        <div class="level-section">
            <div class="level-title">{{ level }} 级事件（{{ level_events|length }} 条）</div>
            {% for event in level_events %}
            <div class="event">
                <a href="{{ event.url }}" target="_blank" class="event-title">{{ event.title }}</a>
                <div class="event-meta">
                    <span class="badge badge-{{ event.level }}">{{ event.level }}级</span>
                    <span>{{ event.source }}</span>
                    <span>重要性：{{ event.score }}/10</span>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        {% endfor %}
    </div>
</body>
</html>
    ''')

    events_by_level = {'A': [], 'B': [], 'C': [], 'D': []}
    for event in events:
        events_by_level[event['level']].append(event)

    html = template.render(
        events_by_level=events_by_level,
        update_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    return html

def main():
    events = load_events()
    html = generate_html(events)

    import os
    os.makedirs('docs', exist_ok=True)
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✓ HTML 生成完成")

if __name__ == '__main__':
    main()

