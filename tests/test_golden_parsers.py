# -*- coding: utf-8 -*-
"""解析器 golden 回归：直接消费 data/issues/ 归档 HTML 与提交版 cases JSON。

两类断言，对应两类「一改就坏」的历史坑：
1. parse_issue()/parse_season() 对已知结构坑期次的输出形状——AGENTS 期数
   结构坑的机器化：2024 第1期结论摘要式、2026 第20期判例一无前缀兜底、
   官方 HTML 跨协议视频重复的去重口径；
2. 提交版 cases-*.json 中**管线无法复现的人工数据**的存在性——2025 含
   人工精修的对阵/赛事/结论申诉引语与 seq215 改判（重跑 parse 会覆盖丢失），
   2026 seq195 与 2024 第1期的对阵是 classify_cases.py 赛季特判的产物。
   把它们钉死：数据被管线意外覆写时这里第一时间爆红。

两种跑法与 test_integrity.py 一致：裸跑逐项汇总 / pytest 独立收集。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.paths import DATA, ISSUES  # noqa: E402
from parse_issues import parse_issue, parse_season  # noqa: E402

FAILURES = []


def _finish(problems):
    FAILURES.extend(problems)
    assert not problems, "\n".join(problems)


def _load_committed(season):
    return json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))


def _parse_archived(season, no):
    html = (ISSUES / season / f"issue_{no:02d}.html").read_text(encoding="utf-8")
    # URL 只被用于取 date（/YYYYMMDD/），伪造一个同结构占位即可
    return parse_issue(
        html, no, f"https://www.thecfa.cn/cppy/20000101/{no:02d}.html", seq=0
    )


def test_parse_2026_issue20_first_case_without_prefix():
    """2026 第20期判例一无「判例N:」前缀：以申诉行识别、前一非空段落作对阵描述。"""
    issue, cases, seq = _parse_archived("2026", 20)
    problems = []
    if len(cases) != 2:
        problems.append(f"2026 第20期应解析出 2 个判例，实际 {len(cases)}")
    else:
        first = cases[0]
        if first["no"] != 1:
            problems.append(f"无前缀首判例 no 应兜底为 1，实际 {first['no']}")
        if first["seq"] != 1 or seq != 2:
            problems.append(f"seq 计数异常: 首={first['seq']} 末={seq}")
        if first["desc"].startswith("判例"):
            problems.append("首判例 desc 应为无前缀的对阵描述段落")
        if "申诉意见认为" not in first["appeal"]:
            problems.append("首判例 appeal 应含申诉意见行")
    if issue["expected_wrong"] != 0:
        problems.append(
            f"2026 第20期标题认定数应为 0（认定无错漏判），实际 {issue['expected_wrong']}"
        )
    _finish(problems)


def test_parse_2024_issue1_summary_style():
    """2024 第1期为结论摘要式文章：判例可解析但 parse 层不带对阵/赛事（classify 特判补全）。"""
    issue, cases, _ = _parse_archived("2024", 1)
    problems = []
    if len(cases) != 3:
        problems.append(f"2024 第1期应解析出 3 个判例，实际 {len(cases)}")
    for c in cases:
        for field in ("comp", "home", "away"):
            if c[field]:
                problems.append(
                    f"seq{c['seq']} parse 层 {field} 应为空（{field}={c[field]!r}），"
                    "对阵是 classify_cases.py 特判补的"
                )
    if issue["video_count"] != 0:
        problems.append(f"2024 第1期应无视频，实际 {issue['video_count']}")
    if issue["expected_wrong"] != 0:
        problems.append(f"2024 第1期标题认定数应为 0，实际 {issue['expected_wrong']}")
    _finish(problems)


def test_parse_season_2025_video_dedup():
    """官方 HTML 同一视频以 http/https 各嵌一次（2025 第22期实测）：
    video_urls 必须按归一化 URL 去重、video_count 按去重后口径计数。"""
    data = parse_season("2025")
    problems = []
    by_no = {i["no"]: i for i in data["issues"]}
    if by_no[22]["video_count"] != 2:
        problems.append(
            f"第22期 video_count 应为 2（去重口径），实际 {by_no[22]['video_count']}"
        )
    by_seq = {c["seq"]: c for c in data["cases"]}
    c163 = by_seq[163]
    urls = c163["video_urls"]
    if len(urls) != 1 or len(set(urls)) != len(urls):
        problems.append(f"seq163 video_urls 应去重为 1 条，实际 {urls}")
    for c in data["cases"]:
        if len(c["video_urls"]) != len(set(c["video_urls"])):
            problems.append(f"seq{c['seq']} video_urls 存在重复 URL")
            break
    # fix_issue27_merge 的前置条件：拆分前 #195 应有 3 段视频、期27 解析为 2 判例
    if len(by_seq[195]["video_urls"]) != 3:
        problems.append(
            f"拆分前 #195 应有 3 段视频，实际 {len(by_seq[195]['video_urls'])}"
        )
    if sum(1 for c in data["cases"] if c["issue"] == 27) != 2:
        problems.append("第27期应解析出 2 个判例（拆分前的合并形态）")
    _finish(problems)


def test_committed_manual_enrichment_2025():
    """2025 cases JSON 含管线外人工数据（对 2025 重跑 parse 会静默丢失，本测试负责看护）。"""
    cases = {c["seq"]: c for c in _load_committed("2025")["cases"]}
    problems = []
    expect_values = [
        (11, "home", "南京城市"),
        (11, "away", "大连鲲城"),
        (48, "comp", "中超联赛"),
        (84, "comp", "全运会"),
    ]
    for seq, field, want in expect_values:
        got = cases[seq].get(field)
        if got != want:
            problems.append(
                f"2025 seq{seq} {field} 应为 {want!r}，实际 {got!r}"
                "（人工精修数据疑似被管线覆写）"
            )
    if not cases[126]["conclusion"].startswith("杭州临平吴越俱乐部在申诉中提及"):
        problems.append(
            "2025 seq126 conclusion 应含申诉引语前缀（人工补充，非 parse 产物）"
        )
    # seq215 改判（2025-10 人工复核：官方红牌问题不予认定但黄牌认定明确）
    c215 = cases[215]
    if c215["referee_verdict"] != "wrong" or "漏判黄牌" not in c215["tags"]:
        problems.append(
            f"2025 seq215 应为 wrong+漏判黄牌，实际 {c215['referee_verdict']}"
            f"/{c215['tags']}"
        )
    # fix27+classify 的语义校正产物
    c195 = cases[195]
    if (c195["issue"], c195["no"], c195["referee_verdict"]) != (27, 2, "correct"):
        problems.append(
            f"2025 seq195 应为 第27期判例2/correct，实际 {c195['issue']}/"
            f"{c195['no']}/{c195['referee_verdict']}"
        )
    _finish(problems)


def test_committed_special_fixes_2024_2026():
    """classify_cases.py 赛季特判的产物锚点：2024 第1期对阵补全、2026 seq195 对阵补全。"""
    problems = []
    c24 = {c["seq"]: c for c in _load_committed("2024")["cases"]}
    if (c24[1]["comp"], c24[1]["home"], c24[1]["away"]) != (
        "中超联赛",
        "浙江",
        "上海海港",
    ):
        problems.append(
            f"2024 seq1 对阵特判异常: {c24[1]['comp']}/{c24[1]['home']}/"
            f"{c24[1]['away']}"
        )
    for seq in (2, 3):
        c = c24[seq]
        if (c["comp"], c["home"], c["away"]) != ("中甲联赛", "佛山南狮", "云南玉昆"):
            problems.append(
                f"2024 seq{seq} 对阵特判异常: {c['comp']}/{c['home']}/{c['away']}"
            )
    c26 = {c["seq"]: c for c in _load_committed("2026")["cases"]}
    c195 = c26[195]
    if (c195["issue"], c195["no"]) != (17, 9):
        problems.append(
            f"2026 seq195 应为 第17期判例9，实际 {c195['issue']}/{c195['no']}"
        )
    if (c195["comp"], c195["home"], c195["away"]) != (
        "中超联赛",
        "山东泰山",
        "天津津门虎",
    ):
        problems.append(
            f"2026 seq195 对阵补全异常: {c195['comp']}/{c195['home']}/{c195['away']}"
        )
    _finish(problems)


CHECKS = [
    test_parse_2026_issue20_first_case_without_prefix,
    test_parse_2024_issue1_summary_style,
    test_parse_season_2025_video_dedup,
    test_committed_manual_enrichment_2025,
    test_committed_special_fixes_2024_2026,
]


def main():
    for check in CHECKS:
        try:
            check()
        except AssertionError:
            print(f"FAIL {check.__name__}")
        else:
            print(f"PASS {check.__name__}")
    if FAILURES:
        print(f"\ngolden 校验失败，共 {len(FAILURES)} 项：")
        for item in FAILURES:
            print(f"  - {item}")
        return 1
    print("\ngolden 解析器与人工数据锚点全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
