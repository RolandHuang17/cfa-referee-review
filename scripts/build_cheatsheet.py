# -*- coding: utf-8 -*-
"""生成 site/cheatsheet.html：考点速查卡（手机翻卡 + A4 打印视图）。

内容来自 data/cheatsheet.json（人工策表：卡面速记 + 翻面细则），
条文出处为 data/laws.json《足球竞赛规则 2026/27》简体中文版。
点击卡片翻面（CSS 3D flip）；打印时全部展开为单页讲义。
"""

import json

from lib.paths import DATA, SITE
from lib.seo import meta_tags
from lib.theme import inject_theme, topbar

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>考点速查卡 · 裁判学习平台</title>
<style>
.cs-head{border-bottom:1px solid var(--line);background:var(--bg2)}
.cs-head .wrap{max-width:1040px;margin:0 auto;padding:24px 16px 16px}
.cs-head h1{margin:0 0 4px;font-family:var(--font-display);font-size:24px;letter-spacing:.4px}
.cs-head .sub{color:var(--muted);font-size:13px;line-height:1.8}
.cs-grid{max-width:1040px;margin:0 auto;padding:20px 16px 70px;display:grid;
  grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.card3d{perspective:1200px;min-height:300px}
.flip{position:relative;width:100%;height:100%;min-height:300px;cursor:pointer;
  transition:transform .5s var(--ease);transform-style:preserve-3d}
.card3d.flipped .flip{transform:rotateY(180deg)}
.cface{position:absolute;inset:0;backface-visibility:hidden;-webkit-backface-visibility:hidden;
  border:1px solid var(--line);border-radius:var(--r-lg);background:var(--card);padding:18px 20px;
  display:flex;flex-direction:column;overflow:auto}
.cface.back{transform:rotateY(180deg);border-color:var(--brand);background:var(--card2)}
.cf-top{display:flex;align-items:center;gap:10px;margin-bottom:4px}
.cf-ic{font-size:26px;flex:none}
.cf-top h2{margin:0;font-family:var(--font-display);font-size:18.5px;flex:1}
.cf-tag{font-size:12px;color:var(--brand);font-weight:600;margin:2px 0 10px}
.cf-hint{margin-top:auto;padding-top:10px;font-size:11.5px;color:var(--faint);
  border-top:1px dashed var(--line)}
.cf-f li{margin:8px 0;font-size:13.8px;line-height:1.75;color:var(--ink)}
.cf-f{padding-left:18px;margin:6px 0 4px}
.cb-sec{margin-bottom:12px}
.cb-sec h3{margin:0 0 5px;font-size:13px;color:var(--brand);letter-spacing:.5px}
.cb-sec ul{margin:0;padding-left:16px}
.cb-sec li{margin:4px 0;font-size:12.8px;line-height:1.7;color:var(--ink2)}
@media print{
  .cs-grid{display:block}
  .card3d{min-height:0;page-break-inside:avoid;margin-bottom:14px;perspective:none}
  .flip{transform:none !important;transition:none;min-height:0;display:flex;flex-direction:column}
  .cface{position:static;backface-visibility:visible;transform:none !important;min-height:0;
    border-radius:0;border:1px solid #999;background:#fff;overflow:visible}
  .cface.back{border-top:none;margin-top:-1px}
  .cf-hint{display:none}
  body{background:#fff;color:#000}
}
</style>
</head>
<body>
__TOPBAR__
<div class="cs-head"><div class="wrap">
  <h1>考点速查卡</h1>
  <div class="sub">考前一夜的 __NCARDS__ 张卡：手球考量链 / 犯规三档 / DOGSO·SPA / VAR 介入 / 红黄牌速查 / 点球程序 / 越位三步 / 重新开始方式 / 2026/27 新规。<b>点击卡片翻面看细则</b>；打印即得单页讲义（全部展开）。条文依据《足球竞赛规则 2026/27》简体中文版（<a href="rules.html">规则全文</a>），评议口径提示提炼自三赛季评议。</div>
</div></div>
<div class="cs-grid" id="csGrid"></div>
<script>
const CARDS = __CARDS__;
document.getElementById("csGrid").innerHTML = CARDS.map((c, i) => `
  <div class="card3d" style="--i:${i}">
    <div class="flip">
      <div class="cface front">
        <div class="cf-top"><span class="cf-ic">${c.icon}</span><h2>${c.title}</h2></div>
        <div class="cf-tag">${c.tagline}</div>
        <ul class="cf-f">${c.front.map(p => `<li>${p}</li>`).join("")}</ul>
        <div class="cf-hint">点击翻面看细则与出处 →</div>
      </div>
      <div class="cface back">
        ${c.back.map(s => `<div class="cb-sec"><h3>${s.h}</h3><ul>${s.items.map(t => `<li>${t}</li>`).join("")}</ul></div>`).join("")}
        <div class="cf-hint">← 点击翻回速记面</div>
      </div>
    </div>
  </div>`).join("");
document.getElementById("csGrid").addEventListener("click", e => {
  const card = e.target.closest(".card3d");
  if (card) card.classList.toggle("flipped");
});
</script>
</body>
</html>
"""


def main():
    data = json.loads((DATA / "cheatsheet.json").read_text(encoding="utf-8"))
    cards_js = json.dumps(
        data["cards"], ensure_ascii=False, separators=(",", ":")
    ).replace("</", "<\\/")
    tb = topbar(
        active="cheatsheet.html",
        stats="stats-2026.html",
        brand_sub="考点速查",
        seasons=("2026", "2025", "2024"),
    )
    html = (
        HTML.replace("__CARDS__", cards_js)
        .replace("__TOPBAR__", tb)
        .replace("__NCARDS__", str(len(data["cards"])))
    )
    html = inject_theme(html, meta=meta_tags("cheatsheet.html"))
    SITE.mkdir(parents=True, exist_ok=True)
    out = SITE / "cheatsheet.html"
    out.write_text(html, encoding="utf-8")
    print(
        f"生成 {out}（{len(data['cards'])} 张速查卡，{len(html.encode('utf-8')) / 1024:.0f} KB）"
    )


if __name__ == "__main__":
    main()
