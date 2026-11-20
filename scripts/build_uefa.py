# -*- coding: utf-8 -*-
"""生成 site/uefa.html：UEFA Clear Line 官方判例库（中文译制为主 + 英文原文辅助 + 逐例官方视频链接）

数据来自 data/uefa.json（fetch_uefa.py 抓取并提交，CI 无网络依赖照常重建）；
中文译文来自 data/uefa-zh.json（翻译层，与抓取管线解耦——fetch_uefa.py parse 会整体
覆写 uefa.json，译文绝不能写进去）。构建时按来源版本配对组名、导语、准则与判例标题。
原文已变或缺译的部分展示官方英文并标记中文待复核。
页面默认纯中文，页头「英文原文」开关（localStorage cfa.uefa-en）切换显示英文原文。
视频为 Akamai token 门禁 HLS，无法本地化/热链，且官方分享页实测
X-Frame-Options: DENY（2026-10 探测）→ 卡片为纯文字 + 「在 UEFA 官网观看」外链；
EMBED 开关保留（若 UEFA 未来放开嵌入，一行切换为卡片内 iframe）。
"""

import json

from lib.seo import meta_tags
from lib.theme import inject_theme, topbar, icon
from lib.uefa_anchors import (
    LEGACY_GROUPS,
    LEGACY_VIDEOS,
    bookmark_groups,
    group_anchor,
    video_anchor,
)
from lib.uefa_content import apply_zh

from lib.paths import DATA, SITE, UEFA_JSON

ZH_JSON = DATA / "uefa-zh.json"
SOURCE_URL = "https://www.uefa.com/running-competitions/refereeing/clear-line/"
EMBED = False  # UEFA 分享页 X-Frame-Options: DENY（实测），纯链接模式
REVIEW_NOTE = '<p class="translation-status">中文待复核，暂显示官方英文。</p>'

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>欧足联 Clear Line 判例库 · 裁判学习平台</title>
<script>try{if(localStorage.getItem("cfa.uefa-en")==="1")document.documentElement.setAttribute("data-uefa-en","")}catch(e){}</script>
<style>
/* ===== uefa 页专属布局 (tokens/组件来自 data-cfa-theme, 布局骨架同 scale 页) ===== */
.page-head{border-bottom:1px solid var(--line);background:var(--bg2)}
.page-head .wrap{max-width:1180px;margin:0 auto;padding:22px 16px 16px}
.page-head-top{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}
.page-head h1{margin:0 0 4px;font-family:var(--font-display);font-size:23px;letter-spacing:.4px}
.page-head .sub{color:var(--muted);font-size:13px}
.page-head .src{margin-top:8px;font-size:13px}
.page-head .src a{color:var(--brand);font-weight:600;text-decoration:none}
.page-head .src a:hover{text-decoration:underline}
.src-banner{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:12px;
  padding:10px 14px;border:1px solid var(--brand);background:var(--info-bg);
  border-radius:var(--r-md);font-size:13.5px;color:var(--ink2)}
.src-banner .ic{color:var(--brand)}
.en-toggle{display:inline-flex;align-items:center;gap:6px;margin-top:2px;padding:5px 13px;
  border-radius:999px;border:1px solid var(--line);background:var(--card2);color:var(--ink2);
  font-size:12.5px;cursor:pointer;transition:.12s;white-space:nowrap;flex-shrink:0}
.en-toggle:hover{border-color:var(--brand);color:var(--ink)}
.en-toggle[aria-pressed="true"]{border-color:var(--brand);background:var(--info-bg);
  color:var(--brand);font-weight:600}
