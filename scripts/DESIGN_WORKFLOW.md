# 设计变更流程

## 原则

- `scripts/template.html` 是设计的**唯一真相来源（SSOT）**
- `docs/index.html` 是**自动生成物**，不要直接编辑
- 任何设计变更都必须通过修改 `template.html` → commit → push → workflow 自动生效

## 设计变更流程

### 1. 修改设计

```bash
# 打开 scripts/template.html 进行修改
```

### 2. 本地预览

```bash
cd C:\Users\16120\Documents\claude-workspace\weekly-report-repo

# 生成本地预览文件（不覆盖 index.html）
python scripts/generate_html.py --preview

# 启动本地服务器（另一个终端）
python -m http.server 8000 --directory docs

# 浏览器访问 http://localhost:8000/preview.html
```

### 3. 验证效果

- [ ] 所有功能正常
- [ ] 数据正确渲染
- [ ] 响应式布局正常

### 4. 提交发布

```bash
git add scripts/template.html
git commit -m "feat: [描述设计变更]"
git push
```

GitHub Actions 会自动：
1. 拉取最新代码
2. 运行 `generate_html.py --force`
3. 从 `template.html` 重新生成 `index.html`
4. 推送到 GitHub Pages

## 紧急回滚

如果生产环境出现问题：

```bash
# 1. 从 Git 历史恢复 template.html
git log --oneline scripts/template.html
git checkout <commit-hash> -- scripts/template.html
git push

# 2. 或手动触发 workflow 重新生成
# 访问 GitHub Actions 页面 → Update workflow → Run workflow → html-only 模式
```

## 设计备份

重大改版前创建 Git tag：

```bash
git tag -a v1.0-hero-carousel -m "Hero轮播设计"
git push origin v1.0-hero-carousel
```

## 命令行参数

| 参数 | 作用 |
|------|------|
| `python scripts/generate_html.py` | 默认：生成到 index.html（有内容对比优化） |
| `python scripts/generate_html.py --force` | 强制重写 index.html（workflow 使用） |
| `python scripts/generate_html.py --preview` | 生成本地 preview.html（不覆盖 index.html） |
