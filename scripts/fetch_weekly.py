# -*- coding: utf-8 -*-
"""抓取全球周更评议节目（YouTube 官方频道/播放列表）→ data/weekly.json
（提交进仓库，build_weekly.py 据此生成 site/weekly.html）

用法: python fetch_weekly.py [fetch|parse|all|discover]   (默认 all)
- fetch: 逐源抓取并缓存 data/local/weekly-cache/（断点续抓，重跑即增量合并）
- parse: 纯本地从缓存重解析 → data/weekly.json
- discover <channel_id> [query]: 辅助模式——列出频道播放列表/频道内检索视频，
  探明新源后把 ID 固化进 SOURCES

双通道抓取设计（YouTube 无公开 API）：
- RSS 通道（主）：feeds/videos.xml?playlist_id=/channel_id= 返回最近 ≤15 条，
  含精确发布时间、完整说明文本与播放统计；
- 页面通道（回补）：播放列表页/频道内检索页 HTML 内嵌 ytInitialData JSON，
  一次性给出存量期目（标题/时长/相对时间），相对时间按抓取日近似为日期。

合并规则按 videoId 字段级进行：RSS 的精确日期与说明覆盖页面近似值，
重复运行只增不减。⚠ YouTube 视频受官方服务条款约束不下载、不内嵌，
本管线只收录元数据并跳官方观看页（与 uefa/pro 同为纯链接模式）。

安全注意：YouTube RSS 属不可信输入——parse_rss 拒绝带 DTD/实体的文档并限制
输入大小，防 XML 实体扩展（标准库 ElementTree 无 defusedxml 时的最小防护）。
"""
import html as htmllib
import json
import random
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import quote

from lib.safe_http import fetch_text

from lib.paths import WEEKLY_CACHE, WEEKLY_JSON

DELAY = (1.5, 3.0)   # 请求间隔礼貌延时（非安全用途）
BACKOFFS = [20, 60]
MIN_PAGE = 250000   # ytInitialData 页面正文下限（404/同意墙壳只有几百字节）
MIN_RSS = 1000
RSS_MAX = 2_000_000  # RSS 解析输入上限（防实体扩展的资源耗尽面）
DESC_MAX = 3500
ACCEPT_LANG = {"Accept-Language": "en-US,en;q=0.9"}  # 固定英文相对时间便于解析

NS = {"a": "http://www.w3.org/2005/Atom",
      "m": "http://search.yahoo.com/mrss/",
      "yt": "http://www.youtube.com/xml/schemas/2015"}

