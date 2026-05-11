# 🌍 全球互联网动态情报站

自动爬取非中美地区的互联网/科技行业动态，通过 AI 分析并展示为可读的情报产品。

**排除**：中国、美国（含港澳台）的互联网公司动态
**包含**：欧洲、亚太、中东、非洲、拉美的互联网/科技公司融资、并购、财报、战略信号

---

## 在线访问

**https://huangjun722.github.io/weekly-report/**

每天北京时间上午 10:00 自动更新。

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

| 信源 | 覆盖区域 | 说明 |
|------|----------|------|
| TechCrunch | 全球 | 创业与科技新闻（含 VC 分类） |
| Tech.eu | 欧洲 | 欧洲科技媒体，融资报道丰富 |
| The Next Web | 欧洲 | 欧洲科技新闻 |
| TechWire Asia | 亚太 | 亚太科技新闻 |
| Tech in Asia | 亚太 | 亚洲科技与创业新闻 |
| WAMDA | 中东 | 中东北非创业生态 |
| MENAbytes | 中东 | 中东创业新闻 |
| TechCabal | 非洲 | 非洲科技与创业 |
| Disrupt Africa | 非洲 | 非洲创业融资（RSS 已恢复） |
| Techpoint | 非洲 | 非洲科技媒体 |
| Ventureburn | 非洲 | 非洲创业融资 |
| LAVCA | 拉美 | 拉丁美洲创投与私募 |
| Contxto | 拉美 | 拉美创业与创新 |

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
│   └── events.json               # 事件数据（保留近 15 天）
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

- **三层信息架构**：今日判断区（30秒扫读）→ 趋势分组事件（3分钟）→ 公司导航/搜索（需要时）
- **两 tab 统一卡片风格**：今日要点和全部事件使用一致的 `.daily-event` 卡片设计
- **趋势主题分组**：事件不再按类型分类，而是按 AI 分析的趋势主题（如"中东FinTech赛道升温"）聚合
- **今日判断区**：顶部展示 AI 每日趋势判断 + 3个关键信号卡片
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
