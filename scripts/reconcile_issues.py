# -*- coding: utf-8 -*-
"""只读对账：官方标题“认定错漏判数” vs 合集最终 wrong 数。

用法: python scripts/reconcile_issues.py [2024|2025|2026 ...]
不带参数=三季。差异不一定是错误（官方标题口径可能含漏判黄牌、低级别联赛等，
或合集按同一方法论改判），本脚本只把差异列出来供人工核对，不修改数据、不阻断 CI。
"""

import json
import sys

from lib.paths import DATA
from lib.site_stats import SEASONS
from lib.issue_notes import title_wrong_count


def main(argv):
    seasons = argv or list(SEASONS)
    total = undisclosed = 0
    for season in seasons:
        data = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        cases = data["cases"]
        print(f"\n=== {season} ===")
        for issue in data["issues"]:
            no = issue["no"]
            actual = sum(
                1
                for c in cases
                if c["issue"] == no and c.get("referee_verdict") == "wrong"
            )
            expected = title_wrong_count(issue)
            if expected is None:
                undisclosed += 1
                print(
                    f"期{no:02d}  标题未披露  合集 wrong {actual}  {issue.get('title', '')[:70]}"
                )
                continue
            if actual == expected:
                continue
            total += 1
            print(
                f"期{no:02d}  标题认定 {expected}  合集 wrong {actual}  "
                f"{issue.get('title', '')[:70]}"
            )
    print(
        f"\n明确数量差异 {total} 期；标题未披露数量 {undisclosed} 期（未披露不视为零，差异需按口径复核）"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
