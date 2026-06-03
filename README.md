# 🌍 全球互联网动态情报站

自动爬取非中美地区的互联网/科技行业动态，通过 AI 分析并展示为可读的情报产品。

**排除**：中国、美国（含港澳台）的互联网公司动态
**包含**：欧洲、亚太、中东、非洲、拉美的互联网/科技公司融资、并购、财报、战略信号

---

## 在线访问

**https://huangjun722.github.io/weekly-report/**

每天北京时间上午 10:00 自动更新。

---

## 使用指南

详细的使用说明、设计背景、技术架构和踩坑记录请见 [docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md)。

---

## 本地运行

### 1. 克隆仓库

```bash
git clone https://github.com/HuangJun722/weekly-report.git
cd weekly-report
```

### 2. 配置 API Key

```bash
# 方式一（推荐）：加密存储
# 1. 创建 .env 文件
cp .env.example .env
# 2. 编辑 .env，填入你的 DeepSeek API Key
# 3. 运行加密脚本（将 key 加密存储到 .env.encrypted）
python scripts/encrypt_key.py

# 方式二（开发调试）：直接使用 .env 文件
# 编辑 .env 填入 DEEPSEEK_API_KEY=sk-xxx
# fetch_news.py 会优先读取 .env

# DeepSeek 获取地址：https://platform.deepseek.com/
# 豆包获取地址：https://console.volcengine.com/ark/
```

### 2.1 配置反馈 API（可选）

反馈表单应写入线上记录，而不是只保存在浏览器。可部署 `workers/feedback-worker.js`，由 Worker 持有 `GITHUB_TOKEN` 并创建内部 Issue：

```bash
# 站点生成时注入前端提交地址
FEEDBACK_ENDPOINT=https://your-worker.example.workers.dev py -3 scripts/generate_html.py --force

# Worker 侧配置 GitHub token，不要写进前端或仓库
wrangler secret put GITHUB_TOKEN
```

未配置 `FEEDBACK_ENDPOINT` 时，页面会提示线上提交通道尚未配置，并保留本机草稿。

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 运行

```bash
# Windows（使用 Python 启动器）
py -3 scripts/generate_html.py --force

# Linux/macOS
python scripts/generate_html.py --force
```

生成的文件在 `docs/index.html`，用浏览器打开即可预览。

---

## 信源

### RSS 信源

| 层级 | 信源 | 覆盖区域 | 说明 |
|------|------|----------|------|
| L2 垂直交易源 | TechCrunch / TechCrunch VC | 全球 | 创业、融资、VC 动态 |
| L2 垂直交易源 | Tech.eu / UKTN / EU-Startups | 欧洲 | 欧洲融资、并购、上市与科技公司动态 |
| L3 区域生态源 | The Recursive / The Next Web | 欧洲 | 欧洲区域生态与战略动态 |
| L2 垂直交易源 | Tech in Asia / Inc42 | 亚太 | 亚洲与印度科技、融资、上市动态 |
| L3 区域生态源 | TechWire Asia | 亚太 | 亚太科技生态动态 |
| L4 垂直赛道精品源 | Finextra / Payments Dive | 全球 | 支付、金融科技、监管和商户网络信号 |
| L4 垂直赛道精品源 | Retail Dive / EcommerceBytes | 全球 | 电商、零售科技、AI 购物和平台变化 |
| L4 垂直赛道精品源 | Social Media Today / Mobile Marketing Magazine | 全球 | 社交平台、移动生态和广告商业化变化 |
| L2 垂直交易源 | WAMDA / MENAbytes | 中东 | 中东北非创业、融资、合作动态 |
| L2/L3 | Disrupt Africa / Ventureburn / TechCabal / Techpoint / WeeTracker | 非洲 | 非洲创业融资、平台经济、区域生态 |
| L2 垂直交易源 | LatamList / LAVCA | 拉美 | 拉美融资、创投、私募与创业动态 |
| L3 区域生态源 | Contxto | 拉美 | 拉美创业与创新生态 |
| L4 深度趋势源 | Rest of World Money / Ecommerce | 全球南方 | 只保留高信号事件，用于趋势和周/月报判断 |

