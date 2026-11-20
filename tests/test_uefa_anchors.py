"""官网调序、增删与多组引用时，已发行的 UEFA 书签仍能定位同一录像。"""

import copy
import json
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_uefa
from lib.uefa_anchors import LEGACY_GROUPS, LEGACY_VIDEOS, group_anchor, video_anchor


class Targets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = Counter()
        self.group_aliases = {}
        self.card_groups = {}
        self.current_group = ""
        self.cards = {}
        self.current = []
        self.pending = ""
        self.permalinks = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        anchor = attrs.get("id")
        if anchor:
            self.ids[anchor] += 1
        klass = attrs.get("class")
        if klass == "legacy-uefa-target":
            self.pending = anchor
        elif tag == "section" and klass == "gsec":
            self.current_group = anchor
            if self.pending:
                self.group_aliases[self.pending] = anchor
            self.pending = ""
        elif tag == "article" and klass == "hcard":
            self.current = [key for key in (anchor, self.pending) if key]
            self.pending = ""
        elif tag == "a" and klass == "watch":
            for key in self.current:
                self.cards[key] = attrs["href"]
                self.card_groups[key] = self.current_group
        elif tag == "a" and klass == "hid":
            self.permalinks.append(attrs["href"][1:])


def render(data, tmp_path, monkeypatch):
    monkeypatch.setattr(build_uefa, "SITE", tmp_path)
    build_uefa.apply_zh(data, build_uefa.load_zh())
    build_uefa.build_page(data)
    result = Targets()
    result.feed((tmp_path / "uefa.html").read_text(encoding="utf-8"))
    assert all(count == 1 for count in result.ids.values())
    assert all(anchor in result.cards for anchor in result.permalinks)
    return result


def test_every_old_alias_follows_its_video_after_source_reordering(
    tmp_path, monkeypatch
):
    data = json.loads(build_uefa.UEFA_JSON.read_text(encoding="utf-8"))
    urls = {
        video_anchor(item["id"], item["url"]): item["url"]
        for group in data["groups"]
        for item in group["items"]
    }
    first = "video-02a7-21381fdca64f-3a2d59a205aa-1000"
    assert LEGACY_VIDEOS[first] == ("factual-decisions", "u-0c1")
    assert len(LEGACY_GROUPS) == 12 and len(LEGACY_VIDEOS) == 83
    data["groups"].reverse()
    for group in data["groups"]:
        group["items"].reverse()
    group = data["groups"][0]
    new = {**group["items"][0], "id": "new-video", "url": "https://example.org/new"}
    group["items"].insert(0, new)
    parsed = render(data, tmp_path, monkeypatch)
    for key, old_alias in LEGACY_GROUPS.items():
        if group_anchor(key) in parsed.ids:
            assert parsed.group_aliases[old_alias] == group_anchor(key)
        else:
            assert old_alias not in parsed.ids
    for canonical, (_, old_alias) in LEGACY_VIDEOS.items():
        if canonical in urls:
            assert parsed.cards[old_alias] == parsed.cards[canonical] == urls[canonical]
        else:
            assert old_alias not in parsed.ids
    assert parsed.cards["video-new-video"] == new["url"]
    assert parsed.cards["u-0c1"] == urls[first]


def test_video_in_two_groups_or_moved_group_keeps_one_public_target(
    tmp_path, monkeypatch
):
    item = {
        "id": "02a7-21381fdca64f-3a2d59a205aa-1000",
        "title": "Example video",
        "url": "https://example.org/video/",
    }
    old = {
        "key": "factual-decisions",
        "name_en": "Decisions",
        "criteria": [],
        "items": [item],
    }
    data = {"groups": [old]}
    target = video_anchor(item["id"])
    old_alias = LEGACY_VIDEOS[target][1]
    new_group = {**old, "key": "a-new-group", "items": [copy.deepcopy(item)]}
    data["groups"].insert(0, new_group)
    both = render(data, tmp_path, monkeypatch)
    assert both.permalinks.count(target) == 2
    assert both.cards[target] == both.cards[old_alias] == item["url"]
    assert both.card_groups[old_alias] == "group-factual-decisions"
    old["items"].remove(item)
    moved = render(data, tmp_path, monkeypatch)
    assert moved.cards[target] == moved.cards[old_alias] == item["url"]
    assert moved.card_groups[old_alias] == "group-a-new-group"
    new_group["items"].clear()
    removed = render(data, tmp_path, monkeypatch)
    assert target not in removed.ids and old_alias not in removed.ids


def test_missing_id_uses_permalink_and_punctuation_has_unambiguous_fragment():
    url = "https://example.org/edition/video/"
    assert video_anchor("", url) == video_anchor("", url.rstrip("/"))
    assert video_anchor("", url) != video_anchor("", url + "second")
    assert video_anchor("clip 1") != video_anchor("clip-1")
    assert "#" not in video_anchor("new#clip") and " " not in group_anchor("new group")