# ---- 数据源注册表（频道/播放列表 ID 已逐一人工核验，2026-10）----------------
# filter 是标题筛选正则：频道型源必填（频道不只发节目）；播放列表型源整单即节目。
SOURCES = [
    {"key": "sfa", "name": "The VAR Review",
     "org": "Scottish FA（苏格兰足总）", "lang": "en", "update": "月更",
     "channel": "UChaFW_N-7dndut-HC4Exe-g",
     "playlists": ["PLRi0DI6Eo0dzHo7aEPPKuAViDn2uBQ4pz", "PLEeXlqS76RSI"],
     "search": "VAR Review", "filter": r"VAR Review"},
    {"key": "tff", "name": "VAR Kayıtları – Sahada İnceleme",
     "org": "Türkiye Futbol Federasyonu（土耳其足协）", "lang": "tr", "update": "周更",
     "channel": "UCVoNfzLtczc_TV8-xKjcmKg",
     "playlists": ["PLbl0EQV1PhxnvOZto0hEQIuyos-oQ7W41", "PLbl0EQV1PhxnQ1rX1MNhO486HWc7pWRDY",
                    "PLbl0EQV1PhxlBA3Pc8ZBfs-1JuBFMNczq", "PLao1i1WImjYM"],
     "search": "VAR Kayıtları", "filter": r"VAR Kay"},
    {"key": "jleague", "name": "Jリーグ審判レポート（シンレポ）",
     "org": "Jリーグ（日本职业足球联赛）", "lang": "ja", "update": "约月更",
     "channel": "",
     "playlists": ["PLkPh_QuTENJIRqYZRyCH1QcjEEGpkjrmS"],
     "search": "", "filter": ""},
    {"key": "england", "name": "Match Officials: Mic'd Up",
     "org": "Sky Sports / PGMOL（英格兰）", "lang": "en", "update": "月更",
     "channel": "UCNAf1k0yIjyGu3k9BwAg3lg",
     "playlists": [],
     "searches": ["Match Officials Mic'd Up", "Mic'd Up Howard Webb", "Match Officials"],
     "search": "", "filter": r"match officials|mic'?d up|howard webb"},
    {"key": "fmx", "name": "VAR Review",
     "org": "Comisión de Árbitros · FMF（墨西哥足协裁判委员会）", "lang": "es", "update": "不定期",
     "channel": "UCdqXXpzLUYbfckwnGIgR_8g",
     "playlists": [],
     "search": "VAR Review", "filter": r"var review"},
    {"key": "afa", "name": "VAR Revisión",
     "org": "Liga Profesional de Fútbol · AFA（阿根廷职业联赛）", "lang": "es", "update": "每轮",
     "channel": "UCJmCVoUfCBQb9lcfXIS8nXQ",
     "playlists": ["PLPFiU8B79-v8"],
     "search": "VAR", "filter": r"\bVAR\b|AUDIO"},
    {"key": "rfs", "name": "Судейский разбор",
     "org": "РФС ТВ（俄罗斯足协）", "lang": "ru", "update": "不定期",
     "channel": "UCLNgRqvauqKU6SOzdAJSQaw",
     "playlists": [],
     "search": "Судейский разбор", "filter": r"Судейский разбор"},
    # 文章型源：无 YouTube 视频，逐轮官方文字认定（索引级——官方正文为 stub）
    {"key": "uaf", "name": "Коментар епізодів（判例解读）",
     "org": "UAF 裁判委员会（乌克兰足协）", "lang": "uk", "update": "每轮",
     "type": "article", "url": "https://uaf.ua/referee-committee",
     "channel": "", "playlists": [], "search": "", "filter": r"арбітрів|коментар",
     "articles": {"listing": "https://uaf.ua/referee-committee?page={n}", "pages": 3}},
]

CLEAN_RE = re.compile(r"<[^>]+>")


def clean(text: str) -> str:
    return htmllib.unescape(re.sub(r"\s+", " ", CLEAN_RE.sub(" ", text))).strip()


def text_of(node):
    """ytInitialData 通用文本提取：{simpleText}|{content}|{runs[]}"""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        if isinstance(node.get("simpleText"), str):
            return node["simpleText"]
        if isinstance(node.get("content"), str):
            return node["content"]
        if isinstance(node.get("runs"), list):
            return "".join(r.get("text", "") for r in node["runs"] if isinstance(r, dict))
    return None


