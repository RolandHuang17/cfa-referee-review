# -*- coding: utf-8 -*-
"""第二轮队徽自动补充:Wikimedia Commons 文件搜索 + 英文维基词条图片。
与 fetch_crests_online.py 同一套严格评分(仅本队名匹配),结果仍需人工目检后生效。"""

import json
import re
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from lib import safe_http as S
from lib.crest_candidates import collect
from lib.paths import TEAMS_JSON

S.ALLOWED_HOSTS |= {
    "zh.wikipedia.org",
    "en.wikipedia.org",
    "commons.wikimedia.org",
    "upload.wikimedia.org",
    "thumb.wikimedia.org",
}
PREFER = re.compile(r"logo|crest|队徽|徽标|shield|football.?club|\.fc\b|\.f\.c", re.I)
NOISE = re.compile(
    r"flag|kit|stadium|map|icon|commons|wikimedia|nike|adidas|ball|sponsor|jersey|shirt",
    re.I,
)


def api(host, params):
    query = "&".join(f"{k}={S.safe_urlencode(v)}" for k, v in params.items())
    last = None
    for attempt in range(4):  # 429/503 退避
        status, text = S.fetch_text(
            f"https://{host}/w/api.php?{query}", timeout=8, retries=1
        )
        if status == 200 and text.startswith("{"):
            time.sleep(0.5)
            return json.loads(text)
        last = f"API {host} {status}"
        if status in (429, 503) or status is None:
            time.sleep(3 * 2**attempt)
            continue
        raise RuntimeError(last)
    raise RuntimeError(last)


def score_image(title, team):
    if NOISE.search(title) or not PREFER.search(title):
        return None
    score = 4 if re.search(r"logo|crest|队徽", title, re.I) else 2
    key = re.sub(r"(足球俱乐部|足球俱乐部有限公司|足球俱乐部股份)$", "", team)
    if key[:2] in title:
        score += 2
    return score


def commons_candidates(team):
    """Commons File 命名空间搜索,标题须含队名关键字。"""
    key = re.sub(r"(足球俱乐部|女足)$", "", team)[:4]
    data = api(
        "commons.wikimedia.org",
        {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": "6",
            "gsrlimit": "12",
            "gsrsearch": f"{key} logo",
        },
    )
    pages = data.get("query", {}).get("pages", {})
    choices = []
    for page in pages.values():
        title = page.get("title", "")
        if key[:2] not in title and team[:2] not in title:
            continue
        score = score_image(title, team)
        if score:
            choices.append(
                (
                    score,
                    title,
                    f"https://commons.wikimedia.org/wiki/{S.safe_urlencode(title)}",
                )
            )
    if not choices:
        return None
    best = sorted(choices, reverse=True)[0]
    return ("commons.wikimedia.org", best[1], best[2])


def enwiki_candidates(team):
    """英文维基本队词条图片(词条标题按常见英文名模式搜索)。"""
    data = api(
        "en.wikipedia.org",
        {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrlimit": "3",
            "gsrsearch": team,
        },
    )
    pages = sorted(
        data.get("query", {}).get("pages", {}).values(),
        key=lambda x: x.get("index", 999),
    )
    best = None
    for page in pages:
        images = api(
            "en.wikipedia.org",
            {
                "action": "query",
                "format": "json",
                "prop": "images",
                "imlimit": "100",
                "titles": page.get("title", ""),
            },
        )
        for p in images.get("query", {}).get("pages", {}).values():
            for image in p.get("images", []):
                title = image.get("title", "")
                if (
                    team[:2] not in title
                    and re.sub(r"(足球俱乐部|女足)$", "", team)[:2] not in title
                ):
                    continue
                score = score_image(title, team)
                if score and (best is None or score > best[1]):
                    best = (
                        "en.wikipedia.org",
                        title,
                        f"https://en.wikipedia.org/wiki/{S.safe_urlencode(page.get('title', ''))}",
                    )
    return best


def image_url(host, title):
    data = api(
        host,
        {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": "240",
        },
    )
    for page in data.get("query", {}).get("pages", {}).values():
        info = page.get("imageinfo", [{}])[0]
        return info.get("thumburl") or info.get("url")
    return None


def lookup(team):
    picked = commons_candidates(team) or enwiki_candidates(team)
    if picked:
        host, title, source = picked
        url = image_url(host, title)
        if url:
            return url, source
    return None


def main():
    collect(TEAMS_JSON, lookup)


if __name__ == "__main__":
    main()
