# 🌍 全球互联网动态情报站

自动爬取非中美地区的互联网行业动态，通过 AI 分析并展示为可读的情报产品。

**排除**：中国、美国（含港澳台）的互联网公司动态
**包含**：欧洲、亚太、中东、拉美、非洲的互联网/科技公司

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

| 信源 | 类型 | 覆盖区域 |
|------|------|----------|
| Hacker News | 新闻聚合 | 全球 |
| GitHub Trending | 开源/工具 | 全球 |
| Tech.eu | 科技媒体 | 欧洲 |
| Sifted | 科技媒体 | 欧洲 |

---

## 技术栈

- **数据采集**：Python + BeautifulSoup + Requests
- **AI 分析**：Google Gemini API（免费额度足够）
- **页面生成**：Jinja2 模板
- **部署**：GitHub Actions + GitHub Pages

**月成本：$0**

---

## 项目结构

```
weekly-report/
├── .github/
│   └── workflows/update.yml   # 自动更新工作流
├── data/
│   └── events.json            # 事件数据
├── scripts/
│   ├── fetch_news.py          # 爬取 + AI 分析
│   ├── generate_html.py       # 生成 HTML
│   └── template.html          # HTML 模板
├── docs/
│   └── index.html             # 生成的页面
├── requirements.txt
└── README.md
```

---

## 设计说明

页面采用"极简克制 + 现代杂志风"设计：

- **三层内容层级**：今日最重要(大卡片) → 本周最重要(中卡片) → 全部动态(紧凑列表)
- **固定顶栏**：搜索和筛选始终可见
- **信源等级标识**：A(绿)/B(蓝)/C(橙)/D(灰)
- **响应式**：移动端单栏布局
