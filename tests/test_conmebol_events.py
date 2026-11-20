"""从文章正文核对南美 VAR 的字段、视频、双语版本及旧译稿。"""

import copy
import hashlib
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
    QUALIFIERS,
    event_anchor,
    event_translation,
    evidence_problems,
    translation_problems,
)
from lib.pagelib import article_anchor
from lib.paths import CONMEBOL_JSON, CONMEBOL_ZH_JSON
from lib.source_snapshot import require_coverage


def video(vid, minute):
    return f'<iframe src="https://www.youtube.com/embed/{vid}?feature=oembed" title="Revisión VAR | Minuto {minute}"></iframe>'


def body(*parts):
    return (
        '<div data-widget_type="theme-post-content.default"><div>'
        + "".join(parts)
        + "</div></div>"
    )


def field(name, value):
    return f"<p><strong>{name}:</strong> {value}</p>"


def fixture(*extra):
    c = {"url": CUP + "partido/", "title": "Análisis: Local vs. Visitante"}
    return fetch.article_details(
        video("outside0000", 88)
        + body(
            "<p>São Paulo vs. Club</p>",
            field("Fecha", "01-02-2022"),
            field("Ciudad", "Quito"),
            field("Estadio", "Nacional"),
            *extra,
        )
        + video("outside0001", 99),
        c,
    )


def test_same_event_renders_its_own_languages_and_stoppage_time():
    row = fixture(
        field("Situación", "No Gol"),
        field("Minuto", "61′"),
        "<p>ESP:</p>",
        video("aaaa0000000", "61"),
        "<p>POR:</p>",
        video("bbbb0000000", "61"),
        field("Tópico", "No Penal"),
        field("Minuto", "90 + 2′"),
        video("cccc0000000", "92"),
    )
    assert row["match"] == "São Paulo vs. Club" and row["fecha"] == "01-02-2022"
    assert [(e["situacion_es"], e["minuto"]) for e in row["events"]] == [
        ("No Gol", "61"),
        ("No Penal", "90+2"),
    ]
    es, pt = row["events"][0]["videos"]
    assert es["lang"] == "es" and pt["lang"] == "pt" and row["youtube"] == es["url"]
    assert len(row["events"][1]["videos"]) == 1
    eid = event_anchor("article", row["events"][0])
    assert eid.endswith("aaaa0000000")
    row["events"][0]["videos"].reverse()
    assert event_anchor("article", row["events"][0]) == eid


def test_inconsistent_source_labels_stay_literal_and_unclassified():
    event = fixture(
        field("Situación", "68′"), field("Minuto", "Gol"), video("aaaa0000000", "68")
    )["events"][0]
    assert event["source_fields"] == {"situacion_es": "68′", "minuto": "Gol"}
    assert (
        not event["situacion_es"]
        and not event["minuto"]
        and event["situacion_norm"] == "other"
    )
    with pytest.raises(ValueError, match="视频标题不一致"):
        fixture(
            field("Situación", "Gol"),
            field("Minuto", "60′"),
            video("aaaa0000000", "85"),
        )
    with pytest.raises(ValueError, match="逐一配对"):
        fixture(field("Situación", "Gol"), field("Minuto", "60′"))
    with pytest.raises(ValueError, match="分钟无法对应"):
        fixture(field("Minuto", "60′"), video("aaaa0000000", "60"))
    with pytest.raises(ValueError, match="情境或分钟之前"):
        fixture(
            video("aaaa0000000", "60"),
            field("Situación", "Gol"),
            field("Minuto", "60′"),
        )


class Targets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.articles, self.events = {}, {}
        self.article = self.event = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article":
            self.article = attrs["id"]
            self.articles[self.article] = []
        if attrs.get("class") == "case-event":
            self.event = attrs["id"]
            self.events[self.event] = []
        if tag == "a" and self.article:
            self.articles[self.article].append(attrs["href"])
            if self.event and "youtube.com/" in attrs["href"]:
                self.events[self.event].append(attrs["href"])

    def handle_endtag(self, tag):
        if tag == "article":
            self.article = self.event = None


