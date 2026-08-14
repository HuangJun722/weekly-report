#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取 AIHOT 热点榜 → data/aihot_hot.json

用法:
    /c/Users/16120/AppData/Local/Python/bin/python scripts/fetch_aihot_hot.py

输出结构:
    data/aihot_hot.json
    - generated_at: 抓取时间
    - fetched_date: 日期
    - items: 热点榜列表，每条含
      - rank / title / heat(热度值) / heat_raw
      - sources: 信源标注列表（"公众号：数字生命卡兹克" 等）
      - summary: AI 综述（story 详情页 description）
      - original_links: [{url, domain}] — story 详情页 isBasedOn 原始来源链接
      - story_url: AIHOT story 详情页地址（备用）

说明:
    - AIHOT 无公开 API，热点数据以 Next.js SSR 渲染。
    - 列表从 /hot 页 JSON-LD ItemList 提取标题与 story 链接，
      热度值与信源标注从渲染 DOM 提取。
    - 每条 story 进详情页，从 JSON-LD NewsArticle 提取 headline/description/isBasedOn。
    - 页面 HTML 通过 requests 直连抓取（复用 fetch_model_leaderboard.py 的降级模式）。
"""

import json
import os
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

HOT_URL = "https://aihot.virxact.com/hot"
STORY_URL = "https://aihot.virxact.com/story/{}"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
}

MAX_ITEMS = 10  # 最多抓取的热点条数
STORY_FETCH_INTERVAL = 0.4  # 进详情页的间隔秒数（防反爬）


def _session():
    s = requests.Session()
    s.trust_env = False
    return s


def _fetch(session, url):
    r = session.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def _extract_itemlist(html):
    """从 JSON-LD 提取热点列表（ItemList）。"""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict) and data.get("@type") == "ItemList":
            items = []
            for el in data.get("itemListElement", []):
                items.append({
                    "name": el.get("name", ""),
                    "story_url": el.get("url", ""),
                })
            if items:
                return items
    return []


def _parse_heat_and_sources(html, story_urls):
    """从 /hot 渲染 DOM 提取热度值与信源标注，按 story 顺序对齐。"""
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all(class_="hot-rank-row")
    result = []
    seen = set()
    for row in rows:
        a = row.find(class_="hot-rank-link") or row.find("a", href=True)
        if not a or not a.get("href"):
            continue
        href = a["href"]
        if not href.startswith("/story/"):
            continue
        if href in seen:
            continue
        seen.add(href)
        # 标题 = 列表行标题（hot-rank-link 文本）
        title = a.get_text(strip=True)
        # 热度值：summary 内 "142 热度值"
        heat = None
        details = row.find(class_="hot-rank-sources")
        if details:
            heat_m = re.search(r'(\d+)\s*热度值', details.get_text(" ", strip=True))
            if heat_m:
                heat = int(heat_m.group(1))
        # 信源：dup-tooltip-item 内每条一个，过滤 "共 N 条围观票" 等统计项
        sources = []
        if details:
            for item_el in details.find_all(class_="dup-tooltip-item"):
                t = item_el.get_text(" ", strip=True)
                if not t or t in sources or re.search(r'\d+\s*条围观票', t):
                    continue
                sources.append(t)
        result.append({
            "story_url": STORY_URL.format(href.rstrip("/").split("/")[-1]),
            "title": title,
            "heat": heat,
            "sources": sources,
        })
    # 按列表顺序对齐（JSON-LD 的顺序为准）
    by_url = {r["story_url"]: r for r in result}
    ordered = []
    for item in story_urls:
        r = by_url.get(item["story_url"])
        if r:
            ordered.append(r)
        else:
            ordered.append({"story_url": item["story_url"], "title": item["name"],
                            "heat": None, "sources": []})
    return ordered


def _extract_newsarticle(html):
    """从 story 详情页 JSON-LD 提取 NewsArticle：headline/description/isBasedOn。"""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict) and data.get("@type") == "NewsArticle":
            based_on = data.get("isBasedOn") or []
            if isinstance(based_on, str):
                based_on = [based_on]
            return {
                "headline": data.get("headline", ""),
                "description": data.get("description", ""),
                "original_links": based_on,
            }
    return {"headline": "", "description": "", "original_links": []}


def _link_domain(url):
    from urllib.parse import urlparse
    try:
        return urlparse(url).netloc or ""
    except Exception:
        return ""


def _dedupe_links(links):
    """去重原始链接：同域名只保留第一条（如多条 x.com 推文只展示一个入口）。"""
    seen_url, seen_domain, out = set(), set(), []
    for u in links:
        if not u or u in seen_url:
            continue
        domain = _link_domain(u)
        if domain in seen_domain:
            continue
        seen_url.add(u)
        seen_domain.add(domain)
        out.append({"url": u, "domain": domain})
    return out


def main():
    s = _session()
    hot_html = _fetch(s, HOT_URL)

    itemlist = _extract_itemlist(hot_html)
    if not itemlist:
        print("WARN | /hot 页未找到 ItemList，尝试从 DOM 提取")
    rows = _parse_heat_and_sources(hot_html, itemlist)

    items = []
    for row in rows[:MAX_ITEMS]:
        try:
            story_html = _fetch(s, row["story_url"])
            article = _extract_newsarticle(story_html)
        except Exception as exc:
            print(f"  ⚠️ story 详情失败: {row['title'][:40]} → {exc}")
            article = {"headline": "", "description": "", "original_links": []}
        time.sleep(STORY_FETCH_INTERVAL)
        items.append({
            "rank": len(items) + 1,
            "title": article.get("headline") or row.get("title") or "",
            "list_title": row.get("title") or "",
            "heat": row.get("heat"),
            "sources": row.get("sources") or [],
            "summary": article.get("description") or "",
            "original_links": _dedupe_links(article.get("original_links") or []),
            "story_url": row.get("story_url") or "",
        })

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    payload = {
        "generated_at": now,
        "fetched_date": now[:10],
        "source": {
            "name": "AIHOT 热点榜",
            "url": HOT_URL,
            "note": "过去 48 小时最热的 AI 事件，按精选报道与讨论热度实时排序。本页为全球 AI 视野补充，点击跳转原始来源。",
        },
        "items": items,
    }

    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

    out_path = os.path.join(base_dir, "aihot_hot.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    archive_dir = os.path.join(base_dir, "aihot_hot")
    os.makedirs(archive_dir, exist_ok=True)
    archive_path = os.path.join(archive_dir, f"{payload['fetched_date']}.json")
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"OK | AIHOT 热点 {len(items)} 条 | 有原始链接 {sum(1 for i in items if i['original_links'])} 条 | {out_path}")
    print(f"OK | 已归档 {archive_path}")


if __name__ == "__main__":
    main()