def yt_data(html: str, pat: str = r"var ytInitialData = ({.*?});</script>"):
    m = re.search(pat, html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:  # noqa: BLE001
        return None


def find_length(node):
    """在缩略图 overlays 子树里找时长徽标文本（形如 38:31）"""
    if isinstance(node, dict):
        for v in node.values():
            r = find_length(v)
            if r:
                return r
    elif isinstance(node, list):
        for v in node:
            r = find_length(v)
            if r:
                return r
    elif isinstance(node, str) and re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", node.strip()):
        return node.strip()
    return None


def harvest(html: str) -> dict:
    """页面 ytInitialData → {videoId: {title, date_text, length}}（新版 lockup + 旧版 renderer 双兼容）"""
    data = yt_data(html)
    out = {}
    if not data:
        return out

    def visit(node):
        if isinstance(node, dict):
            vid = node.get("videoId")
            if isinstance(vid, str) and re.fullmatch(r"[-_a-zA-Z0-9]{11}", vid) \
                    and not vid.startswith(("UC", "PL")):
                rec = out.setdefault(vid, {})
                t = text_of(node.get("title"))
                if t and not rec.get("title"):
                    rec["title"] = t.strip()
                s = text_of(node.get("publishedTimeText"))
                if s and "date_text" not in rec:
                    rec["date_text"] = s
                s = text_of(node.get("lengthText"))
                if s and "length" not in rec:
                    rec["length"] = s
            cid = node.get("contentId")
            # 新版 lockupViewModel：contentId=视频 ID，标题/元信息在 metadata 内
            if isinstance(cid, str) and re.fullmatch(r"[-_a-zA-Z0-9]{11}", cid) \
                    and not cid.startswith(("UC", "PL")) and "metadata" in node:
                rec = out.setdefault(cid, {})
                lm = (node.get("metadata") or {}).get("lockupMetadataViewModel") or {}
                t = text_of(lm.get("title"))
                if t and not rec.get("title"):
                    rec["title"] = t.strip()
                cm = (lm.get("metadata") or {}).get("contentMetadataViewModel") or {}
                for row in cm.get("metadataRows") or []:
                    for part in row.get("metadataParts") or []:
                        s = (text_of(part.get("text")) or "").strip()
                        if re.search(r"ago\b|Streamed|Premiered", s):
                            rec.setdefault("date_text", s)
                # 时长徽标在缩略图 overlays 内（形如 38:31）
                badge = find_length(node.get("contentImage") or {})
                if badge and "length" not in rec:
                    rec["length"] = badge
            for v in node.values():
                visit(v)
        elif isinstance(node, list):
            for v in node:
                visit(v)

    visit(data)
    return out


# YouTube 相对时间两种形态：完整词（2 weeks ago）与紧凑式（1mo ago / 2w ago / 3d ago）
REL_RE = re.compile(r"(\d+)\s*(minutes?|hours?|days?|weeks?|months?|years?|min|mo|h|d|w|y)\s+ago", re.I)
UNIT_MAP = {"min": "minute", "m": "minute", "h": "hour", "d": "day",
            "w": "week", "mo": "month", "y": "year"}
ABS_RE = re.compile(r"(?:Premiered|Streamed(?:\s+live)?\s+on)\s+([A-Z][a-z]{2,8})\s+(\d{1,2}),?\s+(\d{4})")


def approx_date(text: str, today: datetime) -> str:
    """'2 weeks ago' / '1mo ago' / 'Premiered Sep 11, 2026' → ISO 日期（近似），失败返回 ''"""
    if not text:
        return ""
    m = REL_RE.search(text)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower().rstrip("s")
        unit = UNIT_MAP.get(unit, unit if unit in ("minute", "hour", "day", "week", "month", "year") else "")
        if not unit:
            return ""
        delta = {"minute": timedelta(minutes=n), "hour": timedelta(hours=n),
                 "day": timedelta(days=n), "week": timedelta(weeks=n),
                 "month": timedelta(days=30 * n), "year": timedelta(days=365 * n)}[unit]
        return (today - delta).strftime("%Y-%m-%d")
    m = ABS_RE.search(text)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}",
                                     "%B %d %Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def parse_rss(txt: str) -> list:
    """YouTube Atom feed → [{id,title,date,date_src,url,desc,views,length}]"""
    head = txt[:4096].lower()
    if len(txt) > RSS_MAX or "<!doctype" in head or "<!entity" in head:
        return []  # 拒绝带 DTD/实体的文档与超大输入，防 XML 实体扩展
    try:
        root = ET.fromstring(txt.encode("utf-8"))
    except ET.ParseError:
        return []
    if root.tag.rsplit("}", 1)[-1] != "feed":
        return []
    eps = []
    for e in root.findall("a:entry", NS):
        vid_el = e.find("yt:videoId", NS)
        if vid_el is None or not (vid_el.text or "").strip():
            continue
        vid = vid_el.text.strip()
        title_el = e.find("a:title", NS)
        title = ((title_el.text or "") if title_el is not None else "").strip()
        pub_el = e.find("a:published", NS)
        pub = ((pub_el.text or "") if pub_el is not None else "")[:10]
        link_el = e.find("a:link", NS)
        link = link_el.get("href") if link_el is not None else ""
        desc, views = "", None
        mg = e.find("m:group", NS)
        if mg is not None:
            d = mg.find("m:description", NS)
            if d is not None and d.text:
                desc = d.text.strip()
            st = mg.find("m:community/m:statistics", NS)
            if st is not None and (st.get("views") or "").isdigit():
                views = int(st.get("views"))
        eps.append({"id": vid, "title": title, "date": pub, "date_src": "exact" if pub else "",
                    "url": link or f"https://www.youtube.com/watch?v={vid}",
                    "desc": desc, "views": views, "length": ""})
    return eps


