# -*- coding: utf-8 -*-
"""生成 site/hns.html：克罗地亚足协《Sudačka analiza》逐轮判例分析页

数据来自 data/hns.json（fetch_hns.py 抓取提交）+ data/hns-zh.json（判例级中文译制层，
paras 与原文 1:1 序号对齐，数量不齐整判例回退克罗地亚语并 ⚠）。每判例附官方
YouTube 视频直链（跳官方页，不内嵌——硬约束 1）；认定徽章（correct/incorrect）
由 fetch_hns.py 从委员会认定句归一提取。无内嵌第三方资源。
"""
import json

from lib.theme import inject_theme, topbar, icon

from lib.paths import HNS_JSON, HNS_ZH_JSON, SITE

VERDICT = {"correct": ("认定正确", "correct"), "incorrect": ("认定错误", "wrong"),
           "other": ("详见原文", "info")}

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>克罗地亚评议 · Sudačka analiza · 裁判学习平台</title>
<style>
/* ===== hns 页专属布局 (tokens/组件来自 data-cfa-theme, 骨架同 conmebol 页) ===== */
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
.wrap{max-width:1040px;margin:0 auto;padding:18px 16px 60px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 18px}
.year-h{font-family:var(--font-display);font-size:18px;margin:26px 0 12px;letter-spacing:.4px}
.year-h small{font-size:12px;color:var(--muted);font-weight:400;margin-left:8px}
.round{margin-bottom:22px}
.round-h{border-left:3px solid var(--brand);padding-left:14px;margin-bottom:10px}
.round-h h2{font-family:var(--font-display);font-size:19px;margin:0;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.round-h .meta{font-size:12.5px;color:var(--muted);margin-top:3px}
.round-h .meta a{color:var(--brand);text-decoration:none;font-weight:600}
.round-h .meta a:hover{text-decoration:underline}
.ccard{background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);
  padding:14px 16px;margin-bottom:12px;transition:border-color var(--t-fast) var(--ease)}
