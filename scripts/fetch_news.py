import json
import os
from datetime import datetime
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

genai.configure(api_key=os.environ['GEMINI_API_KEY'])

SOURCES = {
    'hackernews': 'https://news.ycombinator.com/',
    'github': 'https://github.com/trending'
}

def fetch_hackernews():
    response = requests.get(SOURCES['hackernews'])
    soup = BeautifulSoup(response.text, 'html.parser')
    items = []
    for item in soup.select('.athing')[:10]:
        title = item.select_one('.titleline a').text
        url = item.select_one('.titleline a')['href']
        items.append({'title': title, 'url': url, 'source': 'Hacker News'})
    return items

def fetch_github_trending():
    response = requests.get(SOURCES['github'])
    soup = BeautifulSoup(response.text, 'html.parser')
    items = []
    for repo in soup.select('article.Box-row')[:10]:
        title = repo.select_one('h2 a').text.strip().replace('\n', '').replace(' ', '')
        url = 'https://github.com' + repo.select_one('h2 a')['href']
        items.append({'title': title, 'url': url, 'source': 'GitHub Trending'})
    return items

def analyze_importance(event):
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    prompt = f"评估这个科技事件的重要性（只返回1-10的数字）：{event['title']}"
    try:
        response = model.generate_content(prompt)
        return int(response.text.strip())
    except:
        return 5

def classify_level(score):
    if score >= 9: return 'A'
    if score >= 7: return 'B'
    if score >= 5: return 'C'
    return 'D'

def main():
    events = []
    all_items = []
    all_items.extend(fetch_hackernews())
    all_items.extend(fetch_github_trending())

    for item in all_items:
        score = analyze_importance(item)
        if score >= 5:
            events.append({
                'title': item['title'],
                'url': item['url'],
                'source': item['source'],
                'level': classify_level(score),
                'score': score,
                'date': datetime.now().isoformat()
            })

    os.makedirs('data', exist_ok=True)
    with open('data/events.json', 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"✓ 爬取完成，共 {len(events)} 条事件")

if __name__ == '__main__':
    main()

