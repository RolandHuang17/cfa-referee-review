"""为尺度对照课连接手工选段、已复核答案、足协原文和三赛季判例。"""

import json
import math
import re
from functools import lru_cache
from urllib.parse import urlsplit

from lib.issue_notes import supplement_issue_no
from lib.law_blocks import text_of
from lib.paths import DATA
from lib.site_stats import SEASONS


CASE_FIELDS = (
    "seq",
    "issue",
    "no",
    "home",
    "away",
    "comp",
    "round",
    "minute",
    "category",
    "desc",
    "appeal",
    "conclusion",
    "referee_verdict",
    "var_verdict",
    "video_files",
    "video_urls",
)
SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _rules_by_category(data_dir, table):
    laws = _read(data_dir / "laws.json")
    by_id = {
        section["id"]: {
            "law": section["id"],
            "title": section["title"],
            "version": laws["season"],
            "href": f"rules.html#{section['id']}",
        }
        for section in laws["sections"]
    }
    return {
        category: [by_id[law] for law in table["law_of_category"][category]]
        for category in table["category_names"]
    }


def _project_cases(data_dir, rules):
    cases = {}
    for season in SEASONS:
        source = _read(data_dir / f"cases-{season}.json")
        issues = {entry["no"]: entry for entry in source["issues"]}
        for entry in issues.values():
            url = urlsplit(entry.get("url") or "")
            if url.scheme not in {"https", "http"} or not url.hostname:
                raise ValueError(f"{season} 第{entry['no']}期缺少评议来源网址")
        for record in source["cases"]:
            key = f"{season}-{record['seq']}"
            if key in cases:
                raise ValueError(f"重复的判例编号 {key}")
            issue = issues[record["issue"]]
            cases[key] = {
                **{field: record[field] for field in CASE_FIELDS},
                "id": key,
                "season": season,
                "source": issue["url"],
                "source_date": issue["date"],
                "rules": rules[record["category"]],
                "href": f"season-{season}.html#case-{record['seq']}",
            }
            # fix_issue27_merge appends the later ruling to its original case.
            supplemental = supplement_issue_no(record["conclusion"])
            if supplemental is not None:
                cited_issue = issues[supplemental]
                cases[key]["supplement"] = {
                    "issue": cited_issue["no"],
                    "date": cited_issue["date"],
                    "url": cited_issue["url"],
                }
    return cases


def _validate_clip(key, clip, case):
    index = clip["video_index"]
    if (
        type(index) is not int
        or index < 0
        or index >= len(case["video_files"])
        or index >= len(case["video_urls"])
        or clip["url"] != case["video_urls"][index]
    ):
        raise ValueError(f"{key} 选段与审看的足协视频不一致")
    times = [clip[k] for k in ("start", "end", "duration")]
    if (
        any(type(t) not in (int, float) or not math.isfinite(t) for t in times)
        or not 0 <= clip["start"] < clip["end"] <= clip["duration"]
    ):
        raise ValueError(f"{key} 选段超出审看的视频时长")


def _validate_case(item, axis, option_ids, case, answers, archive):
    key = item["id"]
    review = answers.get(key, {})
    if (
        review.get("reviewed") is not True
        or item["answer"] not in option_ids
        or item["answer"] != review.get(axis)
    ):
        raise ValueError(f"{key} 的所问判罚轴与人工复核答案不一致")
    if not item["prompt"].strip():
        raise ValueError(f"{key} 缺少文字观察材料")
    target = review.get("discipline_target")
    if axis == "c" and target and target not in item["prompt"]:
        raise ValueError(f"{key} 题干未指明复核的纪律处分对象 {target}")
    quote = item["quote"]
    if not quote.strip() or quote not in case["conclusion"]:
        raise ValueError(f"{key} 引文与该案足协评议认定不一致")
    _validate_clip(key, item["clip"], case)
    source_html, source_text = archive(case["season"], case["issue"])
    if (
        "".join(quote.split()) not in source_text
        or item["clip"]["url"] not in source_html
    ):
        raise ValueError(f"{key} 的引文或视频与当期官方 HTML 存档不一致")


def load_compare(data_dir=DATA):
    """读取并校验课程。规则链接为库内现行版本，足协认定保留比赛当时的原文。"""
    table = _read(data_dir / "xlinks.json")
    categories = table["category_names"]
    rules = _rules_by_category(data_dir, table)
    cases = _project_cases(data_dir, rules)
    review = _read(data_dir / "quiz-answers.json")
    labels = {"r": review["rLabels"], "c": review["cLabels"]}
    curated = _read(data_dir / "compare-lessons.json")
    if curated["version"] != 1:
        raise ValueError("未知的对照课数据版本")

    @lru_cache(maxsize=None)
    def archive(season, issue):
        page = (data_dir / "issues" / season / f"issue_{issue:02d}.html").read_text(
            encoding="utf-8"
        )
        return page, "".join(text_of(page).split())

    seen = set()
    lessons = []
    for lesson in curated["lessons"]:
        slug = lesson["id"]
        if not SLUG.fullmatch(slug) or slug in seen:
            raise ValueError(f"无效或重复的课程编号 {slug}")
        seen.add(slug)
        axis, options = lesson["axis"], lesson["options"]
        if (
            axis not in labels
            or len(set(options)) != len(options)
            or len(options) < 2
            or not set(options) <= labels[axis].keys()
        ):
            raise ValueError(f"{slug} 的答案选项与所问判罚轴不一致")
        if any(not lesson[k].strip() for k in ("title", "question", "difference")):
            raise ValueError(f"{slug} 的标题、提问或对照依据为空")
        pair = lesson["cases"]
        if len(pair) != 2 or pair[0]["id"] == pair[1]["id"]:
            raise ValueError(f"{slug} 需要两个不同的判例")
        for item in pair:
            case = cases.get(item["id"])
            if not case or case["category"] != lesson["category"]:
                raise ValueError(f"{slug} 引用了未知判例或与课程分类不一致")
            _validate_case(item, axis, options, case, review["answers"], archive)
        lessons.append(
            {
                **lesson,
                "options": [
                    {"id": option, "label": labels[axis][option]} for option in options
                ],
                "rules": rules[lesson["category"]],
            }
        )
    return {"lessons": lessons, "cases": cases, "categories": categories}