.ccard:hover{border-color:var(--brand)}
.ccard .chead{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}
.ccard .chead .cmatch{font-weight:700;font-size:14.5px}
.ccard .cinfo{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:9px}
.ccard .cinfo .chip{font-size:12px}
.ccard .cbody p,.ccard .cbody li{font-size:13.5px;line-height:1.85;color:var(--ink2);margin:5px 0}
.ccard .cbody ul{padding-left:20px;margin:5px 0}
.ccard .lbl{font-size:12px;color:var(--faint);letter-spacing:.5px;margin-top:10px}
.ccard details{margin-top:9px;font-size:12.5px;color:var(--muted)}
.ccard details summary{cursor:pointer;color:var(--brand);font-size:12.5px;user-select:none}
.ccard details p,.ccard details li{font-size:12.5px;line-height:1.8;color:var(--muted);white-space:pre-line}
.ccard .clinks{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.ccard .go{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:999px;
  border:1px solid var(--brand);background:var(--info-bg);color:var(--brand);
  font-size:12px;font-weight:600;text-decoration:none;white-space:nowrap}
.ccard .go:hover{background:var(--brand-strong);color:var(--on-brand)}
.empty{display:none;text-align:center;color:var(--muted);padding:40px 0;font-size:14px}
.foot{margin-top:28px;font-size:12px;color:var(--faint);line-height:1.8}
@media (max-width:760px){.ccard .clinks .go{margin-top:4px}}
</style>
</head>
<body class="page-hns">
<a class="skip-link" href="#content0">跳到内容</a>
__TOPBAR__
<header class="page-head">
  <div class="wrap">
    <h1>克罗地亚评议 · Sudačka analiza</h1>
    <div class="sub">克罗地亚足协裁判委员会（Layec 署名）逐轮发布《Sudačka analiza》：逐判例给出「认定正确 / 认定错误」结论 + 技术考量 + 预期决定 + 每判例一段官方视频——全球公开源中与足协评议形态最接近的之一 · 克罗地亚语原文可折叠展开 · 版权归 HNS 所有</div>
    <div class="src-banner">__I_EXTERNAL__ 视频为 YouTube 官方页直链（不内嵌）；__SOURCE_LINK__ · 数据核对日期 __CHECKED__</div>
  </div>
</header>
<div class="wrap" id="content0">
  <div class="chips" data-chips>
    <button class="chip on" data-f="all">全部 <b>__N_ALL__</b></button>
    <button class="chip" data-f="correct">认定正确 <b>__N_OK__</b></button>
    <button class="chip" data-f="incorrect">认定错误 <b>__N_BAD__</b></button>
  </div>
  __SECTIONS__
  <p class="empty" id="emptyTip">没有匹配的判例。</p>
  <p class="foot">判例内容（克罗地亚语原文、认定结论与分析）版权归克罗地亚足球联合会 HNS 所有；本页收录结构化元数据、官方译制与 YouTube 官方页直链（来源 hns.family，核对日期 __CHECKED__）。中文译制为学习用途，欢迎对照克罗地亚语原文修订。栏目页仅露最新数轮，历史轮经种子表并入（fetch_hns.py SEED_IDS）。</p>
</div>
<script>
(function(){
  var chips=document.querySelectorAll("[data-chips] .chip");
  var cards=document.querySelectorAll(".ccard[data-verdict]");
  var years=document.querySelectorAll(".year-h[data-year]");
  chips.forEach(function(c){
    c.addEventListener("click",function(){
      chips.forEach(function(x){x.classList.remove("on");});
      c.classList.add("on");
      var f=c.getAttribute("data-f");
      var any=false;
      cards.forEach(function(a){
        var hit=f==="all"||a.getAttribute("data-verdict")===f;
        a.style.display=hit?"":"none";
        if(hit)any=true;
      });
      years.forEach(function(y){
        var body=document.getElementById("ybody-"+y.getAttribute("data-year"));
        var anyY=false;
        if(body)body.querySelectorAll(".ccard").forEach(function(a){if(a.style.display!=="none")anyY=true;});
        y.style.display=anyY?"":"none";
        if(body)body.style.display=anyY?"":"none";
      });
      var em=document.getElementById("emptyTip");
      if(em)em.style.display=any?"none":"";
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


def render_body(inc, zinc, rid):
    """判例正文：中文优先（1:1 对齐），克罗地亚语原文折叠。"""
    zparas = (zinc or {}).get("paras", [])
    en_paras = inc.get("paras", [])
    body = ""
    if zparas and len(zparas) == len(en_paras):
        body += '<div class="cbody">'
        ul_open = False
        for zp in zparas:
            if zp["k"] == "li" and not ul_open:
                body += "<ul>"
                ul_open = True
            if zp["k"] != "li" and ul_open:
                body += "</ul>"
                ul_open = False
            body += f"<li>{esc(zp['t'])}</li>" if zp["k"] == "li" else f"<p>{esc(zp['t'])}</p>"
        if ul_open:
            body += "</ul>"
        body += "</div>"
    else:
        print(f"⚠ hns-zh 缺判例译制或段数不齐（{rid}/inc{inc.get('no')}），回退克罗地亚语原文")
        body += '<div class="cbody">' + "".join(
            f'<p>{esc(ep["t"])}</p>' for ep in en_paras) + "</div>"
    if en_paras:
        orig = "".join(
            f"<p>{esc(ep['t'])}</p>" if ep["k"] == "p" else f"<li>{esc(ep['t'])}</li>"
            for ep in en_paras)
        orig = f"<ul>{orig}</ul>" if orig.startswith("<li>") else orig
        body += (f'<details><summary>克罗地亚语原文</summary>'
                 f'<div>{orig}</div></details>')
    return body


def build_page(data, zh):
    rounds = data.get("rounds", [])
    zrounds = (zh or {}).get("rounds", {})
    used = set()
    by_year = {}
    for r in rounds:
        zr = zrounds.get(str(r["id"]), {})
        used.add(str(r["id"]))
        y = (r.get("date") or "0000")[:4]
        if not y.isdigit():
            y = "其他"
        by_year.setdefault(y, []).append((r, zr))
    for k in zrounds:
        if k not in used:
            print(f"⚠ hns-zh rounds 键不在 hns.json 中（疑似过期）: {k}")
    n_ok = sum(1 for r in rounds for i in r["incidents"] if i.get("verdict") == "correct")
    n_bad = sum(1 for r in rounds for i in r["incidents"] if i.get("verdict") == "incorrect")
    years = sorted(by_year, reverse=True)
    secs = ""
    for y in years:
        rows = ""
        for r, zr in by_year[y]:
            ztitle = (zr or {}).get("title", "")
            body = ""
            for inc in r.get("incidents", []):
                zinc = (zr or {}).get("incidents", {}).get(str(inc.get("no")), {})
                vlabel, vbadge = VERDICT.get(inc.get("verdict", "other"), VERDICT["other"])
                info = [f"{inc['minute']}′" if inc.get("minute") else "",
                        f"主裁 {inc['referee']}" if inc.get("referee") else ""]
                if inc.get("type"):
                    tzh = (zinc or {}).get("type") or inc["type"]
                    info.insert(0, tzh)
                info_html = "".join(f'<span class="chip">{esc(v)}</span>' for v in info if v)
                links = "".join(
                    f'<a class="go" href="https://www.youtube.com/watch?v={esc(vid)}" target="_blank" '
                    f'rel="noopener noreferrer">{icon("play", 11)} 判例视频 {idx + 1}</a>'
                    for idx, vid in enumerate(inc.get("videos", [])))
                links += (f'<a class="go" href="{esc(r["url"])}" target="_blank" '
                          f'rel="noopener noreferrer">{icon("external", 11)} 官方分析</a>')
                body += f"""<div class="ccard" data-verdict="{esc(inc.get('verdict', 'other'))}">
  <div class="chead"><span class="cmatch">{esc(inc.get("match") or "判例 " + str(inc.get("no")))}</span>
    <span class="badge {vbadge}">{esc(vlabel)}</span></div>
  <div class="cinfo">{info_html}</div>
  {render_body(inc, zinc, r["id"])}
  <div class="clinks">{links}</div>
</div>"""
            rows += f"""<div class="round">
  <div class="round-h"><h2>{esc(ztitle or r["title"])}</h2>
    <div class="meta">{esc(r.get("date", ""))} · {len(r.get("incidents", []))} 个判例 · <a href="{esc(r["url"])}" target="_blank" rel="noopener noreferrer">{icon('external', 11)} 官方文章</a></div>
  </div>
  {body}
</div>"""
        secs += (f'<h3 class="year-h" data-year="{esc(y)}">{esc(y)} <small>'
                 f'{len(by_year[y])} 轮</small></h3><div id="ybody-{esc(y)}">{rows}</div>')
    tb = topbar(active="hns.html", stats="stats-2026.html", brand_sub="克罗地亚评议",
                seasons=("2026", "2025", "2024"))
    src_link = (f'<a href="{esc(data.get("source", ""))}" target="_blank" '
                f'rel="noopener noreferrer">hns.family 裁判栏目</a>')
    html = inject_theme(HTML
                        .replace("__TOPBAR__", tb)
                        .replace("__SOURCE_LINK__", src_link)
                        .replace("__I_EXTERNAL__", icon("external", 14))
                        .replace("__N_ALL__", str(n_ok + n_bad + sum(
                            1 for r in rounds for i in r["incidents"]
                            if i.get("verdict") == "other")))
                        .replace("__N_OK__", str(n_ok))
                        .replace("__N_BAD__", str(n_bad))
                        .replace("__CHECKED__", esc(data.get("fetched", "")))
                        .replace("__SECTIONS__", secs))
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "hns.html").write_text(html, encoding="utf-8")
    print(f"生成 {SITE / 'hns.html'}（{len(rounds)} 轮 / {n_ok + n_bad} 判例已归一认定）")


def main():
    if not HNS_JSON.exists():
        raise SystemExit(f"缺少 {HNS_JSON}；请先运行 fetch_hns.py")
    data = json.loads(HNS_JSON.read_text(encoding="utf-8"))
    zh = {}
    if HNS_ZH_JSON.exists():
        zh = json.loads(HNS_ZH_JSON.read_text(encoding="utf-8"))
    else:
        print("⚠ 缺少 hns-zh.json，正文将显示克罗地亚语原文")
    build_page(data, zh)


if __name__ == "__main__":
    main()
