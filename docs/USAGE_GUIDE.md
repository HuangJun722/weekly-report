# 全球互联网动态情报站 — 使用指南

> 自动采集非中美地区互联网/科技动态，AI 分析后展示为情报产品。
> 在线访问：[https://huangjun722.github.io/weekly-report/](https://huangjun722.github.io/weekly-report/)

---

## 为什么设计这个网站

### 背景

中美互联网动态有大量中文媒体报道（36kr、虎嗅、晚点等），但**欧洲、亚太、中东、非洲、拉美**的科技生态在国内几乎没有系统性信息渠道。偶尔有一篇报道也是碎片化的，无法形成持续追踪。

这个站的目标很简单：**每天花 30 秒扫一眼，知道非中美科技世界在发生什么。**

### 定位

- **情报性质**，不是新闻聚合。不只是"发生了什么"，还试图回答"所以呢？对谁有影响？"
- **低成本运营**，零云成本（GitHub Pages + GitHub Actions），AI 分析每天约 ¥0.003
- **排除中美**，聚焦被主流中文媒体忽视的地区

---

## 信息架构（三层设计）

页面从上到下分三层，对应三种使用深度：

### Layer 1：今日判断（30 秒扫读）

顶部的深色区块：

- **一句话判断**：AI 基于今日信号事件生成的趋势总结，比如"资金流向欧洲太空数据中心、出行科技等赛道"
- **3 个信号卡片**：今日最重要的 3 条事件，点进去看原文

用户场景：每天早上打开，30 秒知道今天什么方向在动。

### Layer 2：趋势主题分组（3 分钟浏览）

今日要点 tab 下，事件按**趋势主题**分组（如"中东 FinTech 赛道升温""欧洲太空经济融资活跃"），每组一个标题 + 若干事件卡片。同一主题的事件放在一起看，能看出产业链联动。

### Layer 3：全部事件 + 搜索筛选（需要时）

切换到"全部事件"tab：

- **按区域筛选**：欧洲 / 亚太 / 中东 / 非洲 / 拉美
- **按事件类型筛选**：融资 / 并购 / 财报 / 战略
- **搜索框**：搜索标题、描述、公司名
- **公司导航**：右侧（或下拉）按公司名跳转
- **日期翻页**：底部"前一日/后一日"浏览历史

### 中资出海独立 tab

涉及中国公司出海（TikTok、Shein、阿里云等）的事件单独放在"中资出海"tab，不与主信息流混合。

---

## 功能说明

### 今日要点 vs 全部事件

两个 tab 使用完全相同的卡片样式，区别在于：
- **今日要点**：趋势主题分组 + 当日统计 + 信号卡片
- **全部事件**：按区域/类型筛选 + 搜索功能更强

### 日期翻页

底部"前一日"和"后一日"按钮可浏览历史数据。翻页时整个"今日要点"面板（判断 + 信号 + 趋势分组）一起切换，已预计算好，无需重新请求。

### 暗色模式

右上角按钮切换亮色/暗色。状态保存在 `localStorage`，下次打开自动恢复。首次访问跟随系统 `prefers-color-scheme`。

### 事件卡片

每条事件卡片包含：

| 元素 | 说明 |
|------|------|
| 缩略图 | 左侧 100px×70px，RSS media_content → og:image 两级兜底 |
| 区域标签 | 欧洲 / 亚太 / 中东 / 非洲 / 拉美（可点击筛选） |
| 情报标签 | 资金流向 / 合作机会 / 警示信号 / 趋势信号 / 中资出海 |
| 来源 | 信源名称 |
| 标题 | 可点击跳转原文 |
| 事件描述 | AI 生成或程序提取的中文摘要，包含公司名 + 具体动作 |
| 公司标签 | 如属于 27 家监控公司之一，显示公司名 |

---

## 数据来源

### RSS 信源（主力，14 个）

| 信源 | 区域 | 状态 |
|------|------|------|
| TechCrunch | 全球 | ✅ |
| TechCrunch VC | 全球 | ✅ |
| Tech.eu | 欧洲 | ✅ |
| The Next Web | 欧洲 | ✅ |
| Tech in Asia | 亚太 | ✅ |
| TechWire Asia | 亚太 | ✅ |
| WAMDA | 中东 | ✅ |
| MENAbytes | 中东 | ✅ |
| TechCabal | 非洲 | ✅ |
| Disrupt Africa | 非洲 | ✅ |
| Techpoint | 非洲 | ✅ |
| Ventureburn | 非洲 | ✅ |
| LAVCA | 拉美 | ✅ |
| Contxto | 拉美 | ✅ |

### HTML 降级采集（备用）

| 信源 | 区域 | 说明 |
|------|------|------|
| DealStreetAsia | 亚太 | JS SPA，降级成功率低 |

### 已移除信源

| 信源 | 原因 |
|------|------|
| Sifted | Cloudflare 拦截 |
| DealStreetAsia RSS | 503 不可用 |
| e27 | Cloudflare + JS 渲染 |
| EU-Startups | Cloudflare 拦截 |
| Bloomberg | 噪声太大，非科技 |

### 27 家公司监控

每天通过 Google News RSS 追踪指定公司的新闻。每家公司最多 3 条/天，7 天日期窗口，URL 去重。

覆盖公司：ByteDance/TikTok、Tencent、Alibaba、JD.com、Kuaishou、Ant Group、Meituan、Kakao、Naver、Rakuten、Sea Limited、Grab、Gojek、VNG Group、Yahoo、Cyberagent、Adyen、Zalando、Allegro、Trendyol、MercadoLibre、Rappi、Noon、Careem、Tabby、Kaspi.kz、Jumia、Konga

---

## 技术架构

### 数据流

```
RSS 信源 ──┐
Google News ├──→ fetch_news.py ──→ events.json ──→ generate_html.py ──→ docs/index.html ──→ GitHub Pages
HTML 降级 ──┘                          ↑
                                   data/summary.json（AI 趋势分析）
```

### 三层评分筛选

所有事件经过 `_calc_score()` 评分后分流：

| 分数 | 处理方式 | 覆盖率 |
|------|----------|--------|
| ≥7 或 funding/ma/earnings | AI 深度分析（豆包 API） | 主力 |
| ≥4 或 is_company | 程序生成描述 | 零成本 |
| <4 | 丢弃 | 过滤噪声 |

### AI 分析管线

三个 P0 Agent，全部走豆包 API：

1. **AI 趋势分析**（`build_daily_ai_summary`）：基于当日信号事件生成"今日判断"
2. **AI 标题改写**（`rewrite_titles_for_display`）：改写程序层泛化描述
3. **AI 情报评分**（`ai_quality_judge`）：对 low-signal 事件做 1-5 分评分，≤2 分丢弃

### RSS Feed

`generate_feed.py` 将 events.json 转换为 Atom XML，输出最新一天全部事件到 `docs/feed.xml`。每天随采集流程自动更新。

- **Feed 地址**：https://huangjun722.github.io/weekly-report/feed.xml
- **格式**：Atom XML（标准 RSS 阅读器均可消费）
- **内容**：最新一天全部事件，不是固定条数
- **用途**：供外部 CLI / RSS 阅读器订阅每日新闻

### 部署

- GitHub Actions 每天定时自动运行
- 采集 → AI 分析 → HTML 生成 → Feed 生成 → 推送到 `docs/` → GitHub Pages 部署
- 也支持 `workflow_dispatch` 手动触发

---

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API Key
# DeepSeek（本地开发主力）：https://platform.deepseek.com/
# 豆包（GHA 主力，本地备用）：https://console.volcengine.com/ark/
# 方式一：加密存储
cp .env.example .env
py scripts/encrypt_key.py
# 方式二：直接写 .env
# DEEPSEEK_API_KEY=sk-xxx
# DOUBAO_API_KEY=xxx
# DOUBAO_MODEL=ep-20260409223830-dnt5b

# 采集 + 分析 + 生成（全流程）
py scripts/fetch_news.py
py scripts/generate_html.py --force

# 仅生成 HTML（使用已有数据）
py scripts/generate_html.py --preview   # 预览模式，生成到 preview.html
py scripts/generate_html.py --force     # 生产模式，覆盖 index.html

# 本地预览
python -m http.server 8000 --directory docs
# 打开 http://localhost:8000/
```

> **Windows 注意**：控制台编码可能不支持 emoji，加 `-X utf8` 参数运行。

---

## 踩过的坑

### DeepSeek API 在 GitHub Actions 结构性不可达

**症状**：workflow 每次都在 DeepSeek 调用上超时，60 分钟跑不完。

**根因**：GitHub Actions 的 US-west runner 无法直连 `api.deepseek.com`（中国 API），每次 POST 请求 Read timed out，三次重试每批次浪费 ~90s，33 批次 × 90s ≈ 50 分钟浪费在等待超时上。

**解决**：检测 `GITHUB_ACTIONS` 环境变量，GHA 环境直接跳过 DeepSeek，只用豆包。本地开发 DeepSeek 正常。

### 豆包 API 返回非 JSON

**症状**：豆包批次调用偶尔返回格式异常的 JSON，解析失败。

**解决**：增加 JSON 修正解析（去除 markdown 代码块标记 ` ```json `），失败后 5s 重试一次，再失败降级到程序生成。

### 事件分析全是泛化描述

**症状**：事件卡片显示"亚太科技公司财报披露""欧洲科技公司战略动态"——完全看不出具体是哪家公司、发生了什么。

**根因**：`GENERIC_REASONS` 使用精确集合匹配（`existing_reason in GENERIC_REASONS`），但程序层产出的 `"{region}科技公司财报披露"` 和集合中的 `"中资科技公司财报披露"` 不匹配（区域前缀不同）。

**解决**：改为子串匹配（`any(p in existing_reason for p in GENERIC_REASONS)`），同时 `_build_reason()` 接收 `company_name` 参数，正则提取失败时直接用已知公司名。最后兜底用标题前段代替区域模板。

### 公司名提取吃掉前文数字

**症状**：`"Baillie Gifford Dumps 248,000 MercadoLibre Shares"` → 提取出 `"000 MercadoLibre"`。

**根因**：`_extract_subject()` 的词边界回溯用 `isalnum()` 检查，数字（`0`）被当成单词的一部分捕获。

**解决**：改为 `isalpha()`，只回退字母不包含数字。

### RSS 信源频繁失效

| 信源 | 失效原因 | 处理 |
|------|----------|------|
| Sifted | Cloudflare 拦截 | 移除 |
| DealStreetAsia RSS | 503 | 改为 HTML 降级 |
| e27 | Cloudflare + JS 渲染 | 移除 |
| EU-Startups | Cloudflare | 移除 |
| Disrupt Africa | RSS 挂了一段时间 | 恢复后重新加入 |

### Workflow push 冲突

**症状**：本地 push 代码 + workflow 自动 push HTML 互相踩，产生 merge 冲突。

**解决**：push 前先 `git fetch` + `git rebase origin/main`，遇到 `docs/index.html` 冲突直接用 `--theirs`（自动生成物以 workflow 版本为准）。

### Workflow 预检不足导致空跑

**症状**：RSS 全部不可达（网络问题）时，workflow 照常跑满 5 分钟，生成空页面。

**解决**：增加 RSS 信源可达性预检（`curl --max-time 8`），全部不可达时跳过采集直接写空 JSON。增加豆包 API 预检，不可用时直接降级到程序生成。

### AI 分析覆盖不均——部分事件描述仍是泛化

**症状**：同一页面上，"亚太AI赛道升温"事件有"香港快手计划分拆Kling AI，估值20亿美元"这样的详细描述，但旁边的 Kakao/Naver 事件只显示"Kakao发布财报"。

**根因**：AI 分析管线（豆包 API）不稳定。事件评分分流正确——公司事件（is_company=true）和 earnings 类型都达到了 AI 门槛——但调用豆包 API 时部分批次超时/失败，回退到程序生成。`enrich()` 在 `generate_html.py` 中运行，无法二次调 AI，只能靠 `_build_reason()` 程序提取。

**后续**：两个改进方向——(1) `_build_reason()` 增强正则从标题提取更多上下文（零成本）；(2) fetch_news.py AI 管线加重试/降级策略（不增加 API 次数，提高成功率）。

### 翻页按钮初始不可点击

**症状**："前一日"/"后一日"按钮在页面加载后都不可点击，实际 `main_date` 是最近日期，应有更多历史日期可浏览。

**根因**：模板初始渲染两个按钮都绑定了 `nav-disabled` 类（`pointer-events: none`），但缺少初始化代码根据 `currentDateIndex` 更新按钮状态。`main_date` 在 `availableDates[0]` 时"后一日"应启用。

**解决**：`template.html` 中 `currentDateIndex` 赋值后立即更新两个按钮的 `className`。

### summary_short 无 AI 产出时留空

**症状**：AI 未处理的事件在"今日要点"tab 中不显示任何 summary，只有 reason。

**根因**：`enrich()` 中有 `reason` 的 fallback（`_build_reason()`），但没有 `summary_short` 的 fallback。当 AI 未生成 `summary_short` 时，字段值为空或标题前 25 字，被渲染条件过滤掉。

**解决**：`enrich()` 中增加 `summary_short` fallback：当字段为空/太短/等于标题前缀时，用 `reason` 兜底。同时渲染层（Jinja + JS）加 `summary_short != reason` 检查避免重复。

---

## 设计原则

- **`scripts/template.html` 是设计的唯一真相来源（SSOT）** — 所有样式和结构改这个文件
- **`docs/*.html` 是自动生成物** — 不要直接编辑，改了也会被覆盖
- **评分不展示** — 分数仅用于内部排序和 AI 筛选阈值，用户看不到
- **无图不占位** — 没有缩略图的事件卡片不留空白框
