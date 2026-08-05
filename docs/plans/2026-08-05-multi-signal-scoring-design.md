# 多类型情报评分设计

## 决策

评分不再试图用一个数字同时判断真实性、产品范围、重要性和展示位置。系统先执行范围与质量闸门，再使用统一的可解释评分向量排序合格事件。

```text
Source -> Observation -> Fact / Claim -> Qualified Event
  -> Evidence Atom -> Weekly Theme -> Monthly Trend
```

研报发布是事实，研报中的行业判断是有归属的 Claim；AI 模型发布、区域政策变化和公司动作同样进入统一事件契约。

## 统一契约

新增字段：

- `content_type`：`industry_report`、`model_release`、`company_action`、`regional_policy` 等。
- `subject_type`：`report`、`ai_model`、`company`、`region_policy`、`industry`。
- `claim_type`：区分机构判断、模型发布事实、性能自述、政策变化和公司动作。
- `confidence_score`：证据可信度，不替代范围门槛。
- `attention_score`：用户注意力排序，不决定事实是否存在。
- `trend_weight`：对周报/月报趋势聚合的贡献权重。
- `score_breakdown`：来源权威性、变化幅度、决策相关性、范围匹配、新颖性和时效性。

## 内容类型规则

| 类型 | 主要变化 | 典型证据 |
|---|---|---|
| `industry_report` | 市场份额、规模、预测、区域结构 | 研究机构公开摘要、方法说明、发布日期 |
| `model_release` | 能力、价格、可获得性、开发者入口 | 官方发布、模型卡、API/价格页、独立基准 |
| `company_action` | 产品、扩张、投资、合作、招聘、组织变化 | 公司公告、IR、Jobs、产品页 |
| `regional_policy` | 法律效力、生效日期、覆盖对象、合规成本 | 监管机构、法规原文、官方解释 |

中国公司按对象属性处理，不因“中国”自动加分。重大 AI/互联网动作可以进入；普通国内经营、营销和泛宣传不能进入。海外动作同时记录 `origin_region=中国` 和 `impact_regions`。

## 展示与趋势

通过范围和质量闸门的研报可以直接进入日报，并以“研报观点”标明归属。日报表达“IDC 判断”，周报/月报只有在跨来源、跨时间或跨对象形成独立证据后才表达“系统综合趋势”。

所有合格事实继续展示；评分只改变 `精选 / 重点 / 观察` 排序。付费全文不可见时只使用公开摘要、目录、新闻稿或公开二次解读，事件必须标明 `interpretation_basis`，不能补写不可见内容。

## 失败模式与控制

- 研究机构旧报告页面反复抓取：发布日期必须独立解析，观察时间不能代替发布日期。
- 模型厂商自报性能被当成客观结论：`performance_claim` 与 `release_fact` 分开。
- 中国公司国内新闻泛滥：范围仍要求命中既定行业/AI或目标区域影响。
- 多家媒体转载同一报告：按机构、数据集和核心主张形成一个 Evidence Atom。
- 评分绕过边界：任何高分都不能救回 `scope_status=filtered` 或质量不合格事件。
