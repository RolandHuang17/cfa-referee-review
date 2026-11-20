# -*- coding: utf-8 -*-
"""生成考点速查卡。内容来自 data/cheatsheet.json，页面支持离线翻阅与 A4 打印。"""

import json
from html import escape

from lib.paths import DATA, SITE
from lib.seo import meta_tags
from lib.theme import inject_theme, topbar


def render_card(card):
    card_id = "card-" + escape(card["id"], quote=True)
    title = escape(card["title"])
    front = "".join(f"<li>{escape(item)}</li>" for item in card["front"])
    sections = []
    for section in card["back"]:
        items = "".join(f"<li>{escape(item)}</li>" for item in section["items"])
        sections.append(
            f"<section><h3>{escape(section['h'])}</h3><ul>{items}</ul></section>"
        )
    return f"""<article class="study-card" id="{card_id}" aria-labelledby="{card_id}-title" tabindex="-1">
  <h2 id="{card_id}-title"><span class="card-icon" aria-hidden="true">{escape(card["icon"])}</span>{title}</h2>
  <details>
    <summary aria-labelledby="{card_id}-action {card_id}-title"><span id="{card_id}-action"><span class="to-back">查看细则</span><span class="to-front">翻回速记</span></span></summary>
    <div class="card-back">{"".join(sections)}</div>
  </details>
  <div class="card-front"><p class="tagline">{escape(card["tagline"])}</p><ul>{front}</ul></div>
</article>"""


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>考点速查卡 · 裁判学习平台</title>
<style>
.cs-head{border-bottom:1px solid var(--line);background:var(--bg2)}
.cs-head .wrap,.cs-grid{max-width:1040px;margin:auto;padding-inline:clamp(16px,3vw,32px)}
.cs-head .wrap{padding-block:24px 20px}
.cs-head h1{margin:0;font:700 26px/1.3 var(--font-display)}
.cs-head p{margin:6px 0;color:var(--muted);line-height:1.65}
.print-tools{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.print-tools[hidden],.print-caption{display:none}
.cs-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,295px),1fr));
  align-items:start;gap:16px;padding-block:20px 64px}
.study-card{scroll-margin-block-start:calc(var(--top-h,50px) + 12px);min-width:0;padding:17px 20px 19px;
  border:1px solid var(--line);border-radius:var(--r-lg);background:var(--card)}
.study-card:target{border-color:var(--brand);box-shadow:inset 3px 0 var(--brand)}
.study-card h2{margin:0;font:700 20px/1.45 var(--font-display);overflow-wrap:anywhere}
.card-icon{margin-inline-end:8px;font-size:20px}
.study-card summary{width:fit-content;min-height:44px;align-content:center;cursor:pointer;
  color:var(--brand);font-size:13px;font-weight:650}
