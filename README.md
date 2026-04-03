# 全球互联网热点周报

每天自动爬取全球互联网热点，通过 AI 分析分级展示。

## 部署步骤

### 1. Fork 或克隆此仓库

### 2. 配置 GitHub Secrets
1. 进入仓库 Settings → Secrets and variables → Actions
2. 添加 Secret：`GEMINI_API_KEY`（你的 Gemini API 密钥）

### 3. 启用 GitHub Pages
1. 进入仓库 Settings → Pages
2. Source 选择 `Deploy from a branch`
3. Branch 选择 `main`，目录选择 `/docs`
4. 保存

### 4. 手动触发首次运行
1. 进入 Actions 标签页
2. 选择 "Update Weekly Report" 工作流
3. 点击 "Run workflow"
4. 等待完成后访问 `https://你的用户名.github.io/weekly-report-web/`

## 使用说明

- 每天凌晨2点（UTC）自动更新
- 支持手动触发更新
- 完全免费部署
