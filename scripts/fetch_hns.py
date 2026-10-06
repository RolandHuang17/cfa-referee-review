# -*- coding: utf-8 -*-
"""抓取克罗地亚足协 HNS《Sudačka analiza》逐轮判例分析 → data/hns.json
（提交进仓库，build_hns.py 据此生成 site/hns.html；中文译制层 data/hns-zh.json）

用法: python fetch_hns.py [fetch|parse|all]   (默认 all)

数据源：hns.family/hns/suci 裁判栏目列表（仅最新数篇；页面不支持翻页）+
SEED_IDS 种子表（人工发现的历史轮文章 ID 固化于此，增量合并只增不减）。
每轮文章由裁判委员会（Layec 署名）发布，逐判例给出「正确/错误」认定：
- 判例头 `<p><strong>Situacija br. N: 对阵 (sudac X, N. minuta): 类型</strong></p>`
- 判例后跟 YouTube 官方视频 iframe（每判例一段）
- 分析段落 + "Slijedom naših tehničkih smjernica:" 要点行（"- " 前缀）
- 认定句：ispravnom=正确 / neispravnom=错误（负向断言防误配）
- 正文止于版权段（"Autorska prava"）
"""
import html as htmllib
import json
import re
import sys
import time

from lib.safe_http import fetch_text

from lib.paths import HNS_CACHE, HNS_JSON

LIST_URL = "https://hns.family/hns/suci"
DELAY = (2.0, 4.0)
BACKOFFS = [20, 60]
MIN_LIST = 50000
MIN_ART = 30000
# 历史轮种子（栏目页只露最新数篇；发现旧文后把 ID 加进来即可自动并入）
SEED_IDS = [30802]

CLEAN_RE = re.compile(r"<[^>]+>")


def clean(s: str) -> str:
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def fetch_url(url: str, minlen: int, slug: str) -> str:
    HNS_CACHE.mkdir(parents=True, exist_ok=True)
    cache_f = HNS_CACHE / f"{slug}.html"
    if cache_f.exists() and cache_f.stat().st_size > minlen:
        return cache_f.read_text(encoding="utf-8", errors="replace")
    for wait in [0] + BACKOFFS:
        if wait:
            time.sleep(wait)
        try:
            st, txt = fetch_text(url, timeout=45, retries=2)
            if st == 200 and len(txt) > minlen:
                cache_f.write_text(txt, encoding="utf-8")
                return txt
            if st == 404:
                return ""
        except Exception:  # noqa: BLE001
            pass
    return ""


def parse_listing(html: str) -> list:
    """栏目页 → [{id, slug, title, date}]（title 取锚点 title 属性，日期取卡内首个日期）"""
    i = html.find("newsList")
    seg = html[i:] if i != -1 else html
    out = {}
    for m in re.finditer(
            r'href="(?:https://hns\.family)?/vijesti/(\d+)/([^"]+)/"\s+title="([^"]+)"(.{0,900}?)</a>', seg, re.S):
        pid, slug, title, tail = m.group(1), m.group(2), clean(m.group(3)), m.group(4)
        if pid in out:
            continue
        dm = re.search(r"(\d{2}\.\d{2}\.\s*20\d\d)", tail)
        date = ""
        if dm:
            d, mo, y = re.match(r"(\d{2})\.(\d{2})\.\s*(20\d\d)", dm.group(1)).groups()
            date = f"{y}-{mo}-{d}"
        out[pid] = {"id": pid, "slug": slug, "title": title, "date": date}
    return list(out.values())


def split_paras(chunk: str) -> list:
    """判例块 <p> 文本 → 行列表（"- " 前缀行拆为要点项）"""
    paras = []
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", chunk, re.S):
        raw = re.sub(r"<[^>]+>", "\n", m.group(1))
        raw = htmllib.unescape(raw).replace("\xa0", " ")
        raw = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", raw)  # 零宽/不可见字符
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("-"):
                line = re.sub(r"^[-–—]\s*", "", line).strip()
                if line:
                    paras.append({"k": "li", "t": re.sub(r"\s+", " ", line)})
            else:
                t = re.sub(r"\s+", " ", line)
                if t:
                    paras.append({"k": "p", "t": t})
    return paras


