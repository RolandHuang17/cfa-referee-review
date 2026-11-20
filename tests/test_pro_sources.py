"""PRO 的官方文章来源、页面卡片与已存视频索引共用同一边界。"""

import json
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_pro
import fetch_pro
from lib.pagelib import article_anchor
from lib.pro_sources import BASE, SOURCE, USSF, article_url, video_url
from lib.source_cache import SourceCache

ARTICLE = BASE + "/2026/06/01/review/"
VIDEO = "https://www.youtube.com/watch?v=abcdefghijk"


class Cards(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = {}
        self.card = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and attrs.get("class") == "acard":
            self.card = attrs["id"]
            self.links[self.card] = []
        if tag == "a" and self.card:
            self.links[self.card].append(attrs["href"])

    def handle_endtag(self, tag):
        if tag == "article":
            self.card = ""


def test_lists_keep_official_dated_posts_and_normalize_equivalent_links():
    page = """
      <h2 class="entry-title"><a href="https://example.org/2026/06/01/review/">Elsewhere</a></h2>
      <h2 class="entry-title"><a href="/2026/06/01/review/?edition=summer">Notes &amp; Decisions</a></h2>
      <h2 class="entry-title"><a href="https://proreferees.com:443/2026/06/01/review">Same article</a></h2>
      <h2 class="entry-title"><a href="https://proreferees.com/category/inside-video-review/">Category</a></h2>
    """
    assert fetch_pro.parse_listing(page) == [
        {"title": "Notes & Decisions", "url": ARTICLE}
    ]
    assert (
        fetch_pro.parse_listing(f'<a href="{ARTICLE}">Previous article</a>')[0]["url"]
        == ARTICLE
    )
    assert article_url(ARTICLE.replace(".com/", ".com:8443/")) == ""
    assert article_url(ARTICLE.replace("https:", "http:")) == ""
    assert article_url(BASE + "/old-permalink/") == BASE + "/old-permalink/"
    assert not article_url(BASE + "/old-permalink/", dated=True)


def test_only_iframes_from_the_official_article_supply_video_ids(monkeypatch):
    frame = "https://www.youtube-nocookie.com/embed/abcdefghijk?feature=oembed"
    markup = f"""<iframe src="{frame}"></iframe><iframe src="{frame}"></iframe>
      <p>https://www.youtube.com/embed/01234567890</p>
      <iframe src="https://example.org/embed/mnopqrstuvw"></iframe>"""
    requested = []

    def read(url):
        requested.append(url)
        return markup

    monkeypatch.setattr(fetch_pro, "fetch_page", read)
    assert fetch_pro.article_videos(ARTICLE) == [VIDEO]
    assert fetch_pro.article_videos("https://example.org/2026/06/01/review/") == []
    assert requested == [ARTICLE]
    assert not video_url("https://example.org/watch?v=abcdefghijk")


def test_existing_cards_preserve_anchors_and_only_publish_verified_links(
    tmp_path, monkeypatch
):
    data = json.loads(build_pro.PRO_JSON.read_text(encoding="utf8"))
    monkeypatch.setattr(build_pro, "SITE", tmp_path)
    build_pro.build_page(data)
    cards = Cards()
    cards.feed((tmp_path / "pro.html").read_text(encoding="utf8"))
    assert len(cards.links) == len(data["articles"])
    for a in data["articles"]:
        assert article_url(a["url"]) == a["url"]
        assert all(video_url(url) == url for url in a.get("videos", []))
        assert cards.links[article_anchor(a["url"])] == a.get("videos", [])[:1] + [
            a["url"]
        ]

    record = data["articles"][0]
    unknown = "https://example.org/reference/"
    old = dict(
        data,
        source=unknown,
        ussf=dict.fromkeys(USSF, unknown),
        articles=[
            dict(record, url=unknown, videos=[VIDEO]),
            dict(record, url=ARTICLE, videos=[unknown, VIDEO]),
        ],
    )
    build_pro.build_page(old)
    markup = (tmp_path / "pro.html").read_text(encoding="utf8")
    cards = Cards()
    cards.feed(markup)
    assert not cards.links[article_anchor(unknown)]
    assert cards.links[article_anchor(ARTICLE)] == [VIDEO, ARTICLE]
    assert "文章来源待核对" in markup and all(
        url in markup for url in (SOURCE, *USSF.values())
    )
    assert unknown not in markup


def test_offline_refresh_keeps_uncertain_old_metadata_without_requesting_it(
    tmp_path, monkeypatch
):
    unknown = "https://example.org/2026/06/01/review/"
    aliases = ARTICLE + "?edition=summer"
    sample = {
        "title": "Existing notes",
        "date": "2026-06-01",
        "series": "ivr",
        "videos": [],
    }
    previous = {"articles": [dict(sample, url=unknown), dict(sample, url=aliases)]}
    dest = tmp_path / "pro.json"
    dest.write_text(json.dumps(previous), encoding="utf8")
    requested = []
    monkeypatch.setattr(fetch_pro, "PRO_JSON", dest)
    monkeypatch.setattr(
        fetch_pro, "CACHE_READER", SourceCache(offline=True, refresh=True)
    )
    monkeypatch.setattr(fetch_pro, "fetch_page", lambda url: "")
    monkeypatch.setattr(
        fetch_pro, "article_videos", lambda url: requested.append(url) or [VIDEO]
    )
    fetch_pro.parse_all()
    after = {
        a["url"]: a for a in json.loads(dest.read_text(encoding="utf8"))["articles"]
    }
    assert requested == [ARTICLE]
    assert after[unknown] == previous["articles"][0]
    assert after[aliases]["videos"] == [VIDEO]
