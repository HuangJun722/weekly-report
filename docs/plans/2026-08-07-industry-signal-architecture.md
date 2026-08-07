# 情报站架构升级：从公司中心走向产业信号感知

日期：2026-08-07
状态：已确定方向，按序实施

## 一、背景与根因

系统长期按"公司中心"架构运转：采集→行业过滤→评分→展示，都以**公司**为轴心。
但产品目标是**全球互联网产业机会感知**——感知区域/行业变化，公司只是变化后的投影。

实测证据（误杀审计，2026-08-07）：
- 单次采集 162 条原文，最终入库 22 条
- 被砍 85 条中 70% 是真噪声（会展广告/公司琐事/清单），约 6%（5 条）是真实误杀的区域/政策/结构信号
- 公司源过闸率近 100%，区域媒体源过闸率极低 → 系统事实上以公司为中心

根因链：采集正常 → 行业过滤误杀区域信号 → 展示只认实体池 → 评分只评公司动作 → 周报素材少且格式化。

## 二、方案总览（四条链路，非三个 bug）

```
Raw Event
   ↓
Event Understanding       采集：区域/行业媒体已覆盖
   ↓
Event Score（公司动作）     现有评分保留，不推翻
   ↓
Signal Extraction        新增：识别"是否代表变化"（政策/技术/资本/用户）
   ↓
Signal Score（变化意义）    规则为主，AI 兜底
   ↓
Change Detection（重复）    事件组合 → 趋势（单事件低分，组合高分）
   ↓
实体池拆层                 Watchlist（人工关注） + Mention（自动发现）
   ↓
周报/月报                  Change Report：写变化不写存在
```

## 三、分步实施

### 阶段 1：政策/监管/结构变化专属通道（采集层）

- 不放开整个行业闸门（会放进 70% 噪声）
- 新增窄通道：事件命中政策词（监管/央行/法案/牌照/数据保护…）且可判区域/行业影响时放行
- 救回审计中那 5 条真实误杀信号，不放进行业媒体清单/广告

**落地（2026-08-07，`scripts/scope_gate.py`）：**
- 在 `assess_scope()` 的 `if not industries` 分支内新增两条窄通道，仅当行业词缺失时生效：
  - **Leg A** `REGIONAL_POLICY_TITLE_TERMS`：标题命中强监管动作词（rules/fined/orders/bars/
    tax/taxable/regulator/antitrust/央行/牌照/制裁…）→ `qualified`，层 `regional_policy`。
    刻意窄于 `POLICY_TERMS`（排除 approval/compliance/license/policy 等高频业务词，防"Vogue nod
    of approval"这类假阳性）；不作区域限定（"欧盟出台 AI 新规"的全球源报道也值得保留）。
  - **Leg B** `REGIONAL_STRUCTURAL_TITLE_TERMS`：标题命中结构/行业变化词（changing/shift/
    battle/consolidation/变革/洗牌…）且信源区域非"全球"综合源（`GLOBAL_REGION_LABELS`）→
    `qualified`，层 `industry_change`。
- 顺带发现并标注：`detect_event_types()` 从不产出 `regional_policy` 类型（下游评分/标签均支持，
  上游从不生成），属遗留缺口，阶段 1 已用标题词通道补上入口，检测器后续再补。

**验证（审计 85 条被砍事件离线重放行）：**
- 放行 8/85，全部为真实信号：Kenya 加密新规、RBI 禁贷、ESOP 税案、New Mexico 责令 Meta 付款、
  Meta 被罚 5.67 亿美元（双源）、新加坡数字银行混战、非洲银行改放贷、肯尼亚电信投诉转向。
- 剩余 77 条（广告/清单/融资/公司琐事）仍全部过滤，零噪声混入。

### 阶段 2：实体池拆分（展示层）

- Watchlist Entity：人工关注对象（腾讯、Grab、Kakao…）
- Mention Entity：自动发现对象（Zalando、Trendyol、某融资公司…）
- 未入 Watchlist 的公司，只要事件匹配也能在索引出现

