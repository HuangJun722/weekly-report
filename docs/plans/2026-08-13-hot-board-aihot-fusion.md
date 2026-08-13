# 热点榜融合方案：借鉴 AIHOT 机制，用我们自己的信号

> 日期：2026-08-13
> 状态：已确认路线（用户选 C），进入实施准备
> 调研对象：https://aihot.virxact.com/hot（AIHOT 热点榜）、我们自己的 events.json 信号体系

## 一、AIHOT 热点榜是什么（第一性原理）

AIHOT 热点榜不是普通排行榜，而是「事件簇 + 热度聚合」：
- 把过去 48h 关于**同一事件**的多源报道（X 推文、Hacker News、RSS 媒体）归并成一个 story
- 热度值由**信源共鸣强度 + 时间衰减**实时计算
- 每条 story 由 AI 汇总全部报道生成综述
- 详情页展示信源时间线 + 每小时热度曲线

**本质 = Google News story clustering 的产品化。**

## 二、关键洞察：底层能力我们已齐

| AIHOT 组件 | 我们的对应物 | 状态 |
|-----------|-------------|------|
| 事件簇（story） | 事件键去重（同实体+同类型合并） | ✅ 昨天已完成 |
| 信源共鸣强度 | merged_from 数量 + source_tier 权威度 | ✅ 已具备 |
| 热度/变化信号 | signal_change_score + attention_score + trend_weight | ✅ 已具备 |
| AI 综述 | content_overview + reason | ✅ 已具备 |

**不需要造热点算法车轮。** 缺的只是「聚合排序 + 展示形态」。

## 三、已确认决策（用户拍板）

**路线 C（混合）：我们的信号做主榜 + AIHOT 做「全球 AI 视野」补充**

### 三个具体确认项

1. **AIHOT 补充块：数据直连原始事件，不转接 AIHOT 站点**
   - AIHOT story 详情页 JSON-LD 的 `isBasedOn` 字段就是原始来源链接数组（已实测：微信、X 推文、ithome、openrouter 等）
   - 做法：抓 /hot 列表 → 每条进 story 详情抓 `isBasedOn` → 展示时点击跳**原始来源文章**，不经 AIHOT 的 story 页
   - 需处理的坑：原始链接里微信/公众号、X 推文可能需要登录或已失效。策略：展示时标注来源类型，优先给可访问的原文链接，微信/X 降权或标注"需登录"

2. **今日情报也加排行展示**
   - 今日情报是首页主 tab（`data-panel="today"`），主内容区是 `f-list` 事件卡片 + 右侧 `f-rail` 侧栏
   - 加排行位置：主内容区 `f-list` 上方插入「今日热点 Top N」横条（我们信号的主榜），右侧 `f-rail` 侧栏加「全球 AI 视野」卡片（AIHOT 补充）

3. **数据获取方式**：复用 `fetch_model_leaderboard.py` 模式（已跑通的 AIHOT SSR 抓取），新增 `scripts/fetch_aihot_hot.py`

## 四、落地设计

### 4.1 我们信号主榜（今日热点，放今日情报主内容区顶部）

```
hot_score = w1 × signal_change_score/100     # 变化强度（已有）
         + w2 × min(共鸣度, 3)/3             # 多源共鸣（merged_from数, 已有）
         + w3 × source_tier权威度归一         # L1官方/L2垂直源权重高（已有）
         × 时间衰减                            # 近7天指数衰减（date字段）
```

- 窗口：近 7 天（默认），可调
- Top N：10~15 条
- 展示：排名 + 标题 + 热度条（相对最高分比例）+ 「N 家信源」聚合标识（hover 展开来源列表，复用模板 tooltip）+ AI 摘要（content_overview）
- 点击：跳事件原文（和今日情报现有卡片一致）
- 实现：`generate_html.py` 加 `build_hot_board(events, window_days=7)`，纯 Python 现成信号计算，零新依赖

### 4.2 AIHOT 全球 AI 视野（补充，放今日情报右侧 f-rail 侧栏）

- 新脚本 `scripts/fetch_aihot_hot.py`（复用模型榜的 SSR 抓取+JSON-LD 解析）
  - 抓 https://aihot.virxact.com/hot 列表（标题 + 热度值 + story URL）
  - 每条进 story 详情抓 `isBasedOn` 原始链接数组 + headline + AI 综述
  - 输出 `data/aihot_hot.json`
- 展示：Top 5~8 条，标题 + 热度值 + 来源标注
- 点击：跳**原始来源文章**（isBasedOn 里可访问的那条），标注来源域名；微信/X 推文等需登录的标注"原文需登录"
- 明确标注「全球 AI 视野 · 来源 AIHOT」，与主榜区分

### 4.3 部署

- GHA 采集 workflow 加一步：跑 `fetch_aihot_hot.py`（或在 generate_html 时检查数据新鲜度）
- 更新 `data/site_updates.json`

## 五、实施步骤

1. 新增 `scripts/fetch_aihot_hot.py`：抓 /hot + story 详情 isBasedOn → `data/aihot_hot.json`
2. `generate_html.py` 加 `build_hot_board()`（主榜计算）+ `build_aihot_vision()`（补充数据透传）
3. `template.html`：今日情报主内容区顶部加「今日热点」横条；f-rail 侧栏加「全球 AI 视野」卡片
4. 更新 `data/site_updates.json`
5. 回归验证：主榜对 08-12 事件（SEA/Jumia 合并事件显示正确共鸣数）；补充块原始链接可点开

## 六、风险与边界

- **AIHOT 反爬**：模型榜已稳定抓取 leaderboard 页，/hot 与 story 页结构类似，风险低。仍保持低频（每日一次）
- **原始链接失效**：AIHOT isBasedOn 里的微信/X 可能需登录或失效。策略：isBasedOn 数组内按可访问性排序，展示可访问的主源；不可访问的标注来源类型但仍给链接
- **主榜质量**：hot_score 用现成信号分，权重 w1/w2/w3 首版用经验值，上线后根据榜单合理性微调
- **不做的事**：不引入向量库、不做实时热度曲线（AIHOT 的每小时曲线对我们是过度投资）

## 附录：AIHOT 数据抓取要点（已实测）

- /hot 列表页 JSON-LD：`ItemList`，每条含 `name`（标题）+ `url`（story 详情页链接）
- story 详情页 JSON-LD：`NewsArticle`，含 `headline`、`description`（AI 综述）、`isBasedOn`（原始来源 URL 数组）
- 列表页 DOM 有热度值文本（如 "140 热度值"）+ 信源标注（"公众号：数字生命卡兹克 · 7小时前"）
- 无公开 API，全部走 SSR HTML 抓取（fetch_model_leaderboard.py 已验证可行）
