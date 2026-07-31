# 可审计事实链重建设计

## 决策

系统继续使用 Python、JSON 和 GitHub Pages，不引入数据库或新服务。改造重点是把现有“文章直接生成页面”收敛为唯一事实链：

```text
Observation -> Snapshot -> Diff Fact -> Candidate Signal
-> Qualified Event -> Evidence Atom -> Weekly Theme -> Monthly Trend
```

页面、RSS、健康报告和转化报告只能消费同一个事件资格结果，渲染阶段不得重新改变事件是否合格。

## 参考站取舍

参考 AIHOT 的编辑结构，而不是复制其内容生产方式：

- 日报保留本站“全部合格事件 + 精选/重点/观察”的导航职责。
- 周报采用“本期主线 -> 3～6 个主题 -> 每个主题的证据事件”。
- 月报采用“结构主线 -> 跨周趋势 -> 较前一周期变化 -> 代表证据”。
- 主题摘要必须来自独立证据，不能由默认机会标签或来源地域生成。

## 数据契约

每条事件增加派生但稳定的展示契约：

- `view_status`: `main / review / filtered`
- `view_reason`: 入选或过滤原因
- `view_priority`: `selected / important / watch`
- `origin_source_id`: 发现该事件的源或对象查询
- `observation_entity_id`: 对象池 ID
- `discovery_source`: RSS、官方页、Jobs 或 Google News

Jobs 候选单独写入 `data/signal_candidates.json`。候选保留证据职位、快照窗口、状态和拒绝原因；只有新增岗位形成明确职能簇且排除来源重置时，才能晋级事件。

## 晋级门槛

- Event：事实、对象或主题、时间、来源、影响说明完整。
- Evidence Atom：同一对象、同一动作的转载只能算一个原子。
- Weekly Theme：至少两个独立事实原子，且不是纯 Google News 或产品边界外事件。
- Monthly Trend：至少跨两个自然周、三个独立事实原子，并给出相对前一周期的变化。
- 默认机会方向不能参与主题或趋势晋级。

## 对象组合

`data/entity_pool.json` 是公司索引唯一来源，并增加三级组合：

- `must`：12 家，要求高频行为源和低频确认源。
- `strategic`：保持至少一个有效观察点。
- `experiment`：只服务明确适配器或信号假设。

公司卡同时展示活动状态与覆盖状态，避免“媒体有新闻”被误解为“直接观察完整”。

## 失败处理

- 抓取或解析失败不能覆盖上一次成功快照。
- 大比例职位全量替换标记 `source_reset_suspected`，不得生成事件。
- 健康报告必须输出 must 覆盖率、失败观察点、候选积压和 Jobs 失败。
- Workflow 文件本轮不修改；健康检查先作为可执行严格检查落地。

