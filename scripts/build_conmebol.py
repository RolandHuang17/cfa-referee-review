# -*- coding: utf-8 -*-
"""生成 site/conmebol.html：南美足联 CONMEBOL《Situación de Análisis VAR》判例页
（评议级：逐案 比赛信息+情境+分钟+官方视频链接）

数据来自 data/conmebol.json（fetch_conmebol.py 抓取提交）+ data/conmebol-zh.json
（url 键情境译制层）。判例视频托管在 YouTube（官方），本页为纯链接模式
（不内嵌、不本地化）。页头/chips/搜索/年份分组骨架来自 lib/pagelib.py。
"""
from lib.theme import inject_theme, topbar, icon

from lib.pagelib import (SEARCH_CSS, esc, filter_js, group_by_year, head_css,
                         load_json_with_zh, search_blob, searchbar)
from lib.paths import CONMEBOL_JSON, CONMEBOL_ZH_JSON, SITE

SIT_LABEL = {
    "penalty": "点球", "ofr_penalty": "点球（现场回看）", "no_penalty": "非点球",
    "red_card": "红牌", "offside": "越位", "no_goal": "进球无效", "other": "判例",
}
SIT_BADGE = {
    "penalty": "wrong", "ofr_penalty": "wrong", "red_card": "wrong",
    "no_penalty": "correct", "no_goal": "pending", "offside": "info", "other": "info",
}
COMP_CN = {"eliminatorias": "世预赛", "libertadores": "解放者杯",
           "sudamericana": "南美杯", "conmebol-recopa": "优胜者杯"}

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>南美 VAR 判例 · 裁判学习平台</title>
<style>
/* ===== conmebol 页专属布局 (tokens/组件来自 data-cfa-theme；页头/筛选骨架来自 lib/pagelib) ===== */
__HEAD_CSS__
__SEARCH_CSS__
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
.ccard .go{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:999px;
  border:1px solid var(--brand);background:var(--info-bg);color:var(--brand);
  font-size:12px;font-weight:600;text-decoration:none;white-space:nowrap}
.ccard .go:hover{background:var(--brand-strong);color:var(--on-brand)}
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
    __SEARCHBAR__
  </div>
</header>
<div class="wrap" id="content0">
  <div class="chips" data-chips>
    <button class="chip on" data-f="all">全部 <b>__N_ALL__</b></button>
    __COMP_CHIPS__
    __SIT_CHIPS__
  </div>
  __SECTIONS__
  <p class="empty" id="emptyTip">没有匹配的判例——换个关键词或筛选试试。</p>
  <p class="foot">判例内容版权归 CONMEBOL 所有；本页收录结构化元数据与官方链接（来源 conmebol.com，核对日期 __CHECKED__）。情境已中文译制（conmebol-zh 译制层），官方西语原文保留标注，以原文为准。</p>
