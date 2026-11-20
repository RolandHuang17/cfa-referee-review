"""旧缓存的文章身份、四篇待核清单与当前可发布的官方证据。"""

import copy
import json
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_conmebol
import fetch_conmebol as fetch
from lib.conmebol_evidence import (
    CUP,
    DETAIL_FIELDS,
    QUALIFIERS,
    UNRELATED_CACHE,
    evidence_problems,
)
from lib.pagelib import article_anchor
from lib.paths import CONMEBOL_ZH_JSON, ROOT
from lib.source_snapshot import SnapshotReads, require_coverage


def identity_html(url, og=None):
    return f'<html><head><link rel="canonical" href="{url}"><meta property="og:url" content="{og or url}"></head><body>Archived article.</body></html>'


@pytest.fixture
def offline(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "CONMEBOL_CACHE", tmp_path)
    monkeypatch.setattr(fetch, "MIN_ART", 1)
    monkeypatch.setattr(fetch, "READS", SnapshotReads(offline=True))
    monkeypatch.setattr(
        fetch, "fetch_text", lambda *_a, **_kw: pytest.fail("离线解析发起了网络请求")
    )
    return tmp_path


@pytest.mark.parametrize(
    "url,actual",
    [
        (QUALIFIERS + "bolivia-vs-brasil/", QUALIFIERS + "bolivia-vs-brasil-2/"),
        (
            CUP + "independiente-del-valle-vs-deportivo-tachira/",
            CUP + "independiente-del-valle-vs-melgar/",
        ),
        (
            CUP + "independiente-del-valle-vs-lanus/",
            CUP + "independiente-del-valle-vs-melgar/",
        ),
        (
            CUP + "atletico-goianiense-vs-nacional/",
            CUP + "atletico-goianiense-vs-sao-paulo/",
        ),
    ],
)
def test_legacy_body_belongs_only_to_the_article_it_identifies(offline, url, actual):
    assert UNRELATED_CACHE[url] == actual
    assert fetch.legacy_cache_path(url) == fetch.legacy_cache_path(actual)
    assert fetch.cache_path(url) != fetch.cache_path(actual)
    historical = identity_html(actual)
    old_file = fetch.legacy_cache_path(url)
    old_file.write_text(historical, encoding="utf-8")
    assert fetch.fetch_page(actual, 1) == historical
    assert not fetch.fetch_page(url, 1)
    # 即使键是新的完整 URL 哈希，缓存内容仍须证明属于本篇。
    fetch.cache_path(url).write_text(historical, encoding="utf-8")
    assert not fetch.fetch_page(url, 1)
    own = identity_html(url)
    fetch.cache_path(url).write_text(own, encoding="utf-8")
    assert fetch.fetch_page(url, 1) == own and not fetch.READS.checked
    assert old_file.read_text(encoding="utf-8") == historical


def test_source_head_checks_article_and_list_pagination():
    url = next(iter(UNRELATED_CACHE))
    actual = UNRELATED_CACHE[url]
    assert not fetch.belongs_to(identity_html(url, actual), url)
    assert not fetch.belongs_to("<html><head><title>Article</title></head></html>", url)
    assert fetch.belongs_to(
        f'<head><meta property="og:url" content="{url}"></head>', url
    )
    page = fetch.COLUMN + "2/"
    assert fetch.belongs_to(identity_html(page, fetch.COLUMN), page)
    assert not fetch.belongs_to(identity_html(page, fetch.COLUMN), fetch.COLUMN + "3/")


def test_online_response_is_checked_before_only_the_hashed_file_is_updated(
    offline, monkeypatch
):
    url, actual = next(iter(UNRELATED_CACHE.items()))
    old = fetch.legacy_cache_path(url)
    old.write_text(identity_html(actual), encoding="utf-8")
    monkeypatch.setattr(fetch, "READS", SnapshotReads(refresh=True))
    monkeypatch.setattr(fetch, "BACKOFFS", [])
    monkeypatch.setattr(
        fetch, "fetch_text", lambda *_a, **_kw: (200, identity_html(actual))
    )
    assert not fetch.fetch_page(url, 1) and not fetch.cache_path(url).exists()
    monkeypatch.setattr(
        fetch, "fetch_text", lambda *_a, **_kw: (200, identity_html(url))
    )
    assert fetch.fetch_page(url, 1) == identity_html(url) and fetch.READS.checked
    assert old.read_text(encoding="utf-8") == identity_html(actual)