def fetch_url(url: str, minlen: int) -> str:
    slug = re.sub(r"[^a-z0-9-]", "_", url.split("youtube.com/")[-1])[:120] or "x"
    cache_f = WEEKLY_CACHE / f"{slug}.txt"
    WEEKLY_CACHE.mkdir(parents=True, exist_ok=True)
    if cache_f.exists() and cache_f.stat().st_size > minlen:
        return cache_f.read_text(encoding="utf-8", errors="replace")
    for wait in [0] + BACKOFFS:
        if wait:
            time.sleep(wait)
        try:
            st, txt = fetch_text(url, headers=ACCEPT_LANG, timeout=45, retries=2)
            if st == 200 and len(txt) > minlen:
                cache_f.write_text(txt, encoding="utf-8")
                return txt
            if st == 404:
                return ""
        except Exception:  # noqa: BLE001
            pass
    return ""


def merge(dst: dict, src: dict):
    """字段级合并：src 有值且 dst 缺失才写入；日期精确优先。"""
    for k in ("title", "url", "date", "date_src", "desc", "views", "length"):
        if not dst.get(k) and src.get(k):
            dst[k] = src[k]
    if dst.get("date_src") == "approx" and src.get("date_src") == "exact":
        dst["date"], dst["date_src"] = src["date"], "exact"


UA_MONTHS = {"січня": "01", "лютого": "02", "березня": "03", "квітня": "04", "травня": "05",
             "червня": "06", "липня": "07", "серпня": "08", "вересня": "09",
             "жовтня": "10", "листопада": "11", "грудня": "12"}


def parse_uaf_cards(html: str) -> list:
    """UAF 列表页 news-card → [{id,title,url,date,desc}]（Livewire 卡块切分）"""
    out = []
    for card in re.split(r'(?=<div wire:key="news-\d+">)', html)[1:]:
        um = re.search(r'class="news-card__image"\s+href="(https://uaf\.ua/news/[^"]+)"', card)
        if not um:
            continue
        url = um.group(1)
        tm = re.search(r'class="fw-600[^"]*\stitle">\s*(?:<!--\[if BLOCK\]><!--\[endif\]-->)?\s*(.+?)\s*<!--\[if ENDBLOCK\]-->', card, re.S)
        title = clean(tm.group(1)) if tm else ""
        if not title:
            am = re.search(r'alt="([^"]+)"', card)
            title = clean(am.group(1)) if am else ""
        dm = re.search(r"(\d{1,2})\s+(" + "|".join(UA_MONTHS) + r")\s+(20\d\d)", card)
        date = f"{dm.group(3)}-{UA_MONTHS[dm.group(2)]}-{int(dm.group(1)):02d}" if dm else ""
        dcm = re.search(r'class="[^"]*description[^"]*">\s*(?:<!--\[if BLOCK\]><!--\[endif\]-->)?\s*<p>\s*(?:<!--\[if BLOCK\]><!--\[endif\]-->)?\s*(.+?)\s*</p>', card, re.S)
        desc = clean(dcm.group(1)) if dcm else ""
        eid = url.rsplit("/", 1)[-1]
        out.append({"id": eid, "title": title, "url": url, "date": date, "desc": desc[:DESC_MAX]})
    return out


