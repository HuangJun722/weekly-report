#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取 AIHOT 大模型排行榜 → data/model_leaderboard.json

用法:
    /c/Users/16120/AppData/Local/Python/bin/python scripts/fetch_model_leaderboard.py

输出结构:
    data/model_leaderboard.json
    - source: 来源信息（名称 / 链接 / 说明）
    - ranking: 主榜前 30 名（共识分排名）
    - official_sources: 12 家官方评测榜单明细（每张前 80 名）

说明:
    - AIHOT 模型榜无公开 API，数据以 SSR 形式内嵌在页面中。
    - 主榜从 leaderboard 页渲染 DOM 提取；官方榜单从 methodology 页的
      React Server Components payload 提取（每张榜按 defaultMetricKey 过滤）。
    - 榜单 description 字段在 SSR 中为乱码（服务端编码损坏），改用硬编码中文说明。
"""

import json
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

LB_URL = "https://aihot.virxact.com/leaderboard"
METH_URL = "https://aihot.virxact.com/leaderboard/methodology"
BASE_URL = "https://aihot.virxact.com"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
}

# 官方榜单来源说明（硬编码中文版；AIHOT SSR 中该字段为乱码不可用）
SOURCE_NOTES = {
    "artificial-analysis": "只使用以统一环境复跑多项当前评测形成的 Intelligence Index；价格只作背景信息。",
    "epoch-eci": "将五十多项跨时期评测拟合到同一能力尺度。",
    "livebench-general": "以持续更新、答案可验证的七类任务衡量当前模型。",
    "arena-text": "用匿名两两盲选补充客观题库无法覆盖的整体回答体验。",
    "arena-webdev": "用匿名两两盲选衡量 Web 开发实战能力。",
    "eqbench-4": "观察对话中的情绪理解；创意写作、长文和 Judgemark 不合并成一张通用票。",
    "vals-index": "综合金融与编码任务；只把 Overall 作为一张来源票。",
    "mercor-apex-agents": "衡量投行、咨询和法律长任务；配置明细保留，但成绩归到基础模型。",
    "agents-last-exam": "保存 full split 的 harness 与推理档位明细，成绩按基础模型归并。",
    "deepswe-v1-1": "在统一 mini-swe-agent harness 下比较代码模型；成绩按基础模型归并。",
    "llm2014-agentic": "保留八个任务的等级与 scaffold 明细；成绩按基础模型归并。",
    "llm2014-reasoning": "专项推理评测，成绩按基础模型归并。",
}

TOP_N = 80  # 每张官方榜单保留前 N 名


def _session():
    """忽略系统代理（环境含 SOCKS 代理配置，requests 缺少 socks 依赖），直连。"""
    s = requests.Session()
    s.trust_env = False
    return s


def _fetch(session, url):
    r = session.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def _js_unescape(s):
    r"""解码 Next.js RSC payload 中的 JS 字符串转义（uXXXX / \\ / \" / \n 等）。"""
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            nxt = s[i + 1]
            if nxt == "u":
                try:
                    out.append(chr(int(s[i + 2:i + 6], 16)))
                    i += 6
                except ValueError:
                    out.append(nxt)
                    i += 2
            elif nxt == "n":
                out.append("\n"); i += 2
            elif nxt == "t":
                out.append("\t"); i += 2
            elif nxt == '"':
                out.append('"'); i += 2
            elif nxt == "\\":
                out.append("\\"); i += 2
            elif nxt == "/":
                out.append("/"); i += 2
            else:
                out.append(nxt); i += 2
        else:
            out.append(c); i += 1
    return "".join(out)


