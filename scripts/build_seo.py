# -*- coding: utf-8 -*-
"""生成站点发现层：sitemap.xml + robots.txt + 404.html。

页面清单来自 lib/pages.py（唯一权威源）；lastmod 取三赛季最新一期评议日期
（数据没更新 sitemap 也不换日期，避免每次构建都刷新被抓取频率拖累）。
404.html 走完整主题（topbar+明暗切换），GitHub Pages 自动用作 404 页。
"""

import json
from datetime import date

from lib.pages import PAGES
from lib.paths import DATA, SITE
from lib.seo import SITE_URL, meta_tags
from lib.theme import icon, inject_theme, topbar


def latest_data_date() -> str:
    """三赛季 cases 数据里最新一期评议日期（YYYYMMDD → ISO 日期），拿不到用今天。"""
    latest = ""
    for season in ("2026", "2025", "2024"):
        path = DATA / f"cases-{season}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for issue in data.get("issues", []):
            d = str(issue.get("date", ""))
            if d.isdigit() and d > latest:
                latest = d
    if not latest:
        return date.today().isoformat()
    return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"


def build_sitemap(lastmod: str):
    urls = []
    for p in PAGES:
        if p["file"] == "404.html":
            continue  # noindex 页不进 sitemap
        urls.append(
            "  <url>\n"
            f"    <loc>{SITE_URL}/{p['file']}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <changefreq>{p['changefreq']}</changefreq>\n"
            f"    <priority>{p['priority']}</priority>\n"
            "  </url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    (SITE / "sitemap.xml").write_text(xml, encoding="utf-8")


def build_robots():
    txt = f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    (SITE / "robots.txt").write_text(txt, encoding="utf-8")


_404_LINKS = [
    ("index.html", "首页", "home", "三赛季入口与浏览模式"),
    ("season-2026.html", "2026 赛季评议", "film", "判例视频合集（进行中）"),
    ("rules.html", "竞赛规则 2026/27", "book", "简体中文版·划词高亮"),
    ("scale.html", "统一判罚尺度", "sliders", "三季 104 例官方场景"),
    ("quiz.html", "考题模式", "quiz", "700+ 题随机出卷"),
]


def build_404():
    cards = "".join(
        f'<a class="e-link" href="{href}">{icon(ic, 16)}<span><b>{label}</b>'
        f"<small>{sub}</small></span></a>"
        for href, label, ic, sub in _404_LINKS
    )
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>页面不存在 · 裁判学习平台</title>
<style>
.err-wrap{{max-width:640px;margin:0 auto;padding:48px 16px 80px;text-align:center}}
.err-code{{font-family:var(--font-display);font-size:88px;font-weight:700;
  color:var(--brand);line-height:1;letter-spacing:2px}}
.err-wrap h1{{font-family:var(--font-display);font-size:21px;margin:18px 0 6px}}
.err-wrap p{{color:var(--muted);font-size:13.5px;margin:0 0 14px}}
.e-search{{display:flex;gap:8px;max-width:420px;margin:0 auto 12px}}
.e-search input{{flex:1;padding:10px 16px;border:1px solid var(--line);border-radius:999px;
  background:var(--card);color:var(--ink);font-size:13.5px;outline:none}}
.e-search input:focus{{border-color:var(--brand)}}
.e-search button{{padding:10px 20px;border:1px solid var(--brand);border-radius:999px;
  background:var(--brand-strong);color:var(--on-brand);font-weight:700;font-size:13.5px;cursor:pointer}}
.e-links{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;
  text-align:left;margin-top:12px}}
.e-link{{display:flex;align-items:center;gap:10px;padding:12px 14px;border:1px solid var(--line);
  border-radius:var(--r-md);background:var(--card);color:var(--ink);text-decoration:none}}
.e-link:hover{{border-color:var(--brand);transform:translateY(-2px)}}
.e-link .ic{{color:var(--brand);flex:none}}
.e-link b{{display:block;font-size:13.5px}}
.e-link small{{color:var(--muted);font-size:11.5px}}
</style>
</head>
<body>
{topbar(active="", brand_sub="页面不存在")}
<main class="err-wrap">
  <div class="err-code">404</div>
  <h1>页面不存在或已移动</h1>
  <p>地址可能输入有误，或页面已更名。输入关键词全站搜一搜：</p>
  <div class="e-search">
    <input id="q404" type="search" placeholder="如：手球 / 越位 / DOGSO / 第12章…" aria-label="全站搜索">
    <button id="go404">搜索</button>
  </div>
  <p>或从常用入口进入：</p>
  <div class="e-links">{cards}</div>
</main>
<script>
(function(){{
  function go(){{
    var q = document.getElementById("q404").value.trim();
    location.href = q ? "search.html?q=" + encodeURIComponent(q) : "search.html";
  }}
  document.getElementById("go404").onclick = go;
  document.getElementById("q404").addEventListener("keydown", function(e){{
    if (e.key === "Enter") go();
  }});
}})();
</script>
</body>
</html>
"""
    html = inject_theme(html, meta=meta_tags("404.html"))
    (SITE / "404.html").write_text(html, encoding="utf-8")


def main():
    lastmod = latest_data_date()
    build_sitemap(lastmod)
    build_robots()
    build_404()
    print(
        f"发现层构建完成: sitemap.xml（{len(PAGES) - 1} 页）+ robots.txt + 404.html，"
        f"lastmod={lastmod}"
    )


if __name__ == "__main__":
    main()
