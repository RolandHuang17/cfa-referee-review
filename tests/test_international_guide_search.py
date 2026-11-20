"""RAP 各期与国际导航资源应逐条可搜，并保留人工策展的原始链接。"""

import json
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_intl
import build_rap
import build_search


class Cards(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = {}
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and attrs.get("class") in ("edition", "res"):
            self.current = attrs["id"]
            assert self.current not in self.links
            self.links[self.current] = []
        if self.current and tag == "a":
            self.links[self.current].append(attrs["href"])

    def handle_endtag(self, tag):
        if tag == "article":
            self.current = None


def test_each_guide_has_one_local_target_and_its_curated_source_links(
    tmp_path, monkeypatch
):
    rap = json.loads(build_rap.RAP_JSON.read_text(encoding="utf8"))
    intl = json.loads(build_intl.INTL_JSON.read_text(encoding="utf8"))
    monkeypatch.setattr(build_rap, "SITE", tmp_path)
    monkeypatch.setattr(build_intl, "SITE", tmp_path)
    build_rap.build_page(rap)
    build_intl.build_page(intl)
    guide_docs = [
        doc for doc in build_search.build_docs() if doc[1] in ("RAP 期目", "资源导航")
    ]
    by_url = {doc[3]: doc for doc in guide_docs}
    assert len(by_url) == len(guide_docs)
    for page, prefix, records in (
        ("rap.html", "edition-", rap["editions"]),
        ("intl.html", "resource-", [r for g in intl["groups"] for r in g["resources"]]),
    ):
        parser = Cards()
        parser.feed((tmp_path / page).read_text(encoding="utf8"))
        assert len(parser.links) == len(records)
        assert sum(key.startswith(page + "#") for key in by_url) == len(records)
        for record in records:
            anchor = prefix + record["id"]
            assert parser.links[anchor] == [link["url"] for link in record["links"]]
            doc = by_url[page + "#" + anchor]
            assert record.get("title", record.get("name")) in doc[2]
            assert record.get("note_cn", "").lower() in doc[4].lower()


def test_pending_edition_is_marked_on_result_and_card_but_unknown_era_is_not_listed(
    tmp_path, monkeypatch
):
    rap = json.loads(build_rap.RAP_JSON.read_text(encoding="utf8"))
    item = dict(
        rap["editions"][0], id="2027-1", title="RAP 2027-1", status="unreviewed"
    )
    item.pop("status_cn", None)
    rap["editions"].extend([item, dict(item, id="2027-2", title="RAP 2027-2", era="")])
    snapshot = tmp_path / "rap.json"
    snapshot.write_text(json.dumps(rap), encoding="utf8")
    monkeypatch.setattr(build_search, "RAP_JSON", snapshot)
    docs = {row[3]: row for row in build_search.build_docs() if row[1] == "RAP 期目"}
    assert docs["rap.html#edition-2027-1"][2] == "RAP 2027-1 · 待人工核对"
    assert "rap.html#edition-2027-2" not in docs
    monkeypatch.setattr(build_rap, "SITE", tmp_path)
    build_rap.build_page(rap)
    page = (tmp_path / "rap.html").read_text(encoding="utf8")
    assert '<span class="ed-status badge pending">待人工核对</span>' in page
    assert 'id="edition-2027-2"' not in page
