"""核对 Dutch Referee 的 UEFA RAP 索引，保留已策展的期数与链接。

python scripts/fetch_rap.py [fetch|merge] [--offline]
默认联网更新索引缓存。--offline 使用最近一次成功解析的本地索引。
merge 将有明确发布平台的新期标为待核。证据不足的链接保存在
data/local/dutchref-cache/pending-editions.json，供人工核对。
"""

import argparse
import html
import json
import re
from urllib.parse import urlsplit

from lib.atomic_json import write_json, write_text
from lib.official_urls import official_url
from lib.paths import DUTCHREF_CACHE, RAP_JSON
from lib.safe_http import fetch_text

INDEX = "https://www.dutchreferee.com/refereeing-assistance-programme/"
MIN_BODY = 20000

BLOCK = re.compile(
    r"<h(?P<level>[1-6])\b[^>]*>(?P<heading>.*?)</h(?P=level)\s*>|"
    r"<a\b[^>]*?\s+href\s*=\s*(?P<quote>[\"'])(?P<url>.*?)(?P=quote)[^>]*>"
    r"(?P<label>.*?)</a\s*>",
    re.I | re.S,
)
EDITION = re.compile(
    r"\b(?:(?P<women>women(?:['’]s|s)?\s+|w)(?=euro))?euro[\s-]+(?P<euro>20\d{2})\b|"
    r"\b(?P<year>20\d{2})(?:\s*[:–-]\s*|\s*\(\s*edition\s+)(?P<number>[1-9]\d?)\b",
    re.I,
)
DOWNLOAD_HOSTS = {"bit.ly", "we.tl", "wetransfer.com", "www.wetransfer.com"}


def clean(text):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text)).split())


def edition_key(text):
    match = EDITION.search(text)
    if not match:
        return ""
    if match["euro"]:
        prefix = "WEURO" if match["women"] else "EURO"
        return f"{prefix}-{match['euro']}"
    return f"{match['year']}-{match['number']}"


def discover(page):
    # WordPress 的读者留言也有自荐下载链接。索引只取文章正文。
    article = re.search(r"<article\b[^>]*>(.*?)</article\s*>", page, re.I | re.S)
    content = (
        article[1]
        if article
        else re.split(r"""\bid\s*=\s*["']comments["']""", page, maxsplit=1, flags=re.I)[
            0
        ]
    )
    editions = {}
    heading = ""
    for block in BLOCK.finditer(content):
        if block["heading"] is not None:
            heading = edition_key(clean(block["heading"]))
            continue
        label = clean(block["label"])
        explicit = edition_key(label)
        key = explicit or heading
        if not key or not (
            explicit or re.search(r"\b(nextaur|download|PC|MAC|link)\b", label, re.I)
        ):
            continue
        url = html.unescape(block["url"]).strip()
        try:
            parts = urlsplit(url)
        except ValueError:
            continue
        if (
            parts.scheme not in ("http", "https")
            or not parts.hostname
            or parts.username
            or parts.password
        ):
            continue
        # Nextaur 的同一组织入口可指向不同期；去重只在同一期内进行。
        editions.setdefault(key, {}).setdefault(url, label)
    return editions


def read_index(offline):
    cache = DUTCHREF_CACHE / "rap-index.html"
    if offline:
        if not cache.is_file():
            raise SystemExit(f"缺少 RAP 索引缓存：{cache}")
        page = cache.read_text(encoding="utf-8")
    else:
        status, page = fetch_text(INDEX, timeout=45, retries=3)
        if status != 200 or not page or len(page) <= MIN_BODY:
            raise SystemExit(f"RAP 索引抓取失败（HTTP {status}），已保留原缓存")
    found = discover(page)
    if not found:
        raise SystemExit("未解析出 RAP 期号与链接，请核对来源索引")
    if not offline:
        write_text(cache, page)
    return found


def platform(url, label, reviewed_downloads):
    parts = official_url(url, {"nextaur.com", "www.nextaur.com"})
    # Only publish already normalized paths in the UEFA organisation. Unfamiliar
    # encodings and alternate routes remain in the local review queue.
    if parts is not None and re.fullmatch(
        r"/uefa(?:/[A-Za-z0-9_~-][A-Za-z0-9._~-]*)*/?", parts.path
    ):
        return "nextaur"
    if (
        url in reviewed_downloads
        and urlsplit(url).hostname in DOWNLOAD_HOSTS
        and re.search(r"\b(download|PC|MAC)\b", label, re.I)
    ):
        return "download"
    return ""


def merge(found):
    data = json.loads(RAP_JSON.read_text(encoding="utf-8"))
    known = {edition_key(e["id"]) for e in data["editions"]}
    reviewed_downloads = {
        link["url"]
        for edition in data["editions"]
        if edition.get("era") == "download" and edition.get("status") != "unreviewed"
        for link in edition.get("links", [])
    }
    pending_path = DUTCHREF_CACHE / "pending-editions.json"
    previous = (
        json.loads(pending_path.read_text(encoding="utf-8"))
        if pending_path.exists()
        else {}
    )
    pending = {k: v for k, v in previous.items() if k not in known}
    additions = []
    for key, urls in found.items():
        if key in known:
            continue
        links = [{"label": label, "url": url} for url, label in urls.items()]
        platforms = {
            platform(url, label, reviewed_downloads) for url, label in urls.items()
        }
        # 欧洲杯名称中的年份可能不等于资料发布年份（如 EURO-2020）。
        if key[:4].isdigit() and len(platforms) == 1 and "" not in platforms:
            era = platforms.pop()
            additions.append(
                {
                    "id": key,
                    "title": f"RAP {key}",
                    "year": int(key[:4]),
                    "era": era,
                    "platform": era,
                    "status": "unreviewed",
                    "status_cn": "待人工核对",
                    "links": links,
                    "note_cn": "来源索引新增，期数与链接待人工核对。",
                }
            )
            pending.pop(key, None)
        else:
            saved = {link["url"]: link for link in pending.get(key, [])}
            saved.update({link["url"]: link for link in links})
            pending[key] = list(saved.values())
    if additions:
        data["editions"] = additions + data["editions"]
        write_json(RAP_JSON, data)
    if previous != pending:
        write_json(pending_path, pending)
    print(f"新增待核 {len(additions)} 期；{len(pending)} 期需核对发布平台或年份")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("fetch", "merge"), nargs="?", default="fetch")
    parser.add_argument("--offline", action="store_true", help="使用本地索引缓存")
    args = parser.parse_args()
    found = read_index(args.offline)
    for key, urls in found.items():
        print(f"RAP {key}")
        for url, label in urls.items():
            print(f"  {label}  {url}")
    if args.mode == "merge":
        merge(found)


if __name__ == "__main__":
    main()
