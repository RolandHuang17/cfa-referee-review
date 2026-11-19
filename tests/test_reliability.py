"""更新故障、历史重建与检索回归用例，全部使用本地数据。"""

import copy
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fetch_hns  # noqa: E402
import fetch_pro  # noqa: E402
import fetch_weekly  # noqa: E402
from lib.atomic_json import write_json  # noqa: E402
from lib.law_blocks import anchored_section  # noqa: E402
from lib.paths import DATA  # noqa: E402
from lib.source_cache import SourceCache  # noqa: E402
from rebuild_cases import rebuild  # noqa: E402


@pytest.mark.parametrize("season", ["2024", "2025", "2026"])
def test_rebuild_preserves_committed_cases(season):
    expected = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
    assert rebuild(season) == expected


@pytest.mark.parametrize(
    "module,file_attr,records,fetch_name",
    [
        (fetch_pro, "PRO_JSON", "articles", "fetch_page"),
        (fetch_hns, "HNS_JSON", "rounds", "fetch_url"),
        (fetch_weekly, "WEEKLY_JSON", "episodes", "collect"),
    ],
)
def test_empty_source_preserves_history(
    tmp_path, module, file_attr, records, fetch_name
):
    previous = json.loads(getattr(module, file_attr).read_text(encoding="utf-8"))
    path = tmp_path / "snapshot.json"
    write_json(path, previous)
    reader = SourceCache(offline=True)
    with (
        mock.patch.object(module, file_attr, path),
        mock.patch.object(module, "CACHE_READER", reader),
        mock.patch.object(
            module, fetch_name, return_value=[] if fetch_name == "collect" else ""
        ),
        mock.patch.object(module.time, "sleep"),
    ):
        module.parse_all()
    updated = json.loads(path.read_text(encoding="utf-8"))
    assert updated[records] == previous[records]
    assert updated["fetched"] == previous["fetched"]


def test_weekly_merges_new_and_old_records(tmp_path):
    previous = json.loads(fetch_weekly.WEEKLY_JSON.read_text(encoding="utf-8"))
    path = tmp_path / "weekly.json"
    write_json(path, previous)
    item = copy.deepcopy(previous["episodes"][0])
    item["title"] = "上游修订的标题"
    item["desc"] = "上游补充的说明"
    with (
        mock.patch.object(fetch_weekly, "WEEKLY_JSON", path),
        mock.patch.object(
            fetch_weekly,
            "collect",
            side_effect=lambda show: [item] if show["key"] == item["show"] else [],
        ),
        mock.patch.object(fetch_weekly.time, "sleep"),
    ):
        fetch_weekly.parse_all()
        fetch_weekly.parse_all()
    updated = json.loads(path.read_text(encoding="utf-8"))["episodes"]
    assert len(updated) == len(previous["episodes"])
    assert next(e for e in updated if e["id"] == item["id"])["title"] == item["title"]


def test_cache_refreshes_mutable_sources_and_parse_is_offline(tmp_path):
    path = tmp_path / "listing.html"
    path.write_text("old listing", encoding="utf-8")
    url = "https://hns.family/hns/suci"
    with mock.patch(
        "lib.source_cache.fetch_text", return_value=(200, "new listing")
    ) as fetch:
        cache = SourceCache()
        assert cache.read(url, path, 2, mutable=True) == "new listing"
        assert url in cache.verified
        assert (
            SourceCache(offline=True).read(url, path, 2, mutable=True) == "new listing"
        )
        assert fetch.call_count == 1
    with mock.patch("lib.source_cache.fetch_text", side_effect=OSError("offline")):
        cache = SourceCache()
        assert cache.read(url, path, 2, mutable=True) == "new listing"
        assert url in cache.failed
        assert not cache.verified


def test_atomic_failure_retains_previous_snapshot(tmp_path):
    path = tmp_path / "data.json"
    write_json(path, {"old": True})
    with mock.patch("lib.atomic_json.os.replace", side_effect=OSError("interrupted")):
        with pytest.raises(OSError):
            write_json(path, {"new": True})
    assert json.loads(path.read_text(encoding="utf-8")) == {"old": True}
    assert list(tmp_path.iterdir()) == [path]


