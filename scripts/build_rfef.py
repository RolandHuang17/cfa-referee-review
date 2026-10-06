# -*- coding: utf-8 -*-
"""生成 site/rfef.html：西班牙 RFEF/CTA《Criterios Arbitrales》判罚标准手册
（中文译制为主 + 西语原文开关 + 本地化判例视频 + 官方链接回退）

数据来自 data/rfef.json（fetch_rfef.py 抓取并提交，CI 无网络依赖照常重建）；
中文译文来自 data/rfef-zh.json（翻译层，与抓取管线解耦——fetch_rfef.py parse 会整体
覆写 rfef.json，译文绝不能写进去）。构建时防御式合并：栏目按 key、分组按 code、
判例/视频说明按 id 匹配，未命中保持西语并打印构建警告；译文里未被匹配的键也告警。
页面默认纯中文，页头「西语原文」开关（localStorage cfa.rfef-es）切换对照。
视频已由 download_rfef_videos.py 本地化至 site/videos/rfef/（git 忽略，本地学习用途）；
缺失时 <video> onerror 自动降级为官方直链。轻量版（html[data-lite]）隐藏全部视频并
显示官方手册横幅。
"""
import json

from lib.theme import inject_theme, topbar, icon

from lib.paths import DATA, SITE, RFEF_JSON

ZH_JSON = DATA / "rfef-zh.json"
SOURCE_URL = "https://www.card.rfef.es/manual/indice/"

# 认定 norm → 徽章配色（复用 theme 的语义徽章 wrong/correct/pending/info）
DEC_BADGE = {
    "penalty": "wrong", "penalty_yellow": "wrong", "penalty_red": "wrong",
    "penalty_no_card": "wrong", "red_card": "wrong",
    "no_penalty": "correct", "no_infringement": "correct", "no_card": "correct",
    "no_sanction": "correct", "offside_off": "correct", "goal_valid": "correct",
    "yellow_card": "pending", "attacking_foul": "pending", "retake": "pending",
    "dfk": "info", "ifk": "info", "offside_on": "info", "other": "info",
}
# 认定中文标签（norm → zh；decision_labels 缺失时回退西语原文）
DEC_CN = {
    "penalty": "点球", "penalty_yellow": "点球+黄牌", "penalty_red": "点球+红牌",
    "penalty_no_card": "点球（不出牌）", "no_penalty": "不判点球",
    "attacking_foul": "进攻犯规", "dfk": "直接任意球", "ifk": "间接任意球",
    "red_card": "红牌", "yellow_card": "黄牌", "no_card": "不出牌",
    "no_sanction": "不予处罚", "no_infringement": "无犯规", "goal_valid": "进球有效",
    "retake": "重开球门球", "offside_on": "越位犯规·间接任意球",
    "offside_off": "不越位·比赛继续", "other": "判例",
}

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>西班牙 CTA 判罚标准手册 · 裁判学习平台</title>
<script>try{if(localStorage.getItem("cfa.rfef-es")==="1")document.documentElement.setAttribute("data-rfef-es","")}catch(e){}</script>
<style>
/* ===== rfef 页专属布局 (tokens/组件来自 data-cfa-theme, 布局骨架同 scale/uefa 页) ===== */
.page-head{border-bottom:1px solid var(--line);background:var(--bg2)}
.page-head .wrap{max-width:1180px;margin:0 auto;padding:22px 16px 16px}
.page-head-top{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}
.page-head h1{margin:0 0 4px;font-family:var(--font-display);font-size:23px;letter-spacing:.4px}
.page-head .sub{color:var(--muted);font-size:13px}
.src-banner{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:12px;
  padding:10px 14px;border:1px solid var(--brand);background:var(--info-bg);
  border-radius:var(--r-md);font-size:13.5px;color:var(--ink2)}
.src-banner .ic{color:var(--brand)}
.src-banner a{color:var(--brand);font-weight:600;text-decoration:none}
.src-banner a:hover{text-decoration:underline}
.es-toggle{display:inline-flex;align-items:center;gap:6px;margin-top:2px;padding:5px 13px;
  border-radius:999px;border:1px solid var(--line);background:var(--card2);color:var(--ink2);
  font-size:12.5px;cursor:pointer;transition:.12s;white-space:nowrap;flex-shrink:0}
