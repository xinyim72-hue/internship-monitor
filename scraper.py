"""
远程实习监控 v2 - 多源爬虫
===========================
数据源:
  1. 实习僧 (shixiseng.com)
  2. 牛客网 (nowcoder.com)
  3. 应届生 BBS (yingjiesheng.com)

每次运行:
  - 抓取三个来源的最新岗位
  - 与 jobs.json 历史数据合并去重
  - 只保留最近 30 天的数据(节省空间)
  - 生成 index.html 供 GitHub Pages 展示
  - 将更新后的 jobs.json + index.html push 到仓库

Author: Xinyi Ma
"""

import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

# =========================================================================
# 配置
# =========================================================================

JOBS_FILE = "docs/jobs.json"        # 持久化数据（在 docs/ 下方便 GitHub Pages）
INDEX_FILE = "docs/index.html"      # 最终展示页面
KEEP_DAYS = 30                       # 保留最近 N 天的岗位
DISPLAY_DAYS = 7                     # 仪表盘默认展示最近 N 天的新岗位
MAX_PER_KEYWORD = 20                 # 每个关键词最多抓 N 条
DELAY = 3                            # 请求间隔（秒）

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

KEYWORDS = [
    "远程 数据分析",
    "远程 数据科学",
    "远程 数据运营",
    "远程 商业分析",
    "居家办公 数据分析",
    "远程 BI",
]

# =========================================================================
# 工具函数
# =========================================================================

def now_bj() -> datetime:
    """Return current Beijing time (UTC+8), works correctly in GitHub Actions."""
    return datetime.now(timezone.utc) + timedelta(hours=8)


