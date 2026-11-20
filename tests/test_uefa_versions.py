"""UEFA 译层只呈现仍与当前官方版本对应的标题、导语和判读准则。"""

import copy
import json
import sys
from html import escape
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_search
import build_uefa
from lib.uefa_content import apply_zh


@pytest.fixture
def materials():
    return (
        json.loads(build_uefa.UEFA_JSON.read_text(encoding="utf-8")),
        build_uefa.load_zh(),
    )


def test_snapshot_keeps_all_author_translations(materials):
    data, zh = materials
    original = copy.deepcopy(zh)
    warnings = []
    apply_zh(data, zh, warnings.append)
    assert not warnings
    for group in data["groups"]:
        translated = zh["groups"][group["key"]]
        assert group["name_current_cn"] == group["name_cn"]
        assert group["intro_cn"] == translated["intro"]
        assert group["criteria_cn"] == translated.get("criteria", [])
        for item in group["items"]:
            assert item["title_cn"] == zh["items"][item["id"]]["title"]
    assert zh == original


def test_current_official_text_replaces_stale_fields_in_existing_anchors(
    materials, tmp_path, monkeypatch
):
    data, zh = materials
    group = data["groups"][1]
    item = group["items"][0]
    block = group["criteria"][0]
    apply_zh(data, zh)
    old = [group["name_current_cn"], group["intro_cn"], item["title_cn"]]
    group["name_en"] = "Updated example group"
    group["intro"] = "Updated official introduction."
    item["title"] = "Updated example video title"
    item["caption"] = "Current official caption."
    block["items"][0] = "Updated criteria for A & B."
    warnings = []
    apply_zh(data, zh, warnings.append)
    assert len(warnings) == 4
    assert group["criteria_cn"][0] is None
    assert all(group["criteria_cn"][1:])
    assert not (group["name_current_cn"] or group["intro_cn"] or item["title_cn"])
    assert group["items"][1]["title_cn"]
    monkeypatch.setattr(build_uefa, "SITE", tmp_path)
    build_uefa.build_page(data)
    page = (tmp_path / "uefa.html").read_text(encoding="utf-8")
    assert all(text not in page for text in old)
    assert page.count(build_uefa.REVIEW_NOTE) == 4
    assert f'<h4 lang="en">{escape(block["h"])}</h4>' in page
    assert '<ul lang="en"><li>Updated criteria for A &amp; B.</li>' in page
    assert 'id="u-1c1"' in page and f'href="{item["url"]}"' in page
    assert f'<h3 lang="en">{item["title"]}</h3>' in page
    assert item["caption"] in page and "cfa.uefa-en" in page
    current = tmp_path / "current.json"
    current.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(build_search, "UEFA_JSON", current)
    rows = [
        row
        for row in build_search.build_docs()
        if row[1] == "UEFA" and row[2] == item["title"]
    ]
    assert len(rows) == 1
    assert old[2] not in rows[0][4]
    assert group["name_en"].lower() in rows[0][4].lower()


def test_moved_and_new_blocks_and_videos_keep_their_own_translation(materials):
    data, zh = materials
    group = data["groups"][1]
    translated = zh["groups"][group["key"]]["criteria"]
    group["criteria"].reverse()
    group["criteria"].insert(0, {"h": "Added section", "items": ["First condition."]})
    group["items"].reverse()
    group["items"].insert(0, {**group["items"][0], "id": "new-edition-video"})
    apply_zh(data, zh)
    assert group["criteria_cn"] == [None, *reversed(translated)]
    assert not group["items"][0]["title_cn"]
    for item in group["items"][1:]:
        assert item["title_cn"] == zh["items"][item["id"]]["title"]


@pytest.mark.parametrize("change", ["reorder", "rename", "no_pin", "duplicate"])
def test_changed_criteria_cannot_inherit_other_blocks_chinese(materials, change):
    data, zh = materials
    group = data["groups"][1]
    block = group["criteria"][0]
    if change == "reorder":
        block["items"].reverse()
    elif change == "rename":
        block["h"] += " (updated)"
    elif change == "no_pin":
        zh["source_versions"]["groups"][group["key"]]["criteria"][0] = None
    else:
        group["criteria"].append(copy.deepcopy(block))
    apply_zh(data, zh)
    assert group["criteria_cn"][0] is None
    assert group["criteria_cn"][1]
    if change == "duplicate":
        assert group["criteria_cn"][-1] is None


def test_duplicate_video_ids_and_absent_versions_are_never_guessed(materials):
    data, zh = materials
    group = data["groups"][0]
    item = group["items"][0]
    group["items"].append(copy.deepcopy(item))
    apply_zh(data, zh)
    assert not (item["title_cn"] or group["items"][-1]["title_cn"])
    assert group["items"][1]["title_cn"]
    del zh["source_versions"]
    apply_zh(data, zh)
    assert not (
        group["items"][1]["title_cn"] or group["intro_cn"] or group["name_current_cn"]
    )
    assert all(block is None for block in data["groups"][1]["criteria_cn"])
