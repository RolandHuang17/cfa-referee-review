# -*- coding: utf-8 -*-
"""生成 site/ifab.html：IFAB《Laws of the Game》VAR 协议与 FAQ 中文全文译制页

数据来自 data/ifab.json（fetch_ifab.py 抓取提交）+ data/ifab-zh.json（全文译制层）。
结构对齐 uefa.html：中文为主、英文原文开关（html[data-ifab-en] + localStorage
cfa.ifab-en）；译文按 section id / block 英文标题 / FAQ id 平铺匹配（rfef-zh 同构），
未命中回退英文并打 ⚠。纯文本官方材料 + 官方外链，无内嵌第三方资源。
"""

import json
from html import escape

from lib.ifab_content import documents

from lib.seo import meta_tags
from lib.theme import inject_theme, topbar, icon

from lib.paths import IFAB_JSON, IFAB_ZH_JSON, SITE

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IFAB · VAR 协议与统一尺度 · 裁判学习平台</title>
<script>try{if(localStorage.getItem('cfa.ifab-en')==='1')document.documentElement.setAttribute('data-ifab-en','')}catch(e){}</script>
<style>
/* ===== ifab 页专属布局 (tokens/组件来自 data-cfa-theme; 中英开关同 uefa 页机制) ===== */
.page-head{border-bottom:1px solid var(--line);background:var(--bg2)}
.page-head .wrap{max-width:1180px;margin:0 auto;padding:22px 16px 18px}
.page-head h1{margin:0 0 5px;font-family:var(--font-display);font-size:23px;letter-spacing:.4px}
.page-head .sub{color:var(--muted);font-size:13px;line-height:1.7}
.page-head .toprow{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap}
.src-banner{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:12px;
  padding:10px 14px;border:1px solid var(--brand);background:var(--info-bg);
  border-radius:var(--r-md);font-size:13.5px;color:var(--ink2)}
.src-banner .ic{color:var(--brand)}
.src-banner a{color:var(--brand);font-weight:600;text-decoration:none}
.src-banner a:hover{text-decoration:underline}
.en-toggle{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:999px;
  border:1px solid var(--brand);background:var(--card);color:var(--brand);
  font-size:12.5px;font-weight:600;cursor:pointer;white-space:nowrap}
.en-toggle:hover{background:var(--info-bg)}
.en-toggle[aria-pressed="true"]{background:var(--brand-strong);color:var(--on-brand)}
.layout{max-width:1180px;margin:0 auto;padding:18px 16px 60px;display:grid;
  grid-template-columns:248px minmax(0,1fr);gap:26px}
.toc{position:sticky;top:76px;align-self:start;max-height:calc(100vh - 96px);overflow:auto;
  border:1px solid var(--line);border-radius:var(--r-md);background:var(--card);padding:12px}
.toc b{display:block;font-size:12px;color:var(--muted);letter-spacing:.8px;margin:2px 0 8px}
.toc a{display:block;padding:6px 9px;border-radius:var(--r-sm);color:var(--ink2);
  font-size:13px;text-decoration:none;line-height:1.5}
.toc a:hover{background:var(--info-bg);color:var(--ink)}
.toc a.cur{background:var(--info-bg);color:var(--brand);font-weight:600}
.toc .toc-g{display:block;margin:10px 0 4px;font-size:11px;color:var(--faint);letter-spacing:1.5px}
.xfaq{margin-top:10px;background:var(--bg2);border-radius:var(--r-sm);padding:8px 12px}
.toc .sub{padding-left:16px;font-size:12.5px}
.doc .sec{margin-bottom:34px}
.doc [id]{scroll-margin-top:calc(var(--top-h,56px) + 16px)}
.doc :is(p,li,summary):target{outline:2px solid var(--brand);outline-offset:3px}
.previous{margin:8px 0;padding:8px 12px;border-left:2px solid var(--line)}
@media print{.page-ifab .toc,.page-ifab .en-toggle{display:none}.page-ifab .panel{break-inside:auto}}
.doc h2{font-family:var(--font-display);font-size:20px;margin:0 0 12px;padding-bottom:8px;
  border-bottom:1px solid var(--line);letter-spacing:.4px}
.doc h3{font-family:var(--font-display);font-size:16px;margin:20px 0 8px;color:var(--brand)}
.doc p,.doc li{font-size:14px;line-height:1.9;color:var(--ink)}
.doc ul{margin:6px 0 12px;padding-left:22px}
.doc li{margin:4px 0}
.doc .panel{background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);
  padding:16px 20px;margin-bottom:14px}
.en{display:none}
html[data-ifab-en] .en{display:revert}
html[data-ifab-en] .zhv{display:none}
html[data-ifab-en] li.zhv{display:none}
html[data-ifab-en] p.zhv,html[data-ifab-en] span.zhv,html[data-ifab-en] div.zhv{display:none}
.faq details{background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);
  padding:12px 16px;margin-bottom:10px}