def collect(show: dict) -> list:
    """一个源的全部期目（RSS 精确通道 + 页面存量回补；文章型源走列表页），按日期倒序。"""
    eps = {}
    today = datetime.now()
    fpat = re.compile(show["filter"], re.I) if show.get("filter") else None

    if show.get("type") == "article":
        cfg = show["articles"]
        for n in range(1, cfg.get("pages", 2) + 1):
            html = fetch_url(cfg["listing"].format(n=n), MIN_PAGE)
            items = parse_uaf_cards(html) if html else []
            hit = 0
            for it in items:
                if fpat and not fpat.search(it["title"]):
                    continue
                item = {"id": it["id"], "show": show["key"], "title": it["title"],
                        "url": it["url"], "date": it["date"],
                        "date_src": "exact" if it["date"] else "",
                        "desc": it["desc"], "views": None, "length": ""}
                if it["id"] in eps:
                    merge(eps[it["id"]], item)
                else:
                    eps[it["id"]] = item
                    hit += 1
            print(f"  listing p{n}: {len(items)} 卡 / 命中 +{hit}", flush=True)
            time.sleep(random.uniform(*DELAY))
        out = list(eps.values())
        for e in out:
            e["show"] = show["key"]
            e["title"] = clean(e.get("title") or "")
        out.sort(key=lambda x: x.get("date") or "0000-00-00", reverse=True)
        return out

    feeds = [f"https://www.youtube.com/feeds/videos.xml?playlist_id={p}"
             for p in show.get("playlists", [])]
    if show.get("channel"):
        feeds.append(f"https://www.youtube.com/feeds/videos.xml?channel_id={show['channel']}")
    for fu in feeds:
        txt = fetch_url(fu, MIN_RSS)
        entries = parse_rss(txt) if txt else []
        hit = 0
        for e in entries:
            if fpat and not fpat.search(e["title"]):
                continue
            if e["id"] in eps:
                merge(eps[e["id"]], e)
            else:
                eps[e["id"]] = dict(e)
                hit += 1
        print(f"  rss …{fu[-42:]}: {len(entries)} 条 / 命中 +{hit}", flush=True)
        time.sleep(random.uniform(*DELAY))

    pages = [f"https://www.youtube.com/playlist?list={p}" for p in show.get("playlists", [])]
    if show.get("channel"):
        for sq in (show.get("searches") or ([show["search"]] if show.get("search") else [])):
            pages.append(f"https://www.youtube.com/channel/{show['channel']}"
                         f"/search?query={quote(sq)}")
    for pu in pages:
        html = fetch_url(pu, MIN_PAGE)
        found = harvest(html) if html else {}
        hit = 0
        for vid, rec in found.items():
            if fpat and not fpat.search(rec.get("title") or ""):
                continue
            date = approx_date(rec.get("date_text", ""), today)
            item = {"id": vid, "title": rec.get("title", ""),
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "date": date, "date_src": "approx" if date else "",
                    "desc": "", "views": None, "length": rec.get("length", "")}
            if vid in eps:
                merge(eps[vid], item)
            else:
                eps[vid] = item
                hit += 1
        print(f"  page …{pu[-48:]}: 回补 {len(found)} / 命中 +{hit}", flush=True)
        time.sleep(random.uniform(*DELAY))

    out = list(eps.values())
    for e in out:
        e.setdefault("url", f"https://www.youtube.com/watch?v={e['id']}")
        e["show"] = show["key"]
        e["desc"] = (e.get("desc") or "")[:DESC_MAX]
        e["title"] = clean(e.get("title") or "")
    out.sort(key=lambda x: x.get("date") or "0000-00-00", reverse=True)
    return out


def parse_all():
    prev = {}
    if WEEKLY_JSON.exists():
        try:
            old = json.loads(WEEKLY_JSON.read_text(encoding="utf-8"))
            prev = {e["id"]: e for e in old.get("episodes", [])
                    if isinstance(e, dict) and e.get("id")}
        except Exception:  # noqa: BLE001
            prev = {}
    episodes, shows = {}, {}
    for show in SOURCES:
        print(f"[{show['key']}] {show['name']}", flush=True)
        got = collect(show)
        newn = 0
        for e in got:
            if e["id"] in prev:
                merge(e, prev[e["id"]])
            if e["id"] in episodes:
                merge(episodes[e["id"]], e)
            else:
                episodes[e["id"]] = e
                newn += 1
        shows[show["key"]] = {"name": show["name"], "org": show["org"],
                              "lang": show["lang"], "update": show["update"],
                              "url": (show.get("url")
                                      or (f"https://www.youtube.com/channel/{show['channel']}"
                                          if show.get("channel") else
                                          f"https://www.youtube.com/playlist?list={show['playlists'][0]}"))}
        print(f"[{show['key']}] 共 {len(got)} 期（净增 {newn}）", flush=True)
        time.sleep(random.uniform(*DELAY))
    data = {"source": "https://www.youtube.com",
            "source_name": "全球周更评议节目判例索引（YouTube 官方频道/播放列表元数据）",
            "fetched": time.strftime("%Y-%m-%d"),
            "shows": shows,
            "episodes": sorted(episodes.values(),
                               key=lambda x: x.get("date") or "0000-00-00", reverse=True)}
    WEEKLY_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    per_show = {}
    for e in data["episodes"]:
        per_show[e["show"]] = per_show.get(e["show"], 0) + 1
    exact = sum(1 for e in data["episodes"] if e.get("date_src") == "exact")
    print(f"parse 完成: {len(data['episodes'])} 期 / {len(shows)} 节目 {per_show}"
          f"（精确日期 {exact}）→ {WEEKLY_JSON}", flush=True)


