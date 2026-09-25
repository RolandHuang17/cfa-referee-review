# -*- coding: utf-8 -*-
"""Check generated site structure, data counts, paths, and offline constraints."""
import json
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from crest_catalog import load_catalog, normalize_team

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PAGES = ["index.html", "season-2024.html", "season-2025.html",
         "stats-2024.html", "stats-2025.html", "rules.html"]


def fail(message):
    raise SystemExit(f"校验失败: {message}")


def main():
    for name in PAGES:
        path = SITE / name
        if not path.exists():
            fail(f"缺少 site/{name}")
        text = path.read_text(encoding="utf-8")
        if re.search(r"__\w+__|\{\{[^}]+\}\}", text):
            fail(f"存在模板占位符: site/{name}")
        if re.search(r"<script\s+src=|fonts\.googleapis|cdnjs|unpkg|jsdelivr", text, re.I):
            fail(f"存在外部脚本或CDN引用: site/{name}")

    expected = {"2024": (160, 161, {"wrong": 60, "correct": 99, "pending": 1}),
                "2025": (227, 229, {"wrong": 82, "correct": 138, "pending": 7})}
    for season, (case_count, video_count, verdicts) in expected.items():
        data = json.loads((ROOT / "data" / f"cases-{season}.json").read_text(encoding="utf-8"))
        cases = data["cases"]
        actual = {key: sum(1 for case in cases if case["referee_verdict"] == key)
                  for key in verdicts}
        videos = sum(len(case["video_files"]) for case in cases)
        if (len(cases), videos, actual) != (case_count, video_count, verdicts):
            fail(f"{season}数据统计不符: cases={len(cases)}, videos={videos}, verdicts={actual}")

    for path in SITE.glob("*.html"):
        for target in re.findall(r"(?:href|src)=\"([^\"]+)\"", path.read_text(encoding="utf-8")):
            if target.startswith(("#", "http://", "https://", "data:", "mailto:")) or "${" in target:
                continue
            target_path = (path.parent / target.split("#", 1)[0]).resolve()
            if target.split("#", 1)[0] and not target_path.exists():
                fail(f"{path.name} 引用了不存在的路径: {target}")

    catalog = load_catalog()
    names = {item["name"] for item in catalog.values()}
    raw_names = set()
    for season in ("2024", "2025"):
        data = json.loads((ROOT / "data" / f"cases-{season}.json").read_text(encoding="utf-8"))
        for case in data["cases"]:
            raw_names.update(filter(None, (case.get("home"), case.get("away"))))
    if len(raw_names) != 107:
        fail(f"队伍原始名称数量异常: {len(raw_names)}")
    for raw in raw_names:
        canonical = normalize_team(raw)
        if canonical not in names:
            fail(f"队伍未登记: {raw} -> {canonical}")
    slugs = [item.get("slug") for item in catalog.values()]
    if len(slugs) != len(set(slugs)):
        fail("队徽 slug 重复")
    for item in catalog.values():
        if item.get("status") not in {"verified", "fallback"}:
            fail(f"队徽状态无效: {item.get('name')}")
        if item.get("status") == "verified":
            path = item.get("path", "")
            if not path.startswith("assets/crests/") or not (ROOT / path).exists():
                fail(f"真实队徽文件不存在: {item.get('name')}")
            if not item.get("source_url") or not item.get("source_type"):
                fail(f"真实队徽缺少来源: {item.get('name')}")
    print(f"队徽目录校验通过: {len(raw_names)} 个原始名称 -> {len(names)} 个标准队伍")

    print("项目校验通过: 6个页面、双赛季数据、离线资源路径和外部引用均正常")


if __name__ == "__main__":
    main()
