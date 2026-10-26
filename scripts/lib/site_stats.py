# -*- coding: utf-8 -*-
"""全站数据规模统计的唯一权威源。

页面描述、门户数字、stats 期数文案都从这里取，避免 81/82、612/615、592/796
这类手写常量再次漂移。只依赖 lib.paths 与 JSON 数据，不 import 任何 builder。
"""

import json

from lib.paths import DATA, IFAB_JSON, IFAB_ZH_JSON, SCALE_JSON

SEASONS = ("2026", "2025", "2024")


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def counts():
    """三季期数/判例数/视频数（视频按 video_files 计）。"""
    seasons = {}
    totals = {"issues": 0, "cases": 0, "videos": 0}
    for season in SEASONS:
        data = _read(DATA / f"cases-{season}.json")
        cases = data.get("cases", [])
        row = {
            "issues": len(data.get("issues", [])),
            "cases": len(cases),
            "videos": sum(len(c.get("video_files") or []) for c in cases),
        }
        seasons[season] = row
        for key in totals:
            totals[key] += row[key]
    return {"seasons": seasons, **totals}


def is_quiz_case(case):
    """与 build_quiz 一致的入池条件：有视频且评议组结论非空。"""
    return bool(case.get("video_files")) and bool(
        (case.get("conclusion") or "").strip()
    )


def is_quiz_scale(item):
    """与 build_quiz 一致的尺度场景入池条件。"""
    decision = item.get("decision") or []
    return (
        bool(decision)
        and not any(x.get("label") == "VAR 机制讲解" for x in decision)
        and bool(item.get("video"))
    )


def quiz_counts():
    """四题源题量：判例 / 尺度 / IFAB FAQ / 理论题。"""
    case_n = 0
    for season in SEASONS:
        data = _read(DATA / f"cases-{season}.json")
        case_n += sum(1 for c in data.get("cases", []) if is_quiz_case(c))

    scale_n = 0
    scale_data = _read(SCALE_JSON)
    for year_data in scale_data.values():
        if not isinstance(year_data, dict):
            continue
        for section in year_data.get("sections", []):
            for group in section.get("groups", []):
                scale_n += sum(
                    1 for item in group.get("items", []) if is_quiz_scale(item)
                )

    ifab = _read(IFAB_JSON)
    ifab_zh = _read(IFAB_ZH_JSON).get("faq", {})
    # build_quiz 只收有中文译制且配置了选项的 FAQ；当前 12 条全满足。
    var_n = sum(1 for q in ifab.get("faq", []) if q.get("id") in ifab_zh)

    theory_n = len(_read(DATA / "theory-questions.json").get("questions", []))
    total = case_n + scale_n + var_n + theory_n
    return {
        "case": case_n,
        "scale": scale_n,
        "var": var_n,
        "theory": theory_n,
        "total": total,
    }


def cheatsheet_count():
    return len(_read(DATA / "cheatsheet.json").get("cards", []))
