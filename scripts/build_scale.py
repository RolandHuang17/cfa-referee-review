# -*- coding: utf-8 -*-
"""解码官方"2026赛季中国足协统一判罚尺度"宣讲包 → data/scale.json
原包 highlight 页为 document.write(unescape("%...")) 编码; 解码后提取:
  编号/场景名, 视频文件, 视频说明, 判罚决定矩阵(激活项), Reason
同时把 mp4 复制到 site/videos/scale/, png 海报到 assets/scale/。
"""
import json
import re
import shutil
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PKG = ROOT / "2026赛季中国足协统一尺度"
CAT = PKG / "files" / "categories"
OUT_JSON = ROOT / "data" / "scale.json"
VID_OUT = ROOT / "site" / "videos" / "scale"
IMG_OUT = ROOT / "assets" / "scale"  # build_all 会整目录重建 site/assets，海报须放根 assets/


def decode_page(path: Path) -> str:
    """document.write(unescape("%...")) → 解码后的完整 HTML"""
    raw = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'document\.write\(unescape\("([^"]+)"\)\)', raw)
    if not m:
        return raw  # 未编码页原样返回
    return unquote(m.group(1))


def clean(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def parse_matrix(body: str):
    """判罚决定矩阵: 返回激活项列表(灰色=未激活)"""
    acts = []
    for table in re.findall(r"<table[\s\S]*?</table>", body):
        for td in re.findall(r"<td[^>]*>\s*(<p[^>]*>.*?</p>)\s*</td>", table, re.S):
            p = td
            text = clean(p)
            if not text:
                continue
            active = "color:grey" not in p and "color: grey" not in p
            acts.append({"label": text, "active": active})
    return acts


def parse_highlight(path: Path):
    body = decode_page(path)
    hl_id = path.stem
    m = re.search(r"<h1[^>]*>\s*([^<]*?)\s*</h1>", body)
    title = clean(m.group(1)) if m else hl_id
    title = re.sub(rf"^{hl_id}\s*-\s*", "", title)
    # 视频说明: slidingDiv 内第一个带 text-indent 的 <p>
    cm = re.search(r'视频说明</h1>.*?<p[^>]*>([^<]+)</p>', body, re.S)
    note = cm.group(1).strip() if cm else ""
    vm = re.search(r'<source[^>]*src="([^"]+\.mp4)"', body)
    video = vm.group(1) if vm else ""
    reason = ""
    rm = re.search(r'<h2>\s*Reason\s*</h2>([\s\S]*?)</div>', body)
    if rm:
        reason = clean(rm.group(1))
    matrix = parse_matrix(body.split("判罚决定")[-1]) if "判罚决定" in body else []
    return {"id": hl_id, "title": title, "video": video, "note": note,
            "reason": reason, "decision": matrix}


# 分组规范名（按片段编号前缀）
GROUPS = [
    ("A", "争抢"), ("B", "战术犯规"), ("C", "手球"), ("D", "罚球区事件"),
    ("E", "比赛管理"), ("F", "越位"), ("G", "视频助理裁判"), ("H", "25/26规则变更"),
]
DECISION_ORDER = ["不犯规", "间接任意球", "直接任意球", "罚球点球", "不出牌", "黄牌", "红牌"]

from theme import inject_theme, icon, topbar

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>2026赛季中国足协统一判罚尺度 · 官方宣讲</title>
<style>
/* ===== scale 页专属布局 (tokens/组件来自 data-cfa-theme) ===== */
.page-head{border-bottom:1px solid var(--line);background:var(--bg2)}
.page-head .wrap{padding-top:22px;padding-bottom:16px;max-width:1180px;margin:0 auto;padding-left:16px;padding-right:16px}
.page-head h1{margin:0 0 4px;font-family:var(--font-display);font-size:23px;letter-spacing:.4px}
.page-head .sub{color:var(--muted);font-size:13px}
.layout{max-width:1180px;margin:0 auto;padding:18px 16px 60px;display:grid;
  grid-template-columns:216px minmax(0,1fr);gap:20px;align-items:start}
.gnavs{position:sticky;top:calc(var(--top-h) + 14px);display:flex;flex-direction:column;gap:4px}
.gnavs .gh{font-size:11px;font-weight:700;color:var(--muted);letter-spacing:2px;margin:2px 4px 6px}
.gnav{display:flex;align-items:center;gap:7px;padding:7px 10px;border-radius:var(--r-sm);
  color:var(--ink2);text-decoration:none;font-size:13.5px;border:1px solid transparent;transition:.12s}
.gnav b{margin-left:auto;font-size:11px;color:var(--muted);font-weight:600}
.gnav span{color:var(--muted);font-size:12.5px}
.gnav:hover{background:var(--card2);color:var(--ink)}
.gnavs .gnav{border-color:var(--line)}
.gnavs .gnav:hover{border-color:var(--brand)}
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
.hempty{padding:40px;text-align:center;color:var(--muted)}
@media (max-width:900px){
  .layout{grid-template-columns:minmax(0,1fr)}
  .gnavs{position:static;flex-direction:row;flex-wrap:wrap}
  .gnavs .gh{flex-basis:100%}
}
</style>
</head>
<body class="page-scale">
<a class="skip-link" href="#gA">跳到内容</a>
__TOPBAR__
<header class="page-head">
  <div class="wrap">
    <h1>2026赛季中国足协统一判罚尺度 · 官方宣讲</h1>
    <div class="sub">内容取自中国足协官方《2026赛季中国足协统一判罚尺度》宣讲材料 · 每例含官方视频片段、视频说明与判罚决定 · 27例 · 版权归中国足协所有</div>
  </div>
</header>
<div class="layout">
  <aside class="gnavs" aria-label="场景分组">
    <div class="gh">场景分组</div>
    __GROUPS__
  </aside>
  <div class="gcontent">
    __SECS__
    <div class="hempty" style="padding-top:10px;font-size:12.5px">宣讲材料持续更新，更多分类以官方发布为准。视频文件请置于 videos/scale/ 文件夹。</div>
  </div>
</div>
</body>
</html>
"""


def build_page(data):
    cats = {k: v for k, v in data.items() if isinstance(v, dict) and "highlights" in v}
    groups = []
    for gid, gname in GROUPS:
        items = [h for h in cats["fouls-misconduct"]["highlights"] if h["id"].startswith(gid)]
        if items:
            groups.append((gid, gname, items))

    nav = "".join(
        f'<a class="gnav" href="#g{gid}">{gid} <span>{gname}</span><b>{len(items)}</b></a>'
        for gid, gname, items in groups)
    secs = ""
    for gid, gname, items in groups:
        cards = ""
        for h in items:
            chips = "".join(
                f'<span class="dchip{" on" if d["active"] else ""}">{d["label"]}</span>'
                for d in sorted(h["decision"], key=lambda x: DECISION_ORDER.index(x["label"])
                                if x["label"] in DECISION_ORDER else 99))
            src = f"videos/scale/{h['id']}.mp4"
            poster = f"assets/scale/fouls-misconduct-{h['id']}.png"
            cards += f"""<article class="hcard" id="h{h['id']}">
  <div class="hhead"><span class="hid">{h['id']}</span><h3>{h['title']}</h3></div>
  <div class="hvideo"><video controls preload="none" poster="{poster}"><source src="{src}" type="video/mp4"></video></div>
  <p class="hnote">{h['note']}</p>
  <div class="drow"><span class="dlbl">判罚决定</span>{chips}</div>
  {f'<p class="hreason">Reason: {h["reason"]}</p>' if h['reason'] else ''}
</article>"""
        secs += f'<section class="gsec" id="g{gid}"><h2>{gid} · {gname} <b>{len(items)}例</b></h2>{cards}</section>'

    html = inject_theme(HTML
            .replace("__TOPBAR__", topbar(active="scale.html", stats="stats-2026.html",
                                          brand_sub="统一判罚尺度", seasons=("2024", "2025", "2026")))
            .replace("__GROUPS__", nav).replace("__SECS__", secs))
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "scale.html").write_text(html, encoding="utf-8")
    print(f"生成 {SITE / 'scale.html'}")


def main():
    cats = {}
    if PKG.exists():
        for cat_dir in sorted(CAT.iterdir()):
            if not cat_dir.is_dir():
                continue
            name = cat_dir.name
            info = {}
            for f, key in (("contents.html", "contents"), ("cat.html", "cat"), ("can.html", "can")):
                p = cat_dir / f
                if p.exists():
                    body = decode_page(p)
                    body = re.sub(r"<style[\s\S]*?</style>", "", body)
                    info[key] = clean(body)[:600]
            hls = []
            hdir = cat_dir / "highlights"
            if hdir.exists():
                for p in sorted(hdir.glob("*.html"), key=lambda x: (len(x.stem), x.stem)):
                    hls.append(parse_highlight(p))
                    src_mp4 = hdir / f"{p.stem}.mp4"
                    src_png = hdir / f"{p.stem}.png"
                    if src_mp4.exists():
                        VID_OUT.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_mp4, VID_OUT / src_mp4.name)
                    if src_png.exists():
                        IMG_OUT.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_png, IMG_OUT / f"{name}-{p.stem}.png")
            cats[name] = {"info": info, "highlights": hls}
            print(f"[{name}] {len(hls)} 条片段")
        OUT_JSON.write_text(json.dumps(cats, ensure_ascii=False, indent=1), encoding="utf-8")

    if not OUT_JSON.exists():
        print("跳过 scale.html: 无宣讲包且无 data/scale.json")
        return
    build_page(json.loads(OUT_JSON.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