### 公司监控

| 层级 | 信源 | 用途 |
|------|------|------|
| L1 官方/IR源 | Rakuten、Grab、MercadoLibre、Adyen、Sea、Zalando、Allegro、Kaspi.kz、Naver、Kakao、HKTVmall、U-NEXT、Square Enix、Jumia | 校准重点客户自身披露，优先保留财报、公告、战略和新闻稿 |
| L5 Google News 补漏源 | 30 家重点公司关键词 | 只做公司动态雷达，每家公司最多 2 条，默认不保留 `other` 类；中资公司只保留海外投资、跨境合作、海外市场和出海业务动向 |

每条事件会写入 `source_tier`、`source_role`、`bd_triggers`、`opportunity_direction`、`follow_up_window`、`bd_priority`。日报用它们辅助判断“今天先看谁和哪些证据”，周报再收敛窗口和方向，月报看趋势与结构变化。

信源处理库维护在 `data/source_registry.json`。新增自动采集源前，先在处理库记录赛道、信号类型、质量层级、抓取方式和晋级判断；候选源样本稳定后再进入脚本配置。

### HTML 备用采集

| 信源 | 覆盖区域 | 说明 |
|------|----------|------|
| DealStreetAsia | 亚太 | RSS 停用（Temporarily Disabled），JS SPA 降级成功率低 |

---

## 技术栈

- **数据采集**：Python + aiohttp + BeautifulSoup（异步 RSS + HTML 降级采集）
- **AI 分析**：评分前置分流 → DeepSeek API（本地主力，GHA 不可达）+ 豆包 API（GHA 实际主力）+ 程序降级
- **API Key 安全**：PBKDF2 + Fernet 加密存储
- **页面生成**：Jinja2 模板
- **部署**：GitHub Actions + GitHub Pages

**月成本：$0**

---

## 项目结构

```
weekly-report/
├── .github/
│   └── workflows/update.yml      # 自动更新工作流（每天北京时间 10:00）
├── data/
│   └── events.json               # 事件数据（保留近 90 天）
├── scripts/
│   ├── fetch_news.py             # 爬取 + AI 分析
│   ├── generate_html.py          # 生成 HTML
│   ├── template.html             # HTML 模板（设计 SSOT）
│   ├── decrypt_key.py            # API Key 解密（PBKDF2 + Fernet）
│   └── DESIGN_WORKFLOW.md        # 设计变更流程
├── docs/
│   └── index.html                # 生成的页面
├── requirements.txt
└── README.md
```

---

## 设计说明

页面采用"极简克制 + 现代杂志风"设计：

- **四层产品职责**：日报看对象和证据 → 周报看窗口和方向 → 月报看趋势和结构变化 → 公司索引看单个对象时间线
- **两 tab 统一卡片风格**：今日要点和全部事件使用一致的 `.daily-event` 卡片设计
- **今日观察区**：顶部展示当日优先观察对象或方向，不把单日事件硬升格为趋势结论
- **证据事件**：日报优先展示可解释的事实事件，关注窗口只在证据足够时辅助展示
- **固定顶栏**：搜索和筛选始终可见
- **事件图片**：左侧 100px×70px 缩略图（RSS media_content → og:image 两级兜底）
- **事件标签**：资金流向 / 合作机会 / 警示信号 / 趋势信号 / 中资出海
- **区域标签**：欧洲 / 亚太 / 中东 / 非洲 / 拉美
- **响应式**：移动端单栏布局

---

## 采集信号类型

1. **融资**：融资轮次、估值变化、投资者
2. **并购**：收购、合并、战略投资
3. **财报**：季度/年度财务结果、IPO、上市
4. **战略**：合作伙伴、新产品发布、扩张、裁员、关停
