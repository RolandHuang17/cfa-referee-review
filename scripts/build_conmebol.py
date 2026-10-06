# -*- coding: utf-8 -*-
"""生成 site/conmebol.html：南美足联 CONMEBOL《Situación de Análisis VAR》判例页
（评议级：逐案 比赛信息+情境+分钟+官方视频链接）

数据来自 data/conmebol.json（fetch_conmebol.py 抓取并提交）。判例视频托管在
YouTube（官方），本页为纯链接模式（不内嵌、不本地化）。
"""
import json

from lib.theme import inject_theme, topbar, icon

from lib.paths import CONMEBOL_JSON, SITE

SIT_LABEL = {
    "penalty": "点球", "ofr_penalty": "点球（现场回看）", "no_penalty": "非点球",
    "red_card": "红牌", "offside": "越位", "no_goal": "进球无效", "other": "判例",
}
SIT_BADGE = {
    "penalty": "wrong", "ofr_penalty": "wrong", "red_card": "wrong",
    "no_penalty": "correct", "no_goal": "pending", "offside": "info", "other": "info",
}

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>南美 VAR 判例 · 裁判学习平台</title>
<style>
/* ===== conmebol 页专属布局 (tokens/组件来自 data-cfa-theme, 骨架同 pro 页) ===== */
.page-head{border-bottom:1px solid var(--line);background:var(--bg2)}
.page-head .wrap{max-width:1000px;margin:0 auto;padding:22px 16px 18px}
.page-head h1{margin:0 0 5px;font-family:var(--font-display);font-size:23px;letter-spacing:.4px}
.page-head .sub{color:var(--muted);font-size:13px;line-height:1.7}
.src-banner{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:12px;
  padding:10px 14px;border:1px solid var(--brand);background:var(--info-bg);
  border-radius:var(--r-md);font-size:13.5px;color:var(--ink2)}
.src-banner .ic{color:var(--brand)}
.src-banner a{color:var(--brand);font-weight:600;text-decoration:none}
.src-banner a:hover{text-decoration:underline}
.wrap{max-width:1000px;margin:0 auto;padding:18px 16px 60px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 18px}
.year-h{font-family:var(--font-display);font-size:18px;margin:26px 0 12px}
.year-h small{font-size:12px;color:var(--muted);font-weight:400;margin-left:8px}
.ccard{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:14px 18px;margin-bottom:12px;
  transition:transform var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease)}