.faq summary{cursor:pointer;font-size:14px;line-height:1.75;font-weight:600;color:var(--ink)}
.faq .a{margin-top:9px;padding-top:9px;border-top:1px dashed var(--line);
  font-size:13.5px;line-height:1.85;color:var(--ink2)}
.links{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px;margin-top:8px}
.links a{background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);padding:12px 15px;
  text-decoration:none;color:var(--ink2);transition:.12s;font-size:12.5px;line-height:1.7}
.links a:hover{border-color:var(--brand);color:var(--ink)}
.links a b{display:block;font-size:13.5px;color:var(--ink);margin-bottom:4px}
.foot{margin-top:28px;font-size:12px;color:var(--faint);line-height:1.8}
@media (max-width:900px){.layout{grid-template-columns:1fr}.toc{position:static;max-height:none}}
</style>
</head>
<body class="page-ifab">
<a class="skip-link" href="#content0">跳到内容</a>
__TOPBAR__
<header class="page-head">
  <div class="wrap">
    <div class="toprow">
      <div>
        <h1>IFAB · VAR 协议与统一尺度</h1>
        <div class="sub">主协议 __SECS_N__ 节、官方 FAQ __FAQ_N__ 则、配套指南 __EXTRAS_N__ 篇。可按段查阅中文译文或切换 IFAB 英文原文。</div>
      </div>
      <button id="btnEn" class="en-toggle" aria-pressed="false">__I_LANG__ 英文原文：关</button>
    </div>
    <div class="src-banner">__I_EXTERNAL__ 译文供学习参考，以 IFAB 官方原文为准；__SOURCE_LINK__ · 核对日期 __CHECKED__</div>
  </div>
</header>
<div class="layout" id="content0">
  <nav class="toc" aria-label="章节导航">
    <b>章节导航</b>
    __TOC__
  </nav>
  <div class="doc">
    __SECTIONS__
    <section class="sec" id="faq">
      <h2><span class="zhv">官方 FAQ 判例</span><span class="en">Official FAQs</span></h2>
      <div class="faq">__FAQ__</div>
    </section>
    <section class="sec" id="links">
      <h2><span class="zhv">配套材料与站内关联</span><span class="en">Related resources</span></h2>
      <div class="links">__LINKS__</div>
    </section>
    <p class="foot">原文版权归 IFAB（The International Football Association Board）所有；本页为独立学习用途的中文译制（译文 __TRANSLATED__ 校对），仅收录文本与官方链接，不复制任何官方图片/字体/脚本。术语对照见页首说明：VAR=视频助理裁判、OFR=场上回看、DOGSO=破坏明显进球得分机会。</p>
  </div>
