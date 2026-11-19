# -*- coding: utf-8 -*-
"""补充人工目录中缺失的队徽，候选图必须来自明确的 Wikimedia 页面。"""

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
    "upload.wikimedia.org",
    "commons.wikimedia.org",
    "thumb.wikimedia.org",
}
PREFER = re.compile(r"logo|crest|队徽|徽标|shield|football.?club|\.fc\b|\.f\.c", re.I)
NOISE = re.compile(
    r"flag|kit|stadium|map|icon|commons|wikimedia|nike|adidas|ball|sponsor", re.I
)


def api(params):
    query = "&".join(f"{k}={S.safe_urlencode(v)}" for k, v in params.items())
    last = None
    for attempt in range(5):  # 429 限流退避：2/6/18/54s，末次固定 48s
        status, text = S.fetch_text(
            f"https://zh.wikipedia.org/w/api.php?{query}", timeout=8, retries=1
        )
        if status == 200 and text.startswith("{"):
            time.sleep(0.6)
            return json.loads(text)
        last = f"Wikipedia API {status}"
        if status in (429, 503):
            time.sleep(2 * 3**attempt if attempt < 4 else 48)
            continue
        raise RuntimeError(last)
    raise RuntimeError(last)


def score_image(title, team):
    if NOISE.search(title) or not PREFER.search(title):
        return None
    score = 4 if re.search(r"logo|crest|队徽", title, re.I) else 2
    if team[:2] in title:
        score += 2
    return score


def own_article_images(team):
    """仅取本队词条(精确标题)的图片，保证队徽来源即本俱乐部。女足等词条无"足球俱乐部"后缀，两种标题都试。"""
    for article in (team + "足球俱乐部", team):
        data = api(
            {
                "action": "query",
                "format": "json",
                "prop": "images",
                "imlimit": "200",
                "titles": article,
            }
        )
        for pid, page in data.get("query", {}).get("pages", {}).items():
            if pid == "-1":
                continue
            images = [image.get("title", "") for image in page.get("images", [])]
            if images:
                return images, article
    return [], team + "足球俱乐部"


def candidate(team):
    # 优先且仅用本队词条图片：跨页面混选曾让名队队徽(如北京国安)覆盖目标队
    images, article = own_article_images(team)
    for title in images:
        score = score_image(title, team)
        if score:
            return (score, title, article)
    # 本队词条无队徽时才回退搜索池，且图片标题必须含队名，杜绝跨俱乐部误配
    data = api(
        {
            "action": "query",
            "format": "json",
            "prop": "images",
            "imlimit": "200",
            "generator": "search",
            "gsrlimit": "5",
            "gsrsearch": team + " 足球俱乐部",
        }
    )
    pages = sorted(
        data.get("query", {}).get("pages", {}).values(),
        key=lambda x: x.get("index", 999),
    )
    choices = []
    for page in pages:
        for image in page.get("images", []):
            title = image.get("title", "")
            if team[:2] not in title:
                continue
            score = score_image(title, team)
            if score:
                choices.append((score, title, page.get("title", "")))
    if not choices:
        return None
    return sorted(choices, reverse=True)[0]


def image_url(title):
    data = api(
        {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": "240",
        }
    )
    for page in data.get("query", {}).get("pages", {}).values():
        info = page.get("imageinfo", [{}])[0]
        return info.get("thumburl") or info.get("url")
    return None


def lookup(team):
    picked = candidate(team)
    if picked:
        url = image_url(picked[1])
        if url:
            return url, f"https://zh.wikipedia.org/wiki/{S.safe_urlencode(picked[2])}"
    return None


def main():
    collect(TEAMS_JSON, lookup)


if __name__ == "__main__":
    main()