.ccard:hover{transform:translateY(-2px);border-color:var(--brand)}
.chead{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.chead .badge{margin-left:auto}
.cmatch{font-family:var(--font-display);font-size:16.5px}
.cinfo{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.cinfo .chip{cursor:default;padding:3px 10px;font-size:11.5px}
.clinks{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.foot{margin-top:28px;font-size:12px;color:var(--faint);line-height:1.8}
@media (max-width:760px){.chead .badge{margin-left:0}}
</style>
</head>
<body class="page-conmebol">
<a class="skip-link" href="#content0">跳到内容</a>
__TOPBAR__
<header class="page-head">
  <div class="wrap">
    <h1>南美足联 VAR 判例</h1>
    <div class="sub">CONMEBOL《Situación de Análisis VAR》：世预赛（南美区）/ 解放者杯 / 南美杯 / 优胜者杯逐案 VAR 判例分析（比赛 · 情境 · 分钟）· 官方视频为 YouTube 链接 · 版权归 CONMEBOL 所有</div>
    <div class="src-banner">__I_EXTERNAL__ 每案附官方分析文章与判例视频链接；__SOURCE_LINK__</div>
  </div>
</header>
<div class="wrap" id="content0">
  <div class="chips" data-chips>
    <button class="chip on" data-f="all">全部 <b>__N_ALL__</b></button>
    __COMP_CHIPS__
    __SIT_CHIPS__
  </div>
  __SECTIONS__
  <p class="foot">判例内容版权归 CONMEBOL 所有；本页收录结构化元数据与官方链接（来源 conmebol.com，核对日期 __CHECKED__）。情境类型以官方西语原文为准，中文标签仅供检索。</p>
</div>
<script>
(function(){
  var chips = document.querySelectorAll("[data-chips] .chip");
  var cards = document.querySelectorAll(".ccard[data-kinds]");
  var years = document.querySelectorAll(".year-h[data-year]");
  chips.forEach(function(c){
    c.addEventListener("click", function(){
      chips.forEach(function(x){ x.classList.remove("on"); });
      c.classList.add("on");
      var f = c.getAttribute("data-f");
      cards.forEach(function(a){
        var hit = f === "all" || (a.getAttribute("data-kinds") || "").indexOf(f) >= 0;
        a.style.display = hit ? "" : "none";
      });
      years.forEach(function(y){
        var grp = document.getElementById("ybody-" + y.getAttribute("data-year"));
        var any = grp ? grp.querySelectorAll('.ccard:not([style*="none"])').length > 0 : false;
        if (grp) grp.style.display = any ? "" : "none";
        y.style.display = any ? "" : "none";
      });
    });
  });
})();
</script>
</body>
</html>
"""


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") \
        .replace('"', "&quot;").replace("'", "&#39;")


def build_page(data):
    cases = data.get("cases", [])
    for c in cases:
        y = (c.get("fecha") or c.get("date") or "0000")[-4:]
        if y.isdigit():
            c["year"] = y
        else:
            c["year"] = "其他"
    years = sorted({c["year"] for c in cases}, reverse=True)
    comps = sorted({c.get("comp") for c in cases if c.get("comp")})
    sits = sorted({c.get("situacion_norm") for c in cases if c.get("situacion_norm")})
    comp_cn = {"eliminatorias": "世预赛", "libertadores": "解放者杯",
               "sudamericana": "南美杯", "conmebol-recopa": "优胜者杯"}
    comp_chips = "".join(
        f'<button class="chip" data-f="{esc(k)}">{esc(comp_cn.get(k, k))} '
        f'<b>{sum(1 for c in cases if c.get("comp") == k)}</b></button>' for k in comps)
    sit_chips = "".join(
        f'<button class="chip" data-f="{esc(k)}">{esc(SIT_LABEL.get(k, k))} '
        f'<b>{sum(1 for c in cases if c.get("situacion_norm") == k)}</b></button>' for k in sits)
    secs = ""
    for y in years:
        rows = ""
        for c in (x for x in cases if x["year"] == y):
            kinds = " ".join(filter(None, [c.get("comp"), c.get("situacion_norm")]))
            badge = SIT_BADGE.get(c.get("situacion_norm", "other"), "info")
            label = SIT_LABEL.get(c.get("situacion_norm", "other"), "判例")
            meta = "".join(
                f'<span class="chip">{esc(v)}</span>'
                for v in (c.get("fecha", ""), c.get("minuto", "") and c["minuto"] + "′",
                          c.get("ciudad", ""), c.get("estadio", ""),
                          comp_cn.get(c.get("comp", ""), "")) if v)
            es_sit = f'<span class="chip" title="官方原文">Situación: {esc(c["situacion_es"])}</span>' \
                if c.get("situacion_es") and c["situacion_es"].lower() != label.lower() else ""
            links = (f'<a class="go" href="{esc(c["url"])}" target="_blank" rel="noopener noreferrer">'
                     f'{icon("note", 11)} 官方分析</a>')
            if c.get("youtube"):
                links += (f'<a class="go" href="{esc(c["youtube"])}" target="_blank" '
                          f'rel="noopener noreferrer">{icon("play", 11)} 判例视频</a>')
            rows += f"""<div class="ccard" data-kinds="{esc(kinds)}">
  <div class="chead"><span class="cmatch">{esc(c.get("match") or c["title"])}</span>
    <span class="badge {badge}">{esc(label)}</span></div>
  <div class="cinfo">{meta}{es_sit}</div>
  <div class="clinks">{links}</div>
</div>"""
        secs += (f'<h3 class="year-h" data-year="{esc(y)}">{esc(y)} <small>'
                 f'{sum(1 for x in cases if x["year"] == y)} 案</small></h3>'
                 f'<div id="ybody-{esc(y)}">{rows}</div>')
    tb = topbar(active="conmebol.html", stats="stats-2026.html", brand_sub="南美 VAR 判例",
                seasons=("2026", "2025", "2024"))
    src_link = (f'<a href="{esc(data.get("source", ""))}" target="_blank" '
                f'rel="noopener noreferrer">conmebol.com VAR 分析专栏</a>')
    html = inject_theme(HTML
                        .replace("__TOPBAR__", tb)
                        .replace("__SOURCE_LINK__", src_link)
                        .replace("__I_EXTERNAL__", icon("external", 14))
                        .replace("__N_ALL__", str(len(cases)))
                        .replace("__COMP_CHIPS__", comp_chips)
                        .replace("__SIT_CHIPS__", sit_chips)
                        .replace("__CHECKED__", esc(data.get("fetched", "")))
                        .replace("__SECTIONS__", secs))
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "conmebol.html").write_text(html, encoding="utf-8")
    print(f"生成 {SITE / 'conmebol.html'}（{len(cases)} 案 / {len(years)} 个年份）")


def main():
    if not CONMEBOL_JSON.exists():
        raise SystemExit(f"缺少 {CONMEBOL_JSON}；请先运行 fetch_conmebol.py")
    data = json.loads(CONMEBOL_JSON.read_text(encoding="utf-8"))
    build_page(data)


if __name__ == "__main__":
    main()
