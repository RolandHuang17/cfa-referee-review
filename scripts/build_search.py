# -*- coding: utf-8 -*-
"""生成 site/search.html：全站统一搜索（一次入口搜全部 20 个页面的内容）。

构建期把可搜索文档压成紧凑数组内联（[类型, 分组标签, 标题, 链接, 全文] 五元组），
页面端纯 JS 子串匹配（中文无分词，indexOf 足够快）+ 来源分组过滤 + 命中上下文摘录。

收录范围与体量控制：
- 三赛季全部判例（desc/appeal/conclusion/tags/对阵，锚点直达判例卡）
- 竞赛规则 24 章（html 剥标签全文，锚点直达章节）
- 统一尺度 104 例（note+决定矩阵，锚点直达场景卡）
- 国际资料：UEFA 判例 / IFAB FAQ / weekly 期目 / CONMEBOL / RFEF / HNS / PRO 文章
  （weekly 长官方说明截断 240 字符，控制索引体量）
"""

import json
import re

from lib.paths import (
    CONMEBOL_JSON,
    CONMEBOL_ZH_JSON,
    DATA,
    HNS_JSON,
    HNS_ZH_JSON,
    IFAB_JSON,
    IFAB_ZH_JSON,
    PRO_JSON,
    RFEF_JSON,
    RFEF_ZH_JSON,
    SCALE_JSON,
    SITE,
    UEFA_JSON,
    UEFA_ZH_JSON,
    WEEKLY_JSON,
    WEEKLY_ZH_JSON,
)
from lib.seo import meta_tags
from lib.theme import inject_theme, js_icons, topbar

# 类型标记：g=分组（case/law/scale/intl），l=显示名
GROUPS = [
    ("case", "判例"),
    ("law", "竞赛规则"),
    ("scale", "尺度场景"),
    ("intl", "国际资料"),
]

TEXT_CAP = 1500  # 单文档全文上限（字符）
WEEKLY_DESC_CAP = 240


