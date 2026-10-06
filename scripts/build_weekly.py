# -*- coding: utf-8 -*-
"""生成 site/weekly.html：全球周更评议节目判例库（YouTube 官方节目元数据索引）

数据来自 data/weekly.json（fetch_weekly.py 抓取并提交）+ data/weekly-zh.json
（人工策展的中文译注层，与 uefa-zh/rfef-zh 同构：未译条目回退官方原文并打 ⚠）。
⚠ YouTube 视频受官方服务条款约束不下载、不内嵌——本页为纯链接模式（同 uefa/pro），
每期跳官方观看页；硬约束 1 的用户批准例外之一。
"""
import json

from lib.theme import inject_theme, topbar, icon

from lib.paths import SITE, WEEKLY_JSON, WEEKLY_ZH_JSON

LANG_LABEL = {"en": "英语", "tr": "土耳其语", "ja": "日语", "es": "西语", "ru": "俄语", "pt": "葡语"}

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>全球周更评议节目 · 裁判学习平台</title>
<style>
/* ===== weekly 页专属布局 (tokens/组件来自 data-cfa-theme, 骨架同 pro 页) ===== */
.page-head{border-bottom:1px solid var(--line);background:var(--bg2)}
.page-head .wrap{max-width:1040px;margin:0 auto;padding:22px 16px 18px}
.page-head h1{margin:0 0 5px;font-family:var(--font-display);font-size:23px;letter-spacing:.4px}
.page-head .sub{color:var(--muted);font-size:13px;line-height:1.7}
.src-banner{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:12px;
  padding:10px 14px;border:1px solid var(--brand);background:var(--info-bg);
  border-radius:var(--r-md);font-size:13.5px;color:var(--ink2)}
.src-banner .ic{color:var(--brand)}
.src-banner a{color:var(--brand);font-weight:600;text-decoration:none}
.src-banner a:hover{text-decoration:underline}
.searchbar{margin-top:14px;position:relative;max-width:460px}
.searchbar .ic{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted)}
.searchbar input{width:100%;padding:9px 34px 9px 36px;border:1px solid var(--line);
  border-radius:999px;background:var(--card);color:var(--ink);font-size:13.5px;outline:none}
.searchbar input:focus{border-color:var(--brand)}
.wrap{max-width:1040px;margin:0 auto;padding:18px 16px 60px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 20px}
.show{margin-bottom:34px}
.show-h{border-left:3px solid var(--brand);padding-left:14px;margin-bottom:6px}
.show-h h2{font-family:var(--font-display);font-size:20px;margin:0;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.show-h h2 small{font-size:12px;color:var(--muted);font-weight:400;font-family:var(--font)}
.show-h .org{font-size:12.5px;color:var(--muted);margin-top:3px}
.show-h .org a{color:var(--brand);text-decoration:none;font-weight:600}
.show-h .org a:hover{text-decoration:underline}
.show-h .intro{font-size:13px;color:var(--ink2);line-height:1.8;margin:8px 0 0;max-width:72em}
.badge{white-space:nowrap}
.year-h{font-family:var(--font-display);font-size:16px;margin:18px 0 10px;letter-spacing:.4px}
.year-h small{font-size:12px;color:var(--muted);font-weight:400;margin-left:8px}
.ecard{background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);
  padding:12px 16px;margin-bottom:10px;display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap;
  transition:border-color var(--t-fast) var(--ease)}
.ecard:hover{border-color:var(--brand)}
.ecard .t{flex:1;min-width:260px}
.ecard .t b{display:block;font-size:14px;line-height:1.55}
.ecard .t .meta{color:var(--muted);font-size:12px;margin-top:2px}
.ecard .note{margin-top:7px;font-size:13px;color:var(--ink2);line-height:1.75;
  padding:8px 11px;background:var(--info-bg);border-radius:var(--r-sm)}
.ecard details{margin-top:7px;font-size:12.5px;color:var(--muted)}
.ecard details summary{cursor:pointer;color:var(--brand);font-size:12.5px;user-select:none}
.ecard details p{margin:7px 0 0;line-height:1.75;white-space:pre-line}
.ecard .go{display:inline-flex;align-items:center;gap:6px;padding:6px 13px;border-radius:999px;
  border:1px solid var(--brand);background:var(--info-bg);color:var(--brand);
  font-size:12.5px;font-weight:600;text-decoration:none;white-space:nowrap;margin-top:2px}
