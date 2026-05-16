# 全球互联网动态情报站 — 项目规范

> 自动爬取非中美地区互联网/科技动态，AI 分析后展示为情报产品。

## 核心架构

- **数据采集**：`scripts/fetch_news.py` — RSS 并行采集 + HTML 降级 + 27家公司监控
- **AI 分析管线**：GHA 直走豆包（跳过结构性不可达的 DeepSeek）；本地 DeepSeek 优先 → 豆包降级 → 程序降级
- **评分前置分流**：`_calc_score()` 评分后，高分（≥7 或 funding/ma/earnings）走 AI，中分（≥4 或 is_company）程序生成，低分（<4）丢弃
- **P0 Agent**：`build_daily_ai_summary()` 生成「今日判断」AI 趋势分析 → `data/summary.json` → HTML 读取；`rewrite_titles_for_display()` 改写程序层泛化描述；`ai_quality_judge()` 过滤低价值 other 事件
- **API Key 加密**：`scripts/decrypt_key.py` — PBKDF2 + Fernet 解密本地加密的 API Key
- **存量补跑**：`scripts/retrofit_events.py` — 扫描 events.json 中泛化描述事件，通过 AI 改写后写回（本地 DeepSeek / GHA 豆包自动切换）
- **Feed 生成**：`generate_feed.py` — events.json → 最新一天全部事件 → `docs/feed.xml`（Atom XML），供外部 CLI 订阅
- **页面生成**：`scripts/generate_html.py` + `scripts/template.html` → 静态 HTML
- **部署**：GitHub Actions + GitHub Pages（`docs/` 目录）
- **Feed 地址**：https://huangjun722.github.io/weekly-report/feed.xml

## AI 分析输出格式

每条事件输出 5 个字段：
- `summary_short`：中英双语摘要
- `reason`：为什么重要（"所以呢"导向，对谁有影响、窗口期、连锁反应）
- `impact`：具体受益方或受损方
- `insight_label`：资金流向 / 合作机会 / 警示信号 / 趋势信号 / 中资出海
- `trend_topic`：所属趋势主题（如"中东FinTech赛道升温"）

## 环境变量

| 变量 | 用途 | 获取地址 |
|------|------|---------|
| `DEEPSEEK_API_KEY` | 主力 AI 分析 | https://platform.deepseek.com/ |
| `DOUBAO_API_KEY` | 降级备用 AI | https://console.volcengine.com/ark/ |

## 无 CLAUDE.md 时的默认行为

进入项目后先读本文件。没有 CLAUDE.md 则按全局指令执行。

## 设计原则

- `scripts/template.html` 是设计的唯一真相来源（SSOT）
- `docs/*.html` 是自动生成物，不要直接编辑
- 三层信息架构：今日判断(30s) → 趋势分组事件(3min) → 公司导航/搜索(需要时)
- 两 tab 卡片风格统一：今日要点和全部事件使用一致的 `.daily-event` 卡片结构
- 评分徽章已移除：事件不显示分数，分数仅用于内部排序和 AI 筛选阈值
- 事件图片：左侧 100px×70px 缩略图，RSS media_content 优先 → og:image 补抓 → 无图不占位
- **事件描述降级**：`enrich()` 中 `summary_short` 在 AI 未命中时以 `reason` 兜底；`reason` 再失败则走 `_build_reason()` 程序生成
- **描述去重**：渲染层（Jinja + JS）检查 `summary_short != reason`，相同时只显示 `reason`
- **翻页初始状态**：`navigateDay()` 需在页面加载时同步 `prevDay`/`nextDay` 按钮状态，模板默认 `nav-disabled` 需 init 代码纠正

## 红线（必须先问我）

- git push、git rebase、git reset --hard
- 修改 workflow 文件（`.github/workflows/`）
- 删除 data/ 目录或 events.json
- 修改 GitHub Secrets

## 环境注意事项

- **工作区位置**：`C:\Users\16120\Documents\claude-workspace\weekly-report-repo\`（不是 `C:\Users\16120\weekly-report-web\`，后者是过期的旧副本）
- **Python 路径**：`C:\Users\16120\AppData\Local\Python\bin\python`（WindowsApps 的 `python`/`python3` 是 Microsoft Store 重定向器，不可用）
- **生成 HTML 命令**：`/c/Users/16120/AppData/Local/Python/bin/python scripts/generate_html.py --force`