def _extract_sources_json(html):
    """从 methodology 页 RSC payload 中提取 sources 数组（标准 JSON）。"""
    payloads = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html, re.S)
    for p in payloads:
        d = _js_unescape(p)
        idx = d.find('"sources"')
        if idx < 0:
            continue
        start = d.find("[", idx)
        depth = 0
        in_str = False
        esc = False
        end = -1
        for i in range(start, len(d)):
            c = d[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c in "[{":
                    depth += 1
                elif c in "]}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
        if end > 0:
            return json.loads(d[start:end + 1])
    raise ValueError("methodology 页未找到 sources 数据")


def _parse_ranking(html):
    """从 leaderboard 页渲染 DOM 提取主榜前 30 名。"""
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all(class_="lb-row")
    ranking = []
    for r in rows:
        rank_el = r.find(class_="lb-rank")
        name_el = r.find(class_="lb-model-copy")
        date_el = r.find(class_="lb-release-date")
        comp_el = r.find(class_="lb-completeness")
        price_el = r.find(class_="lb-pricing")
        score_el = r.find(class_="lb-score")
        if not (name_el and score_el):
            continue
        price = _parse_pricing(price_el)
        ranking.append({
            "rank": int(rank_el.get_text(strip=True)) if rank_el else len(ranking) + 1,
            "name": name_el.find("strong").get_text(strip=True) if name_el.find("strong") else "",
            "provider": name_el.find("small").get_text(strip=True) if name_el.find("small") else "",
            "release_date": date_el.find("strong").get_text(strip=True) if date_el and date_el.find("strong") else "",
            "completeness": comp_el.find("strong").get_text(strip=True) if comp_el and comp_el.find("strong") else "",
            "input_price": price[0],
            "output_price": price[1],
            "consensus_score": _to_float(score_el.find("strong").get_text(strip=True)) if score_el.find("strong") else None,
            "detail_url": (BASE_URL + r.get("href")) if r.get("href", "").startswith("/") else r.get("href", ""),
        })
    return ranking


def _parse_pricing(price_el):
    if not price_el:
        return ("", "")
    if price_el.find(class_="lb-metadata-empty"):
        return ("暂无", "暂无")
    spans = price_el.find_all("span")
    vals = []
    for sp in spans[:2]:
        st = sp.find("strong")
        vals.append(st.get_text(strip=True) if st else "")
    while len(vals) < 2:
        vals.append("")
    return (vals[0], vals[1])


def _to_float(s):
    s = (s or "").strip().replace(",", "").replace("%", "")
    try:
        return float(s)
    except ValueError:
        return None


def _fmt_score(v):
    """把原始分数格式化为展示值：整数去 .0，>=1 保留 1 位小数，<1 保留 3 位有效小数。"""
    if v is None:
        return None
    if v == int(v):
        return str(int(v))
    if v >= 1:
        return f"{v:.1f}"
    return f"{v:.3f}"


def _build_official_sources(sources):
    out = []
    for s in sources:
        models = s.get("models") or []
        default_mk = s.get("defaultMetricKey")
        metric_names = {m.get("key"): m.get("name") for m in (s.get("metrics") or [])}
        filtered = [m for m in models if m.get("metricKey") == default_mk]
        if not filtered:
            filtered = models
        filtered.sort(key=lambda m: (m.get("sourceRank") or 99999))
        top = filtered[:TOP_N]
        metric_label = metric_names.get(default_mk, "")
        out.append({
            "key": s.get("key"),
            "name": s.get("name"),
            "short_name": s.get("shortName"),
            "operator": s.get("operator"),
            "note": SOURCE_NOTES.get(s.get("key"), ""),
            "fetched_at": s.get("fetchedAt", ""),
            "metric_name": metric_label,
            "total_count": len(filtered),
            "models": [
                {
                    "rank": m.get("sourceRank"),
                    "name": m.get("sourceModelName"),
                    "provider": m.get("provider"),
                    "score": _fmt_score(m.get("rawScore")),
                }
                for m in top
            ],
        })
    return out


def main():
    s = _session()
    lb_html = _fetch(s, LB_URL)
    meth_html = _fetch(s, METH_URL)

    ranking = _parse_ranking(lb_html)
    sources = _extract_sources_json(meth_html)
    official = _build_official_sources(sources)

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    payload = {
        "generated_at": now,
        "fetched_date": now[:10],
        "source": {
            "name": "AIHOT 大模型排行榜",
            "leaderboard_url": LB_URL,
            "methodology_url": METH_URL,
            "rules_url": BASE_URL + "/leaderboard/rules",
            "note": "汇总多家公开模型评测榜单，用统一方法计算 AIHOT 共识分。共识分来自 AIHOT 算法，本页仅复制其展示结果。",
        },
        "ranking": ranking,
        "official_sources": official,
    }

    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "model_leaderboard.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    n_rank = len(ranking)
    n_sources = len(official)
    n_models = sum(len(o["models"]) for o in official)
    print(f"OK | 主榜 {n_rank} 名 | 官方榜单 {n_sources} 家 | 榜单模型 {n_models} 行 | {out_path}")


if __name__ == "__main__":
    main()
