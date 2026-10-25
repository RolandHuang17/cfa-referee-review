# -*- coding: utf-8 -*-
"""生成 site/pro.html：美国 PRO 裁判评议索引 + USSF 指南区

PRO（proreferees.com）周更 VAR 评析：Inside Video Review（英）、VAR a Fondo（西）、
The Definitive Angle（文字判例）。数据来自 data/pro.json（fetch_pro.py 抓取并提交）；
文章内嵌视频受官方播放器约束，v1 为纯链接索引模式（每篇跳官方页）。
USSF（ussoccer.com）视频页为 JS 渲染且新内容在 Learning Center（免费注册）登录墙内，
无公开抓取形态 → 本页仅作导航指南（视频页/Learning Center/裁判项目入口）。
页头/chips/搜索/年份分组骨架来自 lib/pagelib.py。
"""

from lib.seo import meta_tags
from lib.theme import inject_theme, topbar, icon

from lib.pagelib import (
    SEARCH_CSS,
    esc,
    filter_js,
    group_by_year,
    head_css,
    load_json_with_zh,
    search_blob,
    searchbar,
)
from lib.paths import PRO_JSON, SITE

SERIES_LABEL = {
    "ivr": ("IVR · VAR 评析（英）", "info"),
    "vaf": ("VAR a Fondo（西）", "pending"),
    "angle": ("The Definitive Angle（文字判例）", "correct"),
    "other": ("PRO 文章", "info"),
}

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>美国 PRO 评议 & USSF · 裁判学习平台</title>
<style>
/* ===== pro 页专属布局 (tokens/组件来自 data-cfa-theme；页头/筛选骨架来自 lib/pagelib) ===== */
__HEAD_CSS__
__SEARCH_CSS__
.acard{background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);
  padding:12px 16px;margin-bottom:10px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;
  transition:border-color var(--t-fast) var(--ease)}
.acard:hover{border-color:var(--brand)}
.acard .t{flex:1;min-width:260px}
.acard .t b{display:block;font-size:14px;line-height:1.55}
.acard .t small{color:var(--muted);font-size:12px}
.acard .badge{white-space:nowrap}
.acard .go{display:inline-flex;align-items:center;gap:6px;padding:6px 13px;border-radius:999px;
  border:1px solid var(--brand);background:var(--info-bg);color:var(--brand);
  font-size:12.5px;font-weight:600;text-decoration:none;white-space:nowrap}
.acard .go:hover{background:var(--brand-strong);color:var(--on-brand)}
.ussf{margin-top:36px;border-top:1px dashed var(--line);padding-top:22px}
.ussf h2{font-family:var(--font-display);font-size:19px;margin:0 0 8px}
.ussf .desc{font-size:13.5px;color:var(--muted);line-height:1.85;margin:0 0 14px}
.tools{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px}
.tool{background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);padding:12px 15px;
  text-decoration:none;color:var(--ink2);transition:.12s}
.tool:hover{border-color:var(--brand);color:var(--ink)}
.tool b{display:block;font-size:13.5px;color:var(--ink);margin-bottom:4px}
.tool span{font-size:12.5px;color:var(--muted);line-height:1.7}
@media (max-width:760px){.acard .go{margin-left:auto}}
</style>
</head>
<body class="page-pro">
<a class="skip-link" href="#content0">跳到内容</a>
__TOPBAR__
<header class="page-head">
  <div class="wrap">
    <h1>美国 PRO 裁判评议</h1>
    <div class="sub">Professional Referee Organization（MLS/NWSL 职业裁判机构）周更 VAR 评析：Inside Video Review（英）· VAR a Fondo（西）· The Definitive Angle（文字判例）· 本页为全量索引，逐篇跳转官方页 · 版权归 PRO 所有</div>
    <div class="src-banner">__I_EXTERNAL__ 每周五发布上一轮评析（Grég Barkey / VAR 评议组）；__SOURCE_LINK__</div>
    __SEARCHBAR__
  </div>
</header>
<div class="wrap" id="content0">
  <div class="chips" data-chips>
    <button class="chip on" data-f="all">全部 <b>__N_ALL__</b></button>
    <button class="chip" data-f="ivr">IVR 评析（英） <b>__N_IVR__</b></button>
    <button class="chip" data-f="vaf">VAR a Fondo（西） <b>__N_VAF__</b></button>
    <button class="chip" data-f="angle">文字判例 <b>__N_ANGLE__</b></button>
    <button class="chip" data-f="MLS">MLS <b>__N_MLS__</b></button>
    <button class="chip" data-f="NWSL">NWSL <b>__N_NWSL__</b></button>
  </div>
  __SECTIONS__
  <p class="empty" id="emptyTip">没有匹配的文章——换个关键词或筛选试试。</p>
  <section class="ussf" id="ussf">
    <h2>__I_SHIELD__ 美国足协（USSF）裁判视频</h2>
    <p class="desc">美国足协的裁判判例内容（Week in Review 系列等）公开形态有限：官网视频页为脚本渲染、完整新集在 Learning Center（免费注册）登录墙内，且无公开的官方 YouTube 播放列表——故本站仅作入口导航，不抓取条目。PRO 的周报（上方索引）是北美最稳定的公开「评议」形态。</p>
    <div class="tools">
      <a class="tool" href="__U_VIDEOS__" target="_blank" rel="noopener noreferrer"><b>Refereeing Videos 官方页</b><span>ussoccer.com/refereeing/videos：栏目入口（部分内容需 JS 渲染/注册）</span></a>
      <a class="tool" href="__U_LEARNING__" target="_blank" rel="noopener noreferrer"><b>U.S. Soccer Learning Center</b><span>learning.ussoccer.com/referee：完整判例课程与 Webinar（免费注册后观看）</span></a>
      <a class="tool" href="__U_REFEREEING__" target="_blank" rel="noopener noreferrer"><b>Referee Program 首页</b><span>裁判项目总入口：规则、指派、教育资料</span></a>
    </div>
  </section>
  <p class="foot">PRO 文章与视频版权归 Professional Referee Organization 所有；本页仅收录标题/日期/系列等元数据与官方链接（来源 proreferees.com，核对日期 __CHECKED__）。USSF 内容归 U.S. Soccer 所有。</p>