def _read(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _strip(html):
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


def _load_laws():
    path = DATA / "laws.json"
    if not path.exists():
        return []
    return _read(path).get("sections", [])


def build_docs():
    docs = []

    def add(g, label, title, url, text):
        text = re.sub(r"\s+", " ", text or "").strip()[:TEXT_CAP]
        if title and url:
            docs.append([g, label, title, url, (text or title).lower()])

    # 三赛季判例
    for season in ("2026", "2025", "2024"):
        data = _read(DATA / f"cases-{season}.json")
        cat_names = {}
        for c in data.get("cases", []):
            cat = c.get("category_name") or c.get("category") or ""
            cat_names[c.get("category")] = cat
        for c in data.get("cases", []):
            teams = (
                f"{c.get('home', '')} vs {c.get('away', '')}" if c.get("home") else ""
            )
            title = f"{c.get('comp', '')}{c.get('round', '')} {teams} · {c.get('category_name', '')}"
            add(
                "case",
                f"{season}赛季",
                title.strip(" ·"),
                f"season-{season}.html#case-{c['seq']}",
                " ".join(
                    filter(
                        None,
                        [
                            c.get("desc"),
                            c.get("appeal"),
                            c.get("conclusion"),
                            teams,
                            " ".join(c.get("tags", [])),
                        ],
                    )
                ),
            )
    # 考点速查卡（卡面 + 翻面全文可搜）
    cheatsheet = _read(DATA / "cheatsheet.json")
    for card in cheatsheet.get("cards", []):
        parts = list(card.get("front", []))
        for sec in card.get("back", []):
            parts.append(sec.get("h", ""))
            parts.extend(sec.get("items", []))
        add(
            "law",
            "考点速查",
            f"速查卡 · {card['title']}",
            "cheatsheet.html",
            " ".join(parts),
        )
    # 竞赛规则
    for s in _load_laws():
        add(
            "law",
            "竞赛规则",
            s["title"],
            f"rules.html#{s['id']}",
            _strip(s.get("html")),
        )
    # 统一尺度场景
    scale = _read(SCALE_JSON)
    for year, ydata in scale.items():
        if not isinstance(ydata, dict):
            continue
        for sec in ydata.get("sections", []):
            for g in sec.get("groups", []):
                for it in g.get("items", []):
                    dec = "、".join(d.get("label", "") for d in it.get("decision", []))
                    add(
                        "scale",
                        f"{year}尺度",
                        f"{g['name']} {it['id']} · {it.get('title', '')}",
                        f"scale.html#h{year}-{it.get('series', '')}-{it['id']}",
                        f"{it.get('note', '')} {dec} {it.get('reason', '')}",
                    )
    # UEFA 判例（中文标题 + 英文原标题都可搜）
    uefa, uzh = _read(UEFA_JSON), _read(UEFA_ZH_JSON)
    for gi, grp in enumerate(uefa.get("groups", [])):
        for i, it in enumerate(grp.get("items", []), 1):
            zh_title = (uzh.get("items", {}).get(it.get("id", "")) or {}).get(
                "title", ""
            )
            add(
                "intl",
                "UEFA",
                zh_title or it.get("title", ""),
                f"uefa.html#u-{gi}c{i}",
                f"{it.get('title', '')} {zh_title} {grp.get('name_cn', '')} {it.get('caption', '')}",
            )
    # IFAB FAQ + 条款（中文层全文）
    ifab, izh = _read(IFAB_JSON), _read(IFAB_ZH_JSON)
    for q in ifab.get("faq", []):
        zq = izh.get("faq", {}).get(q["id"], {})
        add(
            "intl",
            "IFAB",
            f"IFAB FAQ {q['id'].upper()} · {zq.get('q', q.get('q', ''))[:60]}",
            f"ifab.html#faq-{q['id']}",
            f"{zq.get('q', '')} {zq.get('a', '')}",
        )
    for sec in ifab.get("sections", []):
        blocks = izh.get("sections", {}).get(sec["id"], {}).get("blocks", {})
        parts = []
        for b in sec.get("blocks", []):
            zb = blocks.get(b.get("h") or "_head")
            # _head 的值是裸 items 列表，命名子节是 {h, items}
            items = zb if isinstance(zb, list) else (zb or {}).get("items", [])
            for item in items or b.get("items", []):
                parts.append(item.get("t", ""))
        if parts:
            add(
                "intl",
                "IFAB",
                f"IFAB 协议 · {sec.get('h', '')}",
                "ifab.html",
                " ".join(parts),
            )
    # weekly 期目（官方说明截断）
    weekly, wzh = _read(WEEKLY_JSON), _read(WEEKLY_ZH_JSON)
    shows = weekly.get("shows", {})
    for e in weekly.get("episodes", []):
        note = (wzh.get("items", {}).get(e.get("id", "")) or {}).get("note", "")
        show = shows.get(e.get("show", ""), {})
        add(
            "intl",
            "周更节目",
            f"{show.get('name', e.get('show', ''))} · {e.get('title', '')[:80]}",
            "weekly.html",
            f"{note} {e.get('desc', '')[:WEEKLY_DESC_CAP]}",
        )
    # CONMEBOL
    con, czh = _read(CONMEBOL_JSON), _read(CONMEBOL_ZH_JSON)
    for c in con.get("cases", []):
        zh = (czh.get("cases", {}).get(c.get("url", "")) or {}).get("situation", "")
        add(
            "intl",
            "CONMEBOL",
            f"{c.get('comp_cn') or c.get('comp', '')} · {c.get('match', '')}",
            "conmebol.html",
            f"{zh} {c.get('situacion_es', '')} {c.get('estadio', '')}",
        )
    # RFEF（判例情形中文）
    rfef, rzh = _read(RFEF_JSON), _read(RFEF_ZH_JSON)
    for s in rfef.get("sections", []):
        for g in s.get("groups", []):
            for it in g.get("items", []):
                zh = (rzh.get("items", {}).get(it.get("id", "")) or {}).get(
                    "situation", ""
                )
                add(
                    "intl",
                    "RFEF",
                    f"{it.get('id', '')} · {(zh or it.get('situation_es', ''))[:60]}",
                    "rfef.html",
                    f"{zh} {it.get('situation_es', '')}",
                )
    # HNS（判例中文正文）
    hns, hzh = _read(HNS_JSON), _read(HNS_ZH_JSON)
    for r in hns.get("rounds", []):
        for inc in r.get("incidents", []):
            zi = (
                hzh.get("rounds", {})
                .get(str(r.get("id", "")), {})
                .get("incidents", {})
                .get(str(inc.get("no", "")), {})
            )
            raw = zi.get("paras") or inc.get("paras", [])
            paras = " ".join(
                (it.get("t", "") if isinstance(it, dict) else str(it)) for it in raw
            )
            add(
                "intl",
                "HNS",
                f"{r.get('title', '')[:50]} · 判例{inc.get('no', '')}",
                "hns.html",
                paras,
            )
    # PRO 文章（外链官方页）
    pro = _read(PRO_JSON)
    for a in pro.get("articles", []):
        add(
            "intl",
            "PRO",
            f"{a.get('series_name', '')} · {a.get('title', '')[:90]}",
            a.get("url", ""),
            f"{a.get('title', '')} {a.get('league', '')}",
        )
    return docs


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>全站搜索 · 裁判学习平台</title>
<style>
.shead{border-bottom:1px solid var(--line);background:var(--bg2)}
.shead .wrap{max-width:880px;margin:0 auto;padding:26px 16px 18px}
.shead h1{margin:0 0 4px;font-family:var(--font-display);font-size:24px;letter-spacing:.5px}
.shead .sub{color:var(--muted);font-size:13px}
.sbar{position:relative;margin-top:16px}
.sbar .ic{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:var(--muted)}
.sbar input{width:100%;padding:12px 40px 12px 40px;border:1px solid var(--line);border-radius:999px;
  background:var(--card);color:var(--ink);font-size:15px;outline:none}
.sbar input:focus{border-color:var(--brand)}
.schips{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.wrap2{max-width:880px;margin:0 auto;padding:18px 16px 60px}
.scount{font-size:12.5px;color:var(--muted);margin:2px 0 10px}
.sres a.sr{display:block;padding:13px 14px;border:1px solid var(--line);border-radius:var(--r-md);
  margin-bottom:10px;text-decoration:none;background:var(--card)}
.sres a.sr:hover{border-color:var(--brand);transform:translateY(-1px)}
.sr .t1{font-size:14.5px;font-weight:600;color:var(--ink);margin-bottom:4px}
.sr .t1 mark{background:transparent;color:var(--brand);font-weight:700}
.sr .t2{font-size:12.5px;color:var(--muted);line-height:1.7}
.sr .t2 mark{background:var(--amber-bg);color:inherit;border-radius:3px;padding:0 2px}
.sr .gl{display:inline-block;margin-right:7px;padding:1px 9px;border:1px solid var(--line);
  border-radius:999px;font-size:11px;color:var(--brand);background:var(--card2)}
.sempty{text-align:center;color:var(--muted);padding:48px 0;font-size:14px}
.kbd-hint{font-size:12px;color:var(--faint);margin-top:6px}
</style>
</head>
<body>
__TOPBAR__
<div class="shead"><div class="wrap">
  <h1>全站搜索</h1>
  <div class="sub">一次搜遍三赛季判例、竞赛规则、统一尺度场景与国际评议资料（__N__ 份文档）</div>
  <div class="sbar" id="sbar"></div>
  <div class="schips" id="schips"></div>
  <p class="kbd-hint">按 <b>/</b> 聚焦搜索框</p>
</div></div>
<div class="wrap2">
  <div class="scount" id="scount"></div>
  <div class="sres" id="sres"></div>
</div>
<script>
const DOCS = __DOCS__;
const GROUPS = __GROUPS__;
const IC = __ICONS__;
let cur = "all", q = "";
function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}
function rex(kw){ return new RegExp(kw.replace(/[.*+?^${}()|[\]\\]/g,"\\$&"),"gi"); }
function renderBar(){
  document.getElementById("sbar").innerHTML = IC.search +
    '<input id="q" type="search" placeholder="输入关键词：如 手球 越位 点球 DOGSO 暴力行为 判例三…" aria-label="全站搜索">';
  const si = document.getElementById("q");
  ["input","search"].forEach(ev=>si.addEventListener(ev, ()=>{
    q = (si.value||"").trim().toLowerCase();
    render();
  }));
  // 深链预填：search.html?q=关键词（404 页搜索框 / 外部链接入口）
  const qp = new URLSearchParams(location.search).get("q");
  if (qp){
    si.value = qp;
    q = qp.trim().toLowerCase();
    if (q) si.focus();
  }
}
function renderChips(){
  const n = g => g==="all" ? DOCS.length : DOCS.filter(d=>d[0]===g).length;
  document.getElementById("schips").innerHTML =
    `<button class="chip ${cur==="all"?"on":""}" data-g="all">全部 ${n("all")}</button>` +
    GROUPS.map(([g,l])=>`<button class="chip ${cur===g?"on":""}" data-g="${g}">${l} ${n(g)}</button>`).join("");
}
document.getElementById("schips").addEventListener("click", e=>{
  const b = e.target.closest("[data-g]"); if(!b) return;
  cur = b.dataset.g; renderChips(); render();
});
function snippet(text, kw){
  const i = text.toLowerCase().indexOf(kw);
  if (i < 0) return esc(text.slice(0, 110)) + (text.length>110?"…":"");
  const a = Math.max(0, i-45), b = Math.min(text.length, i+kw.length+70);
  return (a>0?"…":"") + esc(text.slice(a, b)).replace(rex(kw), m=>"<mark>"+m+"</mark>") + (b<text.length?"…":"");
}
function render(){
  const kw = q;
  let hits = DOCS.filter(d => (cur==="all"||d[0]===cur) && (!kw || d[4].indexOf(kw)>=0 || d[2].toLowerCase().indexOf(kw)>=0));
  document.getElementById("scount").textContent = kw || cur!=="all"
    ? `命中 ${hits.length} 份文档` : `共 ${DOCS.length} 份文档，输入关键词开始搜索`;
  const box = document.getElementById("sres");
  if (!hits.length){
    box.innerHTML = `<div class="sempty">${kw ? "没有找到相关内容——换个关键词试试（如：手球 / 越位 / 点球 / VAR）" : "输入关键词开始搜索"}</div>`;
    return;
  }
  const gname = Object.fromEntries(GROUPS);
  box.innerHTML = hits.slice(0, 60).map(d=>{
    const ext = /^https?:/.test(d[3]) ? ' target="_blank" rel="noopener noreferrer"' : '';
    const title = kw ? esc(d[2]).replace(rex(kw), m=>"<mark>"+m+"</mark>") : esc(d[2]);
    return `<a class="sr" href="${esc(d[3])}"${ext}>
      <div class="t1"><span class="gl">${gname[d[0]]||d[0]} · ${esc(d[1])}</span>${title}</div>
      <div class="t2">${kw ? snippet(d[4], kw) : esc(d[4].slice(0,110)) + (d[4].length>110?"…":"")}</div>
    </a>`;
  }).join("") + (hits.length>60 ? `<div class="sempty">仅显示前 60 条，输入更具体的关键词缩小范围</div>` : "");
}
document.addEventListener("keydown", e=>{
  const t=(e.target.tagName||"").toLowerCase();
  if(t==="input"||t==="textarea")return;
  if(e.key==="/"){e.preventDefault();const el=document.getElementById("q");if(el)el.focus();}
});
renderBar(); renderChips(); render();
</script>
</body>
</html>
"""


def main():
    docs = build_docs()
    data_js = json.dumps(docs, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )
    groups_js = json.dumps(GROUPS, ensure_ascii=False, separators=(",", ":"))
    tb = topbar(
        active="search.html",
        stats="stats-2026.html",
        brand_sub="全站搜索",
        seasons=("2026", "2025", "2024"),
    )
    html = (
        HTML.replace("__DOCS__", data_js)
        .replace("__GROUPS__", groups_js)
        .replace("__N__", str(len(docs)))
        .replace("__TOPBAR__", tb)
        .replace("__ICONS__", js_icons())
    )
    html = inject_theme(html, meta=meta_tags("search.html"))
    SITE.mkdir(parents=True, exist_ok=True)
    out = SITE / "search.html"
    out.write_text(html, encoding="utf-8")
    by_group = {g: sum(1 for d in docs if d[0] == g) for g, _ in GROUPS}
    size = len(html.encode("utf-8")) / 1024
    print(f"生成 {out}（{len(docs)} 份文档 {by_group}，{size:.0f} KB）")


if __name__ == "__main__":
    main()
