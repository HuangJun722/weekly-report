# 情报站事件去重与类型判定系统性重构方案

> 日期：2026-08-13
> 状态：方案（待确认后实施）
> 关联：b6d2a24（上一轮跨天去重修复）、08-12 批次 63 条事件中 5 组重复 + 第 28 条类型误标

## 一、问题清单（全部复现于 08-12 批次）

| 事件 | 现象 | 直接原因 |
|------|------|---------|
| SEA Limited Q2 财报 | 3 条同日重复（TNGlobal / tradingview / TIKR） | earnings 专用去重要求「标题以公司名开头+财报动词」，三条全不满足 → 掉落通用路径 → 标题相似度 0.08/0.09/0.03 低于 0.5 阈值 → 全部保留 |
| Jumia IFC 融资 | 2 条同日重复（Google News / WeeTracker） | 第二条无 `company_name`（is_company=False）→ 去重走「须相似度≥0.72」分支，实际 0.31 → 保留；且两条 event_types 不同（['funding','earnings'] vs ['funding']） |
| Rakuten / Cytix | 各 2 条同日重复 | 同公司同日多篇报道，标题相似度 0.06 左右，低于 0.5 → 保留 |
| 第 28 条 Cursor | 卡片显示「亚太行业研究报告发布」与实际内容（Cursor 开印度办公室）不符 | 标题含 "Report" 触发 industry_report 关键词 → score 6 走程序生成 → fallback 模板文案「{区域}行业研究报告发布，观点待交叉验证」→ 与真实内容无关 |

## 二、根因（第一性原理）

### 根因 A：去重的维度选错了 —— 标题相似度是弱信号，结构化字段才是主键

业界（Google News story clustering、GDELT 实体中心聚类、TDT 框架）的共识：**判定两条报道是否同一事件，主判据是结构化事件键——「谁 + 什么类型的事 + 何时」**，文本相似度只用于在键相同的情况下防误并，或在键缺失时做兜底。

当前 `_is_same_event()` 恰好相反：以标题 token 相似度为主判据，company_name / event_types / 时间窗只做修正项。后果：

- 同公司同日同类型的三篇报道（SEA），因标题用词完全不同而全部放行
- 同一天同一笔融资（Jumia），因一条缺 company_name、一条类型多标了 earnings，键对不上而放行

标题相似度的上限就在那里：同一事件的报道标题可以毫无共同词（"SE Q2 Earnings Call..." vs "Sea Limited Stock Jumped 15%..."），不同事件的标题反而可能共用词语。把相似度当主判据，是误并、漏并都控不住的根源。

### 根因 B：类型判定由关键词启发式定死，与 AI 能力脱节

`industry_report` 等类型由标题关键词规则在采集侧定死。关键词无法区分 "Report" 的三种语义：①研报本体（"2026 Singapore Digital Banking Report"）②"据报道"（"Cursor...: Report"）③栏目名（"Reporter's Notebook"）。

而系统已有 DeepSeek 主力 AI 分析管线——AI 能看到全文，天然能区分；现在的用法是反的：关键词定类型，AI 只补充文案。关键词猜错类型 → AI 没有纠正权 → fallback 模板直接按错误类型生成展示文案 → 用户看到与内容无关的「行业研究报告发布」。

### 根因 C：fallback 模板按类型生成「断言式文案」，AI 不可用时系统在编故事

`build_event()` 的 fallback 分支（analysis_status='fallback'）会为每种类型生成一句模板理由（"亚太行业研究报告发布，观点待交叉验证"、"亚太科技公司财报披露"…）。这些文案读起来像事实陈述，但 AI 根本没读过原文——类型是猜的，文案是模板拼的。这是比重复更危险的问题：展示层在低置信路径上输出高置信感的断言。

## 三、业界成熟方案对照（本次调研结论）

| 方案 | 出处 | 本项目对应落点 |
|------|------|--------------|
| 事件簇（story clustering）：同实体+同类型+时间窗的先聚合，再选代表文档 | Google News、Apple News 三阶段管线（hausdorff hash 粗分 → 语义精排 → 代表文档） | 事件键优先的去重重写（阶段 1） |
| 实体为中心的聚类：NER 抽实体做锚，事件本体（谁-何时-何地-何事）定键 | GDELT、Meltwater、TDT 框架 | 复用已有 company_name/entity_pool，补别名归一化与标题兜底提取 |
| 混合指纹：词面（SimHash/MinHash）+ 语义（embedding）双通道 | 学术与工业共识（Turpin 2009；现代 SBERT） | 本项目日采 60± 条、标题短，词法+结构化键已足够，不引入向量库（避免过度投资，附录 A 说明） |
| 分类交给能理解内容的模型 | 现代 NLP 管线共识 | 类型判定 AI 化，关键词退回兜底（阶段 2） |
| 聚类质量评估：B-CUBED/Purity 人工标注小样本 | TREC TDT 评测 | 本方案用「5 组已知错误样本 + 3 天抽查」作回归（阶段 3），不引入正式评测框架 |

## 四、方案总览

一句话：**去重从「猜标题像不像」改为「按事实键合并」；类型从「关键词猜」改为「AI 判、关键词兜底」；AI 不可用时不再编造断言文案。**

三个改动层，对应三个根因：

```
采集侧                    分析侧                    展示侧
原文 → 事件键提取  →  去重(键优先) → AI分析(含类型判定) → 展示
       (公司/类型/时间)  (同键即并)   (AI定类型,关键词兜底)  (fallback只显示中性文案)
                                ↕
                    存量数据清理 + 回归验证
```

## 五、实施细节

### 阶段 1：去重重写 —— 事件键优先（改 `_is_same_event` / `_event_signature`）