class Cards(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards = {}
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and attrs.get("class") == "ccard":
            self.current = self.cards[attrs["id"]] = {"text": [], "links": []}
        if tag == "a" and self.current is not None:
            self.current["links"].append(attrs["href"])

    def handle_endtag(self, tag):
        if tag == "article":
            self.current = None

    def handle_data(self, text):
        if self.current is not None:
            self.current["text"].append(text)


def test_published_cases_preserve_list_evidence_and_quarantine_previous_chinese(
    tmp_path, monkeypatch
):
    data = json.loads(fetch.CONMEBOL_JSON.read_bytes())
    zh = json.loads(CONMEBOL_ZH_JSON.read_bytes())
    cases = {c["url"]: c for c in data["cases"]}
    pending = {url for url, c in cases.items() if c.get("detail_status") == "pending"}
    history = zh["pending_cases"]
    assert set(history) == {
        url for url in UNRELATED_CACHE if not url.endswith("-vs-nacional/")
    }
    assert not evidence_problems(data)
    for url in pending:
        case = cases[url]
        assert case["title"].endswith(case["match"]) and case["date"]
        assert all(case[field] == "" for field in DETAIL_FIELDS)
        assert url not in zh["cases"]
    for url, old in history.items():
        actual = UNRELATED_CACHE[url]
        assert old["previous_article_url"] == actual
        historical_words = (
            ("Penal", "点球判罚")
            if url.startswith(QUALIFIERS)
            else ("Fuera de Juego", "越位")
        )
        assert (old["previous_situacion_es"], old["situation"]) == historical_words
    monkeypatch.setattr(build_conmebol, "SITE", tmp_path)
    build_conmebol.build_page(data, zh)
    html = Cards()
    html.feed((tmp_path / "conmebol.html").read_text(encoding="utf-8"))
    assert len(html.cards) == len(cases)
    for url, case in cases.items():
        card = html.cards[article_anchor(url)]
        assert url in card["links"]
        if url in pending:
            assert card["links"] == [url]
            text = "".join(card["text"])
            assert (
                "文章详情待核" in text
                and f"文章发布 {case['date']}" in text
                and case["title"] in text
            )
            if url in history:
                assert history[url]["situation"] not in text
        elif case.get("youtube"):
            assert case["youtube"] in card["links"]


def test_pending_is_limited_to_confirmed_collisions_and_completed_sources_cannot_regress(
    offline,
):
    data = json.loads(fetch.CONMEBOL_JSON.read_bytes())
    case = next(c for c in data["cases"] if c["url"] in UNRELATED_CACHE)
    url = case["url"]
    minimal = {k: case[k] for k in ("title", "date", "url", "excerpt_es", "comp")}
    result = fetch.enrich({**minimal, **fetch.parse_case(minimal)})
    assert result["unrelated_cache_url"] == UNRELATED_CACHE[
        url
    ] and not evidence_problems({"cases": [result]})
    with pytest.raises(ValueError, match="判例文章不可用"):
        fetch.enrich({**minimal, "url": UNRELATED_CACHE[url]})
    completed = copy.deepcopy(result)
    del completed["detail_status"], completed["unrelated_cache_url"]
    with pytest.raises(ValueError, match="缺少"):
        require_coverage(
            fetch.identities({"cases": [completed]}),
            fetch.identities({"cases": [result]}),
            "CONMEBOL",
        )
    for changes in (
        {"url": UNRELATED_CACHE[url]},
        {"youtube": "other video"},
        {"situacion_es": "Penal"},
        {"match": "Other fixture"},
        {"unrelated_cache_url": url},
    ):
        assert evidence_problems({"cases": [{**result, **changes}]})
    incomplete = dict(result)
    del incomplete["fecha"]
    assert evidence_problems({"cases": [incomplete]})
    schema = json.loads((ROOT / "schemas/conmebol.schema.json").read_bytes())
    pairs = schema["properties"]["cases"]["items"]["allOf"][0]["then"]["oneOf"]
    published = {
        row["properties"]["url"]["const"]: row["properties"]["unrelated_cache_url"][
            "const"
        ]
        for row in pairs
    }
    assert published == UNRELATED_CACHE
