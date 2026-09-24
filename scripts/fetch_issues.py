# -*- coding: utf-8 -*-
"""抓取2025赛季32期裁判评议文章页HTML，存入 data/issues_raw/issue_NN.html"""
import re
import sys
import time
from pathlib import Path

from safe_http import fetch_text

BASE = "https://www.thecfa.cn"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "issues_raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 期数 -> (URL路径, 预期发布日期)
ISSUES = {
    1: ("/zyls1/20250227/35667.html", "2025-02-27"),
    2: ("/zyls1/20250305/35703.html", "2025-03-05"),
    3: ("/zyls1/20250319/35769.html", "2025-03-19"),
    4: ("/zyls1/20250328/35803.html", "2025-03-28"),
    5: ("/zyls1/20250402/35819.html", "2025-04-02"),
    6: ("/zyls1/20250409/35844.html", "2025-04-09"),
    7: ("/zyls1/20250416/35868.html", "2025-04-16"),
    8: ("/zyls1/20250423/35901.html", "2025-04-23"),
    9: ("/zyls1/20250501/35914.html", "2025-05-01"),
    10: ("/zyls1/20250507/36449.html", "2025-05-07"),
    11: ("/zyls1/20250514/36471.html", "2025-05-14"),
    12: ("/zyls1/20250521/36493.html", "2025-05-21"),
    13: ("/zyls1/20250604/36545.html", "2025-06-04"),
    14: ("/zyls1/20250618/36597.html", "2025-06-18"),
    15: ("/zyls1/20250625/36616.html", "2025-06-25"),
    16: ("/zyls1/20250703/36647.html", "2025-07-03"),
    17: ("/zyls1/20250709/36668.html", "2025-07-09"),
    18: ("/zyls1/20250718/36707.html", "2025-07-18"),
    19: ("/zyls1/20250724/36722.html", "2025-07-24"),
    20: ("/zyls1/20250730/36757.html", "2025-07-30"),
    21: ("/zyls1/20250806/36774.html", "2025-08-06"),
    22: ("/zyls1/20250813/36785.html", "2025-08-13"),
    23: ("/zyls1/20250820/36819.html", "2025-08-20"),
    24: ("/cppy/20250827/36854.html", "2025-08-27"),
    25: ("/cppy/20250903/36876.html", "2025-09-03"),
    26: ("/cppy/20250917/36917.html", "2025-09-17"),
    27: ("/cppy/20250924/36927.html", "2025-09-24"),
    28: ("/cppy/20251001/36955.html", "2025-10-01"),
    29: ("/cppy/20251008/36962.html", "2025-10-08"),
    30: ("/cppy/20251022/37010.html", "2025-10-22"),
    31: ("/cppy/20251029/37036.html", "2025-10-29"),
    32: ("/cppy/20251105/37055.html", "2025-11-05"),
}

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def main():
    only = [int(x) for x in sys.argv[1:]] or sorted(ISSUES)
    report = []
    for n in only:
        path, _ = ISSUES[n]
        out = OUT_DIR / f"issue_{n:02d}.html"
        if out.exists() and out.stat().st_size > 10000:
            print(f"[{n:02d}] 已存在，跳过")
            report.append((n, "cached"))
            continue
        try:
            status, html = fetch_text(BASE + path)
            if status != 200 or "upgrade" in BASE + path:
                raise RuntimeError(f"HTTP {status}")
            m = TITLE_RE.search(html)
            title = strip_tags(m.group(1)) if m else ""
            if not re.search(r"2025赛季第[一二三四五六七八九十百]+期", title):
                print(f"[{n:02d}] 警告: 标题未匹配到期数: {title}")
            out.write_text(html, encoding="utf-8")
            print(f"[{n:02d}] OK {len(html)}字节  {title}")
            report.append((n, title))
        except Exception as e:  # noqa: BLE001
            print(f"[{n:02d}] 失败: {e}")
            report.append((n, "FAILED"))
        time.sleep(0.4)
    fails = [n for n, t in report if t == "FAILED"]
    print(f"\n完成，失败: {fails if fails else '无'}")


if __name__ == "__main__":
    main()