.es-toggle:hover{border-color:var(--brand);color:var(--ink)}
.es-toggle[aria-pressed="true"]{border-color:var(--brand);background:var(--info-bg);
  color:var(--brand);font-weight:600}
.head-tools{display:flex;flex-direction:column;align-items:flex-end;gap:8px;flex-shrink:0}
.head-filter{position:relative;display:flex;align-items:center}
.head-filter .ic{position:absolute;left:10px;color:var(--muted);pointer-events:none}
.head-filter input{height:32px;min-width:230px;padding:0 12px 0 32px;
  border:1px solid var(--line);border-radius:var(--r-sm);
  background:var(--card);color:var(--ink);font-size:13px}
/* 西语原文辅助层：默认隐藏，页头开关（html[data-rfef-es]）控制显示 */
.es{display:none;font-weight:400;color:var(--muted)}
html[data-rfef-es] small.es{display:inline;font-size:12px}
html[data-rfef-es] p.es,html[data-rfef-es] h4.es{display:block}
.layout{max-width:1180px;margin:0 auto;padding:18px 16px 60px;display:grid;
  grid-template-columns:216px minmax(0,1fr);gap:20px;align-items:start}
.gnavs{position:sticky;top:calc(var(--top-h) + 14px);display:flex;flex-direction:column;gap:4px}
.gnavs .gh{font-size:11px;font-weight:700;color:var(--muted);letter-spacing:2px;margin:2px 4px 6px}
.gnavs .gh:not(:first-child){margin-top:14px}
.gnav{display:flex;align-items:center;gap:7px;padding:7px 10px;border-radius:var(--r-sm);
  color:var(--ink2);text-decoration:none;font-size:13.5px;border:1px solid var(--line);transition:.12s}
.gnav b{margin-left:auto;font-size:11px;color:var(--muted);font-weight:600}
.gnav:hover{background:var(--card2);border-color:var(--brand);color:var(--ink)}
.gcontent{min-width:0}
.gsec{margin-bottom:40px}
.gsec>h2{font-family:var(--font-display);font-size:20px;margin:0 0 10px;letter-spacing:.4px}
.gsec>h2 small{font-size:13px;color:var(--muted);font-weight:400;margin-left:6px}
.gsec>h2 b{font-size:12.5px;color:var(--brand);font-weight:600;margin-left:8px}
.gintro{font-size:13.5px;color:var(--ink2);line-height:1.85;margin:0 0 10px}
.sx{margin:0 0 12px;border:1px solid var(--line);border-radius:var(--r-md);background:var(--card)}
.sx summary{cursor:pointer;padding:9px 14px;font-size:13.5px;font-weight:600;color:var(--brand);
  list-style:none;display:flex;align-items:center;gap:7px}
.sx summary::-webkit-details-marker{display:none}
.sx summary .ic{transition:transform .15s}
.sx[open] summary .ic{transform:rotate(180deg)}
.sx .sxb{padding:2px 14px 12px;font-size:13.5px;color:var(--ink2);line-height:1.85}
.sx .sxb p{margin:6px 0}
.gblock{margin:26px 0 8px}
.gblock>h3{font-family:var(--font-display);font-size:17px;margin:0 0 8px;display:flex;
  align-items:center;gap:9px;flex-wrap:wrap}
.gblock>h3 small{font-size:12px;color:var(--muted);font-weight:400}
.gcode{font-family:var(--font-display);font-size:12px;font-weight:700;color:var(--brand);
  border:1px solid var(--line);border-radius:6px;padding:1px 9px;background:var(--card2)}
.gconcl{font-size:13.5px;color:var(--muted);line-height:1.85;margin:0 0 10px}
.gnotes{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;margin:0 0 14px}
.gnote{background:var(--card2);border:1px solid var(--line);border-radius:var(--r-md);padding:11px 14px}
.gnote h4{margin:0 0 6px;font-size:13.5px;color:var(--brand);line-height:1.5}
.gnote ul{margin:0;padding-left:18px;font-size:13px;color:var(--ink2);line-height:1.85}
.hcard{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:15px 18px;margin-bottom:14px;
  transition:transform var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease)}