1. **事件键先构造**：`(实体键, 事件类型主键, 时间窗口)` 三者一致 → 直接判同事件，跳过相似度判定
   - 实体键 = 归一化 company_name（小写、去尾缀 Inc./Limited/Technologies，Jumia→jumia，Sea Limited→sea）|| 标题主题提取（`_event_subject_key`，company_name 缺失时兜底）
   - 类型主键 = 排序后首个事件类型（Jumia 两条 `['funding','earnings']` 与 `['funding']` 归一为 funding，可并）
   - 时间窗口：同日内必然近似（当日就直接同窗）；跨日用现有 3 天逻辑
2. **相似度降为防误并的否定证据**：键相同但标题相似度极低（<0.15）时，标记为「同键存疑」，提示人工抽查不自动丢弃（保守不误删）
3. **公司别名归一化**：复用 entity_pool / `_get_company_aliases`，Jumia Technologies → Jumia；补「标题含实体名但 company_name 为空」时的实体匹配（Jumia 第二条标题含 "Jumia" 即可归入）
4. **cap 修正**：`company_daily_cap` 目前允许同公司 3 条/日（第 4 条才删）——改为合并后检查，从 3 条降为 2 条/日，超出进入合并链路而非直接保留
5. **同日去重与跨天去重共用同一事件键逻辑**（现两处调用 `_is_same_event`，统一行为）

验证标准：08-12 批次中 SEA 3→1、Jumia 2→1、Rakuten 2→1、Cytix 2→1；抽样 08-07~08-11 五天共 ≤10 条相同键事件人工核对无误并。

### 阶段 2：类型判定 AI 化 + fallback 文案中性化

1. **AI prompt 增加 event_types 判定**：DeepSeek/豆包分析时同时输出该事件属于哪类（funding/ma/earnings/strategy/industry_report/other），AI 结果为权威；关键词规则只作为 AI 失败后的兜底类型
2. **fallback 文案中性化**：`analysis_status='fallback'` 时，展示层不再按类型拼「XX 行业研究报告发布 / XX 公司财报披露」这类断言式模板；改为中性表述：「AI 分析暂不可用，展示原始报道标题与来源」。`insight_label` 也不展示类型化的「趋势信号」等标签（fallback 时隐藏或置「待分析」）
3. **AI 失败时的类型不参与展示**：fallback 事件的 event_types 仅用于存档标记（如过滤检索），不生成任何面向用户的事实性文字

验证标准：第 28 条 Cursor 卡片不再出现「亚太行业研究报告发布」；同类 fallback（Adyen #21、rankingCoach #25、Nvidia #29、Retail Dive #36）不再出现类型化模板文案。

### 阶段 3：存量清理与回归

1. 用新去重逻辑重跑近 30 天数据（对照事件被合并，原事件 URL 保留在 merged_from 字段，可追溯）
2. 08-13 起连续 3 个批次人工抽查：每日重复组数归零 / 误并为零
3. 更新 `data/site_updates.json`（按项目规范补版本记录）

## 六、风险与边界

- **误并风险（同键不同事件）**：如公司同一日既发财报又发融资（键不同，类型不同，安全）；同类型同日两条独立事件（罕见，用低相似度标记存疑防误删兜底）
- **不做的事**：不引入 embedding/向量库（规模小、词法+结构化键足够，见附录 A）；不做正式聚类评估框架（用样本回归代替）
- **数据可追溯**：合并保留 merged_from（现 `_upgrade_event` 已支持），不会丢原始 URL

## 七、实施顺序

阶段 1 → 阶段 2 → 阶段 3，每阶段独立可验证。改动集中在 `scripts/fetch_news.py`（去重+类型）与 `scripts/template.html`+`generate_html.py`（fallback 展示），不触碰 workflow 与数据 schema 结构。

## 八、实施后调整（对照本方案的偏差，已落地于 commit b40e5af）

1. **SEA 验证标准 3→1 实际为 3→2**：`"Sea Limited Stock Jumped 15%"` 属独立的股价反应信号，事件锚点守卫下不再并入财报卡片，单独保留。
2. **company_daily_cap 维持 3 不降为 2**：实测 cap=2 会误删真实事件（Naver-Dunamu 合并审查、Adyen-Toast 合作、TEAM NAVER AI 协作），去重已先合并真重复，cap 无需收紧。
3. **新增事件锚点守卫**：singular 类型合并要求两条标题都含财报/融资/并购锚词，防止同公司同日不同故事（MercadoLibre 多条股票评论、Kakao 财报日游戏新闻）被误并；财报方向相反（利润创新高 vs 净利大跌）不合并。
4. **别名对齐加词边界 + 泛化词黑名单**：`credit line`、`SeABank`、`to grab` 等普通词不再被误当公司别名，杜绝跨公司误并（审计发现 Addi/Elephant、Orbio/Qorelo、Nous/OPEC 等 4 组误并已修复）。
5. **存量清理结果 3065→3045**（方案预估的 3065→3021 是去掉误并后的值）。
6. **已知局限**：同母公司不同子公司财报（Rakuten Bank vs Rakuten Securities）仍可能并入父公司条目，发生率低（99 天 1 例）暂不处理。

## 附录 A：为什么不引入向量 embedding

调研到的工业方案（SimHash+SBERT）面向亿级报道的规模。本项目每日采集约 60 条、标题短、且已具备姓名/类型/时间结构化字段——该规模下结构化事件键是精度与成本的最优解。引入 SBERT 类依赖会带来模型下载、CPU 推理延迟与维护成本，收益（对 60 条/日）可忽略。若未来日采规模上千且跨语种相似判定成为瓶颈，再评估 embedding 方案。