</div>
<script>
__FILTER_JS__
</script>
</body>
</html>
"""


def build_page(data):
    arts = data.get("articles", [])
    n = {
        k: sum(1 for a in arts if a.get("kind") == k or a.get("league") == k)
        for k in ("ivr", "vaf", "angle", "MLS", "NWSL")
    }
    secs = ""
    for y, yarts in group_by_year(arts, fallback="其他"):
        rows = ""
        for a in yarts:
            label, badge = SERIES_LABEL.get(
                a.get("kind", "other"), SERIES_LABEL["other"]
            )
            kinds = " ".join(filter(None, [a.get("kind"), a.get("league")]))
            tags = f'<span class="badge {badge}">{esc(label)}</span>'
            if a.get("league"):
                tags += f'<span class="badge info">{esc(a["league"])}{(" #" + a["round"]) if a.get("round") else ""}</span>'
            vids = "".join(
                f'<a class="go" href="{esc(v)}" target="_blank" rel="noopener noreferrer">{icon("play", 11)} 官方视频</a>'
                for v in (a.get("videos") or [])[:1]
            )
            blob = search_blob(
                a["title"],
                a.get("date"),
                label,
                a.get("league"),
                f"#{a['round']}" if a.get("round") else "",
            )
            rows += f"""<div class="acard" data-kinds="{esc(kinds)}" data-search="{blob}">
  <div class="t"><b>{esc(a["title"])}</b><small>{esc(a.get("date", ""))}</small></div>
  {tags}
  {vids}
  <a class="go" href="{esc(a["url"])}" target="_blank" rel="noopener noreferrer">{icon("external", 11)} 官方页</a>
</div>"""
        secs += (
            f'<h3 class="year-h" data-year="{esc(y)}">{esc(y)} <small>{len(yarts)} 篇</small></h3>'
            f'<div id="ybody-{esc(y)}">{rows}</div>'
        )
    tb = topbar(
        active="pro.html",
        stats="stats-2026.html",
        brand_sub="美国 PRO & USSF",
        seasons=("2026", "2025", "2024"),
    )
    src_link = (
        f'<a href="{esc(data.get("source", ""))}" target="_blank" '
        f'rel="noopener noreferrer">proreferees.com 官方分类页</a>'
    )
    u = data.get("ussf", {})
    html = inject_theme(
        HTML.replace("__TOPBAR__", tb)
        .replace("__SOURCE_LINK__", src_link)
        .replace("__I_EXTERNAL__", icon("external", 14))
        .replace("__I_SHIELD__", icon("shield", 17))
        .replace("__SEARCHBAR__", searchbar("搜索文章：标题 / 系列 / 联赛…"))
        .replace("__HEAD_CSS__", head_css(max_width=1000))
        .replace("__SEARCH_CSS__", SEARCH_CSS)
        .replace(
            "__FILTER_JS__",
            filter_js(
                ".acard",
                filter_attr="data-kinds",
                match="substr",
                 search=True,
                 group="ybody",
             ),
        )
        .replace("__N_ALL__", str(len(arts)))
        .replace("__N_IVR__", str(n["ivr"]))
        .replace("__N_VAF__", str(n["vaf"]))
        .replace("__N_ANGLE__", str(n["angle"]))
        .replace("__N_MLS__", str(n["MLS"]))
        .replace("__N_NWSL__", str(n["NWSL"]))
        .replace("__U_VIDEOS__", esc(u.get("videos", "")))
        .replace("__U_LEARNING__", esc(u.get("learning", "")))
        .replace("__U_REFEREEING__", esc(u.get("refereeing", "")))
        .replace("__CHECKED__", esc(data.get("fetched", "")))
        .replace("__SECTIONS__", secs),
        meta=meta_tags("pro.html"),
    )
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "pro.html").write_text(html, encoding="utf-8")
    print(f"生成 {SITE / 'pro.html'}（{len(arts)} 篇索引）")


def main():
    if not PRO_JSON.exists():
        raise SystemExit(f"缺少 {PRO_JSON}；请先运行 fetch_pro.py")
    data, _ = load_json_with_zh(PRO_JSON)
    build_page(data)


if __name__ == "__main__":
    main()