/* 英文原文辅助层：默认隐藏，页头开关（html[data-uefa-en]）控制显示 */
.en{display:none;font-weight:400;color:var(--muted)}
html[data-uefa-en] small.en{display:inline;font-size:12px}
html[data-uefa-en] p.en,html[data-uefa-en] h4.en{display:block}
html[data-uefa-en] ul.en{display:block}
.gsec h2 small.en{font-size:12px}
.gintro.en{margin:-3px 0 6px;font-size:12.5px;line-height:1.75}
.gcrit ul.en{margin:-2px 0 0;padding-left:18px;font-size:12.5px;line-height:1.7}
.htitle-en{font-size:12.5px;line-height:1.6;margin:-2px 0 0}
.layout{max-width:1180px;margin:0 auto;padding:18px 16px 60px;display:grid;
  grid-template-columns:216px minmax(0,1fr);gap:20px;align-items:start}
.gnavs{position:sticky;top:calc(var(--top-h) + 14px);display:flex;flex-direction:column;gap:4px}
.gnavs .gh{font-size:11px;font-weight:700;color:var(--muted);letter-spacing:2px;margin:2px 4px 6px}
.gnav{display:flex;align-items:center;gap:7px;padding:7px 10px;border-radius:var(--r-sm);
  color:var(--ink2);text-decoration:none;font-size:13.5px;border:1px solid var(--line);transition:.12s}
.gnav b{margin-left:auto;font-size:11px;color:var(--muted);font-weight:600}
.gnav:hover{background:var(--card2);border-color:var(--brand);color:var(--ink)}
.gcontent{min-width:0;scroll-margin-top:calc(var(--top-h) + 8px)}
.gsec{margin-bottom:34px}
.gsec h2{font-family:var(--font-display);font-size:19px;margin:0 0 10px;letter-spacing:.4px}
.gsec h2 small{font-size:13px;color:var(--muted);font-weight:400;margin-left:6px}
.gsec .gintro{font-size:13.5px;color:var(--muted);line-height:1.8;margin:0 0 6px}
.gcrits{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px;margin:10px 0 20px}
.gcrit{background:var(--card2);border:1px solid var(--line);border-radius:var(--r-md);padding:11px 14px}
.gcrit h4{margin:0 0 6px;font-size:13.5px;color:var(--brand);line-height:1.5}
.gcrit ul{margin:0;padding-left:18px;font-size:13px;color:var(--ink2);line-height:1.85}
.gsec ul.gpoints{margin:8px 0 16px;padding-left:20px;color:var(--ink2);font-size:13.5px;line-height:1.9}
.hcard{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:16px 18px;margin-bottom:16px;
  transition:transform var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease)}
.hcard:hover{transform:translateY(-2px);border-color:var(--brand)}
.gsec,.hcard,.legacy-uefa-target{scroll-margin-top:calc(var(--top-h) + 12px)}
.hhead{display:flex;align-items:center;gap:9px;margin-bottom:8px}
.hid{font-family:var(--font-display);font-size:12px;font-weight:700;color:var(--brand);
  border:1px solid var(--line);border-radius:6px;padding:1px 9px;background:var(--card2);white-space:nowrap;text-decoration:none}
.hid:hover{text-decoration:underline}
.hhead h3{margin:0;font-size:16px;font-weight:600;line-height:1.5}
.hnote{font-size:14px;line-height:1.9;margin:8px 0 0}
.translation-status{font-size:12px;color:var(--muted);margin:4px 0}
.hcap{font-size:13.5px;line-height:1.85;margin:8px 0 0;color:var(--ink2)}
.watch{display:inline-flex;align-items:center;gap:7px;margin-top:12px;padding:7px 15px;
  border-radius:999px;border:1px solid var(--brand);background:var(--info-bg);color:var(--brand);
  font-size:13.5px;font-weight:600;text-decoration:none}
