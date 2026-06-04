# 全球互联网动态情报站 V2 使用指南

> 面向全球互联网项目拓展、战略、投资和产业研究场景，把非中美互联网动态整理成“客户拓展机会报告”。
> 在线访问：[https://huangjun722.github.io/weekly-report/](https://huangjun722.github.io/weekly-report/)
> 订阅地址：[https://huangjun722.github.io/weekly-report/feed.xml](https://huangjun722.github.io/weekly-report/feed.xml)

---

## 1. 这个网站现在解决什么问题

V1 更像“非中美科技新闻聚合”。V2 的定位已经变了：它不是让你多看新闻，而是帮助你判断：

- 哪些区域正在出现客户机会？
- 哪些公司值得跟进？
- 哪些事件代表预算、扩张、整合、合规或竞争窗口？
- 本周和本月应该把 BD 精力放在哪里？

推荐把它当作每天的轻量情报台，而不是普通资讯网站。

---

## 2. 最推荐的阅读方式

### 每天 30 秒：看今日情报

打开首页后先看“今日情报”：

1. 看顶部“今日观察”，先知道今天优先看哪些对象或方向。
2. 看右侧“今日摘要”，快速知道事件数、覆盖地区、融资、并购/财报数量。
3. 看“重要的事件”里的事实事件，优先关注有明确公司、金额、区域和合作方向的事件。

适合早上快速扫一眼，判断今天有没有值得转给业务或销售团队的线索。

### 每周 5 分钟：看周报

进入“周报”Tab，重点看三块：

| 模块 | 怎么看 |
|------|--------|
| 本周优先机会 | 按优先级、评分和信源质量排序，适合直接挑跟进对象 |
| 区域机会图 | 看哪个区域事件多、高优先级多、公司活跃度高 |
| 下周跟进行动 | 系统按 7 天内、30 天内、持续观察生成行动建议 |

周报适合回答：“这周哪些客户或区域值得跟？”

### 每月 10 分钟：看月报

进入“月报”Tab，重点看：

| 模块 | 怎么看 |
|------|--------|
| 月度市场优先级 | 看区域热度、平均评分和机会方向 |
| 机会主题 | 看本月机会集中在支付、云、AI、渠道、合规还是整合 |
| 客户分层建议 | 区分 A 类优先触达、B 类持续经营、C 类观察入库 |

月报适合回答：“下个月资源应该投向哪些区域和客户？”

---

## 3. 页面 Tab 说明

### 今日情报

当天主工作区，包含：

- 今日观察对象或方向
- 重要的事件
- 当日摘要
- 右侧报告入口
- 最近日期导航

如果只想快速了解今天先看什么、证据是什么，看这个 Tab 就够。日报不负责判断趋势是否成立，周报再收敛窗口和方向。

### 周报

从“事件列表”升级为“客户拓展机会报告”。它不是简单统计新闻，而是把近 7 天事件组织成：

- 关注窗口
- 方向判断
- 跟进行动

适合每周复盘或给业务团队同步。

### 月报

月度视角下的市场和客户结构：

- 哪些趋势跨周重复出现？
- 哪些区域或赛道出现结构变化？
- 下个月资源应该投向哪些对象或方向？

适合月度规划、区域策略和客户名单整理。

### 公司索引

按预设区域组织重点公司，避免不熟悉公司的人找不到对象。当前区域包括：

- 中资
- 亚太
- 欧洲
- 中东
- 非洲
- 拉美

每家公司卡片会显示近 7 天、近 30 天动态和最新信号。点击公司后，全站会进入公司筛选状态；顶部会出现醒目的筛选提示，避免你忘记当前只是在看某家公司。

### 全部事件

完整事件库，适合细查：

- 搜索关键词
- 按区域筛选
- 按事件类型筛选
- 查看历史日期事件
- 复核低质量或背景事件

当你想找“某个公司最近有没有动态”或“拉美最近有哪些融资”时，用这个 Tab。

### 更新日志

记录网站功能变更，包括页面结构、筛选体验、信源调整、反馈入口等。适合确认最近网站到底改了什么。

### 反馈

用于记录想法、Bug、数据问题和体验建议。反馈表单的产品原则是：用户点击提交后，系统负责写入线上记录，不要求用户理解 GitHub 或二次提交。

- 前端通过 `FEEDBACK_ENDPOINT` 调用反馈 API。
- 推荐用 Cloudflare Worker 持有服务端密钥，再写入 GitHub Issue、飞书表格或数据库。
- 本机草稿只用于失败兜底和恢复内容，不代表线上记录。

当前仓库提供 `workers/feedback-worker.js` 作为轻量实现样例：Worker 接收表单 POST，用服务端 `GITHUB_TOKEN` 创建内部 Issue。GitHub 是维护后台，不暴露给反馈者。

---

## 4. 事件字段怎么理解

V2 事件不只记录“新闻类型”，还会补齐 BD 机会字段。

| 字段 | 含义 |
|------|------|
| `source_tier` | 信源层级，越靠前可信度或业务价值越高 |
| `source_role` | 信源角色，如官方 IR、垂直交易源、区域生态源 |
| `bd_triggers` | BD 触发器，如预算窗口、扩张窗口、整合窗口 |
| `opportunity_direction` | 可能的合作方向，如云与 AI 基础设施、支付与风控、渠道伙伴 |
| `follow_up_window` | 建议跟进窗口：7 天内、30 天内、持续观察 |
| `bd_priority` | 机会优先级：高、中、观察 |

这些字段会影响周报/月报排序，也会影响“客户分层建议”。

### 常见 BD 触发器

| 触发器 | 典型事件 | 可理解为 |
|--------|----------|----------|
| 预算窗口 | 融资、营收增长、利润改善 | 对方可能有新预算 |
| 扩张窗口 | 进入新市场、上线新业务 | 对方可能需要本地合作 |
| 降本窗口 | 裁员、重组、亏损收窄 | 对方可能需要效率工具 |
| 合规窗口 | 牌照、监管、罚款、诉讼 | 对方可能需要合规/安全方案 |
| 整合窗口 | 并购、收购、股权交易 | 对方可能需要系统整合 |
| 生态窗口 | 合作、联盟、开放平台 | 对方可能需要生态伙伴 |
| 竞争窗口 | 市占、挑战、对标、替代 | 对方可能存在竞争防守需求 |

---

## 5. 信源层级

V2 开始按信源质量分层，不再把所有来源当成同等新闻。

| 层级 | 角色 | 代表来源 | 用途 |
|------|------|----------|------|
| L1 官方/IR源 | 官方披露 | Rakuten、Grab、MercadoLibre、Adyen、Sea、Zalando、Allegro、Kaspi.kz、Naver、Kakao、Jumia 官方/IR源 | 校准重点客户自身动作 |
| L2 垂直交易源 | 融资/并购/创投 | TechCrunch、Tech.eu、UKTN、EU-Startups、Tech in Asia、Inc42、WAMDA、LatamList、LAVCA 等 | 捕捉高价值交易和资金流 |
| L3 区域生态源 | 区域科技生态 | The Recursive、The Next Web、TechWire Asia、TechCabal、Techpoint、WeeTracker、Contxto | 补充区域动态和战略信号 |
| L4 垂直赛道精品源 | 子赛道专业观察 | GamesIndustry.biz、PocketGamer.biz、Fintech News Singapore、EcommerceBytes、Mobile World Live | 补充游戏、电商、支付金融、移动生态等赛道信号 |
| L4 深度趋势源 | 趋势观察 | Rest of World Money / Ecommerce | 只保留高信号事件 |
| L5 Google News 补漏源 | 公司雷达 | 重点公司 Google News RSS | 补漏，不作为高可信主源 |

### 子赛道覆盖

V2.1 开始增加垂直赛道精品源，重点覆盖：

| 子赛道 | 代表信源 | 主要看什么 |
|--------|----------|------------|
| 游戏 | GamesIndustry.biz、PocketGamer.biz | 全球/区域游戏市场、移动游戏收入、发行与并购、平台生态变化 |
| 电商/O2O | EcommerceBytes、Rest of World Ecommerce | 线上零售、社交电商、本地生活、渠道和履约变化 |
| Fintech/支付金融 | Fintech News Singapore、Rest of World Money | 支付、钱包、牌照、银行科技、金融基础设施 |
| 文娱社交/移动生态 | Mobile World Live、TechWire Asia、Rest of World | 移动互联网、社交娱乐、运营商生态、区域数字服务 |

这类源不追求数量，而是捕捉能解释市场结构的“报告、排名、收入、用户、支付、合作、监管、并购”信号。

候选精品源包括 Newzoo、The Paypers、FinTech Futures、Retail4Growth、Digital in Asia 等。它们的内容价值高，但当前 RSS/反爬可用性不稳定，暂不直接进入自动采集；后续可按 HTML 低频采集或人工精选方式接入。

### 当前重点公司监控

覆盖公司包括：

ByteDance/TikTok、Tencent、Alibaba、JD.com、Kuaishou、Ant Group、Meituan、Kakao、Naver、Rakuten、Sea Limited、Grab、Gojek、VNG Group、Yahoo、Cyberagent、Adyen、Zalando、Allegro、Trendyol、MercadoLibre、Rappi、Noon、Careem、Tabby、Kaspi.kz、Jumia、Konga。

Google News 已加强噪声过滤，重点过滤：

- 分析师目标价
- 股票预测
- 纯股价波动
- 金融站复写稿
- phishing / password / urgent alert 等安全告警噪声

---

## 6. 更新频率和数据范围

- GitHub Actions 每天自动更新。
- 页面使用 `docs/index.html` 静态生成。
- 事件数据保留近 90 天。
- 首页默认展示最近一次有内容的采集批次。
- 周报按最近 7 天聚合。
- 月报按当月聚合。

如果刚推送了页面代码，线上 GitHub Pages 可能需要一点时间更新。默认不等待 Actions 完成，除非明确要确认部署成功。

---

## 7. 本地预览和维护

### 仅重新生成页面

```powershell
Set-Location -LiteralPath 'D:\共享文件\AI协作工作区\01_工作文件区\weekly-report-repo'
$py='C:\Users\16120\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py scripts\generate_html.py --force
```

### 本地打开预览

```powershell
Set-Location -LiteralPath 'D:\共享文件\AI协作工作区\01_工作文件区\weekly-report-repo\docs'
& $py -m http.server 8765 --bind 127.0.0.1
```

然后打开：

```text
http://127.0.0.1:8765/
```

### 检查脚本语法

```powershell
& $py -m py_compile scripts\fetch_news.py scripts\generate_html.py
```

### 推送前检查

```powershell
git status --branch --short
git diff --check
```

如果远端自动更新抢先推送，优先：

```powershell
git fetch origin
git rebase origin/main
```

如果只冲突 `docs/index.html`，通常重新运行 `scripts\generate_html.py --force`，再 `git add docs/index.html` 即可。

---

## 8. 数据流与部署链路

```text
RSS 信源 ──┐
官方/IR HTML ├──→ scripts/fetch_news.py ──→ data/events.json
Google News ─┘                              │
                                            ↓
                              scripts/generate_html.py
                                            ↓
                                   docs/index.html
                                            ↓
                                      GitHub Pages
```

完整链路：

1. GitHub Actions 定时或手动触发。
2. `scripts/fetch_news.py` 并行抓取 RSS，低频抓取 HTML 备用源和官方/IR 页面，再抓取重点公司 Google News。
3. 抓取结果先做标题、公司别名、低信号、重复事件过滤。
4. `smart_filter()` 控制总量，优先保留信号事件和官方/IR 公司事件。
5. 事件进入评分前置，分为 AI 深度分析、程序生成、丢弃。
6. AI 或程序生成 `reason`、`summary_short`、`impact`、`insight_label`、`trend_topic` 等字段。
7. `analysis_quality.py` 标注 `quality_flags` 和 `needs_repair`。
8. 事件按文章日期写入 `data/events.json`，保留近 90 天。
9. `scripts/generate_html.py` 读取事件，补齐前端字段和 BD 字段，生成 `docs/index.html`。
10. GitHub Pages 从 `docs/` 发布静态网站。

相关生成物：

| 文件 | 作用 |
|------|------|
| `data/events.json` | 近 90 天事件数据 |
| `data/summary.json` | 每日趋势判断缓存 |
| `data/site_updates.json` | 更新日志内容源 |
| `docs/index.html` | 线上主页面 |
| `docs/feed.xml` | Atom/RSS 阅读器订阅入口 |

---

## 9. 评分与筛选机制

### 多因子评分

事件会通过确定性评分函数计算 `score`，主要因子包括：

| 因子 | 说明 |
|------|------|
| 金额 | 标题中解析 `$M`、`$B`、`€M`，金额越大分越高 |
| 事件类型 | 并购、财报、融资、战略等不同类型有不同基础分 |
| 区域权重 | 非洲、中东、亚太、拉美、中资出海等区域有不同权重 |
| 热门赛道 | AI、FinTech、HealthTech、机器人、芯片、气候科技等加分 |
| 知名投资方 | SoftBank、Mubadala、Temasek、a16z、Sequoia 等加分 |
| 公司命中 | 能识别到重点公司或明确公司名时加分 |

最终分数会压到 1-10 区间。

### 事件类型识别

标题先被规则识别为：

| 类型 | 常见关键词 |
|------|------------|
| `funding` | raises、funding、series、seed、valued at、unicorn |
| `ma` | acquires、merger、stake、buys、takeover |
| `earnings` | revenue、earnings、profit、IPO、financial results |
| `strategy` | launches、expands、partners、overseas、global、joint venture |
| `other` | 不命中以上规则 |

### 后端筛选

`smart_filter()` 的基本策略：

1. 融资、并购、财报、战略等信号事件优先保留。
2. 官方/IR 公司事件即使是 `other` 也保留，因为可信度高。
3. Google News 公司 `other` 事件不再无条件保留，避免股票和安全告警噪声。
4. 非公司、非信号事件按优先级补足总量。
5. 每日总量和单区域数量有上限，避免某个区域或信源刷屏。

### 前端展示过滤

页面端还会做一层展示过滤：

- 今日情报：展示最新批次中非 `other`、评分较高的事件，以及 7 天内公司动态。
- 全部事件：展示完整事件列表，并支持搜索、区域筛选、事件类型筛选、公司筛选。
- 低质量候选：仍可查看，但不会抢占主视觉。
- 公司筛选：点击公司索引后，全站进入公司过滤状态，顶部显示筛选提示和结果数量。

### 周/月报排序

周报和月报按 `_bd_priority_rank()` 排序，核心顺序是：

```text
BD 优先级 → 评分 → 信源层级 → 事件类型 → 日期
```

因此官方/IR、垂直交易源、高分融资/并购，会比普通 Google News 背景事件更靠前。

---

## 10. AI 分析管线与质量标注

AI 分析顺序：

```text
DeepSeek 主力 → 豆包兜底 → 程序生成兜底
```

事件会经过评分前置：

| 情况 | 处理 |
|------|------|
| 高分或融资/并购/财报 | AI 深度分析 |
| 中分或公司事件 | 程序生成 + 必要时标题改写 |
| 低分噪声 | 丢弃或作为低优先级背景 |

如果 AI 失败，事件会记录 `analysis_source`、`analysis_status`、`quality_flags`、`needs_repair`，避免把兜底文本伪装成完整分析。

### 3 个 P0 Agent

这里的 P0 不是独立服务，而是采集流程里的三类高优先级 AI 任务：

| Agent | 函数 | 作用 |
|-------|------|------|
| 事件深度分析 | `analyze_events_deepseek()` / `analyze_events_doubao()` | 为高分事件生成中文摘要、影响范围、趋势主题 |
| AI 标题改写 | `rewrite_titles_for_display()` | 对程序层中仍泛化的描述做中文改写 |
| AI 情报评分 | `ai_quality_judge()` | 对 `other` 类事件做 1-5 分价值判断，低分丢弃 |

另外还有每日趋势判断：

| 模块 | 函数 | 作用 |
|------|------|------|
| 每日趋势总结 | `build_daily_ai_summary()` | 基于当天信号事件生成 2-4 句专业情报判断 |

### 质量标注系统

`scripts/analysis_quality.py` 会检查事件是否仍然像兜底文本。

常见质量标记：

| 标记 | 含义 |
|------|------|
| `missing_summary` | 缺少短摘要 |
| `title_prefix_summary` | 摘要只是标题前缀 |
| `missing_reason` | 缺少事件原因 |
| `generic_reason` | 描述仍是“科技动态”“战略调整”等模板话术 |
| `unknown_impact` | 影响对象仍是“未知”或“相关企业” |

质量字段：

| 字段 | 含义 |
|------|------|
| `analysis_source` | `deepseek`、`doubao`、`program`、`unknown` |
| `analysis_status` | `complete`、`partial`、`fallback`、`failed` |
| `quality_flags` | 质量问题列表 |
| `needs_repair` | 是否建议后续补改写 |

这个系统的价值是：即使 AI 失败，也能明确标出“这是兜底结果”，不会让页面误以为它是完整分析。

---

## 11. RSS、HTML 与公司信源完整表

### 当前 RSS 信源

| 层级 | 信源 | 区域 | 角色 | 配额/规则 |
|------|------|------|------|-----------|
| L2 垂直交易源 | TechCrunch | 全球 | venture_media | 扫描 20，最多 8 |
| L2 垂直交易源 | TechCrunch VC | 全球 | venture_media | 扫描 20，最多 8 |
| L2 垂直交易源 | Tech.eu | 欧洲 | venture_media | 扫描 20，最多 8 |
| L2 垂直交易源 | UKTN | 欧洲 | venture_media | 扫描 20，最多 8 |
| L2 垂直交易源 | EU-Startups | 欧洲 | venture_media | 扫描 20，最多 8 |
| L3 区域生态源 | The Recursive | 欧洲 | regional_ecosystem | 扫描 20，最多 6 |
| L3 区域生态源 | The Next Web | 欧洲 | regional_ecosystem | 扫描 20，最多 6 |
| L2 垂直交易源 | Tech in Asia | 亚太 | venture_media | 扫描 24，最多 8 |
| L2 垂直交易源 | Inc42 | 亚太 | venture_media | 扫描 24，最多 8 |
| L3 区域生态源 | TechWire Asia | 亚太 | regional_ecosystem | 扫描 20，最多 6 |
| L4 垂直赛道精品源 | GamesIndustry.biz | 全球 | industry_vertical / 游戏 | 扫描 16，最多 4，只保留高信号内容 |
| L4 垂直赛道精品源 | PocketGamer.biz | 全球 | industry_vertical / 游戏 | 扫描 16，最多 4，只保留高信号内容 |
| L4 垂直赛道精品源 | Fintech News Singapore | 亚太 | industry_vertical / Fintech/支付 | 扫描 16，最多 4，只保留高信号内容 |
| L4 垂直赛道精品源 | Finextra Payments | 全球 | industry_vertical / Fintech/支付 | 扫描 20，最多 4，只保留高信号内容 |
| L4 垂直赛道精品源 | Payments Dive | 全球 | industry_vertical / Fintech/支付 | 扫描 12，最多 3，只保留高信号内容 |
| L4 垂直赛道精品源 | EcommerceBytes | 全球 | industry_vertical / 电商 | 扫描 16，最多 4，只保留高信号内容 |
| L4 垂直赛道精品源 | Retail Dive | 全球 | industry_vertical / 电商 | 扫描 12，最多 3，只保留高信号内容 |
| L4 垂直赛道精品源 | Mobile World Live | 全球 | industry_vertical / 文娱社交/移动生态 | 扫描 16，最多 4，只保留高信号内容 |
| L4 垂直赛道精品源 | Social Media Today | 全球 | industry_vertical / 社交平台 | 扫描 12，最多 3，只保留高信号内容 |
| L4 垂直赛道精品源 | Mobile Marketing Magazine | 全球 | industry_vertical / 移动生态/广告 | 扫描 12，最多 3，只保留高信号内容 |
| L2 垂直交易源 | WAMDA | 中东 | venture_media | 扫描 20，最多 8 |
| L2 垂直交易源 | MENAbytes | 中东 | venture_media | 扫描 20，最多 8 |
| L3 区域生态源 | TechCabal | 非洲 | regional_ecosystem | 扫描 20，最多 6 |
| L2 垂直交易源 | Disrupt Africa | 非洲 | venture_media | 扫描 20，最多 8 |
| L3 区域生态源 | Techpoint | 非洲 | regional_ecosystem | 扫描 20，最多 6 |
| L2 垂直交易源 | Ventureburn | 非洲 | venture_media | 扫描 20，最多 8 |
| L3 区域生态源 | WeeTracker | 非洲 | regional_ecosystem | 扫描 20，最多 6 |
| L2 垂直交易源 | LatamList | 拉美 | venture_media | 扫描 20，最多 8 |
| L2 垂直交易源 | LAVCA | 拉美 | venture_media | 扫描 20，最多 8 |
| L3 区域生态源 | Contxto | 拉美 | regional_ecosystem | 扫描 24，最多 6 |
| L4 深度趋势源 | Rest of World Money | 全球 | deep_trend | 扫描 20，最多 4，只保留信号事件 |
| L4 深度趋势源 | Rest of World Ecommerce | 全球 | deep_trend | 扫描 20，最多 4，只保留信号事件 |

### 当前 HTML / 官方 IR 源

| 层级 | 信源 | 区域 | 用途 |
|------|------|------|------|
| L2 垂直交易源 | DealStreetAsia | 亚太 | RSS 停用后的 HTML 降级，成功率不稳定 |
| L1 官方/IR源 | Rakuten IR | 亚太 | 官方披露、财报、公告 |
| L1 官方/IR源 | Grab IR | 亚太 | 官方披露、财报、公告 |
| L1 官方/IR源 | MercadoLibre IR | 拉美 | 官方披露、财报、公告 |
| L1 官方/IR源 | Adyen IR | 欧洲 | 官方披露、财报、公告 |
| L1 官方/IR源 | Sea Newsroom | 亚太 | 官方披露、财报、公告 |
| L1 官方/IR源 | Zalando IR | 欧洲 | 官方披露、财报、公告 |
| L1 官方/IR源 | Allegro Newsroom | 欧洲 | 官方披露、财报、公告 |
| L1 官方/IR源 | Kaspi.kz IR | 中东 | 官方披露、财报、公告 |
| L1 官方/IR源 | Naver Press | 亚太 | 官方披露、财报、公告 |
| L1 官方/IR源 | Kakao Press | 亚太 | 官方披露、财报、公告 |
| L1 官方/IR源 | Jumia Newsroom | 非洲 | 官方披露、财报、公告 |

### 当前公司监控

Google News 公司监控覆盖 28 个重点对象：

| 区域 | 公司 |
|------|------|
| 中资 | ByteDance/TikTok、Tencent、Alibaba、JD.com、Kuaishou、Ant Group、Meituan |
| 亚太 | Kakao、Naver、Rakuten、Sea Limited、Grab、Gojek、VNG Group、Yahoo、Cyberagent |
| 欧洲 | Adyen、Zalando、Allegro、Trendyol |
| 拉美 | MercadoLibre、Rappi |
| 中东 | Noon、Careem、Tabby、Kaspi.kz |
| 非洲 | Jumia、Konga |

Google News 默认配置：

| 配置 | 含义 |
|------|------|
| `source_tier=L5 Google News 补漏源` | 只做公司动态雷达 |
| `source_role=company_radar` | 公司监控角色 |
| `max=2` | 每家公司最多 2 条 |
| `max_other=0` | 默认不保留 `other` 类 |

### Google News 效果复盘（2026-05-21）

近 14 天样本中，Google News 相关事件仍占比较高：495 条事件中约 217 条来自 Google News 或 Google News 跳转源，说明“降低权重”还不足以改变页面体感。主要噪声包括：

- 股票预测、券商评级、股价涨跌和机构持仓。
- 促销、返利、积分、商品比较和优惠信息。
- 加密币、XRP、token 和交易所联动。
- 政治选举、诉讼、创始人刑案等非 BD 机会信号。
- 安全告警、泛安全厂商稿和历史统计页面。

调整原则：
- Google News 从“低权重补漏”进一步收紧为“低配额补漏”：每家公司最多 2 条，默认不保留 `other`。
- 用支付、电商、社交平台、移动广告等垂类源补足行业维度，而不是让 Google News 继续补量。
- Twitter/X 是海外重要发生渠道，但直接抓取稳定性和合规成本高；当前先接 Social Media Today、Mobile Marketing Magazine 等二次沉淀源，后续再评估 X API、官方 blog、开发者变更日志和垂类 newsletter。

### 已移除或降级信源

| 信源 | 状态 | 原因 |
|------|------|------|
| Sifted | 移除 | Cloudflare 全面拦截 |
| DealStreetAsia RSS | 降级为 HTML | RSS 显示 Temporarily Disabled |
| e27 | 移除 | Angular JS + Cloudflare，RSS 和 HTML 均不可采 |
| Bloomberg | 移除 | 全球综合科技源，区域噪声过大 |
| Google News 泛区域 RSS | 不作为区域主源 | 链接是 Google 内部跳转，非原始来源 |
| Newzoo | 候选，暂不自动采集 | 报告价值高，但当前脚本访问 403，需要 HTML/人工低频接入 |
| The Paypers | 候选，暂不自动采集 | 当前 RSS 地址返回 HTML，不是标准 feed |
| FinTech Futures | 候选，暂不自动采集 | 当前脚本访问 feed 返回 403 |
| Retail4Growth | 候选，暂不自动采集 | 当前 RSS 地址不可用，需要重新验证 |
| Digital in Asia | 候选，暂不自动采集 | 适合文娱社交/数字媒体观察，但需先确认稳定 feed |

---

## 12. 踩过的坑与排障记录

### DeepSeek 在 GitHub Actions 曾经结构性不可达

症状：

- Workflow 每次都卡在 DeepSeek 调用。
- 单批次重试超时，整体任务可能接近 60 分钟。

原因：

- GitHub Actions runner 到 `api.deepseek.com` 的网络不稳定或不可达。

当前处理：

- 当前逻辑是 DeepSeek 主力，失败后快速降级豆包。
- 不再因为 DeepSeek 单点失败拖垮整轮采集。
- Workflow 中会先检测 DeepSeek，再检测豆包。

### 豆包 API 返回非 JSON

症状：

- 模型偶尔返回 Markdown 代码块或格式不标准 JSON。
- 批量解析失败。

处理：

- 解析前去除 ```json / ``` 代码块。
- 批量失败后可逐条兜底。
- 最终失败时回退程序生成，并标记质量状态。

### 事件分析全是泛化描述

症状：

- 页面出现“亚太科技公司财报披露”“欧洲科技公司战略动态”等空泛描述。

原因：

- 程序兜底模板被当成正式分析写入。
- 旧逻辑没有明确标记 `analysis_status` 和 `needs_repair`。

处理：

- `_build_reason()` 从标题和公司名提取更具体描述。
- `analysis_quality.py` 标记 `generic_reason`、`unknown_impact` 等问题。
- 页面保留但弱化低质量候选，避免抢主视觉。

### 公司名提取吃掉前文数字

症状：

```text
Baillie Gifford Dumps 248,000 MercadoLibre Shares
```

曾被提取成：

```text
000 MercadoLibre
```

原因：

- 公司名匹配时向前回溯词边界使用 `isalnum()`，把数字也当成词的一部分。

处理：

- 改为只回退字母，避免吞掉金额或股数。

### Google News 把股票和安全噪声当公司动态

症状：

- 目标价、股票预测、analyst rating、phishing 邮件、安全告警进入公司动态。

处理：

- `COMPANY_BLACKLIST` 和 `COMPANY_LOW_SIGNAL_PATTERNS` 增加金融站、目标价、股票预测、安全告警等模式。
- Google News 继续保留为 L5 补漏源，但不再作为高可信主源。
- 官方/IR 源开始作为 L1 公司动态来源。

### Workflow push 与本地 push 冲突

症状：

- GitHub Actions 自动更新 `docs/index.html`，本地同时推代码，导致 push rejected 或生成文件冲突。

处理：

```powershell
git fetch origin
git rebase origin/main
```

如果只冲突 `docs/index.html`：

```powershell
& $py scripts\generate_html.py --force
git add docs\index.html
git rebase --continue
```

原则：

- `docs/index.html` 是生成物，不手工拼冲突。
- 先吸收远端自动更新数据，再用当前脚本重新生成。

### 共享路径和真实仓库混淆

事实：

```text
D:\共享文件\AI协作工作区\01_工作文件区\weekly-report-repo
```

就是当前真实 Git 仓库。后续不要再误判成影子目录。

处理建议：

- 每次动手前先 `git status --branch --short`。
- 不要对用户未提交改动做 reset 或 checkout。

---

## 13. 常见问题

### 为什么有些事件看起来仍然像背景信息？

因为 Google News 公司雷达会抓到部分边缘动态。V2 已经降低它的权重，并增加官方/IR 源，但 Google News 仍保留为补漏源，避免漏掉重点公司动作。

### 为什么周报/月报有时公司机会多于区域机会？

公司监控和区域信源是两条数据流。若某天重点公司新闻多，周报/月报会更多体现客户机会；如果区域融资/并购源更活跃，则会体现区域机会。后续会继续扩大高质量区域源和官方源，让比例更健康。

### 反馈 Tab 怎么写入线上后台？

当前网站是 GitHub Pages 静态站，页面本身不能安全持有写入密钥。正确做法是增加一个轻量 API 层，例如 Cloudflare Worker、Pages Function、Supabase Edge Function 或飞书 Webhook 转发服务。前端只向 API 提交反馈，API 在服务端写入 GitHub Issue、飞书表格或数据库。

### 线上没立刻更新怎么办？

GitHub Pages 需要部署时间。除非明确要确认部署成功，否则默认推送后不等待 Actions 跑完。

### 可以把它当正式报告用吗？

当前页面适合作为日常情报台和周/月度机会视图。如果要正式对外归档，建议下一步增加独立周报/月报 HTML、Markdown 或 Word 输出。

---

## 14. V2 相比 V1 的关键变化

| 维度 | V1 | V2 |
|------|----|----|
| 产品定位 | 非中美科技新闻聚合 | 全球互联网客户拓展情报台 |
| 周报/月报 | 轻量趋势聚合 | BD 机会报告 |
| 公司索引 | 公司列表/筛选入口 | 按区域组织的连续观察对象 |
| 信源策略 | RSS + Google News | 分层信源 + 官方/IR + Google News 补漏 |
| 事件字段 | 新闻类型、评分、摘要 | 增加 BD 触发器、机会方向、跟进窗口、优先级 |
| 反馈机制 | 无 | 反馈 API + 本机草稿兜底 |
| 更新说明 | 无 | 更新日志 Tab |

---

## 15. 下一步建议

优先级从高到低：

1. 观察下一次自动更新后，Google News 噪声是否下降。
2. 观察第二批官方/IR 源命中质量，优先确认 Allegro、Naver、Jumia 等已能稳定产出真实公告，Sea、Zalando、Kaspi、Kakao 等 SPA 页面继续低频观察。
3. 增加正式周报/月报归档输出。
4. 对历史旧事件运行小批量补改写，优先修复高分但 `needs_repair=true` 的事件。
5. 配置 `FEEDBACK_ENDPOINT` 并部署 `workers/feedback-worker.js` 或等价服务，让反馈默认进入远端。
