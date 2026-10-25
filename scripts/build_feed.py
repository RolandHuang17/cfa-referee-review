# -*- coding: utf-8 -*-
"""生成 site/feed.xml（Atom 订阅）：三赛季最新评议期目。

读者订阅的是「本站收录了什么新评议」——entry 链接直达中国足协官方文章页
（判定的第一手来源），summary 里同时给出本站对应赛季合集页入口。
日期取自官方 URL 路径（YYYYMMDD），时区按北京时间构造 RFC3339。
"""

import json
from xml.sax.saxutils import escape

from lib.paths import DATA, SITE
from lib.seo import SITE_NAME, SITE_URL

PER_SEASON = 8  # 每季取最新 N 期
MAX_ENTRIES = 40


def _iso(d: str) -> str:
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}T09:00:00+08:00"


def collect_entries():
    entries = []
    for season in ("2026", "2025", "2024"):
        path = DATA / f"cases-{season}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        issues = sorted(
            data.get("issues", []), key=lambda i: i.get("date", ""), reverse=True
        )
        for issue in issues[:PER_SEASON]:
            summary = (issue.get("summary") or "").strip()
            if len(summary) > 260:
                summary = summary[:260].rstrip() + "……"
            n_cases = sum(1 for c in data["cases"] if c["issue"] == issue["no"])
            summary += (
                f"（本期 {n_cases} 个判例，已收录于本站 "
                f"{SITE_URL}/season-{season}.html）"
            )
            entries.append(
                {
                    "id": issue["url"],
                    "title": f"{season} 赛季第{issue['no']}期裁判评议",
                    "url": issue["url"],
                    "updated": _iso(str(issue.get("date", ""))),
                    "summary": summary,
                }
            )
    entries.sort(key=lambda e: e["updated"], reverse=True)
    return entries[:MAX_ENTRIES]


def build_feed():
    entries = collect_entries()
    updated = entries[0]["updated"] if entries else "2026-01-01T00:00:00+08:00"
    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f"  <title>{escape(SITE_NAME)}·裁判评议更新</title>",
        f"  <id>{SITE_URL}/feed.xml</id>",
        f'  <link rel="self" href="{SITE_URL}/feed.xml"/>',
        f"  <updated>{updated}</updated>",
        "  <author><name>Roland Huang</name></author>",
    ]
    for e in entries:
        parts += [
            "  <entry>",
            f"    <title>{escape(e['title'])}</title>",
            f"    <id>{escape(e['id'])}</id>",
            f'    <link href="{escape(e["url"])}"/>',
            f"    <updated>{e['updated']}</updated>",
            "    <summary>" + escape(e["summary"]).replace("\n", " ") + "</summary>",
            "  </entry>",
        ]
    parts.append("</feed>")
    (SITE / "feed.xml").write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"feed.xml 构建完成: {len(entries)} 条期目")


if __name__ == "__main__":
    build_feed()