def test_pro_retries_empty_videos_and_preserves_known_links(tmp_path):
    path = tmp_path / "pro.json"
    previous = {
        "fetched": "2026-10-01",
        "articles": [
            {
                "url": "https://proreferees.com/retry/",
                "date": "2026-10-01",
                "series": "ivr",
                "videos": [],
            },
            {
                "url": "https://proreferees.com/keep/",
                "date": "2026-10-01",
                "series": "ivr",
                "videos": ["https://www.youtube.com/watch?v=abcdefghijk"],
            },
        ],
    }
    write_json(path, previous)
    recovered = "https://www.youtube.com/watch?v=lmnopqrstuv"
    with (
        mock.patch.object(fetch_pro, "PRO_JSON", path),
        mock.patch.object(
            fetch_pro, "CACHE_READER", SourceCache(offline=True, refresh=True)
        ),
        mock.patch.object(fetch_pro, "fetch_page", return_value=""),
        mock.patch.object(
            fetch_pro,
            "article_videos",
            side_effect=lambda url: [recovered] if url.endswith("/retry/") else [],
        ),
    ):
        fetch_pro.parse_all()
    articles = {
        a["url"]: a for a in json.loads(path.read_text(encoding="utf-8"))["articles"]
    }
    assert articles["https://proreferees.com/retry/"]["videos"] == [recovered]
    assert (
        articles["https://proreferees.com/keep/"]["videos"]
        == previous["articles"][1]["videos"]
    )


def test_hns_partial_article_preserves_cases_and_videos():
    previous = {
        "round": 1,
        "incidents": [
            {
                "no": 1,
                "match": "A - B",
                "paras": [{"t": "原文"}],
                "videos": ["abcdefghijk"],
            },
            {"no": 2, "match": "C - D", "videos": ["lmnopqrstuv"]},
        ],
    }
    current = {
        "round": 1,
        "incidents": [{"no": 1, "match": "A - B（修订）", "paras": [], "videos": []}],
    }
    merged = fetch_hns.merge_round(previous, current)
    assert len(merged["incidents"]) == 2
    assert merged["incidents"][0]["match"] == "A - B（修订）"
    assert merged["incidents"][0]["videos"] == ["abcdefghijk"]
    assert merged["incidents"][0]["paras"] == previous["incidents"][0]["paras"]
    assert merged["incidents"][1] == previous["incidents"][1]


def test_search_includes_tail_of_law_12_and_stable_anchors():
    from build_search import build_docs

    docs = build_docs()
    assert any("掷物" in d[4] and d[3].startswith("rules.html#law-12-p-") for d in docs)
    section = {"id": "law-12", "html": "<p>第一段</p><p>掷物</p>"}
    _, first = anchored_section(section)
    section["html"] = "<p>新序言</p>" + section["html"]
    _, second = anchored_section(section)
    assert first[-1] == second[-1]


def test_hns_splits_inline_headings_without_paragraph_boundary():
    html = (
        "<h1>Sudačka analiza 11. kola SuperSport HNL-a</h1><p>"
        "<strong>Situacija br. 1: A - B (sudac Test, 10. minuta): zaleđe</strong>"
        '<iframe src="https://www.youtube.com/embed/abcdefghijk"></iframe>'
        "<br>Očekivana odluka:<br>Komisija podržava odluku."
        "<br><strong>Situacija br. 2: C - D (sudac Test, 20. minuta): prekršaj</strong>"
        '<iframe src="https://www.youtube.com/embed/lmnopqrstuv"></iframe>'
        "<br>Očekivana odluka:<br>Igrač je trebao biti opomenut.</p>"
    )
    data = fetch_hns.parse_article("sample", html)
    assert len(data["incidents"]) == 2
    first, second = data["incidents"]
    assert first["videos"] == ["abcdefghijk"]
    assert second["videos"] == ["lmnopqrstuv"]
    assert first["verdict"] == "correct"
    assert second["verdict"] == "incorrect"