def safe_get(url: str, timeout: int = 15) -> requests.Response | None:
    """安全的 HTTP GET，失败返回 None"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code == 200:
            return resp
        print(f"    ⚠️ HTTP {resp.status_code}: {url[:80]}")
        return None
    except Exception as e:
        print(f"    ❌ 请求失败: {e}")
        return None


def extract_text(elem, selectors: list[str]) -> str:
    """从候选 selector 中提取第一个有内容的文本"""
    for sel in selectors:
        found = elem.select_one(sel)
        if found:
            text = found.get_text(strip=True)
            if text:
                return text
    return ""


_SOURCE_BASE = {
    "实习僧": "https://www.shixiseng.com",
    "牛客网": "https://www.nowcoder.com",
    "应届生": "https://www.yingjiesheng.com",
}


def make_job(title: str, company: str, location: str,
             salary: str, link: str, keyword: str, source: str) -> dict:
    """构造标准岗位字典"""
    if link and not link.startswith("http"):
        base = _SOURCE_BASE.get(source, "")
        if base:
            link = urljoin(base + "/", link)
    # Use md5 for a stable, deterministic ID (Python's hash() is randomized per-run)
    job_id = int(hashlib.md5(link.encode(), usedforsecurity=False).hexdigest()[:8], 16)
    return {
        "id": job_id,
        "title": title or "未知岗位",
        "company": company or "未知公司",
        "location": location,
        "salary": salary,
        "link": link,
        "keyword": keyword,
        "source": source,
        "found_at": now_bj().strftime("%Y-%m-%d"),
    }

# =========================================================================
# 数据源 1：实习僧
# =========================================================================

def fetch_shixiseng(keyword: str) -> list[dict]:
    url = f"https://www.shixiseng.com/interns?keyword={quote(keyword)}&type=intern"
    print(f"  [实习僧] {keyword}")
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    # 多个备用 selector
    cards = []
    for sel in [".intern-wrap-block", ".position-card", ".intern-item",
                ".f-l.intern-detail", "[class*='intern-detail']"]:
        cards = soup.select(sel)
        if cards:
            break

    # fallback：找所有含 /intern/ 的链接
    if not cards:
        for a in soup.select("a[href*='/intern/']"):
            text = a.get_text(strip=True)
            if len(text) > 4:
                jobs.append(make_job(
                    title=text, company="", location="", salary="",
                    link=a.get("href", ""), keyword=keyword, source="实习僧"
                ))
        print(f"    ✓ fallback 抓到 {len(jobs)} 个")
        return jobs[:MAX_PER_KEYWORD]

    for card in cards[:MAX_PER_KEYWORD]:
        title = extract_text(card, [".intern-title", ".position-name", "h3 a", ".title"])
        company = extract_text(card, [".intern-company", ".company-name", "[class*='company']"])
        location = extract_text(card, [".intern-location", ".city", "[class*='city']"])
        salary = extract_text(card, [".intern-salary", ".salary", "[class*='salary']"])
        link_elem = card.select_one("a[href]")
        link = link_elem.get("href", "") if link_elem else ""
        if not title:
            continue
        jobs.append(make_job(title, company, location, salary, link, keyword, "实习僧"))

    print(f"    ✓ 抓到 {len(jobs)} 个")
    return jobs

# =========================================================================
# 数据源 2：牛客网实习板块
# =========================================================================

def fetch_nowcoder(keyword: str) -> list[dict]:
    url = f"https://www.nowcoder.com/jobs/internship?keyword={quote(keyword)}"
    print(f"  [牛客网] {keyword}")
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    # 牛客岗位卡片
    cards = []
    for sel in [".position-item", ".job-item", "[class*='position']", "li[class*='item']"]:
        cards = soup.select(sel)
        if cards:
            break

    if not cards:
        # fallback：找所有含 /jobs/detail 的链接
        for a in soup.select("a[href*='/jobs/detail']"):
            text = a.get_text(strip=True)
            if len(text) > 4:
                href = a.get("href", "")
                if not href.startswith("http"):
                    href = "https://www.nowcoder.com" + href
                jobs.append(make_job(
                    title=text, company="", location="", salary="",
                    link=href, keyword=keyword, source="牛客网"
                ))
        print(f"    ✓ fallback 抓到 {len(jobs)} 个")
        return jobs[:MAX_PER_KEYWORD]

    for card in cards[:MAX_PER_KEYWORD]:
        title = extract_text(card, [".position-name", ".job-name", ".title", "h3", "h4"])
        company = extract_text(card, [".company-name", ".firm-name", "[class*='company']"])
        location = extract_text(card, [".city", ".location", "[class*='city']"])
        salary = extract_text(card, [".salary", "[class*='salary']"])
        link_elem = card.select_one("a[href]")
        link = link_elem.get("href", "") if link_elem else ""
        if link and not link.startswith("http"):
            link = "https://www.nowcoder.com" + link
        if not title:
            continue
        jobs.append(make_job(title, company, location, salary, link, keyword, "牛客网"))

    print(f"    ✓ 抓到 {len(jobs)} 个")
    return jobs

# =========================================================================
# 数据源 3：应届生 BBS
# =========================================================================

def fetch_yingjiesheng(keyword: str) -> list[dict]:
    url = f"https://www.yingjiesheng.com/job-{quote(keyword)}.html"
    print(f"  [应届生] {keyword}")
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    cards = []
    for sel in [".zhaopin_list_left", ".job-item", ".joblist-item",
                "dl.clearfix", "[class*='job']"]:
        cards = soup.select(sel)
        if cards:
            break

    if not cards:
        # fallback
        for a in soup.select("a[href*='job']"):
            text = a.get_text(strip=True)
            if len(text) > 4 and len(text) < 50:
                href = a.get("href", "")
                if not href.startswith("http"):
                    href = "https://www.yingjiesheng.com" + href
                jobs.append(make_job(
                    title=text, company="", location="", salary="",
                    link=href, keyword=keyword, source="应届生"
                ))
        print(f"    ✓ fallback 抓到 {min(len(jobs), MAX_PER_KEYWORD)} 个")
        return jobs[:MAX_PER_KEYWORD]

    for card in cards[:MAX_PER_KEYWORD]:
        title = extract_text(card, ["dt a", ".job-name", ".title", "a"])
        company = extract_text(card, [".company", "[class*='company']", "dd.com"])
        location = extract_text(card, [".place", ".city", "[class*='place']"])
        salary = extract_text(card, [".salary", "[class*='salary']"])
        link_elem = card.select_one("a[href]")
        link = link_elem.get("href", "") if link_elem else ""
        if link and not link.startswith("http"):
            link = "https://www.yingjiesheng.com" + link
        if not title:
            continue
        jobs.append(make_job(title, company, location, salary, link, keyword, "应届生"))

    print(f"    ✓ 抓到 {len(jobs)} 个")
    return jobs

# =========================================================================
# 数据持久化
# =========================================================================

def load_jobs() -> list[dict]:
    """从 jobs.json 加载历史数据"""
    path = Path(JOBS_FILE)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("jobs", [])
    except Exception as e:
        print(f"⚠️ 加载 jobs.json 失败: {e}")
        return []


def save_jobs(jobs: list[dict]) -> None:
    """保存到 jobs.json，只保留最近 KEEP_DAYS 天"""
    bj = now_bj()
    cutoff = (bj - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    jobs = [j for j in jobs if j.get("found_at", "2000-01-01") >= cutoff]

    Path(JOBS_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "updated_at": bj.strftime("%Y-%m-%dT%H:%M:%S"),
            "total": len(jobs),
            "jobs": jobs,
        }, f, ensure_ascii=False, indent=2)
    print(f"💾 已保存 {len(jobs)} 个岗位到 jobs.json")

# =========================================================================
# 生成 HTML 仪表盘
# =========================================================================

def generate_html(jobs: list[dict]) -> str:
    """生成完整的 HTML 仪表盘页面（单文件，含 CSS + JS）"""

    # 按 found_at 倒序
    jobs_sorted = sorted(jobs, key=lambda x: x.get("found_at", ""), reverse=True)

    # 统计
    bj = now_bj()
    today = bj.strftime("%Y-%m-%d")
    cutoff_7d = (bj - timedelta(days=DISPLAY_DAYS)).strftime("%Y-%m-%d")
    new_today = sum(1 for j in jobs if j.get("found_at") == today)
    new_7d = sum(1 for j in jobs if j.get("found_at", "") >= cutoff_7d)

    # 生成每个 source 的选项
    sources = sorted(set(j.get("source", "") for j in jobs))
    source_options = "\n".join(
        f'<option value="{s}">{s}</option>' for s in sources
    )

    # 序列化 jobs 数据嵌入 JS
    jobs_json = json.dumps(jobs_sorted, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>远程实习监控仪表盘</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #f0f4f8;
    color: #1a202c;
    min-height: 100vh;
  }}

  /* 顶部 header */
  .header {{
    background: linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%);
    color: white;
    padding: 24px 32px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  }}
  .header h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 6px; }}
  .header p {{ font-size: 14px; opacity: 0.8; }}
  .stats {{
    display: flex;
    gap: 24px;
    margin-top: 16px;
    flex-wrap: wrap;
  }}
  .stat-card {{
    background: rgba(255,255,255,0.15);
    border-radius: 10px;
    padding: 10px 20px;
    text-align: center;
  }}
  .stat-card .num {{ font-size: 28px; font-weight: 800; }}
  .stat-card .label {{ font-size: 12px; opacity: 0.85; margin-top: 2px; }}

  /* 筛选栏 */
  .filter-bar {{
    background: white;
    padding: 16px 32px;
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
    border-bottom: 1px solid #e2e8f0;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
  }}
  .filter-bar input, .filter-bar select {{
    border: 1px solid #cbd5e0;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }}
  .filter-bar input:focus, .filter-bar select:focus {{
    border-color: #3182ce;
  }}
  .filter-bar input {{ width: 260px; }}
  .badge {{
    background: #ebf8ff;
    color: #2b6cb0;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid #bee3f8;
    transition: all 0.15s;
    white-space: nowrap;
  }}
  .badge:hover, .badge.active {{
    background: #2b6cb0;
    color: white;
  }}
  .badge.danger {{ background: #fff5f5; color: #c53030; border-color: #fed7d7; }}
  .badge.danger:hover, .badge.danger.active {{
    background: #c53030; color: white;
  }}

  /* 岗位列表 */
  .container {{
    max-width: 960px;
    margin: 24px auto;
    padding: 0 20px;
  }}
  .section-title {{
    font-size: 15px;
    color: #4a5568;
    margin-bottom: 14px;
    font-weight: 600;
  }}

  /* 岗位卡片 */
  .job-card {{
    background: white;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 12px;
    border: 1px solid #e2e8f0;
    transition: all 0.15s;
    position: relative;
  }}
  .job-card:hover {{
    border-color: #90cdf4;
    box-shadow: 0 4px 12px rgba(49,130,206,0.1);
    transform: translateY(-1px);
  }}
  .job-card.hidden-card {{
    opacity: 0.35;
    background: #f7fafc;
  }}
  .job-card.starred-card {{
    border-left: 4px solid #f6ad55;
  }}
  .job-card.applied-card {{
    border-left: 4px solid #68d391;
  }}

  /* 卡片内容 */
  .job-header {{
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 8px;
  }}
  .new-badge {{
    background: #fed7e2;
    color: #c53030;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 20px;
    white-space: nowrap;
    flex-shrink: 0;
    margin-top: 3px;
  }}
  .job-title {{
    font-size: 16px;
    font-weight: 700;
    color: #1a202c;
    line-height: 1.4;
  }}
  .job-meta {{
    font-size: 13px;
    color: #718096;
    margin-bottom: 12px;
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
  }}
  .job-meta span {{ display: flex; align-items: center; gap: 4px; }}

  /* 操作按钮组 */
  .job-actions {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
  }}
  .btn {{
    padding: 6px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    border: 1.5px solid;
    transition: all 0.15s;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }}
  .btn-primary {{
    background: #2b6cb0;
    color: white;
    border-color: #2b6cb0;
  }}
  .btn-primary:hover {{ background: #1a4f8a; border-color: #1a4f8a; }}
  .btn-star {{
    background: white;
    color: #c05621;
    border-color: #fbd38d;
  }}
  .btn-star:hover, .btn-star.active {{
    background: #fefcbf;
    border-color: #f6ad55;
  }}
  .btn-apply {{
    background: white;
    color: #276749;
    border-color: #9ae6b4;
  }}
  .btn-apply:hover, .btn-apply.active {{
    background: #f0fff4;
    border-color: #68d391;
  }}
  .btn-hide {{
    background: white;
    color: #718096;
    border-color: #e2e8f0;
  }}
  .btn-hide:hover, .btn-hide.active {{
    background: #f7fafc;
    border-color: #cbd5e0;
  }}

  /* 来源标签 */
  .source-tag {{
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 20px;
    font-weight: 600;
  }}
  .source-实习僧 {{ background: #ebf8ff; color: #2c5282; }}
  .source-牛客网 {{ background: #f0fff4; color: #22543d; }}
  .source-应届生 {{ background: #fff5f5; color: #742a2a; }}

  /* 空状态 */
  .empty {{
    text-align: center;
    padding: 80px 20px;
    color: #a0aec0;
  }}
  .empty .emoji {{ font-size: 48px; margin-bottom: 16px; }}
  .empty p {{ font-size: 16px; }}

  /* 底部 */
  .footer {{
    text-align: center;
    padding: 40px 20px;
    color: #a0aec0;
    font-size: 13px;
  }}

  /* 响应式 */
  @media (max-width: 600px) {{
    .header {{ padding: 18px 16px; }}
    .filter-bar {{ padding: 12px 16px; }}
    .filter-bar input {{ width: 100%; }}
    .container {{ padding: 0 12px; }}
    .job-card {{ padding: 14px; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>📊 远程实习监控仪表盘</h1>
  <p>自动聚合实习僧 · 牛客网 · 应届生三大平台的远程数据分析实习岗位</p>
  <div class="stats">
    <div class="stat-card">
      <div class="num" id="stat-today">{new_today}</div>
      <div class="label">今日新增</div>
    </div>
    <div class="stat-card">
      <div class="num" id="stat-7d">{new_7d}</div>
      <div class="label">近7天新增</div>
    </div>
    <div class="stat-card">
      <div class="num" id="stat-total">{len(jobs)}</div>
      <div class="label">近30天总计</div>
    </div>
    <div class="stat-card">
      <div class="num" id="stat-visible">-</div>
      <div class="label">当前显示</div>
    </div>
  </div>
</div>

<div class="filter-bar">
  <input type="text" id="search" placeholder="🔍 搜索岗位、公司名..." oninput="applyFilters()">
  <select id="source-filter" onchange="applyFilters()">
    <option value="">全部来源</option>
    {source_options}
  </select>
  <select id="date-filter" onchange="applyFilters()">
    <option value="7">近7天</option>
    <option value="14">近14天</option>
    <option value="30">近30天</option>
    <option value="0">全部</option>
  </select>
  <span class="badge active" id="filter-all" onclick="setStatusFilter('all')">全部</span>
  <span class="badge" id="filter-starred" onclick="setStatusFilter('starred')">⭐ 收藏</span>
  <span class="badge" id="filter-applied" onclick="setStatusFilter('applied')">✅ 已投</span>
  <span class="badge danger" id="filter-hidden" onclick="setStatusFilter('hidden')">🚫 已隐藏</span>
</div>

<div class="container">
  <p class="section-title" id="result-count"></p>
  <div id="job-list"></div>
  <div class="empty" id="empty-state" style="display:none">
    <div class="emoji">🔍</div>
    <p>没有符合条件的岗位</p>
  </div>
</div>

<div class="footer">
  数据更新于 {bj.strftime("%Y-%m-%d %H:%M")} (北京时间) ·
  仅展示近 {KEEP_DAYS} 天数据 · 
  标记状态保存在本地浏览器，清除缓存后会重置
</div>

<script>
// ── 数据 ──────────────────────────────────────────────
const ALL_JOBS = {jobs_json};
const TODAY = "{today}";
const CUTOFF_7D = "{cutoff_7d}";

// ── 状态管理 (localStorage) ───────────────────────────
const STORAGE_KEY = "internship_monitor_status";

function loadStatus() {{
  try {{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}"); }}
  catch {{ return {{}}; }}
}}
function saveStatus(s) {{
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
}}
function getJobStatus(id) {{
  return loadStatus()[id] || "normal";
}}
function setJobStatus(id, status) {{
  const s = loadStatus();
  if (status === "normal") delete s[id];
  else s[id] = status;
  saveStatus(s);
}}

// ── 过滤状态 ──────────────────────────────────────────
let currentStatusFilter = "all";

function setStatusFilter(f) {{
  currentStatusFilter = f;
  ["all","starred","applied","hidden"].forEach(k => {{
    document.getElementById("filter-" + k).classList.toggle("active", k === f);
  }});
  applyFilters();
}}

// ── 核心渲染 ──────────────────────────────────────────
function applyFilters() {{
  const q = document.getElementById("search").value.trim().toLowerCase();
  const srcFilter = document.getElementById("source-filter").value;
  const days = parseInt(document.getElementById("date-filter").value);
  const statusMap = loadStatus();

  const cutoff = days === 0 ? "0000-00-00" :
    new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);

  let filtered = ALL_JOBS.filter(j => {{
    // 日期筛选
    if ((j.found_at || "") < cutoff) return false;
    // 来源筛选
    if (srcFilter && j.source !== srcFilter) return false;
    // 文本搜索
    if (q) {{
      const haystack = (j.title + j.company + j.keyword).toLowerCase();
      if (!haystack.includes(q)) return false;
    }}
    // 状态筛选
    const st = statusMap[j.id] || "normal";
    if (currentStatusFilter === "all") return st !== "hidden";
    if (currentStatusFilter === "starred") return st === "starred";
    if (currentStatusFilter === "applied") return st === "applied";
    if (currentStatusFilter === "hidden") return st === "hidden";
    return true;
  }});

  document.getElementById("stat-visible").textContent = filtered.length;
  document.getElementById("result-count").textContent =
    `共 ${{filtered.length}} 个岗位`;

  const list = document.getElementById("job-list");
  const empty = document.getElementById("empty-state");

  if (filtered.length === 0) {{
    list.innerHTML = "";
    empty.style.display = "block";
    return;
  }}
  empty.style.display = "none";
  list.innerHTML = filtered.map(j => renderCard(j, statusMap)).join("");
}}

function renderCard(j, statusMap) {{
  const st = statusMap[j.id] || "normal";
  const isNew = (j.found_at || "") >= CUTOFF_7D;
  const isToday = j.found_at === TODAY;

  let cardClass = "job-card";
  if (st === "hidden") cardClass += " hidden-card";
  if (st === "starred") cardClass += " starred-card";
  if (st === "applied") cardClass += " applied-card";

  const newBadge = isToday
    ? '<span class="new-badge">🆕 今日</span>'
    : isNew ? '<span class="new-badge" style="background:#e9d8fd;color:#553c9a">🆕 近7天</span>'
    : '';

  const salary = j.salary ? `<span>💰 ${{j.salary}}</span>` : "";
  const location = j.location ? `<span>📍 ${{j.location}}</span>` : "";

  return `
  <div class="${{cardClass}}" id="card-${{j.id}}">
    <div class="job-header">
      ${{newBadge}}
      <span class="job-title">${{j.title}}</span>
    </div>
    <div class="job-meta">
      <span>🏢 ${{j.company}}</span>
      ${{salary}}
      ${{location}}
      <span>📅 ${{j.found_at}}</span>
      <span class="source-tag source-${{j.source}}">${{j.source}}</span>
    </div>
    <div class="job-actions">
      <a class="btn btn-primary" href="${{j.link}}" target="_blank">🔗 查看投递</a>
      <button class="btn btn-star ${{st==='starred'?'active':''}}"
        onclick="toggleStatus(${{j.id}},'starred')">
        ⭐ ${{st==='starred'?'取消收藏':'收藏'}}
      </button>
      <button class="btn btn-apply ${{st==='applied'?'active':''}}"
        onclick="toggleStatus(${{j.id}},'applied')">
        ✅ ${{st==='applied'?'已投递':'标记已投'}}
      </button>
      <button class="btn btn-hide ${{st==='hidden'?'active':''}}"
        onclick="toggleStatus(${{j.id}},'hidden')">
        🚫 ${{st==='hidden'?'取消隐藏':'隐藏'}}
      </button>
    </div>
  </div>`;
}}

function toggleStatus(id, newSt) {{
  const cur = getJobStatus(id);
  setJobStatus(id, cur === newSt ? "normal" : newSt);
  applyFilters();
}}

// ── 初始化 ────────────────────────────────────────────
applyFilters();
</script>
</body>
</html>"""

