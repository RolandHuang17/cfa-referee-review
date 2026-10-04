# -*- coding: utf-8 -*-
"""抓取 UEFA Clear Line 判例库 → data/uefa.json（提交进仓库，build_uefa.py 据此生成 site/uefa.html）

用法: python fetch_uefa.py [fetch|parse|all]   (默认 all)
- fetch: 落地页→分类页逐页抓取，原始 HTML 缓存 data/local/uefa-cache/（断点续抓，已缓存页不再联网）
- parse: 纯本地从缓存解析写 data/uefa.json（可反复调参重跑，不联网）

⚠ uefa.com 对高频请求 tarpit（挂起不响应）：页间随机间隔 DELAY 秒、完整浏览器头；
   请求失败/内容过短按 tarpit 处理，退避 120s/300s 重试两次，再失败留待下次重跑。
⚠ 视频为 Akamai token 门禁 HLS（无 token 403），不下载；每例保留官方分享页链接。
"""
import gzip
import html as htmllib
import json
import random
import re
import sys
import time
import zlib
from lib.safe_http import safe_request

from lib.paths import UEFA_CACHE, UEFA_JSON
BASE = "https://www.uefa.com"
START = BASE + "/running-competitions/refereeing/clear-line/"
SEED_SLUGS = ["factual-decisions", "red-cards", "red-cards/dogso",
              "red-cards/serious-foul-play", "red-cards/violent-conduct",
              "red-cards/second-yellow", "penalties", "penalties/handball",
              "penalties/holding-pushing", "penalties/tripping", "penalties/step-on-foot",
              "penalties/who-played-the-ball", "penalties/goalkeepers", "penalties/simulation"]
DELAY = (35, 55)          # 每次网络抓取的间隔区间（秒）
BACKOFFS = [120, 300]     # 疑似 tarpit 的退避序列
MIN_BODY = 5000           # 页面正文最小字节数（低于即判 tarpit/异常页）

# 完整浏览器头（缺 Sec-Fetch/Accept-Language 时 uefa.com 会挂起请求；
# gzip+新 UA 与实测成功的 curl 请求一致；经 safe_request 走 safe_http 全部安全层）
BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9,zh-CN;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

# 分组中文名（slug → 中文；未映射回退英文）与展示顺序
GROUP_CN = {
    "factual-decisions": "客观事实判定",
    "dogso": "DOGSO 破坏明显进球",
    "serious-foul-play": "严重犯规",
    "violent-conduct": "暴力行为",
    "second-yellow": "两黄变一红",
    "penalties": "球点球判罚",
    "handball": "手球（点球）",
    "holding-pushing": "拉拽与推搡",
    "tripping": "绊摔",
    "step-on-foot": "踩踏",
    "who-played-the-ball": "是否触到球",
    "goalkeepers": "守门员",
    "simulation": "假摔",
    "red-cards": "红牌判罚",
}
GROUP_ORDER = list(GROUP_CN.keys())

CLEAN_RE = re.compile(r"<[^>]+>")


def clean(text: str) -> str:
    return htmllib.unescape(re.sub(r"\s+", " ", CLEAN_RE.sub(" ", text))).strip()


def slug_of(url: str) -> str:
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    return tail if tail else "clear-line-home"


def _decode_body(resp, hdrs: dict) -> str:
    data = resp.read()
    enc = (hdrs.get("content-encoding") or "").lower()
    if "gzip" in enc:
        data = gzip.decompress(data)
    elif "deflate" in enc:
        data = zlib.decompress(data, -zlib.MAX_WBITS)
    charset = "utf-8"
    ctype = hdrs.get("content-type", "")
    if "charset=" in ctype:
        # 报头可能带尾部分号或引号（charset=utf-8;），剥掉防 LookupError
        charset = (ctype.split("charset=")[-1].split(";")[0]
                   .strip().strip('"').strip("'"))
    return data.decode(charset, errors="replace")


def fetch_with_backoff(url: str) -> str:
    """带 tarpit 退避的抓取（safe_request：白名单+DoH+IP钉扎不变）；失败返回 ''。"""
    for i, wait in enumerate([0] + BACKOFFS):
        if wait:
            print(f"  疑似 tarpit/失败，退避 {wait}s 后第 {i} 次重试…", flush=True)
            time.sleep(wait)
        try:
            st, hdrs, resp, conn = safe_request(url, headers=BROWSER_HEADERS, timeout=45)
            txt = _decode_body(resp, hdrs)
            resp.close()
            conn.close()
            if st == 404:  # 路径错误不重试（组内嵌套 slug 由页面链接发现兜底）
                print("  HTTP 404（跳过）", flush=True)
                return ""
            if st == 200 and len(txt) > MIN_BODY:
                return txt
            print(f"  HTTP {st}, {len(txt)}B", flush=True)
        except Exception as e:
            print(f"  请求异常: {e}", flush=True)
    return ""


def clear_line_links(page: str) -> list:
    out = []
    for href in re.findall(r'href="([^"]*running-competitions/refereeing/clear-line/[^"#?]+/?)"', page):
        url = BASE + href if href.startswith("/") else href
        url = url.rstrip("/") + "/"
        out.append(url)
    return out