.hcard:hover{transform:translateY(-2px);border-color:var(--brand)}
.hhead{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}
.hid{font-family:var(--font-display);font-size:12.5px;font-weight:700;color:var(--brand);
  border:1px solid var(--line);border-radius:6px;padding:1px 9px;background:var(--card2);white-space:nowrap}
.hhead .badge{margin-left:auto}
.sit{font-size:14px;line-height:1.9;margin:0}
.xnote{font-size:13px;line-height:1.8;margin:8px 0 0;color:var(--ink2);
  border-left:3px solid var(--brand);padding:2px 0 2px 10px}
.vgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;margin-top:12px}
.vitem{margin:0}
.vitem video{width:100%;aspect-ratio:16/9;background:#000;border-radius:var(--r-md);display:block}
.vitem figcaption{font-size:12.5px;color:var(--muted);line-height:1.7;margin-top:6px}
.vitem .watch{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;width:100%;
  justify-content:center;aspect-ratio:16/9;border-radius:var(--r-md);
  border:1px dashed var(--brand);color:var(--brand);font-size:13px;font-weight:600;
  text-decoration:none;background:var(--info-bg)}
.vfail{display:none;margin-top:10px;padding:8px 12px;border:1px solid var(--amber);
  background:var(--amber-bg);color:var(--ink2);border-radius:var(--r-sm);font-size:13px}
.vfail.show{display:block}
html[data-lite] .lite-banner{display:flex}
.lite-banner{display:none;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:18px;
  padding:10px 14px;border:1px solid var(--amber);background:var(--amber-bg);
  border-radius:var(--r-md);font-size:13.5px;color:var(--ink2)}
.lite-banner a{color:var(--brand);font-weight:600;text-decoration:none}
.lite-banner a:hover{text-decoration:underline}
html[data-lite] .vgrid{display:none}
html[data-lite] .sit{font-size:15px}
@media (max-width:900px){
  .layout{grid-template-columns:minmax(0,1fr)}
  .gnavs{position:static;flex-direction:row;flex-wrap:wrap}
  .gnavs .gh{flex-basis:100%}
}
</style>
<script>
/* vfb 必须在正文之前定义：未下载完成的视频在首屏解析期就触发 onerror */
function vfb(el, url){
  var w = el.parentElement;
  if (!w) return;
  var a = document.createElement('a');
  a.className = 'watch';
  a.href = url;
  a.target = '_blank';
  a.rel = 'noopener noreferrer';
  a.innerHTML = '__I_PLAY__ 在线观看（官方直链） __I_EXT__';
  w.innerHTML = '';
  w.appendChild(a);
}
</script>
</head>
<body class="page-rfef">
<a class="skip-link" href="#content0">跳到内容</a>
__TOPBAR__
<header class="page-head">
  <div class="wrap">
    <div class="page-head-top">
      <div>
        <h1>西班牙 CTA《Criterios Arbitrales》判罚标准手册</h1>
        <div class="sub">RFEF 裁判委员会官方手册（2026/27 版）：点球 · 红牌 · DOGSO · APP · 越位逐条判罚尺度 + 官方判例视频 · 中文译制仅供参考、以官方西语原文为准 · 版权归 RFEF 所有</div>
      </div>
      <div class="head-tools">
        <div class="search-wrap head-filter">__I_SEARCH__<input id="fFilter" type="search"
          placeholder="过滤判例（编号/中文/西语）" autocomplete="off"></div>
        <button id="btnEs" class="es-toggle" type="button" aria-pressed="false">西语原文：关</button>
      </div>
    </div>
    <div class="lite-banner">__I_INFO__ 当前为轻量版：判例视频已隐藏。完整视频请前往 <a href="__SOURCE_URL__" target="_blank" rel="noopener noreferrer">RFEF 官方手册页</a>在线观看，或切回完整版。</div>
    <div class="src-banner">__I_EXTERNAL__ 官方判例视频已本地化（本地学习用途，与各赛季评议视频同策略）；缺失时自动改用官方在线链接。来源：__SOURCE_LINK__</div>
  </div>
</header>
<div class="layout">
  <aside class="gnavs" aria-label="手册栏目" data-navs>__NAVS__</aside>
  <div class="gcontent">__SECS__</div>
</div>
<script>
(function(){
  var KEY="cfa.rfef-es";
  var d=document.documentElement,btn=document.getElementById("btnEs");
  function paint(on){
    if(on){d.setAttribute("data-rfef-es","")}else{d.removeAttribute("data-rfef-es")}
    if(btn){btn.setAttribute("aria-pressed",on?"true":"false");
      btn.textContent=on?"西语原文：开":"西语原文：关"}
  }
  var on=false;try{on=localStorage.getItem(KEY)==="1"}catch(e){}
  paint(on);
  if(btn)btn.addEventListener("click",function(){
    on=!d.hasAttribute("data-rfef-es");
    try{localStorage.setItem(KEY,on?"1":"0")}catch(e){}
    paint(on);
  });
  /* 轻量版切换时同步横幅（theme.py 的 cfa:lite 事件） */
  window.addEventListener("cfa:lite", function(ev){}, false);
  /* 简易文本过滤：匹配判例编号/中文/西语文本 */
  var inp=document.getElementById("fFilter");
  if(inp)inp.addEventListener("input",function(){
    var q=this.value.trim().toLowerCase();
    document.querySelectorAll(".gcontent .gsec").forEach(function(sec){
      var any=false;
      sec.querySelectorAll(".gblock").forEach(function(gb){
        var gAny=false;
        gb.querySelectorAll(".hcard").forEach(function(c){
          var hit=!q||c.textContent.toLowerCase().indexOf(q)>=0;
          c.style.display=hit?"":"none";
          if(hit)gAny=true;
        });
        gb.style.display=gAny?"":"none";
        if(gAny)any=true;
      });
      sec.style.display=any?"":"none";
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


def load_zh():
    if not ZH_JSON.exists():
        return None
    try:
        return json.loads(ZH_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"⚠ rfef-zh.json 解析失败，按无译文处理: {e}")
        return None


def apply_zh(data, zh):
    """把 rfef-zh.json 译文并入 data：栏目按 key、分组按 code、判例/视频说明按 id 匹配；
    未命中保持西语并打印警告；译文里未被匹配的键也告警（防 rfef.json 更新后译文漂移）。"""
    if not zh:
        return
    zh_secs = zh.get("sections") or {}
    zh_items = zh.get("items") or {}
    used_s, used_i = set(), set()
    for s in data.get("sections", []):
        key = s.get("key", "")
        zs = zh_secs.get(key)
        if not zs:
            if zh_secs:
                print(f"⚠ 栏目 [{key}] 无译文，该栏目保持西语")
            continue
        used_s.add(key)
        for f in ("name", "intro", "complexity", "general"):
            if zs.get(f):
                s[f + "_cn"] = zs[f]
        for g in s.get("groups", []):
            zg = (zs.get("groups") or {}).get(g.get("code", ""))
            if not zg:
                continue
            if zg.get("name"):
                g["name_cn"] = zg["name"]
            if zg.get("conclusion"):
                g["conclusion_cn"] = zg["conclusion"]
            znotes = zg.get("notes")
            if znotes is not None:
                if len(znotes) == len(g.get("notes_es") or []):
                    g["notes_cn"] = znotes
                else:
                    print(f"⚠ 分组 [{g.get('code')}] notes 条数与西语不一致，该组判读注记回退西语")
    # 判例与视频说明（按 id 平铺匹配，跨栏目唯一）
    for s in data.get("sections", []):
        for g in s.get("groups", []):
            for it in g.get("items", []):
                zi = zh_items.get(it.get("id", ""))
                if zi and zi.get("situation"):
                    it["situation_cn"] = zi["situation"]
                    used_i.add(it["id"])
                if zi and zi.get("extra"):
                    it["extra_cn"] = zi["extra"]
                for v in it.get("videos", []):
                    zv = zh_items.get(v.get("id", ""))
                    if zv and zv.get("caption"):
                        v["caption_cn"] = zv["caption"]
                        used_i.add(v["id"])
                    elif v.get("caption_es"):
                        # 说明与情形重复的视频在 zh 层省略（构建时复用情形译文）
                        v["caption_same"] = True
    stale_s = sorted(set(zh_secs) - used_s)
    stale_i = sorted(set(zh_items) - used_i)
    if stale_s:
        print(f"⚠ 译文中存在未匹配的栏目 key: {', '.join(stale_s)}")
    if stale_i:
        head = ", ".join(stale_i[:6]) + (" …" if len(stale_i) > 6 else "")
        print(f"⚠ 译文中存在未匹配的判例/视频 id（{len(stale_i)} 条）: {head}")


def _zh_or_es(cn, es):
    """返回 (主文本, 西语文本)；主文本缺省时用西语。"""
    if cn:
        return cn, (es or "")
    return es or "", ""


def build_page(data):
    dec_labels = {}
    zh = load_zh()
    if zh and zh.get("decision_labels"):
        dec_labels = zh["decision_labels"]

    def dec_label(norm, es):
        return dec_labels.get(norm) or DEC_CN.get(norm) or es or "判例"

    secs = data.get("sections", [])
    extras = data.get("extra_topics", [])
    navs, secs_html = "", ""
    n_items = n_vids = 0
    for si, s in enumerate(secs):
        anchor = f"s-{si}"
        items = [it for g in s["groups"] for it in g["items"]]
        n_items += len(items)
        n_vids += sum(len(it.get("videos", [])) for it in items)
        navs += (f'<a class="gnav" href="#{anchor}">{esc(s.get("name_cn") or s["name_es"])}'
                 f'<b>{len(items)}</b></a>')
        # —— 栏目头 ——
        name_cn, name_es = _zh_or_es(s.get("name_cn"), s.get("name_es", ""))
        h2 = f'<h2>{esc(name_cn)}'
        if name_es:
            h2 += f' <small class="es">{esc(name_es)}</small>'
        h2 += f' <b>{len(items)} 例 · {sum(len(it.get("videos", [])) for it in items)} 视频</b></h2>'
        body = ""
        cn_i, es_i = _zh_or_es(s.get("intro_cn"), s.get("intro_es"))
        if cn_i:
            body += f'<p class="gintro">{esc(cn_i)}</p>'
            if es_i:
                body += f'<p class="gintro es">{esc(es_i)}</p>'
        for fld, label in (("complexity", "解读复杂性"), ("general", "通用判罚尺度")):
            cn_t, es_t = _zh_or_es(s.get(fld + "_cn"), s.get(fld + "_es"))
            if not cn_t:
                continue
            inner = f"<p>{esc(cn_t)}</p>"
            if es_t:
                inner += f'<p class="es">{esc(es_t)}</p>'
            body += (f'<details class="sx"><summary>{icon("chev-d", 13)} {label}</summary>'
                     f'<div class="sxb">{inner}</div></details>')
        # —— 分组 ——
        for g in s["groups"]:
            body += '<div class="gblock">'
            gn_cn, gn_es = _zh_or_es(g.get("name_cn"), g.get("name_es", ""))
            h3 = f'<h3><span class="gcode">{esc(g["code"])}</span>{esc(gn_cn)}'
            if gn_es:
                h3 += f' <small class="es">{esc(gn_es)}</small>'
            h3 += "</h3>"
            body += h3
            gc_cn, gc_es = _zh_or_es(g.get("conclusion_cn"), g.get("conclusion_es"))
            if gc_cn:
                body += f'<p class="gconcl">{esc(gc_cn)}</p>'
                if gc_es:
                    body += f'<p class="gconcl es">{esc(gc_es)}</p>'
            if g.get("notes_es"):
                znotes = g.get("notes_cn") or []
                blocks = ""
                for ni, nt in enumerate(g["notes_es"]):
                    z = znotes[ni] if ni < len(znotes) else None
                    zh_items_ = z["items"] if z else nt["items"]
                    lis = "".join(f"<li>{esc(x)}</li>" for x in zh_items_)
                    h4 = esc(z["h"]) if z else esc(nt["h"])
                    if z:
                        lis += "".join(f'<li class="es">{esc(x)}</li>' for x in nt["items"])
                        h4 += f'<h4 class="es" style="margin:-2px 0 6px;font-size:12px;font-weight:400">{esc(nt["h"])}</h4>'
                    blocks += f'<div class="gnote"><h4>{h4}</h4><ul>{lis}</ul></div>'
                body += f'<div class="gnotes">{blocks}</div>'
            for it in g["items"]:
                n_badge = DEC_BADGE.get(it.get("decision_norm", "other"), "info")
                label = dec_label(it.get("decision_norm", "other"), it.get("decision_es", ""))
                card = f'<article class="hcard"><div class="hhead"><span class="hid">{esc(it["id"])}</span>'
                card += f'<span class="badge {n_badge}">{esc(label)}'
                es_dec = f'<span class="es" style="font-weight:400;margin-left:4px">{esc(it["decision_es"])}</span>' \
                    if it.get("decision_es") and dec_labels else ""
                card += es_dec + "</span></div>"
                cn_s, es_s = _zh_or_es(it.get("situation_cn"), it.get("situation_es"))
                card += f'<p class="sit">{esc(cn_s)}</p>'
                if es_s:
                    card += f'<p class="sit es">{esc(es_s)}</p>'
                cn_x, es_x = _zh_or_es(it.get("extra_cn"), it.get("decision_extra_es"))
                if cn_x:
                    card += f'<p class="xnote">{esc(cn_x)}'
                    if es_x:
                        card += f'<span class="es">{esc(es_x)}</span>'
                    card += "</p>"
                vids = it.get("videos", [])
                if vids:
                    figs = ""
                    for v in vids:
                        cap_cn, cap_es = _zh_or_es(
                            v.get("caption_cn")
                            or (it.get("situation_cn") if v.get("caption_same") else ""),
                            v.get("caption_es"))
                        if v.get("caption_same"):
                            cap_cn = cap_es = ""  # 与情形文本重复，不逐视频重复渲染
                        fig = f'<figure class="vitem"><video controls preload="none" ' \
                              f'src="{esc(v["file"])}" onerror="vfb(this,\'{v["url"]}\')"></video>'
                        if cap_cn:
                            fig += f"<figcaption>{esc(cap_cn)}</figcaption>"
                            if cap_es:
                                fig += f'<figcaption class="es">{esc(cap_es)}</figcaption>'
                        fig += "</figure>"
                        figs += fig
                    card += f'<div class="vgrid">{figs}</div>'
                card += "</article>"
                body += card
            body += "</div>"
        secs_html += f'<section class="gsec" id="{anchor}">{h2}{body}</section>'
    # 延伸栏目
    if extras:
        navs += '<div class="gh">延伸栏目</div>'
        for x in extras:
            navs += (f'<a class="gnav" href="{esc(x["url"])}" target="_blank" '
                     f'rel="noopener noreferrer">{esc(x["name_cn"])} {icon("external", 11)}</a>')
    tb = topbar(active="rfef.html", stats="stats-2026.html",
                brand_sub="RFEF 判罚标准", seasons=("2026", "2025", "2024"), lite_btn=True)
    src_link = (f'<a href="{SOURCE_URL}" target="_blank" rel="noopener noreferrer">'
                f'card.rfef.es《Criterios Arbitrales》官方手册</a>')
    html = inject_theme(HTML
                        .replace("__TOPBAR__", tb)
                        .replace("__SOURCE_URL__", SOURCE_URL)
                        .replace("__SOURCE_LINK__", src_link)
                        .replace("__I_EXTERNAL__", icon("external", 14))
                        .replace("__I_INFO__", icon("help", 14))
                        .replace("__I_SEARCH__", icon("search", 13))
                        .replace("__I_PLAY__", icon("play", 13))
                        .replace("__I_EXT__", icon("external", 12))
                        .replace("__NAVS__", navs)
                        .replace("__SECS__", secs_html))
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "rfef.html").write_text(html, encoding="utf-8")
    print(f"生成 {SITE / 'rfef.html'}（{len(secs)} 栏目 / {n_items} 例 / {n_vids} 视频）")


def main():
    if not RFEF_JSON.exists():
        raise SystemExit(f"缺少 {RFEF_JSON}；请先运行 fetch_rfef.py 抓取")
    data = json.loads(RFEF_JSON.read_text(encoding="utf-8"))
    apply_zh(data, load_zh())
    build_page(data)


if __name__ == "__main__":
    main()
