"""Offline results open the article that cites the matching official permalink."""

import json
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_conmebol
import build_pro
import build_search
from lib.pagelib import article_anchor


class ArticleLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.cards = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and "id" in attrs:
            self.current = attrs["id"]
            assert self.current not in self.cards
            self.cards[self.current] = []
        elif tag == "a" and self.current is not None:
            self.cards[self.current].append(attrs.get("href"))

    def handle_endtag(self, tag):
        if tag == "article":
            self.current = None


def test_every_indexed_article_has_one_local_card_and_official_source(
    monkeypatch, tmp_path
):
    docs = build_search.build_docs()
    for module, name, label, key in (
        (build_pro, "pro", "PRO", "articles"),
        (build_conmebol, "conmebol", "CONMEBOL", "cases"),
    ):
        data = json.loads((build_search.DATA / f"{name}.json").read_bytes())
        monkeypatch.setattr(module, "SITE", tmp_path)
        if name == "conmebol":
            zh = json.loads(build_search.CONMEBOL_ZH_JSON.read_bytes())
            module.build_page(data, zh)
        else:
            module.build_page(data)
        parser = ArticleLinks()
        parser.feed((tmp_path / f"{name}.html").read_text(encoding="utf-8"))
        targets = [d[3] for d in docs if d[1] == label]
        assert len(targets) == len(set(targets)) == len(parser.cards) == len(data[key])
        assert set(targets) == {f"{name}.html#{anchor}" for anchor in parser.cards}
        for article in data[key]:
            url = article["url"]
            anchor = article_anchor(url)
            assert anchor == article_anchor(url.rstrip("/") + "/")
            assert url in parser.cards[anchor]