def fetch_all():
    UEFA_CACHE.mkdir(parents=True, exist_ok=True)
    queue, seen = [START] + [BASE + f"/running-competitions/refereeing/clear-line/{s}/" for s in SEED_SLUGS], set()
    while queue:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        cache_f = UEFA_CACHE / f"{slug_of(url)}.html"
        if cache_f.exists() and cache_f.stat().st_size > MIN_BODY:
            print(f"缓存命中: {cache_f.name}", flush=True)
            page = cache_f.read_text(encoding="utf-8", errors="replace")
        else:
            print(f"抓取: {url}", flush=True)
            page = fetch_with_backoff(url)
            if not page:
                print(f"  抓取失败（重跑本脚本可续）: {url}", flush=True)
                continue
            cache_f.write_text(page, encoding="utf-8")
            time.sleep(random.uniform(*DELAY))
        for u in clear_line_links(page):
            if u not in seen:
                queue.append(u)
    print(f"fetch 完成，缓存页数: {len(list(UEFA_CACHE.glob('*.html')))}", flush=True)


def parse_videos(page: str) -> list:
    items = []
    for m in re.finditer(r'data-options="([^"]+)"', page):
        txt = htmllib.unescape(m.group(1))
        if '"hlsStreamUrl"' not in txt:  # videoplayer 组件的 options 含 HLS 流地址
            continue
        try:
            opts = json.loads(txt)
        except json.JSONDecodeError:
            continue
        if not opts.get("sharingurl"):
            continue
        items.append({"id": opts.get("id", ""),
                      "title": clean(opts.get("title") or ""),
                      "url": opts["sharingurl"],
                      "date": (opts.get("publicationDate") or "")[:10]})
    # 去重（同页引用同一视频时保留首现）
    seen, uniq = set(), []
    for it in items:
        if it["id"] not in seen:
            seen.add(it["id"])
            uniq.append(it)
    # 官方视频说明文字（与视频按文档顺序配对，数量不符则留空）
    caps = [clean(c) for c in re.findall(
        r'class="article-embedded_caption"[^>]*>([\s\S]*?)</span>', page)]
    if len(caps) == len(uniq):
        for it, cap in zip(uniq, caps):
            it["caption"] = cap
    else:
        for it in uniq:
            it["caption"] = ""
    return uniq


def parse_page_meta(page: str) -> dict:
    """取正文区（Article body → Related topics 之间）的介绍段落与 ✅/❌ 准则分节。"""
    m = re.search(r"Article body", page)
    endm = re.search(r"Related topics", page)
    body = page[m.end(): endm.start() if endm else len(page)] if m else page
    paras = [clean(p) for p in re.findall(r"<p[^>]*>([\s\S]*?)</p>", body)]
    paras = [p for p in paras if len(p) > 60]
    criteria = []
    hs = list(re.finditer(r"<h([234])[^>]*>([\s\S]*?)</h\1>", body))
    for i, hm in enumerate(hs):
        label = clean(hm.group(2))
        if not label or label.lower() == "article body":
            continue
        chunk = body[hm.end(): hs[i + 1].start() if i + 1 < len(hs) else len(body)]
        txts = [clean(x) for x in re.findall(r"<(?:p|li)[^>]*>([\s\S]*?)</(?:p|li)>", chunk)]
        txts = [t for t in txts if len(t) > 25]
        if txts:
            criteria.append({"h": label, "items": txts})
    # 页面名: h1 + 分类型 h2（分类名在 "Article body" 之前的头部区；找不到再退回全页扫描）
    h1m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", page)
    name_en = clean(h1m.group(1)) if h1m else ""
    zones = [page[:m.start()]] if m else []
    zones.append(page)
    for zone in zones:
        for hm in re.finditer(r"<h[23][^>]*>([\s\S]*?)</h[23]>", zone):
            t = clean(hm.group(1))
            if not t or re.search(r"(?i)article body|what referees consider|related topics|"
                                  "^explore$|^more$|change language|social and apps|follow us on|services links", t):
                continue
            if t.lower() in name_en.lower():
                continue
            name_en = f"{name_en} – {t}" if name_en else t
            break
        else:
            continue
        break
    return {"name_en": name_en, "intro": " ".join(paras[:2]), "criteria": criteria}


def parse_all():
    groups = []
    for f in sorted(UEFA_CACHE.glob("*.html")):
        page = f.read_text(encoding="utf-8", errors="replace")
        items = parse_videos(page)
        if not items:
            continue
        slug = f.stem
        meta = parse_page_meta(page)
        for it in items:
            if it.get("caption") == it["title"]:  # 说明与标题重复时不保留
                it["caption"] = ""
        groups.append({"key": slug,
                       "name_en": meta["name_en"] or slug,
                       "name_cn": GROUP_CN.get(slug, slug),
                       "intro": meta["intro"],
                       "criteria": meta["criteria"],
                       "items": items})
    order = {k: i for i, k in enumerate(GROUP_ORDER)}
    groups.sort(key=lambda g: order.get(g["key"], 99))
    data = {"source": START,
            "source_name": "UEFA Clear Line 官方判例库",
            "fetched": time.strftime("%Y-%m-%d"),
            "groups": groups}
    UEFA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(len(g["items"]) for g in groups)
    print(f"parse 完成: {len(groups)} 组 / {n} 例 → {UEFA_JSON}", flush=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("fetch", "all"):
        fetch_all()
    if mode in ("parse", "all"):
        parse_all()


if __name__ == "__main__":
    main()
