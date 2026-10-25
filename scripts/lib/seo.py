# -*- coding: utf-8 -*-
"""SEO/发现层共享件：meta 标签块、favicon（SVG data-URI，保单文件自包含）、JSON-LD。

pages.py 是标题/描述的唯一权威源；各页 <title> 仍是更口语化的浏览器标签文案，
两层职责不同（tab 标题 vs 搜索引擎/社交分享卡）——不要把 <title> 删了只留这里。

用法：inject_theme(html, meta=meta_tags("xxx.html")) 在 </head> 前注入；
og/canonical 基于 lib.pages 的 file/title/desc 生成，feed.xml 由 build_feed.py 产出。
"""

import json
from urllib.parse import quote

from lib.pages import by_file

SITE_URL = "https://rolandhuang17.github.io/cfa-referee-review"
SITE_NAME = "裁判学习一站式平台"

# 与 theme.py 的 shield 图标同源的极简 favicon（陶土色盾牌），URL 编码进 data-URI
_ICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="#b3573a" stroke="#8a3f27" stroke-width="1" '
    'd="M12 2l8 3.5V12c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10V5.5z"/>'
    '<path fill="none" stroke="#f7f2e7" stroke-width="1.8" stroke-linecap="round" '
    'd="M9 12l2 2 4-4"/></svg>'
)
FAVICON = "data:image/svg+xml," + quote(_ICON, safe="")


def _esc(value):
    return (
        (value or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    )


def jsonld_website():
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": SITE_URL + "/",
        "inLanguage": "zh-CN",
    }


def jsonld_dataset():
    return {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "中国足协裁判评议判例库（2024–2026）",
        "description": "三赛季 81 期裁判评议全量判例：事件描述、申诉意见、评议组认定原文、"
        "教学分类与错漏判影响标注。",
        "url": SITE_URL + "/",
        "inLanguage": "zh-CN",
        "isAccessibleForFree": True,
        "license": "https://github.com/RolandHuang17/cfa-referee-review/blob/main/NOTICE.md",
        "creator": {"@type": "Person", "name": "Roland Huang"},
    }


def meta_tags(page_file, extra_jsonld=None):
    """生成某页的 <head> meta 块（description/canonical/og/twitter/favicon/feed 发现）。

    extra_jsonld: 额外的 schema.org 对象（或对象列表），以 ld+json 内联。
    """
    p = by_file(page_file)
    url = f"{SITE_URL}/{page_file}"
    lines = []
    if page_file == "404.html":
        lines.append('<meta name="robots" content="noindex">')
    else:
        lines.append(f'<meta name="description" content="{_esc(p["desc"])}">')
        lines.append(f'<link rel="canonical" href="{url}">')
        lines += [
            '<meta property="og:type" content="website">',
            f'<meta property="og:site_name" content="{SITE_NAME}">',
            '<meta property="og:locale" content="zh_CN">',
            f'<meta property="og:title" content="{_esc(p["title"])}">',
            f'<meta property="og:description" content="{_esc(p["desc"])}">',
            f'<meta property="og:url" content="{url}">',
            '<meta name="twitter:card" content="summary">',
        ]
    lines += [
        f'<link rel="icon" href="{FAVICON}">',
        '<link rel="manifest" href="manifest.webmanifest">',
        '<link rel="alternate" type="application/atom+xml" '
        f'title="{SITE_NAME}·评议更新订阅" href="feed.xml">',
    ]
    blocks = (
        list(extra_jsonld)
        if isinstance(extra_jsonld, (list, tuple))
        else ([extra_jsonld] if extra_jsonld else [])
    )
    for obj in blocks:
        payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace(
            "</", "<\\/"
        )
        lines.append(f'<script type="application/ld+json">{payload}</script>')
    return "\n".join(lines)