PLAYER_RE = r"ytInitialPlayerResponse\s*=\s*({.+?});\s*(?:</script>|var\s|</head>)"


def fill_dates():
    """对无精确日期的期目逐条抓 watch 页，从 playerMicroformatRenderer.publishDate 补齐。"""
    data = json.loads(WEEKLY_JSON.read_text(encoding="utf-8"))
    todo = [e for e in data.get("episodes", [])
            if e.get("id") and (e.get("date_src") != "exact" or not e.get("date"))]
    print(f"待补精确日期: {len(todo)} 期", flush=True)
    fixed = 0
    for i, e in enumerate(todo):
        vid = e["id"]
        try:
            html = fetch_url(f"https://www.youtube.com/watch?v={vid}", 200000)
            d = yt_data(html, PLAYER_RE) if html else None
            pub = ((d or {}).get("microformat", {}).get("playerMicroformatRenderer", {})
                   or {}).get("publishDate", "")
        except Exception:  # noqa: BLE001
            pub = ""
        if pub:
            e["date"] = str(pub)[:10]
            e["date_src"] = "exact"
            fixed += 1
        print(f"  [{i + 1}/{len(todo)}] {vid}: {e.get('date') or '仍无日期'}", flush=True)
        time.sleep(random.uniform(*DELAY))
    WEEKLY_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    total = len(data.get("episodes", []))
    exact = sum(1 for e in data["episodes"] if e.get("date_src") == "exact")
    print(f"dates 完成: 新补 {fixed} 条，全库精确日期 {exact}/{total}", flush=True)


def discover(channel_id: str, query: str = ""):
    """辅助模式：列出频道播放列表与频道内检索命中，供探明新源。"""
    if query:
        found = harvest(fetch_url(
            f"https://www.youtube.com/channel/{channel_id}/search?query={quote(query)}", MIN_PAGE))
        print(f"频道内检索 [{query}] 命中 {len(found)} 条：")
        for vid, rec in list(found.items())[:30]:
            print(f"  {vid}  {rec.get('length', ''):>8}  {rec.get('title', '')[:80]}")
    pls = {}
    html = fetch_url(f"https://www.youtube.com/channel/{channel_id}/playlists", MIN_PAGE)
    data = yt_data(html) if html else None

    def walk(node):
        if isinstance(node, dict):
            pid = node.get("playlistId") or node.get("contentId")
            if isinstance(pid, str) and pid.startswith(("PL", "VLPL")):
                lm = (node.get("metadata") or {}).get("lockupMetadataViewModel") or {}
                t = text_of(lm.get("title")) or text_of(node.get("title"))
                pls.setdefault(pid.removeprefix("VL"), t or "?")
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    if data:
        walk(data)
    print(f"频道播放列表 {len(pls)} 个：")
    for pid, t in pls.items():
        print(f"  {pid}  {t[:80]}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "discover":
        if len(sys.argv) < 3:
            raise SystemExit("用法: fetch_weekly.py discover <channel_id> [query]")
        discover(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
        return
    if mode == "dates":
        fill_dates()
        return
    if mode in ("fetch", "parse", "all"):
        parse_all()
    else:
        raise SystemExit("用法: fetch_weekly.py [fetch|parse|all|dates|discover]")


if __name__ == "__main__":
    main()