def test_current_all_articles_videos_and_recovered_five_incidents(
    tmp_path, monkeypatch
):
    data = json.loads(CONMEBOL_JSON.read_bytes())
    zh = json.loads(CONMEBOL_ZH_JSON.read_bytes())
    cases = {c["url"]: c for c in data["cases"]}
    events = [e for c in cases.values() for e in c["events"]]
    assert (len(cases), len(events), sum(len(e["videos"]) for e in events)) == (
        60,
        88,
        95,
    )
    assert sum(len(c["events"]) > 1 for c in cases.values()) >= 19
    assert sum(len(e["videos"]) > 1 for e in events) >= 7
    assert sum("source_fields" in e for e in events) == 2
    assert not evidence_problems(data) and not translation_problems(data, zh)
    assert not any(c.get("detail_status") for c in cases.values())
    expected = {
        QUALIFIERS + "bolivia-vs-brasil/": [("62", "Posible Penal", "0iotrWLgAJ0")],
        CUP + "independiente-del-valle-vs-deportivo-tachira/": [
            ("89", "No Penal", "gnue9xzWApw")
        ],
        CUP + "independiente-del-valle-vs-lanus/": [
            ("60", "Gol", "ONE6TOLhbIY"),
            ("85", "Error de Identidad", "Kq9pP_NKwe4"),
        ],
        CUP + "atletico-goianiense-vs-nacional/": [
            ("91", "Tarjeta Roja", "6wAFK299Me0")
        ],
    }
    history = next(v for v in data["source_history"] if v["date"] == "2026-11-20")
    assert set(history["article_sha256"]) == set(expected)
    assert all(len(s) == 64 for s in history["article_sha256"].values())
    for u, triples in expected.items():
        assert [
            (e["minuto"], e["situacion_es"], e["videos"][0]["url"].split("=")[-1])
            for e in cases[u]["events"]
        ] == triples
    # 仅锁定原有 47 篇人工译稿；以后另加的文章或译稿可照常增长。
    original_articles = set(
        """1b5cdd2b4374962d 8c306105c577d322 f2522d425e67f7e2 c03af5e82c179d66 908c7dec52f4fb1b
1238fc678f406519 bbc3f39f72682755 ba6f7d13277a0cb2 20205f1d369d020b 87d5d662fbe1abf8
b8c21e7cebb049c3 79ebbd49ce3461b1 50c16e301ebbf357 cc018d7ef994b5df e00088b2560a8d98
5ca02659e57bbf4e febfc46c198b93d6 f9ee63b61ce90299 b4927db9d57834a9 f6716aec22371017
de03d38ee5836074 bdec970c054a2edb 412e1abfa3bfe036 5897914a7fa26353 f1ba74bde837caf5
7ca9d953c9a8d244 21915fb7ccf7187b 28a3498a07afb400 d583823481b0a15c 2a8dec783e4636c9
ea1ec8abc144029e c3b2e0e7ca4dc0f0 f6a08a2c53faa975 3cdc2a952fd274a3 b148d961af874b2d
3a012800c5afafcd 5e2dd13eb7940fe5 52bbb1d3c78ee13d 59a4c2e4b8ffee5d add25398c7e894fe
af192b7bfb3622d3 2f007ca7ea5d0c0e 17e79b3d50e0d5b4 a7124af2ad2b0288 204021e69a0978c4
819d3d80d72bdcb9 0f65da6c2d6a506b""".split()
    )
    old = {
        u: r["situation"]
        for u, r in zh["cases"].items()
        if article_anchor(u).removeprefix("article-") in original_articles
    }
    assert (
        hashlib.sha256(
            json.dumps(old, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        == "d6ac236834fb93e918dff1015ff1056ee2b2f40d9f104f19a8853ea16b3cf943"
    )
    brasil = cases[QUALIFIERS + "brasil-vs-colombia/"]
    assert [event_translation(brasil["url"], e, zh) for e in brasil["events"]] == [
        "进球无效",
        "非点球",
    ]
    monkeypatch.setattr(build_conmebol, "SITE", tmp_path)
    build_conmebol.build_page(data, zh)
    page = (tmp_path / "conmebol.html").read_text("utf8")
    targets = Targets()
    targets.feed(page)
    assert len(targets.articles) == len(cases) and len(targets.events) == len(events)
    for u, c in cases.items():
        assert u in targets.articles[article_anchor(u)]
        for e in c["events"]:
            assert targets.events[event_anchor(u, e)] == [v["url"] for v in e["videos"]]
    assert page.count("官方字段标注不一致") == 2 and "文章详情待核" not in page
    assert "Situación: 68′ · Minuto: Gol" in page
    assert not any(line.endswith(" ") for line in page.splitlines())
    with pytest.raises(ValueError, match="缺少"):
        altered = copy.deepcopy(data)
        next(c for c in altered["cases"] if len(c["events"]) > 1)["events"].pop()
        require_coverage(fetch.identities(data), fetch.identities(altered), "CONMEBOL")


def test_only_registered_exact_events_can_be_untranslated_and_can_be_reviewed():
    data = json.loads(CONMEBOL_JSON.read_bytes())
    zh = json.loads(CONMEBOL_ZH_JSON.read_bytes())
    assert len(zh["untranslated"]) == 8
    eid, text = next(iter(zh["untranslated"].items()))
    revised = copy.deepcopy(zh)
    del revised["untranslated"][eid]
    assert translation_problems(data, revised)
    revised["events"] = {eid: {"source_situation": text, "situation": "本条经核译名"}}
    assert not translation_problems(data, revised)
    revised["events"][eid]["source_situation"] += " updated"
    assert translation_problems(data, revised)
    revised = copy.deepcopy(zh)
    revised["untranslated"][eid] += " updated"
    assert translation_problems(data, revised)
    changed = copy.deepcopy(data)
    c = next(c for c in changed["cases"] if len(c["events"]) > 1)
    c["events"][1]["situacion_es"] = "Nuevo caso"
    assert translation_problems(changed, zh)
    missing = copy.deepcopy(data)
    missing["cases"] = [
        c
        for c in missing["cases"]
        if not any(event_anchor(c["url"], e) == eid for e in c["events"])
    ]
    assert translation_problems(missing, zh)
