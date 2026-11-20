"""IFAB 已复核的中英文问答、干扰项和评分键须同时对应。"""

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_quiz
from lib import site_stats, var_quiz
from lib.ifab_content import documents, fingerprint


def load_inputs():
    return (
        json.loads(build_quiz.IFAB_JSON.read_text(encoding="utf-8")),
        json.loads(build_quiz.IFAB_ZH_JSON.read_text(encoding="utf-8")),
    )


def test_existing_twelve_faqs_match_the_original_reviewed_bank():
    rows = var_quiz.reviewed_var_questions(*load_inputs())
    assert [r["k"] for r in rows] == [f"var-q{i}" for i in range(1, 13)]
    # Original 6ad8574: decoded from both committed IFAB JSON files and the original VAR_OPTS literal.
    serialized = json.dumps(
        rows, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    assert (
        hashlib.sha256(serialized).hexdigest()
        == "cf15acb63117daab97f69c9082ee404b68d190ec024db1d3466efd1b32c7994e"
    )
    assert all(len(set(r["opts"])) == 4 and 0 <= r["ans"] < 4 for r in rows)
    assert all(r["link"] == "ifab.html#faq-" + r["qid"] for r in rows)


@pytest.mark.parametrize(
    "change",
    [
        "official-question",
        "official-answer",
        "new-translation-and-pin",
        "chinese-question",
        "chinese-answer",
        "duplicate",
        "missing-translation",
        "blank-answer",
        "missing-translation-pin",
        "choice-text",
        "scoring-key",
        "incomplete-key",
    ],
)
def test_changed_or_ambiguous_faq_cannot_use_its_previous_grading_key(
    change, monkeypatch
):
    data, zh = load_inputs()
    q = next(item for item in data["faq"] if item["id"] == "q1")
    tr = zh["faq"]["q1"]
    if change == "official-question":
        q["q"] = "Which sample is shown?"
    elif change == "official-answer":
        q["a"] = "The second sample."
    elif change == "new-translation-and-pin":
        q.update(q="Which sample is shown?", a="The second sample.")
        tr.update(q="显示了哪个样本？", a="第二个样本。")
        zh["source_versions"]["faq/q1"] = fingerprint([q["q"], q["a"]])
        assert documents({"faq": [q]}, zh)[0]["faq"][0]["za"] == "第二个样本。"
    elif change == "chinese-question":
        tr["q"] = "显示了哪个样本？"
    elif change == "chinese-answer":
        tr["a"] = "第二个样本。"
    elif change == "duplicate":
        data["faq"].append(copy.deepcopy(q))
    elif change == "missing-translation":
        del zh["faq"]["q1"]
    elif change == "blank-answer":
        tr["a"] = " "
    elif change == "missing-translation-pin":
        del zh["source_versions"]["faq/q1"]
    else:
        choices = copy.deepcopy(var_quiz.VAR_OPTS["q1"])
        if change == "choice-text":
            choices["opts"][2] = "选第三个样本。"
        elif change == "scoring-key":
            choices["ans"] = (choices["ans"] + 1) % 4
        else:
            del choices["ans"]
        monkeypatch.setitem(var_quiz.VAR_OPTS, "q1", choices)
    warnings = []
    rows = var_quiz.reviewed_var_questions(data, zh, warnings.append)
    assert {row["qid"] for row in rows} == {f"q{i}" for i in range(2, 13)}
    assert len(warnings) == 1 and "q1 待复核" in warnings[0]


def test_renewed_question_can_return_after_separate_grading_review(monkeypatch):
    data, zh = load_inputs()
    q = next(item for item in data["faq"] if item["id"] == "q1")
    q.update(q="Which sample is shown?", a="The third sample.")
    translated = {"q": "显示了哪个样本？", "a": "第三个样本。"}
    zh["faq"]["q1"] = translated
    zh["source_versions"]["faq/q1"] = fingerprint([q["q"], q["a"]])
    choices = {"opts": ["第一", "第二", "第三", "第四"], "ans": 2}
    choices["review"] = var_quiz.review_version("q1", q, translated, choices)
    monkeypatch.setitem(var_quiz.VAR_OPTS, "q1", choices)
    rows = var_quiz.reviewed_var_questions(data, zh)
    assert len(rows) == 12
    assert rows[0]["k"] == "var-q1" and rows[0]["q"] == translated["q"]
    assert rows[0]["opts"][rows[0]["ans"]] == "第三"


def test_new_official_id_needs_a_reviewed_choice_set():
    data, zh = load_inputs()
    data["faq"].append({"id": "sample", "q": "A sample?", "a": "Yes."})
    zh["faq"]["sample"] = {"q": "是样本吗？", "a": "是。"}
    zh["source_versions"]["faq/sample"] = fingerprint(["A sample?", "Yes."])
    warnings = []
    rows = var_quiz.reviewed_var_questions(data, zh, warnings.append)
    assert len(rows) == 12 and all(row["qid"] != "sample" for row in rows)
    assert len(warnings) == 1 and "sample 待复核" in warnings[0]


def test_quiz_and_homepage_count_the_same_reviewed_questions(tmp_path, monkeypatch):
    data, zh = load_inputs()
    data["faq"][0]["a"] = "A changed answer in a local fixture."
    official, translated = tmp_path / "ifab.json", tmp_path / "ifab-zh.json"
    official.write_text(json.dumps(data), encoding="utf-8")
    translated.write_text(json.dumps(zh), encoding="utf-8")
    for module in (build_quiz, site_stats):
        monkeypatch.setattr(module, "IFAB_JSON", official)
        monkeypatch.setattr(module, "IFAB_ZH_JSON", translated)
    bank, _, _, actual, _ = build_quiz.build_bank()
    counts = site_stats.quiz_counts()
    assert actual == counts["var"] == 11
    assert counts["total"] == len(bank)
    assert "var-q1" not in {q["k"] for q in bank}
    translated.unlink()
    assert site_stats.quiz_counts()["var"] == build_quiz.build_bank()[3] == 0