.ecard .go:hover{background:var(--brand-strong);color:var(--on-brand)}
.empty{display:none;text-align:center;color:var(--muted);padding:40px 0;font-size:14px}
.foot{margin-top:28px;font-size:12px;color:var(--faint);line-height:1.8}
@media (max-width:760px){.ecard .go{margin-left:auto}}
</style>
</head>
<body class="page-weekly">
<a class="skip-link" href="#content0">跳到内容</a>
__TOPBAR__
<header class="page-head">
  <div class="wrap">
    <h1>全球周更评议节目判例库</h1>
    <div class="sub">七档官方周更/定期评议节目（苏格兰·土耳其·日本·英格兰·墨西哥·阿根廷·俄罗斯）的结构化期目索引：官方标题 / 精确或近似日期 / 时长 / 播放量 / 官方说明原文 + 中文译注 · 每期跳官方观看页 · 版权归各机构所有</div>
    <div class="src-banner">__I_EXTERNAL__ YouTube 视频受官方条款约束不本地化，本页只收录元数据并跳转官方观看；数据核对日期 __CHECKED__</div>
    <div class="searchbar">__I_SEARCH__<input id="q" type="search" placeholder="搜索期目标题 / 中文译注 / 官方说明…" aria-label="搜索期目"></div>
  </div>
</header>
<div class="wrap" id="content0">
  <div class="chips" data-chips>
    <button class="chip on" data-f="all">全部 <b>__N_ALL__</b></button>
    __SHOW_CHIPS__
  </div>
  __SECTIONS__
  <p class="empty" id="emptyTip">没有匹配的期目——换个关键词试试。</p>
  <p class="foot">各节目内容版权归苏格兰足总 / 土耳其足协 / 日本 J 联赛 / Sky Sports·PGMOL / 墨西哥足协裁判委员会 / 阿根廷职业足球联赛 / 俄罗斯足协所有；本页仅收录标题、日期、时长、播放量与官方说明等元数据及官方观看链接（核对日期 __CHECKED__）。中文译注为学习社区策展，欢迎对照原片修订。日期带 ≈ 者由「N 周前」等相对时间按抓取日近似。</p>
