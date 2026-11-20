"""逐场修正比分独立于事项及受损方，赛事阶段不改变比分关联键。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_stats


def test_cup_round_preserves_score_lookup_and_source():
    impact, scores, cases = build_stats.load("2024")
    key = "中国足协杯|0|山东泰山|成都蓉城"
    match = build_stats.build_matches(impact, scores, cases)[key]
    assert match["seqs"] == [145]
    assert "中国足协杯赛半决赛" in cases[145]["match_info"]
    assert match["round_label"] == "半决赛"
    assert (match["score"]["h"], match["score"]["a"]) == (1, 0)
    assert match["score"]["source"] == scores[key]["source"]


@pytest.mark.parametrize("unknown", [0, "第0轮", "", None])
def test_unknown_round_does_not_infer_from_incident_text(unknown):
    case = {"match_info": "中国足协杯，主队VS客队，获胜方将进入半决赛"}
    assert build_stats.round_label("中国足协杯", unknown, [case]) == "轮次待核"
    assert (
        build_stats.round_label(
            "中国足协杯", unknown, [{"match_info": "足协杯决赛阶段，主队VS客队"}]
        )
        == "轮次待核"
    )
    assert build_stats.round_label("中国足协杯", 2, [case]) == "第2轮"


def test_both_teams_share_corrected_score_and_keep_their_own_result():
    data, _, _ = build_stats.build_data("2025")
    for view in ("victims", "benefits"):
        for team, outcome in (("南京城市", "win"), ("南通支云", "loss")):
            rows = [
                row for row in data[view][team]["detail"] if row["seq"] in (141, 142)
            ]
            assert rows
            for row in rows:
                assert (row["score"]["h"], row["score"]["a"]) == (0, 1)
                assert row["corrected"] == (0, 2)
                assert row["team_result"] == (outcome, outcome)
    data, _, _ = build_stats.build_data("2026")
    for view in ("victims", "benefits"):
        for team, outcome, status in (
            ("大连可为", "loss", "worsened"),
            ("上海赛更达", "win", "changed"),
        ):
            rows = [
                r
                for r in data[view][team]["detail"]
                if r["seq"] in (155, 156, 157, 158)
            ]
            assert rows
            for row in rows:
                assert row["corrected"] == (0, 1)
                assert row["team_result"] == ("draw", outcome)
                assert row["status"] == status


def test_chances_alone_do_not_adjust_score():
    impact, scores, cases = build_stats.load("2026")
    # 去掉该场唯一的进球误判，保留三例错判或漏判点球和一次漏黄。
    chances = {"impacts": {str(k): impact["impacts"][str(k)] for k in (155, 156, 157)}}
    match = build_stats.build_matches(chances, scores, cases)[
        "中乙联赛|12|大连可为|上海赛更达"
    ]
    assert (
        (match["score"]["h"], match["score"]["a"]) == match["corrected_score"] == (1, 1)
    )
