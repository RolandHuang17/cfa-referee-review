# -*- coding: utf-8 -*-
"""枚举 thecfa.cn /cppy/ 栏目(裁判评议结果发布)的列表页，输出评议文章 URL+标题+日期。
用途：新赛季接入时发现新期URL（如2027赛季），结果人工核对后写入
fetch_issues.py 的 ISSUES 表与 parse_issues.py 的 ISSUE_URL 表（两处同步）。
"""
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
from lib import safe_http as S

BASE = "https://www.thecfa.cn"
ITEM_RE = re.compile(r'href="(/cppy/\d{8}/\d+\.html)"[^>]*>([^<]*评议[^<]*)<')
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def fetch(url):
    status, text = S.fetch_text(url, timeout=15, retries=2)
    if status != 200 or "upgrade" in (text or "")[:400]:
        raise RuntimeError(f"fetch {url} -> {status} (失效页)")
    return text


def main():
    seen = {}
    for page in range(1, 8):
        url = BASE + "/cppy/index.html" if page == 1 else f"{BASE}/cppy/index_{page}.html"
        try:
            html = fetch(url)
        except Exception as exc:
            print(f"!! 列表页 {page}: {exc}")
            break
        for path, title in ITEM_RE.findall(html):
            if path not in seen:
                seen[path] = title.strip()
        dates = DATE_RE.findall(html)
        print(f"列表页 {page}: {len(seen)} 个候选, 页面日期样本 {dates[:3]}")
        if page > 1 and not ITEM_RE.search(html):
            break
    for path, title in sorted(seen.items(), key=lambda kv: kv[0], reverse=True):
        print(f"{path}  {title[:60]}")
    print(f"共 {len(seen)} 条")


if __name__ == "__main__":
    main()