</div>
<script>
__FILTER_JS__
</script>
</body>
</html>
"""


def build_page(data, zh=None):
    cases = data.get("cases", [])
    zcases = (zh or {}).get("cases", {})
    used = set()
    for c in cases:
        z = zcases.get(c.get("url", ""))
        if z and z.get("situation"):
            c["situacion_zh"] = z["situation"]
            used.add(c.get("url", ""))
    for k in zcases:
        if k not in used:
            print(f"⚠ conmebol-zh cases 键不在 conmebol.json 中（疑似过期）: {k[:80]}")
    comps = sorted({c.get("comp") for c in cases if c.get("comp")})
    sits = sorted({c.get("situacion_norm") for c in cases if c.get("situacion_norm")})
    comp_chips = "".join(
        f'<button class="chip" data-f="{esc(k)}">{esc(COMP_CN.get(k, k))} '
        f'<b>{sum(1 for c in cases if c.get("comp") == k)}</b></button>' for k in comps)
    sit_chips = "".join(
        f'<button class="chip" data-f="{esc(k)}">{esc(SIT_LABEL.get(k, k))} '
        f'<b>{sum(1 for c in cases if c.get("situacion_norm") == k)}</b></button>' for k in sits)
    secs = ""
    for y, ycases in group_by_year(
            cases, date_of=lambda c: (c.get("fecha") or c.get("date") or "")[-4:],
            fallback="其他"):
        rows = ""
        for c in ycases:
            kinds = " ".join(filter(None, [c.get("comp"), c.get("situacion_norm")]))
            norm = c.get("situacion_norm", "other")
            badge = SIT_BADGE.get(norm, "info")
            label = SIT_LABEL.get(norm, "判例")
            meta = "".join(
                f'<span class="chip">{esc(v)}</span>'
                for v in (c.get("fecha", ""), c.get("minuto", "") and c["minuto"] + "′",
                          c.get("ciudad", ""), c.get("estadio", ""),
                          COMP_CN.get(c.get("comp", ""), "")) if v)
            if c.get("situacion_zh"):
                es_sit = f'<span class="chip">情境：{esc(c["situacion_zh"])}</span>'
                if c.get("situacion_es") and c["situacion_es"].lower() != label.lower():
                    es_sit += f'<span class="chip" title="官方西语原文">原文: {esc(c["situacion_es"])}</span>'
            else:
                if c.get("situacion_es"):
                    print(f"⚠ conmebol-zh 缺该案情境译制，回退西语: {c.get('url', '')[:70]}")
                es_sit = f'<span class="chip" title="官方原文">Situación: {esc(c["situacion_es"])}</span>' \
                    if c.get("situacion_es") and c["situacion_es"].lower() != label.lower() else ""
            links = (f'<a class="go" href="{esc(c["url"])}" target="_blank" rel="noopener noreferrer">'
                     f'{icon("note", 11)} 官方分析</a>')
            if c.get("youtube"):
                links += (f'<a class="go" href="{esc(c["youtube"])}" target="_blank" '
                          f'rel="noopener noreferrer">{icon("play", 11)} 判例视频</a>')
            blob = search_blob(c.get("match") or c.get("title"), c.get("fecha"),
                               c.get("ciudad"), c.get("estadio"), COMP_CN.get(c.get("comp", ""), ""),
                               c.get("situacion_zh"), c.get("situacion_es"), label)
            rows += f"""<div class="ccard" data-kinds="{esc(kinds)}" data-search="{blob}">
  <div class="chead"><span class="cmatch">{esc(c.get("match") or c["title"])}</span>
    <span class="badge {badge}">{esc(label)}</span></div>
  <div class="cinfo">{meta}{es_sit}</div>
  <div class="clinks">{links}</div>
</div>"""
        secs += (f'<h3 class="year-h" data-year="{esc(y)}">{esc(y)} <small>'
                 f'{len(ycases)} 案</small></h3><div id="ybody-{esc(y)}">{rows}</div>')
    tb = topbar(active="conmebol.html", stats="stats-2026.html", brand_sub="南美 VAR 判例",
                seasons=("2026", "2025", "2024"))
    src_link = (f'<a href="{esc(data.get("source", ""))}" target="_blank" '
                f'rel="noopener noreferrer">conmebol.com VAR 分析专栏</a>')
    html = inject_theme(HTML
                        .replace("__TOPBAR__", tb)
                        .replace("__SOURCE_LINK__", src_link)
                        .replace("__I_EXTERNAL__", icon("external", 14))
                        .replace("__SEARCHBAR__", searchbar("搜索判例：对阵 / 球场 / 情境…"))
                        .replace("__HEAD_CSS__", head_css(max_width=1000))
                        .replace("__SEARCH_CSS__", SEARCH_CSS)
                        .replace("__FILTER_JS__", filter_js(".ccard", filter_attr="data-kinds",
                                                            match="substr", search=True, group="ybody"))
                        .replace("__N_ALL__", str(len(cases)))
                        .replace("__COMP_CHIPS__", comp_chips)
                        .replace("__SIT_CHIPS__", sit_chips)
                        .replace("__CHECKED__", esc(data.get("fetched", "")))
                        .replace("__SECTIONS__", secs))
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "conmebol.html").write_text(html, encoding="utf-8")
    print(f"生成 {SITE / 'conmebol.html'}（{len(cases)} 案 / "
          f"{len({y for y, _ in group_by_year(cases, date_of=lambda c: (c.get('fecha') or c.get('date') or '')[-4:], fallback='其他')})} 个年份）")


def main():
    if not CONMEBOL_JSON.exists():
        raise SystemExit(f"缺少 {CONMEBOL_JSON}；请先运行 fetch_conmebol.py")
    data, zh = load_json_with_zh(CONMEBOL_JSON, CONMEBOL_ZH_JSON)
    build_page(data, zh)


if __name__ == "__main__":
    main()