**根因（2026-08-07 定位）：** 07-31 实体池重构用 `entity_pool`（32 家）替换了
`PRESET_COMPANIES` 硬编码清单，14 家被监控公司从公司索引消失——欧洲丢 3 家
（Zalando/Allegro/Trendyol）、中资丢 7 家（ByteDance/Tencent/Alibaba 等）、
Kaspi.kz 和 Konga 各丢 1。同时 Adyen 卡显示事件 0：`build_entity_event_timelines`
用主列表门槛 `is_main_view_event` 过滤，而主列表刻意整体排除 Google News 聚合源，
Adyen 覆盖面恰以 Google News 为主。

**落地（2026-08-07，`scripts/generate_html.py` + `scripts/template.html`）：**
- 公司卡门槛改为 `is_main_view_event(event) or is_company_quality_signal(event)`：
  主列表事件照旧保留，新增「公司质量信号」放行（Google News 强事件、存量
  view_status 为 filtered 的合格公司事件都能上卡）。Adyen 卡 0 → 12 事件。
- Mention 层持久化：监控雷达（`fetch_news.COMPANY_SOURCES`）中未纳入 entity_pool
  的 14 家公司生成持久索引卡，有近 7 天合格事件就带事件，没有则显示「监控中」。
  另保留事件自动发现：出现近 7 天合格事件但不在雷达/观察池的公司也加卡。
- 模板 tier 标签「自动发现」改为「关注中」（覆盖雷达监控 + 自动发现两类），
  卡片 detail 区分「监控中：公司雷达覆盖」与「自动发现：出现在公司源事件中」。

**验证：** 公司索引 32（Watchlist）+ 14（Mention）共 46 张卡。Adyen 12 事件。
测试套件 111 通过、1 个既有失败（原代码同样失败，非本次引入）。

### 阶段 3：评分体系升级（Event → Event + Signal）

- **Event Score**：保留现有融资/并购/财报/裁员评分，回答"公司发生了什么"
- **Signal Score**：新增，回答"这件事代表什么变化"
  - 信号分类先行：Market / Policy / Technology / Capital / Consumer / Company
  - 规则打分（区域+行业+变化词组合），规则判不了才送 AI，避免评分漂移
  - 组合评分：单事件低分不否决，趋势维度看"事件集合"重复出现
- 审计约束：Signal 层是"更聪明的窄门"，不得把 70% 噪声拉高

**落地（2026-08-07，`scripts/signal_scoring.py`）：**
- 新增 6 维信号分类 `infer_signal_type()`：Market / Policy / Technology / Capital /
  Consumer / Company。**policy 判定不以 content_type/scope_layer 标签为准**，必须命中
  窄词表（复用阶段 1 验证过的 `REGIONAL_POLICY_TITLE_TERMS` 词集）——旧数据可能把
  无政策词的 commerce 观点文误标成 regional_policy 层，标签不可信，词表命中才算。
- 新增 `signal_change_score()` 变化轴评分（0-100，回答"变化有多重要"），三档约束：
  - **不在目标行业内**（scope_status 非 qualified、无 scope_industries）→ 直接 0 分，
    与 Event Score 正交的"窄门"底线。
  - **行业内但无明确变化证据**（无变化词/量化）→ 0 分。普通 qualified 事件必须命中
    变化词/量化词才算"有变化"，不信任 scope_layer 标签（阶段 1 窄通道救回的事件凭
    `scope_reason` 标记直接放行）。
  - 量化加分只认"数字+单位/金额"模式（`%`、`$€£`、million/billion/亿/万），
    B2B/B2C/5G/Web3 这类缩写里的数字不算量化。
- 变化轴权重：policy 25 / technology 22 / market 20 / capital 18 / consumer 16 /
  company 12——改变产业结构/规则/能力的变化权重高，公司琐事权重低。
- 接入 `apply_signal_contract()`：每个事件自动获得 `signal_type`、`signal_change_score`、
  `signal_change_blocked`、`signal_change_breakdown` 四个字段。generate_html 经
  `prepare_event_contract` 自动带上，无需改采集管线。
