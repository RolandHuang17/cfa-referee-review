# -*- coding: utf-8 -*-
"""抓取中国足协裁判评议文章页HTML（2024/2025双赛季）
用法: python fetch_issues.py [赛季] [期数...]
输出: data/issues_raw/{season}/issue_NN.html
"""
import re
import sys
import time
from pathlib import Path

from safe_http import fetch_text

BASE = "https://www.thecfa.cn"
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "issues_raw"

# 期数 -> (URL路径, 预期发布日期)
ISSUES = {
    "2025": {
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
    },
    "2024": {
        1: ("/zyls1/20240311/33847.html", "2024-03-11"),
        2: ("/zyls1/20240403/34026.html", "2024-04-03"),
        3: ("/zyls1/20240417/34203.html", "2024-04-17"),
        4: ("/zyls1/20240424/34242.html", "2024-04-24"),
        5: ("/zyls1/20240430/34273.html", "2024-04-30"),
        6: ("/zyls1/20240504/34283.html", "2024-05-04"),
        7: ("/zyls1/20240508/34347.html", "2024-05-08"),
        8: ("/zyls1/20240515/34422.html", "2024-05-15"),
        9: ("/zyls1/20240529/34512.html", "2024-05-29"),
        10: ("/zyls1/20240612/34609.html", "2024-06-12"),
        11: ("/zyls1/20240619/34632.html", "2024-06-19"),
        12: ("/zyls1/20240703/34717.html", "2024-07-03"),
        13: ("/zyls1/20240710/34755.html", "2024-07-10"),
        14: ("/zyls1/20240717/34776.html", "2024-07-17"),
        15: ("/zyls1/20240725/34794.html", "2024-07-25"),
        16: ("/zyls1/20240731/34836.html", "2024-07-31"),
        17: ("/zyls1/20240807/34876.html", "2024-08-07"),
        18: ("/zyls1/20240821/34955.html", "2024-08-21"),
        19: ("/zyls1/20240829/34973.html", "2024-08-29"),
        20: ("/20240904/35000.html", "2024-09-04"),
        21: ("/zyls1/20240912/35042.html", "2024-09-12"),
        22: ("/zyls1/20240919/35054.html", "2024-09-19"),
        23: ("/zyls1/20240925/35077.html", "2024-09-25"),
        24: ("/zyls1/20241009/35116.html", "2024-10-09"),
        25: ("/zyls1/20241023/35228.html", "2024-10-23"),
        26: ("/zyls1/20241030/35271.html", "2024-10-30"),
        27: ("/zyls1/20241130/35387.html", "2024-11-30"),
    },
}


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def main():
    season = sys.argv[1] if len(sys.argv) > 1 else "2025"
    issues = ISSUES[season]
    only = [int(x) for x in sys.argv[2:]] or sorted(issues)
    outdir = RAW / season
    outdir.mkdir(parents=True, exist_ok=True)
    fails = []
    for n in only:
        path, _ = issues[n]
        out = outdir / f"issue_{n:02d}.html"
        if out.exists() and out.stat().st_size > 10000:
            print(f"[{season}-{n:02d}] 已存在，跳过")
            continue
        try:
            status, html = fetch_text(BASE + path)
            if status != 200:
                raise RuntimeError(f"HTTP {status}")
            m = re.search(r"<title>(.*?)</title>", html, re.S)
            title = strip_tags(m.group(1)) if m else ""
            out.write_text(html, encoding="utf-8")
            print(f"[{season}-{n:02d}] OK {len(html)}字节  {title[:46]}")
        except Exception as e:  # noqa: BLE001
            fails.append(n)
            print(f"[{season}-{n:02d}] 失败: {e}")
        time.sleep(0.4)
    print(f"\n{season}赛季完成，失败: {fails if fails else '无'}")


if __name__ == "__main__":
    main()
