# 全球互联网动态情报站 — 项目规范

> 自动爬取非中美地区互联网/科技动态，AI 分析后展示为情报产品。

## 核心架构

- **数据采集**：`scripts/fetch_news.py` — RSS 并行采集 + HTML 降级 + 31 家公司监控
- **AI 分析管线**：DeepSeek 主力（GHA 已可达）→ 豆包降级 → 程序降级；本周实际 68% 由 DeepSeek 完成
- **评分前置分流**：`_calc_score()` 评分后，高分（≥7 或 funding/ma/earnings）走 AI，中分（≥4 或 is_company）程序生成，低分（<4）丢弃
- **P0 Agent**：`build_daily_ai_summary()` 生成「今日判断」AI 趋势分析 → `data/summary.json` → HTML 读取；`rewrite_titles_for_display()` 改写程序层泛化描述；`ai_quality_judge()` 过滤低价值 other 事件
- **Feed 生成**：`generate_feed.py` — 复用 `generate_html.build_display_context()` 的看板最终事件卡片，只推高价值且解释完整事件 → `docs/feed.xml`（Atom XML），供外部 CLI 订阅
- **页面生成**：`scripts/generate_html.py` + `scripts/template.html` → 静态 HTML
- **部署**：GitHub Actions + GitHub Pages（`docs/` 目录）
- **Feed 地址**：https://huangjun722.github.io/weekly-report/feed.xml

## AI 分析输出格式

每条事件输出 6 个字段：
- `content_overview`：内容概要，1-2 句客观复述事件本身发生了什么（谁、做了什么、金额/数据、进展），比 summary_short 更完整，用于卡片「内容概要」行
- `summary_short`：中英双语摘要（一句话），用作卡片标题
- `reason`：为什么重要（"所以呢"导向，对谁有影响、窗口期、连锁反应）—— 卡片展示为「点评」
- `impact`：具体受益方或受损方（卡片不展示，保留在数据中）
- `insight_label`：资金流向 / 合作机会 / 警示信号 / 趋势信号 / 中资出海
- `trend_topic`：所属趋势主题（如"中东FinTech赛道升温"）

卡片展示规则（template.html SSOT）：顶部只显示分层（精选/重点/观察）+ 公司名；正文 = 标题 + 内容概要（`front_overview`，优先 AI 扩写 `content_overview`，存量缺省用 `summary_short` 兜底且不与标题重复）+ 点评（`reason`）。区域（`region`）保留在数据中供日报统计与筛选，不作为卡片标签。

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

## 收尾与交接

- **阶段收尾固定两步**：① 代码有改动时先说「存档一下」——Agent 执行 `git commit`（本地存档，不推送），把当前代码快照存进 git；② 再跑洁癖/整理文档。①管代码快照，②管文档同步，缺一不可。
- **方案阶段先落盘**：只做了方案、还没实施时，先让 Agent 把方案写成 `docs/plans/YYYY-MM-DD-主题.md`，再进入实施。只飘在对话里的方案，会话一断就丢。
- **换 Agent / 断会话时交接**：用 `D:\共享文件\AI协作工作区\02_进度同步\HANDOFF_TEMPLATE.md` 生成交接指针包——只写线索（文件路径、commit、设计文档位置）和意图/坑，状态交 git 自己查。
- **新 Agent 接手**：先读本文件 + `02_进度同步/决策记录.md`（决策已绑定 commit，可用 `git show <hash>` 溯源），再跑 `git status` + `git log --oneline -15`，然后**一句话复述对当前任务的理解，用户点头后再动手**。
- 交接记录转述对用户审阅有价值，保留；同时补关键文件指针供 Agent 精确取数。

## 环境注意事项

- **工作区位置**：`D:\共享文件\AI协作工作区\01_工作文件区\weekly-report-repo\`（2026-08 确认的唯一真实仓库；C 盘 `Documents\claude-workspace\weekly-report-repo` 和 `weekly-report-web` 都是过期的旧副本，不要用）
- **Python 路径**：`C:\Users\16120\AppData\Local\Python\bin\python`（WindowsApps 的 `python`/`python3` 是 Microsoft Store 重定向器，不可用）
- **生成 HTML 命令**：`/c/Users/16120/AppData/Local/Python/bin/python scripts/generate_html.py --force`
