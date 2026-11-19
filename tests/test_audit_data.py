"""赛季审计回归；使用归档、临时分片和模拟 HTTP，运行时无需联网。"""

import io
import json
import re
import sys
from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_stats  # noqa: E402
from build_page import rule_context  # noqa: E402
import verify_videos  # noqa: E402
from lib import safe_http  # noqa: E402
from lib.jsonschema_lite import validate  # noqa: E402
from parse_issues import parse_case_head  # noqa: E402


def read_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("season", ("2024", "2025", "2026"))
def test_issue_metadata_matches_final_cases(season):
    data = read_json(f"data/cases-{season}.json")
    for issue in data["issues"]:
        cases = [c for c in data["cases"] if c["issue"] == issue["no"]]
        assert issue["video_count"] == sum(len(c["video_files"]) for c in cases)
    added_time = [
        c
        for c in data["cases"]
        if re.search(r"比赛第\s*\d+\s*[+＋]\s*\d+\s*分钟", c["desc"])
    ]
    assert added_time
    for case in added_time:
        assert re.fullmatch(r"\d+\+\d+", case["minute"])
    assert parse_case_head("比赛第 45 ＋ 2 分钟，主队进攻。")[-1] == "45+2"


@pytest.mark.parametrize("season", ("2024", "2025", "2026"))
def test_impact_counts_and_match_dates(season):
    impact, scores, cmap = build_stats.load(season)
    matches = build_stats.build_matches(impact, scores, cmap)
    dates = {
        i["no"]: i["date"] for i in read_json(f"data/cases-{season}.json")["issues"]
    }
    for key, match in matches.items():
        if "corrected_score" in match:
            assert min(match["corrected_score"]) >= 0
        day = scores.get(key, {}).get("date", "")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            for seq in match["seqs"]:
                assert (
                    date.fromisoformat(day).strftime("%Y%m%d")
                    <= dates[cmap[seq]["issue"]]
                ), key
    payload, _, _ = build_stats.build_data(season)
    for view in ("victims", "benefits"):
        for team in payload[view].values():
            for league, summary in [("", team), *team.get("byLeague", {}).items()]:
                rows = [
                    d for d in team["detail"] if not league or d["league"] == league
                ]
                assert summary["cases"] == len({r["seq"] for r in rows})
                assert sum(summary["types"].values()) == len(rows)
                assert summary["n_matches"] == len(
                    {(r["league"], r["round"], r["home"], r["away"]) for r in rows}
                )


def test_2024_offside_does_not_subtract_a_goal():
    impact, scores, cmap = build_stats.load("2024")
    match = build_stats.build_matches(impact, scores, cmap)[
        "中乙联赛|15|湖北青年星|大连鲲城"
    ]
    assert match["seqs"] == [90]
    assert match["corrected_score"] == (0, 1)
    assert match["items"][0]["swing"] == 0
    key = "中乙联赛|15|湖北青年星|大连鲲城"
    unverified = {key: dict(scores[key], date="2024-07-13")}
    assert rule_context(cmap[90], unverified, [], "20240710")["date"] == ""
    assert rule_context(cmap[90], scores, [], "20240710")["date"] == "2024-07-06"
    assert match["items"][0]["type"] == "missed_offside_opponent"
    for key, day, result in [
        ("中甲联赛|21|江西庐山|黑龙江冰城", "2024-08-31", (0, 0)),
        ("中甲联赛|21|辽宁铁人|大连英博", "2024-09-01", (2, 1)),
    ]:
        record = scores[key]
        assert (record["date"], record["h"], record["a"]) == (day, *result)
        assert record["source_url"].startswith("https://")


@pytest.mark.parametrize(
    "name,field,bad",
    [
        ("impact", "impacts", {"items": []}),
        ("quiz-answers", "answers", {"auto": True, "reviewed": "false"}),
        ("weekly", "shows", {"name": "无官方链接"}),
    ],
)
def test_schema_validates_dynamic_keys(name, field, bad):
    schema = read_json(f"schemas/{name}.schema.json")["properties"][field]
    problems = validate({"sample": bad}, schema)
    assert problems and all(
        "$.sample." in issue or "$.sample:" in issue for issue in problems
    )


def setup_http(monkeypatch, responses):
    ranges = []

    def request(url, headers, timeout):
        ranges.append(headers.get("Range"))
        status, hdrs, body = next(responses)
        return status, hdrs, io.BytesIO(body), io.BytesIO()

    monkeypatch.setattr(safe_http, "safe_request", request)
    monkeypatch.setattr(safe_http.time, "sleep", lambda seconds: None)
    return ranges


@pytest.mark.parametrize("header", ["bytes */5", "", "bytes */bad"])
def test_416_unconfirmed_never_publishes_part(tmp_path, monkeypatch, header):
    target = tmp_path / "clip.mp4"
    part = target.with_suffix(".mp4.part")
    part.write_bytes(b"old-extra")
    ranges = setup_http(monkeypatch, iter([(416, {"content-range": header}, b"")]))
    with pytest.raises(RuntimeError):
        safe_http.download("https://example.test/clip", target, retries=1)
    assert ranges == ["bytes=9-"]
    assert not target.exists()
    assert part.read_bytes() == b"old-extra"


@pytest.mark.parametrize(
    "status,headers,body,expected,ranges",
    [
        (416, {"content-range": "bytes */3"}, b"", b"abc", ["bytes=3-"]),
        (
            206,
            {"content-range": "bytes 3-4/5", "content-length": "2"},
            b"de",
            b"abcde",
            ["bytes=3-"],
        ),
        (416, {"content-range": "bytes */1"}, b"", b"fresh", ["bytes=3-", None]),
        (206, {"content-range": "bytes 1-2/5"}, b"XX", b"fresh", ["bytes=3-", None]),
    ],
)
def test_resume_checks_byte_range(
    tmp_path, monkeypatch, status, headers, body, expected, ranges
):
    target = tmp_path / "clip"
    target.with_suffix(".part").write_bytes(b"abc")
    got = setup_http(
        monkeypatch,
        iter([(status, headers, body), (200, {"content-length": "5"}, b"fresh")]),
    )
    assert safe_http.download("https://example.test/clip", target, retries=2) == (
        200,
        len(expected),
    )
    assert got == ranges and target.read_bytes() == expected


@pytest.mark.parametrize(
    "local,remote,code,field",
    [
        (None, 5, 1, "missing"),
        (b"abc", 5, 1, "mismatch"),
        (b"abc", None, 2, "unverified"),
        (b"abc", 3, 0, "ok"),
    ],
)
def test_verifier_distinguishes_missing_unknown_and_verified(
    tmp_path, monkeypatch, local, remote, code, field
):
    name = "2026/i01c01-1.mp4"
    url = "https://videooss.thecfa.cn/upload/video/clip.mp4"
    case = {"seq": 1, "video_files": [name], "video_urls": [url]}
    (tmp_path / "cases-2026.json").write_text(
        json.dumps({"cases": [case]}), encoding="utf-8"
    )
    if local is not None:
        (tmp_path / "2026").mkdir()
        (tmp_path / name).write_bytes(local)
    for key in ("DATA", "SITE_VIDEOS", "LOCAL_LOGS"):
        monkeypatch.setattr(verify_videos, key, tmp_path)
    head = Mock(return_value=remote)
    monkeypatch.setattr(verify_videos, "head_size", head)
    assert verify_videos.main(["2026"]) == code
    report = json.loads((tmp_path / "verify_result.json").read_text(encoding="utf-8"))
    assert report[field] and report["ok"] == int(code == 0)
    if local is not None:
        head.assert_called_once_with(url)
