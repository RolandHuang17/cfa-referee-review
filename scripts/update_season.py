# -*- coding: utf-8 -*-
"""赛季增量更新一键编排：按 AGENTS.md「数据管线」的固定顺序串起各步骤。

用法（仓库根执行）:
  python scripts/update_season.py 2026                # 全流程：fetch → parse → … → test
  python scripts/update_season.py 2026 --skip-fetch   # 官方页面已抓过，跳过第 1 步
  python scripts/update_season.py 2026 --dry-run      # 只打印将执行的命令序列，不运行
  python scripts/update_season.py 2026 --discover     # 全流程前先跑 enum_issues 探测新期 URL

顺序是硬约束：fix_issue27_merge 必须在 classify 之前（拆分结构），classify 末尾含
赛季特判，改了前面步骤后必须 build_all 收尾——单脚本锁死顺序即防漏步错位。
人工环节不属于本脚本（跑完后按末尾提示补做）：比分查证、pending 判定复核、视频下载。
新期接入仍需先人工把 URL 写入 fetch_issues.ISSUES 与 parse_issues.ISSUE_URL 两处
（--discover 可先探测）；两表一致性由 tests/test_integrity.py 断言。

安全说明：传给子进程的脚本名与参数全部来自下面的字面量步骤表；命令行输入只用于
在三个常量表之间做 == 选择（choices 白名单 + 二次校验），不进入任何执行参数。
子进程统一走 build_all.run()（列表参数、shell=False、check=True）。
"""
import argparse

from build_all import run

from lib.paths import ROOT

# 公共收尾：impact 之后各赛季完全一致
# （test 步骤存绝对路径——build_all.run 的 SCRIPTS / 绝对路径 按 pathlib 语义原样保留）
_TAIL = [
    ("generate_teams_catalog.py", [], "队伍目录重建"),
    ("fetch_crests.py", [], "队徽目录校验"),
    ("build_all.py", [], "全站重建"),
    (str(ROOT / "tests" / "test_integrity.py"), [], "完整性断言"),
]
DISCOVER_STEP = ("enum_issues.py", [], "探测新期 URL（人工核对后写入两处 URL 表）")

# 三赛季步骤表：全部字面量；顺序 = AGENTS.md 数据管线，勿调换
_STEPS_2024 = [
    ("fetch_issues.py", ["2024"], "抓取官方页面存档"),
    ("parse_issues.py", ["2024"], "解析 → cases JSON"),
    ("classify_cases.py", ["2024"], "教学分类与结论复核"),
    ("make_impact_2024.py", [], "错漏判影响标注"),
] + _TAIL
_STEPS_2025 = [
    ("fetch_issues.py", ["2025"], "抓取官方页面存档"),
    ("parse_issues.py", ["2025"], "解析 → cases JSON"),
    ("fix_issue27_merge.py", [], "拆分第27期内嵌的第26期补充认定（必须在 classify 前）"),
    ("classify_cases.py", ["2025"], "教学分类与结论复核"),
    ("make_impact.py", [], "错漏判影响标注"),
] + _TAIL
_STEPS_2026 = [
    ("fetch_issues.py", ["2026"], "抓取官方页面存档"),
    ("parse_issues.py", ["2026"], "解析 → cases JSON"),
    ("classify_cases.py", ["2026"], "教学分类与结论复核"),
    ("make_impact_2026.py", [], "错漏判影响标注"),
] + _TAIL
TABLE = {"2024": _STEPS_2024, "2025": _STEPS_2025, "2026": _STEPS_2026}


def main():
    ap = argparse.ArgumentParser(description="赛季增量更新一键编排")
    ap.add_argument("season", choices=["2024", "2025", "2026"], help="赛季")
    ap.add_argument("--skip-fetch", action="store_true", help="跳过 fetch_issues（页面已抓过）")
    ap.add_argument("--dry-run", action="store_true", help="只打印命令序列，不执行")
    ap.add_argument("--discover", action="store_true", help="先跑 enum_issues 探测新期 URL")
    args = ap.parse_args()
    if args.season == "2024":
        steps = list(_STEPS_2024)
    elif args.season == "2025":
        steps = list(_STEPS_2025)
    elif args.season == "2026":
        steps = list(_STEPS_2026)
    else:  # 白名单二次校验（defence in depth）
        raise SystemExit(f"未知赛季: {args.season}")

    if args.discover:
        steps.insert(0, DISCOVER_STEP)
    if args.skip_fetch:
        steps = [st for st in steps if st[0] != "fetch_issues.py"]

    print(f"=== {args.season} 赛季更新，共 {len(steps)} 步 ===")
    for i, (script, argv, desc) in enumerate(steps, 1):
        print(f"  {i}. {script} {' '.join(argv)}  — {desc}")
    if args.dry_run:
        print("(--dry-run：未执行)")
        return

    for i, (script, argv, _desc) in enumerate(steps, 1):
        print(f"\n[{i}/{len(steps)}] python {script} {' '.join(argv)}")
        run(script, *argv)

    print(f"""
=== 完成。人工环节提醒（按需补做）===
- 新增错漏判的比分查证：data/match-scores-{args.season}.json，补齐后重跑本脚本 --skip-fetch
- pending 判定的复核：见 classify_cases 输出与 cases-{args.season}.json
- 视频下载（耗时长，单独跑）：python scripts/download_videos_parallel.py {args.season}
  完成后可 python scripts/verify_videos.py {args.season} 校验
- 若判例数/判定分布变化：tests/test_integrity.py 的 EXPECTED 基准需同步
""")


if __name__ == "__main__":
    main()
