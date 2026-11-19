"""对照课引用官方评议、已复核答案和审看过的具体视频片段。"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from lib import compare


def test_free_projection_preserves_every_case_and_provenance():
    payload = compare.load_compare()
    projected = payload["cases"]
    expected = set()
    for season in compare.SEASONS:
        source = json.loads((compare.DATA / f"cases-{season}.json").read_bytes())
        issues = {i["no"]: i for i in source["issues"]}
        for row in source["cases"]:
            key = f"{season}-{row['seq']}"
            expected.add(key)
            result = projected[key]
            assert all(result[field] == row[field] for field in compare.CASE_FIELDS)
            assert result["id"] == key
            assert result["source"] == issues[row["issue"]]["url"]
            assert result["href"] == f"season-{season}.html#case-{row['seq']}"
            assert row["category"] in payload["categories"]
            assert result["rules"]
    assert set(projected) == expected
    assert projected["2024-1"]["video_files"] == []
    assert projected["2024-112"]["conclusion"] == ""


def test_supplementary_rulings_keep_both_source_issues():
    cases = compare.load_compare()["cases"]
    cases_with_supplement = {key for key, case in cases.items() if "supplement" in case}
    assert cases_with_supplement == {"2025-183", "2025-188"}
    issue_dir = compare.DATA / "issues" / "2025"
    original = (issue_dir / "issue_26.html").read_text(encoding="utf-8")
    later = (issue_dir / "issue_27.html").read_text(encoding="utf-8")
    for key in cases_with_supplement:
        case = cases[key]
        assert case["source"].endswith("/20250917/36917.html")
        assert case["supplement"] == {
            "issue": 27,
            "date": "20250924",
            "url": "https://www.thecfa.cn/cppy/20250924/36927.html",
        }
        final_sentence = case["conclusion"].split("。")[-2]
        assert final_sentence in compare.text_of(later)
        assert final_sentence not in compare.text_of(original)
        assert case["video_urls"][1] in later
        assert case["video_urls"][1] not in original


def test_published_routes_questions_and_eight_official_answers():
    data = compare.load_compare()
    lessons = {lesson["id"]: lesson for lesson in data["lessons"]}
    expected = {
        "handball": ("r", (1, "penalty"), (28, "playon")),
        "offside": ("r", (14, "goal_valid"), (29, "goal_invalid")),
        "contact-intensity": ("c", (94, "yellow"), (47, "red")),
        "penalty-contact": ("r", (13, "playon"), (18, "playon")),
    }
    laws = json.loads((compare.DATA / "laws.json").read_bytes())
    sections = {s["id"]: s["title"] for s in laws["sections"]}
    for slug, (axis, first, second) in expected.items():
        lesson = lessons[slug]
        assert lesson["axis"] == axis
        assert [(x["id"], x["answer"]) for x in lesson["cases"]] == [
            (f"2026-{seq}", answer) for seq, answer in [first, second]
        ]
        options = {item["id"] for item in lesson["options"]}
        assert "unsure" not in options
        assert all(item["label"] for item in lesson["options"])
        for rule in lesson["rules"]:
            assert rule["version"] == laws["season"]
            assert rule["title"] == sections[rule["law"]]
            assert rule["href"] == f"rules.html#{rule['law']}"
        for item in lesson["cases"]:
            # 文字盲判不将含临场决定、VAR 或专家答案的原始经过用作题干。
            assert all(
                word not in item["prompt"]
                for word in (
                    "漏判",
                    "VAR",
                    "评议组",
                    "出示黄牌",
                    "出示红牌",
                    "进球有效",
                    "进球无效",
                )
            )
            assert item["answer"] in options
            assert item["quote"] in data["cases"][item["id"]]["conclusion"]


LESSON_FILE = "compare-lessons.json"
REVIEW_FILE = "quiz-answers.json"
FIRST = ("lessons", 0)
FIRST_CASE = (*FIRST, "cases", 0)


@pytest.mark.parametrize(
    ("filename", "path", "value", "message"),
    [
        ("cases-2026.json", ("issues", 0, "url"), "", "评议来源网址"),
        (LESSON_FILE, ("lessons", 1, "id"), "handball", "课程编号"),
        (LESSON_FILE, (*FIRST, "id"), "易变化的标题#A", "课程编号"),
        (LESSON_FILE, (*FIRST, "cases", 1, "id"), "2026-1", "两个不同的判例"),
        (LESSON_FILE, (*FIRST_CASE, "id"), "2026-99999", "未知判例"),
        (LESSON_FILE, (*FIRST, "category"), "offside", "课程分类"),
        (LESSON_FILE, (*FIRST, "axis"), "c", "答案选项"),
        (LESSON_FILE, (*FIRST_CASE, "answer"), "playon", "人工复核答案"),
        (REVIEW_FILE, ("answers", "2026-1", "reviewed"), False, "人工复核答案"),
        (
            REVIEW_FILE,
            ("answers", "2026-47", "discipline_target"),
            "另一名队员",
            "处分对象",
        ),
        (LESSON_FILE, (*FIRST_CASE, "quote"), "编造的评议结论", "足协评议认定"),
        (
            LESSON_FILE,
            (*FIRST_CASE, "clip", "url"),
            "https://videooss.thecfa.cn/other.mp4",
            "足协视频",
        ),
        (LESSON_FILE, (*FIRST_CASE, "clip", "video_index"), -1, "足协视频"),
        (LESSON_FILE, (*FIRST_CASE, "clip", "start"), -1, "视频时长"),
        (LESSON_FILE, (*FIRST_CASE, "clip", "end"), 50, "视频时长"),
        (LESSON_FILE, (*FIRST_CASE, "clip", "start"), float("nan"), "视频时长"),
    ],
)
def test_broken_editorial_links_block_build(
    monkeypatch, filename, path, value, message
):
    original = compare._read

    def broken(file):
        data = original(file)
        if file.name == filename:
            target = data
            for index in path[:-1]:
                target = target[index]
            target[path[-1]] = value
        return data

    monkeypatch.setattr(compare, "_read", broken)
    with pytest.raises(ValueError, match=message):
        compare.load_compare()


@pytest.mark.parametrize("missing", ["official-text", "official-video"])
def test_archived_article_must_contain_quote_and_media(tmp_path, monkeypatch, missing):
    original = compare._read
    item = original(compare.DATA / "compare-lessons.json")["lessons"][0]["cases"][0]
    archived = tmp_path / "issues" / "2026" / "issue_01.html"
    archived.parent.mkdir(parents=True)
    archived.write_text(
        item["clip"]["url"] if missing == "official-text" else item["quote"],
        encoding="utf-8",
    )
    monkeypatch.setattr(
        compare, "_read", lambda path: original(compare.DATA / path.name)
    )
    with pytest.raises(ValueError, match="官方 HTML 存档"):
        compare.load_compare(tmp_path)