- **自检修复（BUG 自检，2026-08-07）：** 首版"有变化"门槛只看本模块词表，导致 scope
  已判合格的融资/政策类真信号（央行代币化、区域融资）在 Signal 层 0 分。修复三点：
  1. **词表对齐 scope_gate**——`has_explicit_change` 复用 scope 层的 ACTION/INDUSTRY/
     QUANTIFIED/POLICY 词表，Signal 层与 scope 层判"是不是变化"同口径，分差只在"变化
     有多重要"；
  2. **强变化类型直通**——event_type ∈ {funding, ma, earnings, regional_policy} 天然是
     变化，不再依赖标题词（修复前"Eight Central Banks Test Tokenised Cross-Border
     Payments"得 0）；
  3. **补齐结构变化动词**——joins/tests/unveils/debuts/ramps up/commits/backs/weighs/
     extends/operationalises/承诺/推进…（修复前"Maybank Joins MAS' BLOOM"、"Mastercard
     Tests Crypto Credential"、6G 时间表均误杀为 0）。
  试错记录：过度修正一版把 qualified 全放行 → 261 条全 ≥55 失去区分度，回退；改为
  scope 词表对齐 + 强类型直通 + 动词补齐后，区分度与召回同时成立。

**验证（审计 77 条被砍噪声 + 全量 2809 条事件重放，`scripts/verify_signal_score.py`）：**
- 审计 77 条噪声（会展广告/公司琐事/清单）→ `signal_change_score` 全为 0，零噪声混入。
- events.json 全量：scope 已 filtered 的事件无一得分>0（Signal 层不推翻 scope 决定）。
- qualified 261 条：216 条得正分（有明确变化的真信号），45 条 0 分（观点文/文档/任命/公司琐事）。
- 分类抽查修正：修复前「B2B eCommerce is not B2C」被判 policy 100 分（误信 layer 标签
  + 把缩写数字当量化）→ 修复后正确归入"无明确变化" 0 分。
- 量化加分只认"数字+单位/金额"模式（`%`、`$€£`、million/billion/亿/万），B2B/B2C/5G/Web3
  这类缩写里的数字不计量化。
- 测试套件：test_signal_scoring 4/4、test_contract_backfill 5/5、全量无新回归
  （仅 test_view_selectors 既有失败，原代码同样失败）。

### 阶段 4：周报反格式化（输出层）

- 多喂具体事件（不只 2 条）
- 禁套话（"本周…预示…"/"由 N 条事实支持"/"资本涌动"）
- 固定大类标题改为具体标题
- 周报 = Change Report：写本周发生的变化，不写"存在哪些话题"

**落地（2026-08-07，`scripts/period_themes.py` + `scripts/generate_html.py`）：**
- **多喂事件**：AI 编辑 prompt 每条主题从 2 条证据提到 4 条；新增 `change_brief` 字段
  携带代表事件的具体标题/日期/类型，随 prompt 交给 AI（不只是裸标题）。
- **禁套话**：`build_weekly_themes` 的 `why` 去掉"本周由 N 个独立事实支持"元描述，改为
  直接引用代表事件的原因。AI prompt 增加反格式化硬约束：禁止"本周…预示…"、
  "资本涌动"、"开启新篇章"、"值得关注"等空话，禁止"由 N 条事实支持"元描述，每句话
  要有可验证信息。
- **固定大类标题改具体标题**：AI 为每个主题额外输出 `theme_title`（10-25 字，含具体
  对象/区域/动作），解析后覆盖 `window.title` / `direction`，不再显示"AI与云基础设施"
  这类大类标签。月报趋势同理。
- **写变化不写存在**：prompt 明确要求叙事写"本周/本月在某个方向实际发生了什么变化"，
  不写"存在哪些话题"。

**验证：** test_period_report 17/17 通过（新增 5 个反格式化专项测试：theme_title 覆盖
大类、why 无元套话、AI 收到 4 条证据、月报趋势标题覆盖）。全量测试无新回归
（仅 test_view_selectors 既有失败，原代码同样失败）。

### 延后：Opportunity Score（战略价值层）

- 依赖"客户"定义（自用/对外），阶段 1 不做
- Event + Signal 两层跑稳后再评估

## 四、系统已有雏形（不是从零建）

- `insight_label`（资金流向/合作机会/警示信号/背景补充）→ 信号分类
- `signal_clusters`（信号聚类）→ 事件集合
- `trend_topic`（趋势主题）→ 主题
- 现有 Signal 层散落，本次工作是**接成一条链**，非新建

## 五、红线约束

- 采集规则调整（阶段 1）、评分 prompt 改动（阶段 3）属敏感改动，改后必须用审计真实样本验证
- 不删除历史数据；entity_pool 拆分保留现有 32 家为 Watchlist 核心
- 每阶段完成后验证产出无回退（沿用 autoescape 后的验证方法）
