# -*- coding: utf-8 -*-
"""站点完整性断言：页面自包含、数据计数、内部链接、队徽目录。

两种跑法，检查项完全一致：
  python tests/test_integrity.py   逐项打印 PASS/FAIL，末尾汇总全部问题，退出码即结论
  python -m pytest tests/          每个 check 独立报告

fail-collecting：每个 check 把问题攒进局部 list 再一次性 assert，所以一次运行
就能看到全部问题，不必修一个跑一遍。CI 走前一种，退出码非零即拦截部署。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 插 scripts/ 而不是 scripts/lib/，让 import 写成 from lib.crest_catalog import ...，
# 与入口脚本走完全相同的包布局——lib 包本身坏了这里就会失败，这是特性。
sys.path.insert(0, str(ROOT / "scripts"))

from lib.crest_catalog import load_catalog, normalize_team, validate_catalog  # noqa: E402
from lib.paths import DATA, SITE  # noqa: E402

PAGES = ["index.html", "season-2024.html", "season-2025.html", "season-2026.html",
         "stats-2024.html", "stats-2025.html", "stats-2026.html", "rules.html",
         "scale.html", "uefa.html", "quiz.html"]
SEASONS = ("2024", "2025", "2026")
# 每季期望值（人工复核后的基准，改动判例分类或解析需同步更新）
EXPECTED = {"2024": (160, 161, {"wrong": 60, "correct": 99, "pending": 1}),
            "2025": (227, 229, {"wrong": 82, "correct": 138, "pending": 7}),
            "2026": (225, 224, {"wrong": 95, "correct": 121, "pending": 9})}
# 考题模式题库基准：每季「有视频且有认定原文」的判例数 + 尺度场景数（改口径需同步）
EXPECTED_QUIZ = {"2024": 141, "2025": 227, "2026": 224}

FAILURES = []


def _finish(problems):
    FAILURES.extend(problems)
    assert not problems, "\n".join(problems)


def test_pages_exist_and_are_self_contained():
    problems = []
    for name in PAGES:
        path = SITE / name
        if not path.exists():
            problems.append(f"缺少 site/{name}")
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"__\w+__|\{\{[^}]+\}\}", text):
            problems.append(f"存在模板占位符: site/{name}")
        if re.search(r"<script\s+src=|fonts\.googleapis|cdnjs|unpkg|jsdelivr", text, re.I):
            problems.append(f"存在外部脚本或CDN引用: site/{name}")
    _finish(problems)


def test_season_case_counts():
    problems = []
    for season, (case_count, video_count, verdicts) in EXPECTED.items():
        data = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        cases = data["cases"]
        actual = {key: sum(1 for case in cases if case["referee_verdict"] == key)
                  for key in verdicts}
        videos = sum(len(case["video_files"]) for case in cases)
        if (len(cases), videos, actual) != (case_count, video_count, verdicts):
            problems.append(f"{season}数据统计不符: cases={len(cases)} videos={videos} "
                            f"verdicts={actual}，期望 {case_count}/{video_count}/{verdicts}")
    _finish(problems)


def test_internal_links_resolve():
    problems = []
    for path in SITE.glob("*.html"):
        for target in re.findall(r"(?:href|src)=\"([^\"]+)\"", path.read_text(encoding="utf-8")):
            if target.startswith(("#", "http://", "https://", "data:", "mailto:")) or "${" in target:
                continue
            if target.startswith("videos/"):
                continue  # 视频为本地 gitignored 资产，线上按需提供
            stem = target.split("#", 1)[0]
            if stem and not (path.parent / stem).resolve().exists():
                problems.append(f"{path.name} 引用了不存在的路径: {target}")
    _finish(problems)


def test_team_catalog_complete():
    catalog = load_catalog()
    names = {item["name"] for item in catalog.values()}
    raw_names = set()
    for season in SEASONS:
        data = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        for case in data["cases"]:
            raw_names.update(filter(None, (case.get("home"), case.get("away"))))
    problems = []
    for raw in sorted(raw_names):
        canonical = normalize_team(raw)
        if canonical not in names:
            problems.append(f"队伍未登记: {raw} -> {canonical}")
    slugs = [item.get("slug") for item in catalog.values()]
    if len(slugs) != len(set(slugs)):
        problems.append(f"队徽 slug 重复: {sorted({s for s in slugs if slugs.count(s) > 1})}")
    _finish(problems)
    print(f"队徽目录校验通过: {len(raw_names)} 个原始名称 -> {len(names)} 个标准队伍")


def test_crest_files_and_provenance():
    _finish(validate_catalog(load_catalog()))


def test_quiz_bank_pool():
    """考题模式题库回归基准：判例池（有视频+认定原文）与尺度场景池计数。"""
    problems = []
    bank_path = SITE / "quiz.html"
    if not bank_path.exists():
        problems.append("缺少 site/quiz.html")
        _finish(problems)
        return
    per_season = {s: 0 for s in SEASONS}
    for season in SEASONS:
        data = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        per_season[season] = sum(1 for c in data["cases"]
                                 if c.get("video_files") and (c.get("conclusion") or "").strip())
    text = bank_path.read_text(encoding="utf-8")
    m = re.search(r'"meta":\{"case":(\d+),"scale":(\d+)\}', text)
    if not m:
        problems.append("quiz.html 缺少 meta 题库统计（case/scale）")
    else:
        n_case, n_scale = int(m.group(1)), int(m.group(2))
        if n_case != sum(per_season.values()):
            problems.append(f"考题判例池不符: quiz={n_case}，期望 {sum(per_season.values())}（{per_season}）")
        scale_total = 0
        if (DATA / "scale.json").exists():
            sd = json.loads((DATA / "scale.json").read_text(encoding="utf-8"))
            for yd in sd.values():
                if not isinstance(yd, dict):
                    continue
                for sec in yd.get("sections", []):
                    for g in sec.get("groups", []):
                        for it in g.get("items", []):
                            dec = it.get("decision") or []
                            if dec and not any(x.get("label") == "VAR 机制讲解" for x in dec) \
                                    and it.get("video"):
                                scale_total += 1
        if n_scale != scale_total:
            problems.append(f"考题尺度场景池不符: quiz={n_scale}，期望 {scale_total}")
        for season, expected in EXPECTED_QUIZ.items():
            if per_season[season] != expected:
                problems.append(f"{season}考题判例池 {per_season[season]} != 基准 {expected}")
    _finish(problems)
    print(f"考题题库校验通过: 判例 {sum(per_season.values())} + 尺度场景 "
          f"{int(m.group(2)) if m else '?'} 题")


CHECKS = [
    test_pages_exist_and_are_self_contained,
    test_season_case_counts,
    test_quiz_bank_pool,
    test_internal_links_resolve,
    test_team_catalog_complete,
    test_crest_files_and_provenance,
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
        print(f"\n校验失败，共 {len(FAILURES)} 项：")
        for item in FAILURES:
            print(f"  - {item}")
        return 1
    print(f"\n项目校验通过: {len(PAGES)}个页面、三赛季数据、离线资源路径和外部引用均正常")
    return 0


if __name__ == "__main__":
    sys.exit(main())