# =========================================================================
# 主流程
# =========================================================================

def main():
    print("=" * 60)
    print(f"🚀 远程实习监控 v2 启动: {now_bj().strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print("=" * 60)

    # 1. 加载历史数据
    old_jobs = load_jobs()
    old_links = {j.get("link") for j in old_jobs if j.get("link")}
    print(f"📂 历史岗位: {len(old_jobs)} 个\n")

    # 2. 多源抓取
    all_new: list[dict] = []
    for kw in KEYWORDS:
        for fetcher in [fetch_shixiseng, fetch_nowcoder, fetch_yingjiesheng]:
            jobs = fetcher(kw)
            all_new.extend(jobs)
            time.sleep(DELAY)
        print()

    print(f"📊 本次抓取原始数据: {len(all_new)} 条")

    # 3. 去重（只保留历史里没有的链接）
    seen_links: set[str] = set()
    truly_new: list[dict] = []
    for j in all_new:
        lnk = j.get("link", "")
        if not lnk or lnk in old_links or lnk in seen_links:
            continue
        truly_new.append(j)
        seen_links.add(lnk)

    print(f"✨ 真正新增: {len(truly_new)} 个岗位\n")

    # 4. 合并 + 保存
    merged = old_jobs + truly_new
    save_jobs(merged)

    # 5. 生成 HTML
    print("🎨 生成 HTML 仪表盘...")
    html = generate_html(merged)
    Path(INDEX_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ index.html 已生成 ({len(html)//1024} KB)")

    print("\n" + "=" * 60)
    print("✅ 完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
