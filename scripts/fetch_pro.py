# -*- coding: utf-8 -*-
"""抓取美国 PRO（Professional Referee Organization）裁判评议周报索引 → data/pro.json
（提交进仓库，build_pro.py 据此生成 site/pro.html）

用法: python fetch_pro.py [fetch|parse|all]   (默认 all)
- fetch: 逐页抓取两个分类的列表页（Inside Video Review 含西语 VAR a Fondo；
  The Definitive Angle 文字判例），缓存 data/local/pro-cache/（断点续抓）
- parse: 纯本地从缓存解析写 data/pro.json

PRO 为普通 WordPress 博客（无 tarpit），周更：MLS/NWSL 每轮一篇 VAR 评析
（Inside Video Review，西语同名系列 VAR a Fondo）+ 文字判例（The Definitive Angle）。
v1 只抓列表页元数据（标题/日期/系列/联赛/轮次/链接），文章内嵌视频一律跳官方页。
"""

import html as htmllib
import json
import random
import re
import sys
import time

from lib.atomic_json import write_json
from lib.source_cache import SourceCache

from lib.paths import PRO_CACHE, PRO_JSON

CACHE_READER = SourceCache()

BASE = "https://proreferees.com"
CATEGORIES = [
    ("inside-video-review", "Inside Video Review（VAR 评析·英）", "ivr"),
    ("the-definitive-angle", "The Definitive Angle（文字判例）", "angle"),
]
DELAY = (1.5, 3.0)
MAX_PAGES = 30  # 每个分类最多翻页数（防御）
MIN_BODY = 20000
BACKOFFS = [20, 60]

CLEAN_RE = re.compile(r"<[^>]+>")


def clean(text: str) -> str:
    return htmllib.unescape(re.sub(r"\s+", " ", CLEAN_RE.sub(" ", text))).strip()


def fetch_page(url: str) -> str:
    slug = (
        re.sub(r"[^a-z0-9-]", "_", url.split("proreferees.com/")[-1].strip("/"))
        or "home"
    )
    cache_f = PRO_CACHE / f"{slug}.html"
    return CACHE_READER.read(url, cache_f, MIN_BODY, mutable="/category/" in url)


def parse_listing(page: str) -> list:
    """列表页 → [{title, url, date}]。WordPress 文章卡：h2/h1 内 <a href> 或独立 <a rel>。"""
    out, seen = [], set()
    # 文章标题链接（WP 主题各异，兼容 h1/h2/h3 内锚 + entry-title 类）
    for m in re.finditer(
        r'<h([1-3])[^>]*class="[^"]*(?:entry-title|post-title)[^"]*"[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)</a>',
        page,
    ):
        url, title = m.group(2), clean(m.group(3))
        if url in seen or "/category/" in url or "/page/" in url:
            continue
        seen.add(url)
        out.append({"title": title, "url": url})
    if not out:  # 兜底：正文区所有指向文章的锚（日期路径式 URL）
        for m in re.finditer(
            r'<a[^>]+href="(https://proreferees\.com/20\d\d/\d\d/\d\d/[^"]+)"[^>]*>([\s\S]*?)</a>',
            page,
        ):
            url, title = m.group(1), clean(m.group(2))
            if url in seen or not title or len(title) < 8:
                continue
            seen.add(url)
            out.append({"title": title, "url": url})
    return out


SERIES_RE = re.compile(
    r"(?i)^\s*(Inside Video Review|VAR a Fondo|The Definitive Angle)\s*[:：]?\s*(.*)$"
)
LEAGUE_RE = re.compile(r"\b(MLS|NWSL|USL)\b")
YT_EMBED_RE = re.compile(r"youtube(?:-nocookie)?\.com/embed/([-\w]{11})", re.I)


def article_videos(url: str) -> list:
    """文章页内嵌 YouTube 视频 → 官方观看直链（v2：2026-10 实测 IVR/VAF 文章均嵌 YouTube iframe）"""
    page = fetch_page(url)
    if not page:
        return []
    ids = list(dict.fromkeys(YT_EMBED_RE.findall(page)))
    return [f"https://www.youtube.com/watch?v={i}" for i in ids]


