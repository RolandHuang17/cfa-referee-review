# -*- coding: utf-8 -*-
"""解码官方"统一判罚尺度"宣讲包（2025/2026）→ data/scale.json + site/scale.html
原包 highlight 页为 document.write(unescape("%...")) 编码; 解码后提取:
  编号/场景名, 视频文件, 视频说明, 判罚决定矩阵(激活项), Reason
两代包的矩阵激活标记不同: 2026 用 <p style="color:grey">(灰=未激活),
2025 用前置图标 <img .../t.jpg>=激活 / c.jpg=未激活; 2025 VAR 页判罚为英文标签。
视频复制到 site/videos/scale/{year}/, 海报到 assets/scale/{year}-*.png。
原包路径见 PACKAGES; 不在仓库内(第三方库会被安全钩子拦截), 缺失时复用已提取的 data/scale.json。
"""
import json
import re
import shutil
from pathlib import Path
from urllib.parse import unquote

from theme import inject_theme, topbar

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT_JSON = ROOT / "data" / "scale.json"
VID_OUT = ROOT / "site" / "videos" / "scale"
IMG_OUT = ROOT / "assets" / "scale"  # build_all 会整目录重建 site/assets，海报须放根 assets/
def PKG_IMG(year):
    return IMG_OUT  # 海报平铺: assets/scale/{year}-{cat}-{series}-{id}.png

PACKAGES = {
    "2026": ROOT.parent / "统一尺度宣讲原始包-2026",
    "2025": ROOT / "2025-中国足球协会判罚统一尺度（Win版）",
}
SERIES_NAMES = {"highlights": "判罚案例", "reckless": "纪律处罚", "var": "VAR 视频助理裁判",
                "tam": "战术犯规"}
EN2CN = {"No Foul": "不犯规", "No Card": "不出牌", "Indirect Free Kick": "间接任意球",
         "Direct Free Kick": "直接任意球", "Penalty Kick": "罚球点球", "Yellow Card": "黄牌",
         "Red Card": "红牌", "Goal": "进球", "Penalty": "罚球点球"}

# 分组排序（同组按场景名聚合）

def decode_page(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'document\.write\(unescape\("([^"]+)"\)\)', raw)
    return unquote(m.group(1)) if m else raw


