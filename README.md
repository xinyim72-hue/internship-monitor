# 📊 Internship Monitor · 远程实习监控仪表盘

> 自动聚合国内主流招聘平台的**远程数据分析/数据科学/商业分析实习岗位**，每天自动更新，免配置，一键 Fork 即用。

**🔗 Live Dashboard → [点击查看 xinyim72-hue.github.io/internship-monitor](https://xinyim72-hue.github.io/internship-monitor/)**

---

## Demo

仪表盘实时展示最近 30 天抓取到的岗位，支持搜索、按来源/时间筛选、收藏、标记已投递、隐藏。所有标记状态保存在浏览器本地（localStorage），刷新或关闭不丢失。

```
┌─────────────────────────────────────────────────────┐
│  📊 远程实习监控仪表盘                                │
│  今日新增: 12  |  近7天: 47  |  近30天总计: 134      │
├─────────────────────────────────────────────────────┤
│  🔍 搜索岗位、公司名...  [来源▼] [近7天▼]            │
│  [全部] [⭐收藏] [✅已投] [🚫已隐藏]                 │
├─────────────────────────────────────────────────────┤
│  🆕今日  数据分析实习生         字节跳动              │
│          📍远程  💰 150/天  实习僧  2026-05-30       │
│          [🔗查看投递] [⭐收藏] [✅标记已投] [🚫隐藏] │
│  ─────────────────────────────────────────────────  │
│  🆕近7天 商业分析实习（BI方向）  腾讯                 │
│          📍居家办公  牛客网  2026-05-28               │
│          [🔗查看投递] [⭐收藏] [✅标记已投] [🚫隐藏] │
└─────────────────────────────────────────────────────┘
```

---

## Features

| 功能 | 说明 |
|------|------|
| **三大数据源** | 实习僧 · 牛客网 · 应届生 BBS，6 个关键词覆盖远程数据分析/数据科学/数据运营/商业分析/BI |
| **每日自动更新** | GitHub Actions 每天北京时间 09:00 抓取，增量去重，自动 commit & push |
| **实时搜索过滤** | 按岗位名、公司名、关键词全文搜索 |
| **时间/来源筛选** | 近 7 / 14 / 30 天，或按数据源单独筛选 |
| **收藏 & 投递追踪** | ⭐ 收藏感兴趣岗位，✅ 标记已投递，🚫 隐藏不感兴趣的 |
| **本地状态持久化** | 所有标记存 localStorage，刷新不丢失 |
| **一键投递** | 每个岗位直接链接到原始平台投递页 |
| **免费零配置** | 不需要任何 API key 或 Secret |

---

## Tech Stack

| 层 | 技术 |
|----|------|
| 爬虫 | Python 3.11 · requests · BeautifulSoup4 · lxml |
| 自动化 | GitHub Actions（每日定时 + 手动触发） |
| 数据存储 | `docs/jobs.json`（近 30 天，JSON 格式） |
| 前端 | 纯 HTML + CSS + Vanilla JS，单文件，无框架依赖 |
| 托管 | GitHub Pages（`docs/` 目录） |

---

## Fork 自己用

**3 步完成，无需任何额外配置：**

```bash
# Step 1: Fork 本仓库
# 点击右上角 Fork 按钮 → 选择你的账户

# Step 2: 开启 GitHub Pages
# 仓库 Settings → Pages → Source 选 "Deploy from branch"
# Branch: main，目录: /docs → Save

# Step 3: 触发第一次抓取
# Actions → Daily Internship Scraper → Run workflow
```

等 1-2 分钟，访问 `https://<你的用户名>.github.io/internship-monitor/` 即可。

**自定义关键词：** 修改 `scraper.py` 顶部的 `KEYWORDS` 列表，改成你需要的岗位类型。

---

## Project Structure

```
internship-monitor/
├── .github/workflows/daily.yml   # GitHub Actions 自动化脚本
├── docs/
│   ├── index.html                # 自动生成的仪表盘页面
│   └── jobs.json                 # 持久化岗位数据（近 30 天）
├── scraper.py                    # 多源爬虫 + HTML 生成器
└── requirements.txt
```

---

## License

MIT · 欢迎 Fork 改造成自己需要的招聘监控工具