def parse_article(pid: str, html: str) -> dict | None:
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    title = clean(h1.group(1)) if h1 else ""
    if "analiza" not in title.lower():
        return None
    dm = re.search(r'<div class="date"><h3>(\d{2})\.(\d{2})\.(20\d\d)\.', html)
    date = f"{dm.group(3)}-{dm.group(2)}-{dm.group(1)}" if dm else ""
    rm = re.search(r"(\d+)\.\s*kola", title)
    # 正文区：RELATED ARTICLES 之后、版权段之前
    start = html.find("RELATED ARTICLES")
    body = html[start:] if start != -1 else html
    end = body.find("Autorska prava")
    if end != -1:
        body = body[:end]
    # 逐判例切分
    marks = [(m.start(), m.end(), m.group(1)) for m in
             re.finditer(r"<p[^>]*>\s*<strong>\s*Situacija br\.\s*(\d+)", body)]
    incidents = []
    for i, (s, hdr_end, no) in enumerate(marks):
        chunk_end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        chunk = body[s:chunk_end]
        hm = re.search(r"Situacija br\.\s*\d+\s*:\s*(.+?)</strong>", chunk, re.S)
        head = clean(hm.group(1)) if hm else ""
        match = minute = referee = typ = ""
        pm = re.match(r"(.*?)\s*\(([^)]*)\)\s*[:：;]\s*(.+)$", head)
        if pm:
            match, inner, typ = pm.group(1).strip(), pm.group(2).strip(), pm.group(3).strip()
            rm2 = re.search(r"sudac\s+([^,)]+)", inner)
            referee = rm2.group(1).strip() if rm2 else ""
            mm = re.search(r"(\d+)\.\s*minuta", inner)
            minute = mm.group(1) if mm else ""
        else:
            match, typ = head, ""
        videos = re.findall(r"youtube\.com/embed/([-\w]{11})", chunk)
        paras = [p for p in split_paras(chunk) if not p["t"].startswith("Situacija br.")]
        verdict = "other"
        vtext = " ".join(p["t"] for p in paras)
        # 判定归一：委员会句式（顺序敏感）——错误在先（否定词干扰用负向断言防误配）
        if re.search(r"neispravnom|neispravna|neispravno", vtext, re.I):
            verdict = "incorrect"
        elif re.search(r"trebao intervenirati", vtext, re.I):
            verdict = "incorrect"   # VAR 本应介入而未介入
        elif re.search(r"predstavlja .{0,40}pogrešk", vtext, re.I):
            verdict = "incorrect"   # 构成清晰明显错误
        elif re.search(r"podržava|ispravno primijenjeno|(?<!ne)ispravno|(?<!ne)ispravnom|(?<!ne)ispravna",
                       vtext, re.I):
            verdict = "correct"
        elif re.search(r"ne pokazuje .{0,40}pogrešk", vtext, re.I):
            verdict = "correct"     # 录像未显示清晰明显错误
        incidents.append({"no": int(no), "match": match, "referee": referee, "minute": minute,
                          "type": typ, "videos": videos, "paras": paras, "verdict": verdict})
    return {"id": pid, "title": title, "date": date,
            "round": int(rm.group(1)) if rm else 0,
            "url": f"https://hns.family/vijesti/{pid}/",
            "incidents": incidents}


def parse_all():
    prev = {}
    if HNS_JSON.exists():
        try:
            old = json.loads(HNS_JSON.read_text(encoding="utf-8"))
            prev = {r["id"]: r for r in old.get("rounds", [])}
        except Exception:  # noqa: BLE001
            prev = {}
    # 枚举：栏目页 + 种子
    found = {}
    lhtml = fetch_url(LIST_URL, MIN_LIST, "suci")
    if lhtml:
        for a in parse_listing(lhtml):
            if "analiza" in a["title"].lower():
                found[a["id"]] = a
        print(f"栏目页: {len(found)} 篇判例分析", flush=True)
    else:
        print("⚠ 栏目页抓取失败", flush=True)
    for pid in SEED_IDS:
        if pid not in found:
            found[pid] = {"id": str(pid), "slug": "", "title": "", "date": ""}
    rounds = []
    for pid, meta in sorted(found.items(), key=lambda kv: -int(kv[0])):
        pid = str(pid)
        html = fetch_url(f"https://hns.family/vijesti/{pid}/", MIN_ART, pid)
        if not html:
            print(f"⚠ 文章抓取失败，跳过: {pid}", flush=True)
            continue
        r = parse_article(pid, html)
        if not r:
            print(f"⚠ 非判例分析文章，跳过: {pid}", flush=True)
            continue
        if not r["date"]:
            r["date"] = meta.get("date", "")
        if pid in prev:  # 增量合并（字段级保底）
            for k, v in prev[pid].items():
                if not r.get(k) and v:
                    r[k] = v
        rounds.append(r)
        print(f"  {pid} 「{r['title'][:46]}」 {r['date']} 判例 {len(r['incidents'])} 个 "
              f"视频 {sum(len(i['videos']) for i in r['incidents'])} 段", flush=True)
        time.sleep(2.0)
    rounds.sort(key=lambda x: x.get("date") or "0000", reverse=True)
    data = {"source": LIST_URL,
            "source_name": "克罗地亚足协 HNS《Sudačka analiza》逐轮判例分析（Sudačka komisija / Layec）",
            "fetched": time.strftime("%Y-%m-%d"),
            "rounds": rounds}
    HNS_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    n_inc = sum(len(r["incidents"]) for r in rounds)
    n_vid = sum(len(i["videos"]) for r in rounds for i in r["incidents"])
    verd = {}
    for r in rounds:
        for i in r["incidents"]:
            verd[i["verdict"]] = verd.get(i["verdict"], 0) + 1
    print(f"parse 完成: {len(rounds)} 轮 / {n_inc} 判例 / {n_vid} 视频 / 认定分布 {verd} → {HNS_JSON}", flush=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("fetch", "parse", "all"):
        parse_all()
    else:
        raise SystemExit("用法: fetch_hns.py [fetch|parse|all]")


if __name__ == "__main__":
    main()