.watch:hover{background:var(--brand-strong);border-color:var(--brand-strong);color:var(--on-brand)}
.hdate{font-size:12px;color:var(--faint);margin-left:10px}
.uefa-frame{position:relative;width:100%;max-width:880px;aspect-ratio:16/9;
  background:#000;border-radius:var(--r-md);overflow:hidden;margin-top:12px}
.uefa-frame iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
html[data-lite] .uefa-frame{display:none}
@media (max-width:900px){
  .layout{grid-template-columns:minmax(0,1fr)}
  .gnavs{position:static;flex-direction:row;flex-wrap:wrap}
  .gnavs .gh{flex-basis:100%}
}
</style>
</head>
<body class="page-uefa">
<a class="skip-link" href="#content0">跳到内容</a>
__TOPBAR__
<header class="page-head">
  <div class="wrap">
    <div class="page-head-top">
      <div>
        <h1>欧足联 Clear Line 判例库</h1>
        <div class="sub">UEFA 官方裁判判例宣讲（2026 年 8 月上线）：真实比赛视频场景 + 官方判罚解释 · 中文译制，译文仅供参考、以官方英文原文为准 · 版权归 UEFA 所有</div>
      </div>
      <button id="btnEn" class="en-toggle" type="button" aria-pressed="false">英文原文：关</button>
    </div>
    <div class="src-banner">__I_EXTERNAL__ 视频受 UEFA 版权技术保护（token 门禁），本页提供每例的官方观看链接；__SOURCE_LINK__</div>
  </div>
</header>
<div class="layout">
  <aside class="gnavs" aria-label="场景分组" data-navs>__NAVS__</aside>
  <main class="gcontent" id="content0" tabindex="-1">__SECS__</main>
</div>
<script>
(function(){
  var KEY="cfa.uefa-en";
  var d=document.documentElement,btn=document.getElementById("btnEn");
  function paint(on){
    if(on){d.setAttribute("data-uefa-en","")}else{d.removeAttribute("data-uefa-en")}
    if(btn){btn.setAttribute("aria-pressed",on?"true":"false");
      btn.textContent=on?"英文原文：开":"英文原文：关"}
  }
  var on=false;try{on=localStorage.getItem(KEY)==="1"}catch(e){}
  paint(on);
  if(btn)btn.addEventListener("click",function(){
    on=!d.hasAttribute("data-uefa-en");
    try{localStorage.setItem(KEY,on?"1":"0")}catch(e){}
    paint(on);
  });
})();
</script>
</body>
</html>
"""


def esc(s):
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def load_zh():
    if not ZH_JSON.exists():
        return None
    try:
        return json.loads(ZH_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"⚠ uefa-zh.json 解析失败，按无译文处理: {e}")
        return None


def legacy_target(content, anchor):
    if anchor:
        return f'<div class="legacy-uefa-target" id="{anchor}">{content}</div>'
    return content


def build_page(data):
    groups = data.get("groups", [])
    owners = bookmark_groups(groups)
    navs, secs = "", ""
    for g in groups:
        anchor = group_anchor(g["key"])
        cn_name, en_name = g.get("name_current_cn") or "", g.get("name_en") or ""
        navs += (
            f'<a class="gnav" href="#{anchor}">{esc(cn_name or en_name)}'
            f"<b>{len(g['items'])}</b></a>"
        )
        icn, ien = g.get("intro_cn") or "", g.get("intro") or ""
        if icn:
            intro = f'<p class="gintro">{esc(icn)}</p>'
            if ien:
                intro += f'<p class="gintro en">{esc(ien)}</p>'
        else:
            intro = (
                f'<p class="gintro" lang="en">{esc(ien)}</p>{REVIEW_NOTE}'
                if ien
                else ""
            )
        crit = ""
        if g.get("criteria"):
            ccn = g.get("criteria_cn") or []
            blocks = ""
            for bi, c in enumerate(g["criteria"]):
                z = ccn[bi] if bi < len(ccn) else None
                en_h, en_lis = (
                    esc(c["h"]),
                    "".join(f"<li>{esc(x)}</li>" for x in c["items"]),
                )
                if z:
                    h4 = f'<h4>{esc(z["h"])}</h4><h4 class="en" lang="en">{en_h}</h4>'
                    cn_lis = "".join(f"<li>{esc(x)}</li>" for x in z["items"])
                    ul = f'<ul>{cn_lis}</ul><ul class="en" lang="en">{en_lis}</ul>'
                else:
                    h4 = f'<h4 lang="en">{en_h}</h4>'
                    ul = f'<ul lang="en">{en_lis}</ul>{REVIEW_NOTE}'
                blocks += f'<div class="gcrit">{h4}{ul}</div>'
            crit = f'<div class="gcrits">{blocks}</div>'
        cards = ""
        for i, it in enumerate(g["items"], 1):
            target = video_anchor(it["id"], it["url"])
            card_id, old = "", ""
            if owners.get(target) == g["key"]:
                del owners[target]
                card_id = f' id="{target}"'
                old = LEGACY_VIDEOS.get(target, ("", ""))[1]
            tcn, ten = it.get("title_cn") or "", it.get("title") or ""
            title_en = (
                f'<p class="htitle-en en" lang="en">{esc(ten)}</p>'
                if (tcn and ten)
                else ""
            )
            frame = ""
            if EMBED:
                frame = (
                    f'<div class="uefa-frame"><iframe src="{esc(it["url"])}" loading="lazy" '
                    f'allowfullscreen title="{esc(ten)}"></iframe></div>'
                )
            caption = (
                f'<p class="hcap">{esc(it["caption"])}</p>' if it.get("caption") else ""
            )
            date = (
                f'<span class="hdate">{esc(it.get("date", ""))}</span>'
                if it.get("date")
                else ""
            )
            card = f"""<article class="hcard"{card_id}>
  <div class="hhead"><a class="hid" href="#{target}" aria-label="{esc(tcn or ten)}的永久链接">#{i}</a><h3 lang="{"zh-CN" if tcn else "en"}">{esc(tcn or ten)}</h3></div>
  {title_en}{"" if tcn else REVIEW_NOTE}{frame}{caption}
  <a class="watch" href="{esc(it["url"])}" target="_blank" rel="noopener noreferrer">{icon("play", 13)} 在 UEFA 官网观看 {icon("external", 13)}</a>{date}
</article>"""
            cards += legacy_target(card, old)
        if cn_name:
            en_part = f'<small class="en">{esc(en_name)}</small>' if en_name else ""
            h2 = f"<h2>{esc(cn_name)} {en_part} <b>{len(g['items'])}例</b></h2>"
        else:
            h2 = f'<h2><span lang="en">{esc(en_name)}</span> <b>{len(g["items"])}例</b></h2>{REVIEW_NOTE}'
        secs += legacy_target(
            f'<section class="gsec" id="{anchor}">{h2}{intro}{crit}{cards}</section>',
            LEGACY_GROUPS.get(g["key"]),
        )
    tb = topbar(
        active="uefa.html",
        stats="stats-2026.html",
        brand_sub="UEFA Clear Line",
        seasons=("2024", "2025", "2026"),
        lite_btn=True,
    )
    src_link = f'<a href="{SOURCE_URL}" target="_blank" rel="noopener noreferrer">前往 UEFA Clear Line 官方发布页</a>'
    html = inject_theme(
        HTML.replace("__TOPBAR__", tb)
        .replace("__SOURCE_LINK__", src_link)
        .replace("__I_EXTERNAL__", icon("external", 14))
        .replace("__NAVS__", navs)
        .replace("__SECS__", secs),
        meta=meta_tags("uefa.html"),
    )
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "uefa.html").write_text(html, encoding="utf-8")
    n = sum(len(g["items"]) for g in groups)
    print(f"生成 {SITE / 'uefa.html'}（{len(groups)} 组 / {n} 例，EMBED={EMBED}）")


def main():
    if not UEFA_JSON.exists():
        raise SystemExit(f"缺少 {UEFA_JSON}；请先运行 fetch_uefa.py 抓取")
    data = json.loads(UEFA_JSON.read_text(encoding="utf-8"))
    apply_zh(data, load_zh(), print)
    build_page(data)


if __name__ == "__main__":
    main()