def clean(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def parse_matrix(body: str, after_kw: str):
    """判罚决定矩阵: 兼容两代标记。返回与原文顺序一致的 [{label, active}]。"""
    seg = body.split(after_kw)[-1]
    acts = []
    for table in re.findall(r"<table[\s\S]*?</table>", seg):
        if "<p" not in table:
            continue
        use_img = bool(re.search(r'img[^>]*src="[^"]*/(?:t|c)\.jpg', table))
        last_img = None
        for cell in re.findall(r"<td[^>]*>([\s\S]*?)</td>", table):
            img = re.search(r'src="[^"]*/(t|c)\.jpg', cell)
            if img:
                last_img = img.group(1)
            p = re.search(r"<p[^>]*>([^<]+)</p>", cell)
            if not p:
                continue
            label = p.group(1).strip()
            label = EN2CN.get(label, label)
            if not label:
                continue
            if use_img:
                active = last_img == "t"
            else:
                active = "color:grey" not in cell
            acts.append({"label": label, "active": active})
    return acts


def parse_note(body: str):
    """视频说明: '视频说明'标题后的第一段实质文本(p 或无样式的 h2)"""
    seg = body.split("视频说明")[-1]
    for m in re.finditer(r"<(p|h2)([^>]*)>([^<]{15,})</", seg):
        if "color:#fff" in m.group(2) or "color: #fff" in m.group(2):
            continue  # 面板标题
        return m.group(3).strip()
    return ""


def parse_highlight(path: Path, year: str, cat: str, series: str):
    body = decode_page(path)
    hl_id = path.stem
    m = re.search(r"<h1[^>]*>\s*([^<]*?)\s*</h1>", body)
    title = re.sub(r"\s+", " ", m.group(1)).strip() if m else hl_id
    title = re.sub(r"^[A-Z]*\d+\s*-\s*", "", title)  # 去"A1 - "/"1 - "编号前缀（文件号与标题号可能错位）
    if title == hl_id or not title:  # VAR 等无名页
        title = f"场景 {hl_id}"
    vm = re.search(r'<source[^>]*src="([^"]+\.mp4)"', body)
    reason = ""
    rm = re.search(r'<h2>\s*Reason\s*</h2>([\s\S]*?)</div>', body)
    if rm:
        reason = clean(rm.group(1))
    fname = f"{series}-{hl_id}"
    return {"id": hl_id, "series": series, "title": title,
            "note": parse_note(body),
            "decision": parse_matrix(body, "判罚决定") or parse_matrix(body, "Decision"),
            "reason": reason,
            "video": f"videos/scale/{year}/{fname}.mp4",
            "poster": f"assets/scale/{year}-{cat}-{fname}.png"}, \
           (PKG_VID(year) / f"{fname}.mp4", PKG_IMG(year) / f"{year}-{cat}-{fname}.png")


def PKG_VID(year):
    return VID_OUT / year


def extract_season(year: str, pkg: Path):
    cats = []
    cat_root = pkg / "files" / "categories"
    for cat_dir in sorted(p for p in cat_root.iterdir() if p.is_dir()):
        groups = {}
        order = []
        for series_dir in sorted(p for p in cat_dir.iterdir() if p.is_dir()):
            series = series_dir.name
            name = SERIES_NAMES.get(series, series)
            for p in sorted(series_dir.glob("*.html"),
                            key=lambda x: int(x.stem) if x.stem.isdigit() else 999):
                item, files = parse_highlight(p, year, cat_dir.name, series)
                # 分组键：VAR 无名页归入"视频助理裁判"组
                gkey = item["title"]
                if series == "var" and re.match(r"^场景 \d+$", gkey):
                    gkey = "视频助理裁判"
                    item["title"] = f"VAR 场景 {p.stem}"
                (VID_OUT / year).mkdir(parents=True, exist_ok=True)
                (IMG_OUT).mkdir(parents=True, exist_ok=True)
                src_mp4 = series_dir / f"{p.stem}.mp4"
                src_png = series_dir / f"{p.stem}.png"
                if src_mp4.exists():
                    shutil.copy2(src_mp4, files[0])
                if src_png.exists():
                    shutil.copy2(src_png, files[1])
                if gkey not in groups:
                    groups[gkey] = {"name": gkey, "items": []}
                    order.append(gkey)
                groups[gkey]["items"].append(item)
        cats.append({"key": cat_dir.name,
                     "name": "犯规与不正当行为" if cat_dir.name == "fouls-misconduct" else cat_dir.name,
                     "groups": [groups[k] for k in order]})
    return {"sections": cats}


def legacy_migrate():
    """旧 v1 数据/文件迁移到按年分目录结构"""
    if OUT_JSON.exists():
        d = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        if "sections" not in d.get("2026", {}):
            OUT_JSON.unlink()
    for flat in VID_OUT.glob("*.mp4"):  # 旧平铺 2026 视频 → 2026/
        (VID_OUT / "2026").mkdir(parents=True, exist_ok=True)
        flat.rename(VID_OUT / "2026" / f"highlights-{flat.stem}.mp4")
    # 旧海报拍平为 {year}- 前缀（含历史遗留的年份子目录）
    for old in list(IMG_OUT.glob("fouls-misconduct-*.png")):
        old.rename(IMG_OUT / f"2026-{old.name}")
    for sub in ("2026", "2025"):
        d = IMG_OUT / sub
        if d.is_dir():
            for f in d.iterdir():
                name = f.name if f.name.startswith(sub) else f"{sub}-{f.name}"
                f.rename(IMG_OUT / name)
            d.rmdir()


# 分组排序（同组按场景名聚合）
GROUP_ORDER = ["争抢", "战术犯规", "手球", "手球犯规", "罚球区事件", "罚球区内手球犯规",
               "球点球时的侵入", "越位", "越位犯规", "比赛管理", "视频助理裁判", "25/26规则变更"]
DECISION_ORDER = ["不犯规", "间接任意球", "直接任意球", "罚球点球", "不出牌", "黄牌", "红牌",
                  "不越位犯规", "干扰比赛", "越位犯规", "干扰对方队员", "越位位置获得利益"]


def sort_groups(groups):
    def key(g):
        return (GROUP_ORDER.index(g["name"]) if g["name"] in GROUP_ORDER else len(GROUP_ORDER), g["name"])
    return sorted(groups, key=key)


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>中国足协统一判罚尺度 · 官方宣讲合集</title>
<style>
/* ===== scale 页专属布局 (tokens/组件来自 data-cfa-theme) ===== */
.page-head{border-bottom:1px solid var(--line);background:var(--bg2)}
.page-head .wrap{max-width:1180px;margin:0 auto;padding:22px 16px 16px}
.page-head h1{margin:0 0 4px;font-family:var(--font-display);font-size:23px;letter-spacing:.4px}
.page-head .sub{color:var(--muted);font-size:13px}
.season-tabs{display:flex;gap:8px;margin-top:14px}
.season-tab{padding:7px 18px;border-radius:999px;border:1px solid var(--line);
  background:var(--card);color:var(--ink2);font-size:13.5px;cursor:pointer;font-family:inherit}
.season-tab.on{background:var(--ink);border-color:var(--ink);color:var(--bg);font-weight:600}
.layout{max-width:1180px;margin:0 auto;padding:18px 16px 60px;display:grid;
  grid-template-columns:216px minmax(0,1fr);gap:20px;align-items:start}
.sblock{display:none}
.sblock.on{display:block}
.gnavs{position:sticky;top:calc(var(--top-h) + 14px);display:flex;flex-direction:column;gap:4px}
.gnavs .gh{font-size:11px;font-weight:700;color:var(--muted);letter-spacing:2px;margin:2px 4px 6px}
.gnav{display:flex;align-items:center;gap:7px;padding:7px 10px;border-radius:var(--r-sm);
  color:var(--ink2);text-decoration:none;font-size:13.5px;border:1px solid var(--line);transition:.12s}
.gnav b{margin-left:auto;font-size:11px;color:var(--muted);font-weight:600}
.gnav:hover{background:var(--card2);border-color:var(--brand);color:var(--ink)}
.gcontent{min-width:0}
.gsec{margin-bottom:34px}
.gsec h2{font-family:var(--font-display);font-size:19px;margin:0 0 12px;letter-spacing:.4px}
.gsec h2 b{font-size:13px;color:var(--brand);font-weight:600;margin-left:6px}
.hcard{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:16px 18px;margin-bottom:16px}
.hhead{display:flex;align-items:center;gap:9px;margin-bottom:10px}
.hid{font-family:var(--font-display);font-size:13px;font-weight:700;color:var(--brand);
  border:1px solid var(--line);border-radius:6px;padding:1px 9px;background:var(--card2)}
.hhead h3{margin:0;font-size:16.5px;font-weight:600}
.hvideo video{width:100%;max-width:880px;aspect-ratio:16/9;background:#000;
  border-radius:var(--r-md);display:block}
.hnote{font-size:14.5px;line-height:1.9;margin:12px 0 0;text-indent:2em}
.drow{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:11px}
.dlbl{font-size:12px;color:var(--muted);letter-spacing:1px;margin-right:4px}
.dchip{padding:2.5px 11px;border-radius:999px;border:1px solid var(--line);
  color:var(--faint);font-size:12px;background:var(--card2)}
.dchip.on{background:var(--info-bg);border-color:var(--brand);color:var(--brand);font-weight:700}
.hreason{font-size:12px;color:var(--faint);margin:9px 0 0}
@media (max-width:900px){
  .layout{grid-template-columns:minmax(0,1fr)}
  .gnavs{position:static;flex-direction:row;flex-wrap:wrap}
  .gnavs .gh{flex-basis:100%}
}
</style>
</head>
<body class="page-scale">
<a class="skip-link" href="#content0">跳到内容</a>
__TOPBAR__
<header class="page-head">
  <div class="wrap">
    <h1>中国足协统一判罚尺度 · 官方宣讲合集</h1>
    <div class="sub">内容取自中国足协官方《统一判罚尺度》宣讲材料 · 每例含官方视频片段、视频说明与判罚决定 · 版权归中国足协所有</div>
    <div class="season-tabs" role="tablist">__TABS__</div>
  </div>
</header>
<div class="layout">
  <aside class="gnavs" aria-label="场景分组" data-navs>__NAVS__</aside>
  <div class="gcontent">__SECS__</div>
</div>
<script>
(function(){
  var tabs = document.querySelectorAll(".season-tab");
  var blocks = document.querySelectorAll(".sblock");
  tabs.forEach(function(t){
    t.addEventListener("click", function(){
      tabs.forEach(function(x){ x.classList.toggle("on", x === t); });
      blocks.forEach(function(b){ b.classList.toggle("on", b.dataset.season === t.dataset.season); });
      try { history.replaceState(null, "", "#s" + t.dataset.season); } catch(_) {}
    });
  });
})();
</script>
</body>
</html>
"""


def build_page(data):
    seasons = sorted(data.keys(), reverse=True)
    tabs = "".join(
        f'<button class="season-tab{" on" if i == 0 else ""}" role="tab" data-season="{s}"'
        f' aria-selected="{str(i == 0).lower()}">{s} 赛季</button>'
        for i, s in enumerate(seasons))
    navs, secs = "", ""
    for i, s in enumerate(seasons):
        nav, sec = "", ""
        for si, secdata in enumerate(data[s]["sections"]):
            for gi, g in enumerate(secdata["groups"]):
                anchor = f"s{s}-{si}-{gi}"
                nav += (f'<a class="gnav" href="#{anchor}">{g["name"]}'
                        f'<b>{len(g["items"])}</b></a>')
                cards = ""
                for h in g["items"]:
                    chips = "".join(
                        f'<span class="dchip{" on" if d["active"] else ""}">{d["label"]}</span>'
                        for d in sorted(h["decision"],
                                        key=lambda x: DECISION_ORDER.index(x["label"])
                                        if x["label"] in DECISION_ORDER else 99))
                    cards += f"""<article class="hcard" id="h{s}-{h['series']}-{h['id']}">
  <div class="hhead"><span class="hid">{h['id']}</span><h3>{h['title']}</h3></div>
  <div class="hvideo"><video controls preload="none" poster="{h['poster']}"><source src="{h['video']}" type="video/mp4"></video></div>
  <p class="hnote">{h['note']}</p>
  <div class="drow"><span class="dlbl">判罚决定</span>{chips}</div>
  {f'<p class="hreason">Reason: {h["reason"]}</p>' if h['reason'] else ''}
</article>"""
                sec += (f'<section class="gsec" id="{anchor}">'
                        f'<h2>{g["name"]} <b>{len(g["items"])}例</b></h2>{cards}</section>')
        navs += f'<div class="gnavcol sblock{" on" if i == 0 else ""}" data-season="{s}">{nav}</div>'
        secs += f'<div class="sblock{" on" if i == 0 else ""}" data-season="{s}" id="content{i}">{sec}</div>'
    tb = topbar(active="scale.html", stats="stats-2026.html", brand_sub="统一判罚尺度",
                seasons=("2024", "2025", "2026"))
    html = inject_theme(HTML.replace("__TOPBAR__", tb)
                        .replace("__TABS__", tabs).replace("__NAVS__", navs)
                        .replace("__SECS__", secs))
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "scale.html").write_text(html, encoding="utf-8")
    n = sum(len(g["items"]) for s in seasons for sec in data[s]["sections"] for g in sec["groups"])
    print(f"生成 {SITE / 'scale.html'}（{'/'.join(seasons)} 共 {n} 例）")


def main():
    legacy_migrate()
    data = {}
    if OUT_JSON.exists():
        d = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        data = {k: v for k, v in d.items() if isinstance(v, dict) and "sections" in v}
    for year, pkg in PACKAGES.items():
        if pkg.exists():
            data[year] = extract_season(year, pkg)
        elif year not in data:
            print(f"跳过 {year}: 原包缺失且无已提取数据")
    for year in data:  # 组排序
        for sec in data[year]["sections"]:
            sec["groups"] = sort_groups(sec["groups"])
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    build_page(data)


if __name__ == "__main__":
    main()
