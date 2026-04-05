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
cp .env.example .env
# 编辑 .env，填入你的 Gemini API Key
# 获取地址：https://aistudio.google.com/apikey
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 运行

```bash
# 抓取数据 + 生成 HTML
python scripts/fetch_news.py
python scripts/generate_html.py

# 仅生成 HTML（数据已存在）
python scripts/generate_html.py
```

生成的文件在 `docs/index.html`，用浏览器打开即可预览。

---

## 信源

### RSS 信源

| 信源 | 覆盖区域 | 说明 |
|------|----------|------|
| TechCrunch | 全球 | 创业与科技新闻（含 VC 分类） |
| Tech.eu | 欧洲 | 欧洲科技媒体，融资报道丰富 |
| Sifted | 欧洲 | 欧洲科技创业媒体 |
| EU-Startups | 欧洲 | 欧洲创业公司融资 |
| Tech in Asia | 亚太 | 亚洲科技与创业新闻 |
| DealStreetAsia | 亚太 | 亚太融资与并购 |
| e27 | 亚太 | 东南亚科技生态 |
| WAMDA | 中东 | 中东北非创业生态 |
| TechCabal | 非洲 | 非洲科技与创业 |
| Techpoint | 非洲 | 非洲科技媒体 |
| Ventureburn | 非洲 | 非洲创业融资 |
| LAVCA | 拉美 | 拉丁美洲创投与私募 |
| Contxto | 拉美 | 拉美创业与创新 |

### HTML 备用采集

| 信源 | 覆盖区域 | 说明 |
|------|----------|------|
| Disrupt Africa | 非洲 | RSS 已废弃，改用 HTML 采集 |

---

## 技术栈

- **数据采集**：Python + BeautifulSoup + Requests（RSS + HTML 降级采集）
- **AI 分析**：Google Gemini API（免费额度足够）
- **页面生成**：Jinja2 模板
- **部署**：GitHub Actions + GitHub Pages

**月成本：$0**

---

## 项目结构

```
weekly-report/
├── .github/
│   └── workflows/update.yml   # 自动更新工作流（每天北京时间 10:00）
├── data/
│   └── events.json            # 事件数据（保留近 7 天）
├── scripts/
│   ├── fetch_news.py          # 爬取 + AI 分析
│   ├── generate_html.py        # 生成 HTML
│   └── template.html          # HTML 模板
├── docs/
│   └── index.html             # 生成的页面
├── requirements.txt
└── README.md
```

---

## 设计说明

页面采用"极简克制 + 现代杂志风"设计：

- **两层内容层级**：今日高价值信号（大卡片）+ 全部动态（紧凑列表）
- **固定顶栏**：搜索和筛选始终可见
- **事件分类**：融资（紫）/ 并购（红）/ 财报（绿）/ 战略（橙）/ 其他（灰）
- **区域标签**：欧洲 / 亚太 / 中东 / 非洲 / 拉美
- **信源等级**：A（8分以上）/ B（6-7分）/ C（4-5分）/ D（<4分）
- **响应式**：移动端单栏布局

---

## 采集信号类型

1. **融资**：融资轮次、估值变化、投资者
2. **并购**：收购、合并、战略投资
3. **财报**：季度/年度财务结果、IPO、上市
4. **战略**：合作伙伴、新产品发布、扩张、裁员、关停
