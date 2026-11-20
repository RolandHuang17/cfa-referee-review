"""A reader can identify the intended record before following a search result."""

import json
import sys
from collections import defaultdict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_search
from lib.conmebol_evidence import event_anchor, event_rows
from lib.pagelib import article_anchor


@pytest.fixture(scope="module")
def indexed():
    return {row[3]: row for row in build_search.build_docs()}


def test_round_names_and_publication_dates_survive_indexing(indexed):
    pro = json.loads(build_search.PRO_JSON.read_text(encoding="utf-8"))
    rounds = [
        article
        for article in pro["articles"]
        if article["title"] == "The Definitive Angle: MLS Matchday 34"
    ]
    assert len({article["date"] for article in rounds}) >= 2
    for article in rounds:
        title = indexed["pro.html#" + article_anchor(article["url"])][2]
        assert article["date"] in title and article["title"] in title
    weekly = json.loads(build_search.WEEKLY_JSON.read_text(encoding="utf-8"))
    for episode in weekly["episodes"]:
        assert episode["title"] in indexed["weekly.html#ep-" + episode["id"]][2]
    cases = json.loads(build_search.CONMEBOL_JSON.read_text(encoding="utf-8"))
    for case in cases["cases"]:
        row = indexed["conmebol.html#" + article_anchor(case["url"])]
        assert case["title"] in row[4]
        if case.get("date"):
            assert "发布 " + case["date"] in row[2]
        if case.get("detail_status") == "pending":
            assert "文章详情待核" in row[2]
            assert row[4].strip() == case["title"]
        else:
            assert "文章详情待核" not in row[2]


def test_repeated_law_text_has_distinct_readable_locations(indexed):
    groups = defaultdict(list)
    for url, row in indexed.items():
        if row[1] == "竞赛规则":
            section = url.split("-p-", 1)[0]
            groups[(section, row[4])].append(row[2])
    repeats = [titles for titles in groups.values() if len(titles) > 1]
    assert repeats
    assert all(len(titles) == len(set(titles)) for titles in repeats)


def test_multi_incident_articles_reach_the_described_video(indexed):
    cases = json.loads(build_search.CONMEBOL_JSON.read_bytes())["cases"]
    targets = {row[3] for row in indexed.values() if row[1] == "CONMEBOL 判例时刻"}
    expected = set()
    for case in cases:
        events = event_rows(case)
        if len(events) < 2:
            continue
        for event in events:
            href = "conmebol.html#" + event_anchor(case["url"], event)
            expected.add(href)
            row = indexed[href]
            assert case["match"] in row[2] and case["title"] in row[4]
            if event.get("minuto"):
                assert event["minuto"] + "′" in row[2]
            for video in event["videos"]:
                if video.get("title"):
                    assert " ".join(video["title"].split()) in row[4]
    assert targets == expected
    lanus = next(c for c in cases if c["url"].endswith("valle-vs-lanus/"))
    for minute, video in (("60", "ONE6TOLhbIY"), ("85", "Kq9pP_NKwe4")):
        href = "conmebol.html#" + article_anchor(lanus["url"]) + "-" + video
        assert minute + "′" in indexed[href][2]
