# -*- coding: utf-8 -*-
"""抓取南美足联 CONMEBOL《Situación de Análisis VAR》逐案判例 → data/conmebol.json
（提交进仓库，build_conmebol.py 据此生成 site/conmebol.html）

用法: python fetch_conmebol.py [all]   (默认 all；解析内联在抓取中)
- 专栏为 Elementor 文章网格，列表页直接给出每案元数据：
  标题(赛事: 主 vs 客)、日期、摘要(Fecha/Ciudad/Estadio/Situación/Minuto)
- 分页 /2/ /3/ … 由 e-load-more-anchor 的 data-max-page/next-page 指示（实测 10 页）
- ⚠ 该站 HTML 属性大量不带引号，解析正则需兼容 quoted/unquoted
"""

import html as htmllib
import hashlib
import json
import random
import re
import time
import sys
from html.parser import HTMLParser

from lib.conmebol_evidence import DETAIL_FIELDS, UNRELATED_CACHE, evidence_problems
from lib.source_snapshot import SnapshotReads, publish
from lib.safe_http import fetch_text

from lib.paths import CONMEBOL_CACHE, CONMEBOL_JSON

READS = SnapshotReads()

BASE = "https://www.conmebol.com"
COLUMN = BASE + "/sistema-asistencia-arbitral-por-video/"
MAX_PAGES = 12
DELAY = (2.0, 4.0)
MIN_BODY = 100000
MIN_ART = 100000
BACKOFFS = [20, 60]

ARTICLE_RE = re.compile(
    r'<article[^>]*class="[^"]*elementor-post[^"]*"[^>]*>([\s\S]*?)</article>', re.I
)
TITLE_RE = re.compile(
    r'elementor-post__title[^>]*>\s*<a[^>]+href=("([^"]*)"|([^\s>]+))[^>]*>([\s\S]*?)</a>',
    re.I,
)
DATE_RE = re.compile(r"elementor-post-date[^>]*>\s*([^<]+?)\s*<", re.I)
EXCERPT_RE = re.compile(r"elementor-post__excerpt[^>]*>\s*<p[^>]*>([\s\S]*?)</p>", re.I)
TORNEO_RE = re.compile(r"torneos-([a-z0-9-]+)")
NEXT_RE = re.compile(r'data-next-page=("([^"]*)"|([^\s>]+))')
MAXPAGE_RE = re.compile(r'data-max-page=("?)(\d+)\1')

COMP_CN = {
    "eliminatorias": "世界杯预选赛（南美区）",
    "libertadores": "解放者杯",
    "sudamericana": "南美杯",
    "conmebol-recopa": "南美优胜者杯（Recopa）",
    "recopa": "南美优胜者杯（Recopa）",
}
SITUATIONS = {
    "penal": "penalty",
    "mano penal": "penalty",
    "no penal": "no_penalty",
    "on field review – penal": "ofr_penalty",
    "tarjeta roja": "red_card",
    "roja": "red_card",
    "fuera de juego": "offside",
    "no fuera de juego": "no_offside",
    "no gol": "no_goal",
    "gol anulado": "no_goal",
    "gol": "goal",
}


def clean(text: str) -> str:
    return htmllib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))).strip()


def norm_situation(s: str) -> str:
    return SITUATIONS.get(" ".join((s or "").casefold().split()), "other")


