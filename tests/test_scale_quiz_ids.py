"""尺度题键既能区分来源场景，也可识别已经存到本地的旧编号。"""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_quiz
import build_scale
import build_search
from lib.scale_quiz_ids import LEGACY_SCALE_IDS, assign_scale_quiz_ids
from lib.site_stats import quiz_counts


def test_all_questions_have_stable_independent_keys():
    bank = build_quiz.build_bank()[0]
    keyed = {q["k"]: q for q in bank}
    assert len(keyed) == len(bank) == quiz_counts()["total"]
    assert len(LEGACY_SCALE_IDS) == 8
    for legacy, candidates in LEGACY_SCALE_IDS.items():
        assert legacy not in keyed
        answers = {
            frozenset(d["label"] for d in keyed[k]["dec"] if d["active"])
            for k in candidates
        }
        assert len(answers) == len(candidates)
        for key, old_answer in candidates.items():
            q = keyed[key]
            assert old_answer == "、".join(d["label"] for d in q["dec"] if d["active"])
            assert q["link"] == f"scale.html#h{q['s']}-{q['series']}-{q['id']}"
    collided = {k for candidates in LEGACY_SCALE_IDS.values() for k in candidates}
    assert len(collided) == 18
    for q in bank:
        if q["t"] == "scale" and (q["s"], q["series"]) in {
            ("2024", "highlights"),
            ("2025", "reckless"),
            ("2026", "highlights"),
        }:
            old = f"sc-{q['s']}-{q['id']}"
            if old in LEGACY_SCALE_IDS:
                assert q["k"] in collided
            else:
                assert q["k"] == old
    reverse = list(reversed(copy.deepcopy(bank)))
    assign_scale_quiz_ids(reverse)
    assert list(reversed(reverse)) == bank


def test_scale_quiz_search_and_official_material_share_scene_anchors(
    tmp_path, monkeypatch
):
    scale = json.loads(build_quiz.SCALE_JSON.read_text(encoding="utf-8"))
    monkeypatch.setattr(build_scale, "SITE", tmp_path)
    build_scale.build_page(scale)
    page = (tmp_path / "scale.html").read_text(encoding="utf-8")
    docs = {doc[3] for doc in build_search.build_docs()}
    questions = [q for q in build_quiz.build_bank()[0] if q["t"] == "scale"]
    assert (
        len({q["link"] for q in questions}) == len(questions) == quiz_counts()["scale"]
    )
    for q in questions:
        assert q["link"] in docs
        anchor = q["link"].split("#", 1)[1]
        assert page.count(f'id="{anchor}"') == 1


def test_a_retired_candidate_or_a_new_series_cannot_claim_published_keys():
    def question(year, series, number):
        return {"t": "scale", "s": year, "series": series, "id": number}

    rows = [
        question("2025", "reckless", "1"),  # 其他两个旧候选暂未入池。
        question("2025", "new", "1"),
        question("2025", "reckless", "6"),  # 这道已发布的单义题继续沿用原键。
        question("2025", "new", "6"),
        question("2026", "highlights", "1"),
        question("2026", "new", "1"),
        question("2027", "highlights", "1"),
        question("2027", "new", "1"),
    ]
    assign_scale_quiz_ids(rows)
    assert [q["k"] for q in rows] == [
        "sc-2025-reckless-1",
        "sc-2025-new-1",
        "sc-2025-6",
        "sc-2025-new-6",
        "sc-2026-1",
        "sc-2026-new-1",
        "sc-2027-highlights-1",
        "sc-2027-new-1",
    ]
    assert len(LEGACY_SCALE_IDS["sc-2025-1"]) == 3
    assert rows[1]["k"] not in LEGACY_SCALE_IDS["sc-2025-1"]
    with pytest.raises(ValueError, match="题库编号重复"):
        assign_scale_quiz_ids([*rows, rows[0].copy()])