</div>
<script>
(function(){
  var curShow="all", q="";
  var chips=document.querySelectorAll("[data-chips] .chip");
  var secs=document.querySelectorAll("section.show");
  var emptyTip=document.getElementById("emptyTip");
  function apply(){
    var anyVisible=false;
    secs.forEach(function(sec){
      var hitShow=curShow==="all"||sec.getAttribute("data-show")===curShow;
      var any=false;
      sec.querySelectorAll(".ecard").forEach(function(c){
        var hit=hitShow&&(!q||(c.getAttribute("data-search")||"").indexOf(q)>=0);
        c.style.display=hit?"":"none";
        if(hit)any=true;
      });
      sec.querySelectorAll(".year-h").forEach(function(y){
        var body=y.nextElementSibling,anyY=false;
        if(body)body.querySelectorAll(".ecard").forEach(function(c){if(c.style.display!=="none")anyY=true;});
        y.style.display=anyY?"":"none";
        if(body)body.style.display=anyY?"":"none";
      });
      sec.style.display=any?"":"none";
      if(any)anyVisible=true;
    });
    if(emptyTip)emptyTip.style.display=anyVisible?"none":"";
  }
  chips.forEach(function(c){
    c.addEventListener("click",function(){
      chips.forEach(function(x){x.classList.remove("on");});
      c.classList.add("on");
      curShow=c.getAttribute("data-f")||"all";
      apply();
    });
  });
  var si=document.getElementById("q");
  if(si)["input","search"].forEach(function(ev){
    si.addEventListener(ev,function(){q=(si.value||"").trim().toLowerCase();apply();});
  });
})();
</script>
</body>
</html>
"""


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") \
        .replace('"', "&quot;").replace("'", "&#39;")


def human_views(v):
    if not v:
        return ""
    if v >= 10000:
        w = v / 10000
        return f"{w:.1f}".rstrip("0").rstrip(".") + "万"
    return str(v)


def build_page(data, zh):
    eps = data.get("episodes", [])
    shows = data.get("shows", {})
    zh_shows = (zh or {}).get("shows", {})
    zh_items = (zh or {}).get("items", {})
    # 译注层校验：key 对不上的打警告（同 uefa-zh 工作流）
    ids = {e.get("id") for e in eps}
    for k in zh_items:
        if k not in ids:
            print(f"⚠ weekly-zh.items 键 {k} 不在 weekly.json 中（疑似过期）")
    for k in zh_shows:
        if k not in shows:
            print(f"⚠ weekly-zh.shows 键 {k} 不在 weekly.json 中（疑似过期）")

    by_show = {}
    for e in eps:
        by_show.setdefault(e.get("show", ""), []).append(e)

    chips, secs = "", ""
    for key, show in shows.items():
        items = by_show.get(key, [])
        if not items:
            continue
        intro = zh_shows.get(key, {}).get("intro", "")
        chips += (f'<button class="chip" data-f="{esc(key)}">{esc(show.get("name", key))} '
                  f'<b>{len(items)}</b></button>')
        # 年份分组（无日期归「日期待定」垫底）
        by_year = {}
        for e in items:
            by_year.setdefault((e.get("date") or "")[:4] or "待定", []).append(e)
        years = sorted((y for y in by_year if y != "待定"), reverse=True) + \
                (["待定"] if "待定" in by_year else [])
        body = ""
        for y in years:
            rows = ""
            for e in by_year[y]:
                vid = e.get("id", "")
                note = zh_items.get(vid, {}).get("note", "")
                desc = e.get("desc") or ""
                meta = []
                d = e.get("date")
                if d:
                    meta.append(("≈" if e.get("date_src") == "approx" else "") + d)
                else:
                    meta.append("日期待定")
                if e.get("length"):
                    meta.append(e["length"])
                v = human_views(e.get("views"))
                if v:
                    meta.append(v + " 次观看")
                lang = LANG_LABEL.get(e.get("lang") or shows[key].get("lang"), "")
                if lang:
                    meta.append(lang)
                search_blob = esc(" ".join(filter(None, [e.get("title", ""), note, desc[:400]])).lower())
                inner = (f'<div class="t"><b>{esc(e.get("title", ""))}</b>'
                         f'<div class="meta">{esc(" · ".join(meta))}</div>')
                if note:
                    inner += f'<div class="note">{esc(note)}</div>'
                if desc:
                    inner += (f'<details><summary>官方说明（原文）</summary>'
                              f'<p>{esc(desc)}</p></details>')
                inner += "</div>"
                rows += (f'<div class="ecard" data-search="{search_blob}">{inner}'
                         f'<a class="go" href="{esc(e.get("url", ""))}" target="_blank" '
                         f'rel="noopener noreferrer">{icon("play", 11)} 官方观看</a></div>')
            label = f"{y} 年" if y != "待定" else "日期待定"
            body += (f'<h3 class="year-h" data-year="{esc(y)}">{esc(label)} '
                     f'<small>{len(by_year[y])} 期</small></h3><div>{rows}</div>')
        surl = show.get("url", "#")
        secs += f"""<section class="show" data-show="{esc(key)}">
  <div class="show-h">
    <h2>{esc(show.get("name", key))} <span class="badge info">{esc(show.get("update", ""))}</span></h2>
    <div class="org">{esc(show.get("org", ""))} · <a href="{esc(surl)}" target="_blank" rel="noopener noreferrer">{icon('external', 11)} 官方频道</a></div>
    {f'<p class="intro">{esc(intro)}</p>' if intro else ''}
  </div>
  {body}
</section>"""
    html = inject_theme(HTML
                         .replace("__TOPBAR__", topbar(active="weekly.html", stats="stats-2026.html",
                                                       brand_sub="全球周更节目"))
                         .replace("__I_EXTERNAL__", icon("external", 14))
                         .replace("__I_SEARCH__", icon("search", 15))
                         .replace("__N_ALL__", str(len(eps)))
                         .replace("__SHOW_CHIPS__", chips)
                         .replace("__SECTIONS__", secs)
                         .replace("__CHECKED__", esc(data.get("fetched", ""))))
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "weekly.html").write_text(html, encoding="utf-8")
    print(f"生成 {SITE / 'weekly.html'}（{len(eps)} 期 / {len(shows)} 节目）")


def main():
    if not WEEKLY_JSON.exists():
        raise SystemExit(f"缺少 {WEEKLY_JSON}；请先运行 fetch_weekly.py")
    data = json.loads(WEEKLY_JSON.read_text(encoding="utf-8"))
    zh = {}
    if WEEKLY_ZH_JSON.exists():
        zh = json.loads(WEEKLY_ZH_JSON.read_text(encoding="utf-8"))
    else:
        print("⚠ 缺少 weekly-zh.json，页面将以原文呈现（无中文译注）")
    build_page(data, zh)


if __name__ == "__main__":
    main()
