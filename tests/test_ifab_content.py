"""IFAB 英文来源、中文版本和检索锚点的同源契约。"""

import copy
import json
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_ifab
import build_search
from lib.ifab_content import documents, fingerprint, search_rows, version_inputs


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = Counter()

    def handle_starttag(self, tag, attrs):
        anchor = dict(attrs).get("id")
        if anchor:
            self.ids[anchor] += 1


def source_and_translation():
    data = {
        "sections": [
            {
                "id": "s1",
                "h": "Principles",
                "num": "1",
                "blocks": [
                    {
                        "h": "",
                        "items": [
                            {"k": "p", "t": "A & B"},
                            {"k": "li", "t": "Start again."},
                        ],
                    }
                ],
            }
        ],
        "faq": [{"id": "q1", "q": "What does A & B mean?", "a": "Review both."}],
    }
    zh = {
        "sections": {
            "s1": {
                "h": "原则",
                "blocks": {
                    "_head": [{"k": "p", "t": "甲与乙"}, {"k": "li", "t": "重新开始。"}]
                },
            }
        },
        "faq": {"q1": {"q": "甲与乙是什么？", "a": "两者均复核。"}},
    }
    zh["source_versions"] = {
        key: fingerprint(value) for key, value in version_inputs(data)
    }
    return data, zh


def test_real_search_entries_cover_both_languages_and_link_to_single_targets(
    tmp_path, monkeypatch
):
    data = json.loads(build_ifab.IFAB_JSON.read_text(encoding="utf8"))
    zh = json.loads(build_ifab.IFAB_ZH_JSON.read_text(encoding="utf8"))
    docs = documents(data, zh)
    monkeypatch.setattr(build_ifab, "SITE", tmp_path)
    build_ifab.build_page(data, zh)
    anchors = Anchors()
    anchors.feed((tmp_path / "ifab.html").read_text(encoding="utf8"))
    assert max(anchors.ids.values()) == 1
    rows = [r for r in build_search.build_docs() if r[1] == "IFAB"]
    indexed = {r[3].split("#", 1)[1]: r[4].lower() for r in rows}
    assert len(rows) == len(indexed)
    assert all(anchors.ids[key] == 1 for key in indexed)
    for doc in docs:
        assert anchors.ids[doc["id"]] == 1
        for block in doc["blocks"]:
            for item in block["items"]:
                assert anchors.ids[item["id"]] == 1
                if block["faq_copy"]:
                    assert item["id"] not in indexed
                else:
                    assert " ".join(item["en"].lower().split()) in indexed[item["id"]]
                    assert " ".join(item["zh"].lower().split()) in indexed[item["id"]]
        for q in doc["faq"]:
            if q["old_id"]:
                assert anchors.ids[q["old_id"]] == 1
            for field in ("q", "a", "zq", "za"):
                assert " ".join(q[field].lower().split()) in indexed[q["id"]]
    en, zh_term = "one corner flag is missing", "缺一支角旗"
    assert [k for k, t in indexed.items() if en in t] == [
        k for k, t in indexed.items() if zh_term in t
    ]
    assert sum(en in t for t in indexed.values()) == 1


@pytest.mark.parametrize(
    "change", ["insert", "edit", "reverse", "wrong_type", "missing", "unversioned"]
)
def test_source_drift_never_assigns_old_chinese_to_changed_english(change):
    data, zh = source_and_translation()
    items = data["sections"][0]["blocks"][0]["items"]
    old_anchor = documents(data, zh)[0]["blocks"][0]["items"][0]["id"]
    if change == "insert":
        items.insert(0, {"k": "p", "t": "An additional condition."})
    elif change == "edit":
        items[0]["t"] = "A or B"
    elif change == "reverse":
        items.reverse()
    elif change == "wrong_type":
        zh["sections"]["s1"]["blocks"]["_head"][0]["k"] = "li"
    elif change == "missing":
        del zh["sections"]["s1"]["blocks"]["_head"]
    else:
        del zh["source_versions"]
    warnings = []
    block = documents(data, zh, warnings.append)[0]["blocks"][0]
    assert warnings and all(not item["zh"] for item in block["items"])
    assert [item["en"] for item in block["items"]] == [i["t"] for i in items]
    assert not any(
        "甲与乙" in text
        for _, _, text in search_rows(data, zh)
        if "Start again." in text
    )
    markup = build_ifab.render_doc_body([block])
    assert 'class="en"' not in markup and '<span lang="en">' in markup
    if change != "missing":
        assert "旧版译文（待核对）" in markup and "甲与乙" in markup
    if change == "insert":
        assert old_anchor == block["items"][1]["id"]


def test_partial_translations_and_faq_version_changes_escape_once_and_keep_source():
    data, zh = source_and_translation()
    zh["sections"]["s1"]["blocks"]["_head"][1]["t"] = ""
    del zh["faq"]["q1"]["a"]
    doc, faqdoc = documents(data, zh)
    markup = build_ifab.render_doc_body(doc["blocks"])
    assert '<span class="en" lang="en">A &amp; B</span>' in markup
    assert '<span lang="en">Start again.</span>' in markup
    q = faqdoc["faq"][0]
    assert '<div lang="en">Review both.</div>' in build_ifab.render_faq(q)
    old_anchor = q["id"]
    data["faq"][0]["a"] = "A new official answer."
    changed = documents(data, zh)[-1]["faq"][0]
    assert changed["id"] == old_anchor and changed["old_id"] == "faq-q1"
    assert not changed["zq"] and "甲与乙是什么？" in changed["previous"]
    assert 'class="en"' not in build_ifab.render_faq(changed)
    assert "甲与乙是什么？" not in list(search_rows(data, zh))[-1][2]


def test_duplicate_block_headings_do_not_claim_the_same_translation():
    data, zh = source_and_translation()
    duplicate = copy.deepcopy(data["sections"][0]["blocks"][0])
    duplicate["items"][0]["t"] = "A different passage."
    data["sections"][0]["blocks"].append(duplicate)
    doc = documents(data, zh)[0]
    assert all(not item["zh"] for b in doc["blocks"] for item in b["items"])
    ids = [item["id"] for b in doc["blocks"] for item in b["items"]]
    assert len(ids) == len(set(ids))