.study-card summary:hover{text-decoration:underline;text-underline-offset:.2em}
.study-card .to-front,.study-card details[open] .to-back{display:none}
.study-card details[open] .to-front{display:inline}
.study-card li{margin:5px 0;overflow-wrap:anywhere}
.study-card ul{padding-inline-start:1.3em;margin:5px 0}
.card-front,.card-back{border-top:1px solid var(--line);padding-top:10px}
.tagline,.card-back h3{color:var(--brand);font-size:13px;font-weight:650;line-height:1.5}
.tagline{margin:0 0 10px}
.card-back section+section{margin-top:12px}
.card-back h3{margin:0 0 3px}
.card-back ul{color:var(--ink2)}
@media screen{
  .study-card details[open]+.card-front{display:none}
}
@media screen and (prefers-reduced-motion:no-preference){
  .study-card details[open] .card-back{animation:turn-card .22s ease-out;transform-origin:top left}
  @keyframes turn-card{from{opacity:.55;transform:perspective(850px) rotateY(-7deg)}}
}
@page{size:A4;margin:12mm}
@media print{
  .cs-head,.study-card{background:white;color:black}
  .cs-head .wrap,.cs-grid{max-width:none;margin:0;padding:0}
  .cs-head{margin-bottom:3mm;border-color:#777}
  .cs-head h1{font-size:17pt}
  .cs-head .sub,.print-tools,.study-card summary,.card-icon{display:none}
  .print-caption{display:block;margin:1mm 0 2mm;font-size:9pt}
  .cs-grid{display:block;column-count:2;column-gap:7mm}
  .study-card,.study-card:target{display:flex;flex-direction:column;break-inside:avoid;
    margin:0 0 4mm;padding:2mm 0 0;border:0;border-top:1px solid #666;border-radius:0;box-shadow:none}
  .study-card h2{font-size:12pt}
  .study-card details{order:2}
  .study-card details::details-content{display:contents;content-visibility:visible}
  .study-card ul{margin:1mm 0;padding-inline-start:1.2em}
  .study-card li{margin:.45mm 0;font-size:9.5pt;line-height:1.35}
  .tagline,.card-back h3{margin:1mm 0;color:#222;font-size:9.5pt}
  .card-front,.card-back{padding:0;border:0}
  .card-back section+section{margin-top:2mm}
  html[data-print-front] .cs-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4mm}
  html[data-print-front] .study-card{display:block;margin:0;break-inside:avoid}
  html[data-print-front] .study-card details{display:none}
  html[data-print-front] .study-card li{font-size:11pt;line-height:1.4;margin:1mm 0}
}
</style>
</head>
<body>
<a class="skip-link" href="#main">跳到速查卡</a>
__TOPBAR__
<header class="cs-head"><div class="wrap">
  <h1>考点速查卡</h1>
  <p class="sub">__NCARDS__ 张卡。先看卡面要点，再翻看细则与评议提示。<a href="rules.html">查阅《足球竞赛规则 2026/27》全文</a></p>
  <div class="print-tools" hidden>
    <button type="button" class="btn" data-print="front">打印单页速记（仅卡面要点）</button>
    <button type="button" class="btn" data-print="full">打印完整讲义（含细则）</button>
  </div>
  <p class="print-caption">足球竞赛规则 2026/27 · <span>卡面要点与完整细则</span></p>
</div></header>
<main id="main" tabindex="-1"><div class="cs-grid">__CARDS__</div></main>
<script>
const grid = document.getElementById("main");
grid.addEventListener("click", event => {
  const card = event.target.closest(".study-card");
  if (!card || event.target.closest("summary,a,button") || !getSelection().isCollapsed) return;
  const details = card.querySelector("details");
  details.open = !details.open;
});
const printTools = document.querySelector(".print-tools");
const caption = document.querySelector(".print-caption span");
let closedBeforePrint = [];
printTools.hidden = false;
printTools.addEventListener("click", event => {
  const mode = event.target.closest("[data-print]")?.dataset.print;
  if (!mode) return;
  const front = mode === "front";
  document.documentElement.toggleAttribute("data-print-front", front);
  caption.textContent = front ? "单页速记 · 仅卡面要点" : "卡面要点与完整细则";
  window.print();
});
window.addEventListener("beforeprint", () => {
  // Modern engines reveal closed details through the print stylesheet.
  if (document.documentElement.hasAttribute("data-print-front") || CSS.supports("selector(details::details-content)")) return;
  for (const details of grid.querySelectorAll("details:not([open])")) {
    closedBeforePrint.push(details);
    details.open = true;
  }
});
window.addEventListener("afterprint", () => {
  closedBeforePrint.forEach(details => { details.open = false; });
  closedBeforePrint = [];
  document.documentElement.removeAttribute("data-print-front");
  caption.textContent = "卡面要点与完整细则";
});
</script>
</body>
</html>
"""


def main():
    cards = json.loads((DATA / "cheatsheet.json").read_text(encoding="utf-8"))["cards"]
    tb = topbar(
        active="cheatsheet.html",
        stats="stats-2026.html",
        brand_sub="考点速查",
        seasons=("2026", "2025", "2024"),
    )
    html = (
        HTML.replace("__CARDS__", "\n".join(render_card(card) for card in cards))
        .replace("__TOPBAR__", tb)
        .replace("__NCARDS__", str(len(cards)))
    )
    html = inject_theme(html, meta=meta_tags("cheatsheet.html"))
    SITE.mkdir(parents=True, exist_ok=True)
    out = SITE / "cheatsheet.html"
    out.write_text(html, encoding="utf-8")
    print(
        f"生成 {out}（{len(cards)} 张速查卡，{len(html.encode('utf-8')) / 1024:.0f} KB）"
    )


if __name__ == "__main__":
    main()