class PageIdentity(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical = set()
        self.og = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and "canonical" in (attrs.get("rel") or "").lower().split():
            self.canonical.add((attrs.get("href") or "").rstrip("/"))
        if tag == "meta" and attrs.get("property") == "og:url":
            self.og.add((attrs.get("content") or "").rstrip("/"))


def belongs_to(page, url):
    head = PageIdentity()
    head.feed(page.partition("</head>")[0])
    # 列表第 2–5 页有逐页 canonical，但 og:url 统一标注栏目首页。
    markers = (
        (head.canonical or head.og)
        if url.startswith(COLUMN)
        else head.canonical | head.og
    )
    return markers == {url.rstrip("/")}


def cache_path(url):
    return CONMEBOL_CACHE / (hashlib.sha256(url.encode("utf-8")).hexdigest() + ".html")


def legacy_cache_path(url):
    slug = (
        re.sub(r"[^a-z0-9-]", "_", url.split("conmebol.com/")[-1].strip("/"))[:80]
        or "col1"
    )
    return CONMEBOL_CACHE / f"{slug}.html"


def fetch_page(url: str, min_body: int = 0) -> str:
    """按完整 URL 缓存；旧文件只读，正文身份必须与所请求的来源一致。"""
    min_body = min_body or MIN_BODY
    cache_f = cache_path(url)
    for path in (cache_f, legacy_cache_path(url)):
        cached = READS.cached(url, path, min_body)
        if cached and belongs_to(cached, url):
            return cached
    if READS.offline:
        return ""
    CONMEBOL_CACHE.mkdir(parents=True, exist_ok=True)
    for i, wait in enumerate([0] + BACKOFFS):
        if wait:
            time.sleep(wait)
        try:
            st, txt = fetch_text(url, timeout=45, retries=2)
            if st == 200 and len(txt) > min_body and belongs_to(txt, url):
                READS.store(url, cache_f, txt)
                return txt
        except Exception:  # noqa: BLE001
            pass
    return ""


def parse_page(page: str) -> tuple:
    cases = []
    next_url, max_page = "", 1
    nm = NEXT_RE.search(page)
    if nm:
        next_url = (nm.group(2) or nm.group(3) or "").strip('"')
    mm = MAXPAGE_RE.search(page)
    if mm:
        max_page = int(mm.group(2))
    for am in ARTICLE_RE.finditer(page):
        block = am.group(1)
        tm = TITLE_RE.search(block)
        if not tm:
            continue
        url = (tm.group(2) or tm.group(3) or "").strip('"')
        title = clean(tm.group(4))
        if "situacion-de-analisis" not in url:
            continue
        dm = DATE_RE.search(block)
        em = EXCERPT_RE.search(block)
        exc = clean(em.group(1)) if em else ""
        torneos = TORNEO_RE.findall(block)
        comp = ""
        for t in torneos:
            if (
                t in COMP_CN
                or "libertadores" in t
                or "sudamericana" in t
                or "recopa" in t
            ):
                comp = t
                break
        cases.append(
            {
                "title": title,
                "url": url,
                "date": clean(dm.group(1)) if dm else "",
                "excerpt_es": exc,
                "comp": comp,
            }
        )
    return cases, next_url, max_page


def _clean_minute(v: str) -> str:
    return re.sub(r"\s*CONMEBOL\.com\s*$", "", (v or "").strip()).rstrip("′'")


def parse_case(c: dict) -> dict:
    """摘要 → 结构化字段：Bolivia vs. Brasil Fecha: .. Ciudad: .. Estadio: .. Situación: .. Minuto: .."""
    exc = c.get("excerpt_es", "")

    def grab(pat):
        m = re.search(
            pat
            + r"\s*:\s*(.*?)(?=\s+(?:Fecha|Ciudad|Estadio|Situaci[oó]n|Minuto|CONMEBOL)\s*:|$)",
            exc,
            re.I,
        )
        return clean(m.group(1)) if m else ""

    match = ""
    mm = re.match(r"^(.*?)\s*Fecha\s*:", exc, re.I)
    if mm:
        match = clean(mm.group(1))
    sit = grab(r"Situaci[oó]n")
    minute = grab(r"Minuto")
    return {
        "match": match or c["title"].split(":")[-1].strip(),
        "fecha": grab(r"Fecha"),
        "ciudad": grab(r"Ciudad"),
        "estadio": grab(r"Estadio"),
        "situacion_es": sit,
        "situacion_norm": norm_situation(sit),
        "minuto": _clean_minute(minute),
        "comp_cn": COMP_CN.get(c.get("comp", ""), ""),
    }


EMBED_RE = re.compile(
    r"https://(?:www\.)?youtube\.com/embed/([A-Za-z0-9_-]{11})(?:[?#].*)?$"
)
FIELD_RE = re.compile(
    r"(Fecha|Ciudad|Estadio|Situación|Situacion|Tópico|Minuto)\s*:\s*(.*)", re.I
)
MINUTE_RE = re.compile(r"\d+(?:\s*\+\s*\d+)?[′’']?")


class ArticleBody(HTMLParser):
    """读取 WordPress 文章正文中的字段和 iframe，保持 DOM 顺序。"""

    separators = {"p", "li", "ul", "h2", "h3", "h4", "br", "div", "figure", "iframe"}

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.parts = []
        self.buffer = []

    def flush(self):
        part = " ".join("".join(self.buffer).split())
        if part:
            self.parts.append(part)
        self.buffer.clear()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div":
            if self.depth:
                self.depth += 1
            elif attrs.get("data-widget_type") == "theme-post-content.default":
                self.depth = 1
        if self.depth:
            if tag in self.separators:
                self.flush()
            if tag == "iframe":
                match = EMBED_RE.fullmatch(attrs.get("src") or "")
                if match:
                    self.parts.append(
                        {
                            "url": "https://www.youtube.com/watch?v=" + match[1],
                            "title": (attrs.get("title") or "").strip(),
                        }
                    )

    def handle_data(self, data):
        if self.depth:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if self.depth and tag in self.separators:
            self.flush()
            if tag == "div":
                self.depth -= 1


def article_details(page, case):
    body = ArticleBody()
    body.feed(page)
    meta, events = {}, []
    event = None
    last_text, lang = "", ""
    for part in body.parts:
        if isinstance(part, dict):
            if event is None or "minuto" not in event:
                raise ValueError(f"视频在情境或分钟之前: {case['url']}")
            event["videos"].append({**part, "lang": lang})
            lang = ""
            continue
        field = FIELD_RE.fullmatch(part)
        if field:
            key, value = field[1].lower(), field[2].strip()
            if key in ("fecha", "ciudad", "estadio"):
                if key in meta and meta[key] != value:
                    raise ValueError(f"同一文章出现不同 {key}: {case['url']}")
                meta[key] = value
                if key == "fecha" and re.search(r"\bvs[.\s-]", last_text, re.I):
                    meta["match"] = last_text
            elif key == "minuto":
                if not event or "minuto" in event:
                    raise ValueError(f"分钟无法对应情境: {case['url']}")
                if MINUTE_RE.fullmatch(value):
                    event["minuto"] = re.sub(r"\s+", "", value).rstrip("′’'")
                elif MINUTE_RE.fullmatch(event["situacion_es"]) and value:
                    # 两篇原文把标签和值交叉写入。原样列出，不替编辑部交换值。
                    event["source_fields"] = {
                        "situacion_es": event["situacion_es"],
                        "minuto": value,
                    }
                    event.update(situacion_es="", situacion_norm="other", minuto="")
                else:
                    raise ValueError(f"不能解析文章分钟: {case['url']}")
            else:
                event = {
                    "situacion_es": value,
                    "situacion_norm": norm_situation(value),
                    "videos": [],
                }
                events.append(event)
                lang = ""
        elif part.rstrip(":").upper() in ("ESP", "POR"):
            lang = {"ESP": "es", "POR": "pt"}[part.rstrip(":").upper()]
        last_text = part
    if not events or any("minuto" not in e or not e["videos"] for e in events):
        raise ValueError(f"文章情境、分钟与视频未能逐一配对: {case['url']}")
    for event in events:
        stated = event["minuto"] or (
            event["source_fields"]["situacion_es"].rstrip("′’'")
        )
        for video in event["videos"]:
            minute_title = re.search(
                r"\bminuto\s+(\d+(?:\s*\+\s*\d+)?)", video["title"], re.I
            )
            if minute_title and sum(map(int, minute_title[1].split("+"))) != sum(
                map(int, stated.split("+"))
            ):
                raise ValueError(f"正文分钟和同段视频标题不一致: {case['url']}")
    if not meta.get("match"):
        meta["match"] = case["title"].rsplit(":", 1)[-1].strip()
    first = events[0]
    return {
        **meta,
        "situacion_es": first["situacion_es"],
        "situacion_norm": first["situacion_norm"],
        "minuto": first["minuto"],
        "youtube": first["videos"][0]["url"],
        "events": events,
    }


def enrich(c: dict) -> dict:
    """逐篇读取文章，按官方正文顺序将同段录像附到各情境。"""
    page = fetch_page(c["url"], MIN_ART)
    if not page:
        if READS.offline and c["url"] in UNRELATED_CACHE:
            c.pop("events", None)
            c.update(dict.fromkeys(DETAIL_FIELDS, ""))
            c.update(
                match=c["title"].rsplit(":", 1)[-1].strip(),
                situacion_norm="other",
                detail_status="pending",
                unrelated_cache_url=UNRELATED_CACHE[c["url"]],
            )
            return c
        raise ValueError(f"判例文章不可用: {c['url']}")
    c.update(article_details(page, c))
    c.pop("detail_status", None)
    c.pop("unrelated_cache_url", None)
    return c


def identities(data):
    for case in data.get("cases", []):
        yield case["url"], "case"
        if case.get("detail_status") != "pending":
            yield case["url"], "article"
        for event in case.get("events", []):
            for video in event["videos"]:
                yield case["url"], video["url"]
        for field in ("youtube", "situacion_es", "fecha", "minuto"):
            if case.get(field):
                yield case["url"], field


def main():
    global READS
    READS = SnapshotReads(offline="parse" in sys.argv, refresh="--refresh" in sys.argv)
    seen, cases = set(), []
    url, page_no = COLUMN, 1
    max_page = MAX_PAGES
    while url and page_no <= max_page and page_no <= MAX_PAGES:
        page = fetch_page(url)
        if not page:
            raise ValueError(f"第 {page_no} 页抓取失败")
        got, next_url, mp = parse_page(page)
        if page_no == 1:
            max_page = mp
        if max_page > MAX_PAGES:
            raise ValueError(f"来源有 {max_page} 页，超过本次抓取上限 {MAX_PAGES}")
        new = 0
        for c in got:
            if c["url"] not in seen:
                seen.add(c["url"])
                cases.append({**c, **parse_case(c)})
                new += 1
        print(
            f"p{page_no}: +{new}（累计 {len(cases)}，max_page={max_page}）", flush=True
        )
        if not new or (not next_url and page_no < max_page):
            raise ValueError(f"第 {page_no} 页无新增或提前缺失后续分页")
        url, page_no = next_url, page_no + 1
        if not READS.offline and url and page_no <= max_page:
            time.sleep(random.uniform(*DELAY))
    # 赛事名兜底：torneos-* 类不可靠，从标题推导（⚠ 先查 eliminatoria：
    # 「Eliminatorias Sudamericanas」含 sudamericana 字样，顺序反了会误判）
    for c in cases:
        t = c["title"].lower()
        if "eliminatoria" in t:
            c["comp"] = "eliminatorias"
        elif "libertadores" in t:
            c["comp"] = "libertadores"
        elif "recopa" in t:
            c["comp"] = "conmebol-recopa"
        elif "sudamericana" in t:
            c["comp"] = "sudamericana"
        c["comp_cn"] = COMP_CN.get(c.get("comp", ""), "")
    # 逐案增强：抓文章页补字段 + YouTube 判例视频
    n_en = 0
    for i, c in enumerate(cases):
        before = (c.get("situacion_es"), c.get("youtube"))
        enrich(c)
        if (c.get("situacion_es"), c.get("youtube")) != before:
            n_en += 1
        if not READS.offline and i < len(cases) - 1:
            time.sleep(random.uniform(1.5, 3.0))
    comp_map = {}
    for c in cases:
        comp_map[c["situacion_norm"]] = comp_map.get(c["situacion_norm"], 0) + 1
    data = {
        "source": COLUMN,
        "source_name": "CONMEBOL《Situación de Análisis VAR》逐案判例",
        "cases": cases,
    }
    if CONMEBOL_JSON.exists():
        history = json.loads(CONMEBOL_JSON.read_bytes()).get("source_history")
        if history:
            data["source_history"] = history
    problems = evidence_problems(data)
    if problems:
        raise ValueError(problems[0])
    publish(CONMEBOL_JSON, data, identities, checked=READS.checked)
    print(f"parse 完成: {len(cases)} 案 {comp_map} → {CONMEBOL_JSON}", flush=True)


if __name__ == "__main__":
    main()