def classify(title: str) -> dict:
    sm = SERIES_RE.search(title)
    series = (sm.group(1) if sm else "").lower()
    kind = {
        "inside video review": "ivr",
        "var a fondo": "vaf",
        "the definitive angle": "angle",
    }.get(series, "other")
    rest = sm.group(2) if sm else title
    lm = LEAGUE_RE.search(rest)
    league = lm.group(1) if lm else ""
    roundno = ""
    rm = re.search(r"#\s*(\d+)\s*(?:\+\s*#?\s*(\d+))?", rest)
    if rm:
        roundno = rm.group(1) + ("+" + rm.group(2) if rm.group(2) else "")
    return {
        "kind": kind,
        "league": league,
        "round": roundno,
        "lang": "es" if kind == "vaf" else "en",
    }


def parse_all():
    old = json.loads(PRO_JSON.read_text(encoding="utf-8")) if PRO_JSON.exists() else {}
    articles = list(old.get("articles", []))
    checked = []

    for slug, name_cn, kind in CATEGORIES:
        for pageno in range(1, MAX_PAGES + 1):
            url = (
                f"{BASE}/category/{slug}/"
                if pageno == 1
                else f"{BASE}/category/{slug}/page/{pageno}/"
            )
            page = fetch_page(url)
            if not page:
                break
            items = parse_listing(page)
            if pageno == 1 and items and url in CACHE_READER.verified:
                checked.append(slug)
            new = 0
            for it in items:
                dm = re.search(r"/(20\d\d)/(\d\d)/(\d\d)/", it["url"])
                date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" if dm else ""
                meta = classify(it["title"])
                articles.append(
                    {**it, "date": date, "series": kind, "series_name": name_cn, **meta}
                )
                new += 1
            print(f"{slug} p{pageno}: +{new}", flush=True)
            if new == 0:
                CACHE_READER.failed.add(url)
                break
            if pageno < MAX_PAGES:
                if not CACHE_READER.offline:
                    time.sleep(random.uniform(*DELAY))
    # 去重（IVR 分类与官网首页可能重复；VAR a Fondo 归入 IVR 分类）
    merged = {}
    for item in articles:
        previous = merged.get(item["url"], {})
        merged[item["url"]] = dict(previous)
        for key, value in item.items():
            if value not in ("", None, []) or key not in merged[item["url"]]:
                merged[item["url"]][key] = value
    uniq = sorted(merged.values(), key=lambda x: x["date"], reverse=True)
    # 空列表可能来自暂时抓取失败，下次重试；--refresh 同时重查已有链接。
    n_vid = 0
    for a in uniq:
        if a.get("videos") and not CACHE_READER.refresh:
            continue
        vids = article_videos(a["url"])
        a["videos"] = vids or a.get("videos", [])
        if vids:
            n_vid += 1
        print(
            f"  videos {a['url'].rstrip('/').split('/')[-1][:44]}: {len(vids)}",
            flush=True,
        )
        if not CACHE_READER.offline:
            time.sleep(random.uniform(*DELAY))
    data = {
        "source": BASE + "/category/inside-video-review/",
        "source_name": "美国 PRO 裁判评议（Inside Video Review / VAR a Fondo / The Definitive Angle）",
        "fetched": time.strftime("%Y-%m-%d")
        if len(checked) == len(CATEGORIES) and not CACHE_READER.failed
        else old.get("fetched", ""),
        "ussf": {
            "videos": "https://www.ussoccer.com/refereeing/videos",
            "learning": "https://learning.ussoccer.com/referee",
            "refereeing": "https://www.ussoccer.com/refereeing",
        },
        "articles": uniq,
    }
    data["latest_content"] = max((a["date"] for a in uniq), default="")
    if uniq:
        write_json(PRO_JSON, data)
    by_series = {}
    for a in uniq:
        by_series[a["series"]] = by_series.get(a["series"], 0) + 1
    print(f"parse 完成: {len(uniq)} 篇 {by_series} → {PRO_JSON}", flush=True)


def main():
    global CACHE_READER
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode not in ("fetch", "parse", "all"):
        raise SystemExit("用法: fetch_pro.py [fetch|parse|all] [--refresh]")
    CACHE_READER = SourceCache(offline=mode == "parse", refresh="--refresh" in sys.argv)
    parse_all()


if __name__ == "__main__":
    main()
