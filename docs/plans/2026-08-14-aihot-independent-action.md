# AIHOT 独立 Action 拆分 + 周报/月报融入 + RSS 汇总

> 日期：2026-08-14
> 状态：已确认路线（用户拍板），进入实施
> 关联：`2026-08-13-hot-board-aihot-fusion.md`（AIHOT 融合定案）

## 一、背景与问题

- AIHOT 热点（`data/aihot_hot.json`）当前嵌在主采集 workflow（`update.yml`）里，一天跑两次，抓一次覆盖一次，是"即时快照"。
- AIHOT 模型榜（`data/model_leaderboard.json`）**完全没有自动化**，靠手动跑，`generated_at` 停在 2026-08-10，已停更 4 天。
- 两个都从 AIHOT 来，都是轻量外部数据快照（不依赖 RSS 采集、不依赖全量 AI 分析），却绑在沉重的全量采集管线上，互相拖累。
- AIHOT 榜是 48h 滚动窗口实时变化，快照与实时永远有差，页面上"看着旧"是常态。

## 二、目标（用户拍板）

1. **AIHOT 独立 action**：热点 + 模型榜拆出，单独 workflow，北京时间 08:00 / 20:00 各跑一次。
2. **周报/月报融入 AIHOT**：报告里展示当期 AI 热点（复用现有热点卡样式，不标注"来源 AIHOT"）。
3. **RSS 加全球AI视野汇总**：feed 里加一条独立 Top5 汇总条。

## 三、设计

### 3.1 数据：按天归档 + 保留当前快照

`fetch_aihot_hot.py` 抓取后写两份：
- `data/aihot_hot/YYYY-MM-DD.json` — 按天归档，供周报/月报按周期取数；同一天多次抓取覆盖为当天最新。
- `data/aihot_hot.json` — 当前快照，继续供今日情报页「近期AI热点」卡片 + RSS 使用。

### 3.2 新 workflow：`.github/workflows/aihot.yml`

- cron（GitHub Actions 用 UTC，北京 = UTC+8）：
  - 北京 08:00 = UTC 00:00 → `0 0 * * *`
  - 北京 20:00 = UTC 12:00 → `0 12 * * *`
- 步骤：抓热点 → 抓模型榜 → `generate_html.py --force`（传 DeepSeek/豆包 key；周报月报 AI 编辑层随数据刷新，**失败不阻断**，json 一定提交）→ `generate_feed.py` → **git-auto-commit-action 提交**（自动 fetch+rebase 合并，解决与主采集撞车）。
- 失败兜底：每个抓取脚本 `|| echo` 不阻断；generate_html 失败不阻断（数据保住，页面等下一次刷新）。

### 3.3 主采集清理

`update.yml` 删除 `Fetch AIHOT hot topics` 步骤。AIHOT 文件只归独立 action 写，避免两套抢写。

### 3.4 周报/月报融入

- `build_period_report()` 新增 `aihot_hot` 字段：按 `start/end` 读取归档目录，过滤周期内热点、按标题去重、最多 10 条，每条含 title/heat/url/date。
- `template.html`：周报 panel 与月报 panel 各加「本周AI热点」/「本月AI热点」小节，复用 `f-hot` 样式，空则隐藏。

### 3.5 RSS 汇总条

`generate_feed.py` 读当前快照 `aihot_hot.json`，拼一条独立 entry「全球AI视野 · Top5」，标题 + 热度 + 原始链接，放在事件流之后。entry id 按日期生成。

## 四、撞车处理

- 主采集（`concurrency: intelligence-station`）与 AIHOT（`concurrency: aihot-data`）分组不同，不互相取消。
- 同时 push 撞车：AIHOT 用 `git-auto-commit-action` 自动 fetch+rebase+push 自愈；cron 已错开（主采集 02:00/09:00，AIHOT 08:00/20:00）。

## 五、风险与边界

- **generate_html 依赖 DeepSeek**：AIHOT workflow 传 key 跑完整生成；若 AI 编辑层失败则跳过生成（`|| true`），数据仍提交，页面由下一次生成刷新。
- **聚合不做**：AIHOT 与站内事件主题交集少、无本站评分字段，塞进聚类会稀释主题证据质量。本期只做"小节呈现"，聚合等数据说话。
- **不改站内事件模型**：AIHOT 数据不进 events.json，不进评分管线。
- 修改 workflow 属项目红线，用户已通过目标指令明确授权本次改动。

## 六、实施步骤

1. `fetch_aihot_hot.py` 按天归档。
2. 新增 `.github/workflows/aihot.yml`。
3. `update.yml` 删 AIHOT 抓取步骤。
4. `generate_html.py`：`build_period_report` 加 `aihot_hot`。
5. `template.html`：周报月报 panel 加小节。
6. `generate_feed.py` 加 Top5 汇总条。
7. 本地验证（离线测试 + 生成 HTML 检查）+ 更新 `site_updates.json` + commit 存档。
