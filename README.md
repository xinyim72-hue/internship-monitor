# 📊 Internship Monitor · 远程实习监控仪表盘

> 自动聚合国内主流招聘平台的远程数据分析实习岗位，每天自动更新，一键查看投递。

**🔗 Live Dashboard → [点击查看](https://你的用户名.github.io/internship-monitor/)**

---

## Features

- **三大数据源**：实习僧 · 牛客网 · 应届生 BBS，关键词覆盖"远程数据分析/数据科学/数据运营/商业分析"
- **每日自动更新**：GitHub Actions 每天北京时间 09:00 自动抓取，增量去重，push 到 GitHub Pages
- **可交互仪表盘**：
  - 🔍 实时搜索过滤（岗位名 / 公司名 / 关键词）
  - 📅 按时间筛选（近 7 / 14 / 30 天）
  - 🏢 按来源筛选
  - ⭐ 收藏感兴趣的岗位
  - ✅ 标记已投递
  - 🚫 隐藏不感兴趣的
  - 标记状态保存在浏览器本地，关闭后不丢失
- **一键投递**：每个岗位直接提供原始链接，点击跳转对应平台投递页

---

## Tech Stack

`Python 3.11` · `requests` · `BeautifulSoup4` · `GitHub Actions` · `GitHub Pages`

数据持久化：`docs/jobs.json`（保留近 30 天）  
前端：纯 HTML + CSS + Vanilla JS，无框架依赖，单文件

---

## Deploy Your Own

```bash
# 1. Fork 本仓库
# 2. Settings → Pages → Source 选 "Deploy from branch: main / docs"
# 3. Actions → Daily Internship Scraper → Run workflow (手动触发第一次)
# 4. 等 1-2 分钟，访问 https://你的用户名.github.io/internship-monitor/
```

不需要配置任何 API key 或 Secret，完全免费。

---

## License

MIT · 欢迎 Fork 改造成自己需要的招聘监控工具