</div>
<script>
(function(){
  var b=document.getElementById("btnEn");
  if(!b)return;
  function paint(){
    var on=document.documentElement.hasAttribute("data-ifab-en");
    b.setAttribute("aria-pressed",on?"true":"false");
    b.textContent="英文原文："+(on?"开":"关");
  }
  b.addEventListener("click",function(){
    var on=document.documentElement.hasAttribute("data-ifab-en");
    if(on)document.documentElement.removeAttribute("data-ifab-en");
    else document.documentElement.setAttribute("data-ifab-en","");
    try{localStorage.setItem("cfa.ifab-en",on?"0":"1")}catch(_){ }
    paint();
  });
  paint();
  function revealFaq(){
    var target=document.getElementById(location.hash.slice(1));
    var details=target && target.closest("details");
    if(details){details.open=true;target.scrollIntoView();}
  }
  revealFaq();
  window.addEventListener("hashchange",revealFaq);
  var printClosed=null;
  window.addEventListener("beforeprint",function(){
    if(printClosed!==null)return;
    printClosed=Array.from(document.querySelectorAll(".faq > details:not([open]), details.xfaq:not([open])"));
    printClosed.forEach(function(d){d.open=true;});
  });
  window.addEventListener("afterprint",function(){
    if(printClosed!==null)printClosed.forEach(function(d){d.open=false;});
    printClosed=null;
  });
})();
</script>
</body>
</html>
"""


def esc(text):
    return escape(text or "", quote=True)


def pair(zh, en, tag="span"):
    """有译文时切换语言；单语的原文在两种模式下都可读。"""
    if zh and en:
        return f'<{tag} class="zhv">{esc(zh)}</{tag}><{tag} class="en" lang="en">{esc(en)}</{tag}>'
    lang = ' lang="en"' if en else ""
    return f"<{tag}{lang}>{esc(en or zh)}</{tag}>"


def previous_translation(lines):
    paragraphs = "".join(f"<p>{esc(line)}</p>" for line in lines if line)
    if not paragraphs:
        return ""
    return f'<details class="previous"><summary>旧版译文（待核对）</summary>{paragraphs}</details>'


def render_doc_body(blocks):
    parts = []
    for block in blocks:
        if block["h"]:
            parts.append(f"<h3>{pair(block['zh'], block['h'])}</h3>")
        in_list = False
        for item in block["items"]:
            listed = item["k"] == "li"
            if in_list != listed:
                parts.append("<ul>" if listed else "</ul>")
                in_list = listed
            tag = "li" if listed else "p"
            parts.append(
                f'<{tag} id="{esc(item["id"])}">{pair(item["zh"], item["en"])}</{tag}>'
            )
        if in_list:
            parts.append("</ul>")
        parts.append(previous_translation(block["previous"]))
    return "".join(parts)


def render_faq(q):
    alias = f' id="{esc(q["old_id"])}"' if q["old_id"] else ' class="xfaq"'
    return (
        f'<details{alias}><summary id="{esc(q["id"])}">{pair(q["zq"], q["q"])}</summary>'
        f'<div class="a">{pair(q["za"], q["a"], "div")}</div>'
        + previous_translation(q["previous"])
        + "</details>"
    )


def build_page(data, zh):
    links = data.get("links", [])
    docs = documents(data, zh or {}, lambda msg: print("⚠ " + msg))
    toc, secs, faq_html = "", "", ""
    extras_started = False
    for doc in docs:
        if doc["group"] == "faq":
            faq_html = "".join(
                render_faq(q) for q in doc["faq"]
            ) + previous_translation(doc["previous"])
            continue
        if doc["group"] == "extras" and not extras_started:
            toc += '<span class="toc-g">配套协议与指南</span>'
            extras_started = True
        heading = doc["zh"] or doc["h"]
        toc += f'<a href="#{esc(doc["id"])}">{esc(heading)}</a>'
        title = pair(doc["zh"], doc["h"])
        if doc["num"]:
            title = esc(str(doc["num"])) + ". " + title
        body = (
            previous_translation(doc["previous"])
            + render_doc_body(doc["blocks"])
            + "".join(render_faq(q) for q in doc["faq"])
        )
        source = (
            (
                f'<p><a href="{esc(doc["url"])}" target="_blank" rel="noopener noreferrer">'
                f"IFAB 官方原文 · {esc(heading)}</a></p>"
            )
            if doc["url"]
            else ""
        )
        secs += f'<section class="sec" id="{esc(doc["id"])}"><h2>{title}</h2>{source}<div class="panel">{body}</div></section>'
    toc += '<a href="#faq">官方 FAQ 判例</a><a href="#links">配套材料与站内关联</a>'

    links_html = ""
    for link in links:
        if link.get("internal"):
            links_html += (
                f'<a href="{esc(link["url"])}"><b>{icon("book", 13)} {esc(link["label"])}</b>'
                f"站内页面</a>"
            )
        else:
            links_html += (
                f'<a href="{esc(link["url"])}" target="_blank" rel="noopener noreferrer">'
                f"<b>{icon('external', 13)} {esc(link['label'])}</b>theifab.com 官方页</a>"
            )

    html = inject_theme(
        HTML.replace(
            "__TOPBAR__",
            topbar(
                active="ifab.html", stats="stats-2026.html", brand_sub="IFAB 统一尺度"
            ),
        )
        .replace("__I_EXTERNAL__", icon("external", 14))
        .replace("__I_LANG__", icon("globe", 14))
        .replace(
            "__SOURCE_LINK__",
            f'<a href="{esc(data.get("source", ""))}" target="_blank" '
            f'rel="noopener noreferrer">theifab.com 官方协议页</a>',
        )
        .replace("__TOC__", toc)
        .replace("__SECTIONS__", secs)
        .replace("__FAQ__", faq_html)
        .replace("__SECS_N__", str(len(data.get("sections", []))))
        .replace("__FAQ_N__", str(len(data.get("faq", []))))
        .replace("__EXTRAS_N__", str(len(data.get("extras", []))))
        .replace("__LINKS__", links_html)
        .replace("__CHECKED__", esc(data.get("fetched", "")))
        .replace("__TRANSLATED__", esc((zh or {}).get("translated", ""))),
        meta=meta_tags("ifab.html"),
    )
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "ifab.html").write_text(html, encoding="utf-8")
    print(
        f"生成 {SITE / 'ifab.html'}（{len(data.get('sections', []))} 节 / FAQ {len(data.get('faq', []))} 条 / 链接 {len(links)}）"
    )


def main():
    if not IFAB_JSON.exists():
        raise SystemExit(f"缺少 {IFAB_JSON}；请先运行 fetch_ifab.py")
    data = json.loads(IFAB_JSON.read_text(encoding="utf-8"))
    zh = {}
    if IFAB_ZH_JSON.exists():
        zh = json.loads(IFAB_ZH_JSON.read_text(encoding="utf-8"))
    else:
        print("⚠ 缺少 ifab-zh.json，页面将以英文原文呈现")
    build_page(data, zh)


if __name__ == "__main__":
    main()
