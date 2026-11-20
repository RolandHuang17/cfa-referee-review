"""RAP 维护入口应识别期号别名，保护人工索引并保留核查依据。"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_rap
import fetch_rap


@pytest.mark.parametrize(
    "text,key",
    [
        ("Download RAP 2024:1", "2024-1"),
        ("Refereeing Assistance Programme 2024 – 1", "2024-1"),
        ("RAP Euro 2024", "EURO-2024"),
        ("RAP Women’s Euro 2017", "WEURO-2017"),
        ("WEURO-2017", "WEURO-2017"),
        ("RAP 2016 (edition 2)", "2016-2"),
    ],
)
def test_edition_key(text, key):
    assert fetch_rap.edition_key(text) == key


def test_cached_index_refresh_and_failed_parse(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_rap, "DUTCHREF_CACHE", tmp_path)
    monkeypatch.setattr(fetch_rap, "MIN_BODY", 20)
    old = '<a href="https://bit.ly/old">Download RAP 2024:1</a>'
    new = '<a href="https://nextaur.com/uefa/">Nextaur RAP 2026-2</a>'
    cache = tmp_path / "rap-index.html"
    cache.write_text(old, encoding="utf-8")
    monkeypatch.setattr(fetch_rap, "fetch_text", lambda *a, **k: (200, new))
    assert set(fetch_rap.read_index(offline=False)) == {"2026-2"}
    updated = cache.read_bytes()
    assert updated.decode() == new
    monkeypatch.setattr(fetch_rap, "fetch_text", lambda *a, **k: (200, " " * 100))
    with pytest.raises(SystemExit):
        fetch_rap.read_index(offline=False)
    assert cache.read_bytes() == updated
    assert set(fetch_rap.read_index(offline=True)) == {"2026-2"}


def test_merge_keeps_reviewed_editions_and_separates_uncertain_links(
    tmp_path, monkeypatch
):
    source = tmp_path / "rap.json"
    original = fetch_rap.RAP_JSON.read_bytes()
    source.write_bytes(original)
    monkeypatch.setattr(fetch_rap, "RAP_JSON", source)
    monkeypatch.setattr(fetch_rap, "DUTCHREF_CACHE", tmp_path / "cache")
    old_html = """
        <h2>Refereeing Assistance Programme 2024:1</h2>
        <a href="https://bit.ly/first">Download RAP 2024-1 for PC</a>
        <a href="https://bit.ly/mac">Download RAP 2024:1 for MAC</a>
        <h2>RAP Euro 2024</h2><a href="https://bit.ly/euro">Download</a>
        <h2>RAP Women's Euro 2017</h2><a href="https://bit.ly/weuro">Download</a>
    """
    fetch_rap.merge(fetch_rap.discover(old_html))
    assert source.read_bytes() == original
    found = fetch_rap.discover(
        "<article>"
        + old_html
        + """
        <h2>RAP 2026-2</h2>
        <a href="https://nextaur.com/uefa/">Open Nextaur</a>
        <a href="https://nextaur.com/uefa/">Open Nextaur</a>
        <h2>RAP 2027-1</h2>
        <a href="https://nextaur.com/uefa/">Open Nextaur</a>
        <h2>RAP 2027-2</h2><a href="https://bit.ly/unchecked">Download</a>
        </article>
        <div id="comments"><a href="https://bit.ly/comment">Download RAP 2028-1</a></div>
        """
    )
    assert "2028-1" not in found
    fetch_rap.merge(found)
    new_bytes = source.read_bytes()
    data = json.loads(new_bytes)
    assert data["editions"][2:] == json.loads(original)["editions"]
    assert data["checked"] == json.loads(original)["checked"]
    first, second = data["editions"][:2]
    assert {first["id"], second["id"]} == {"2026-2", "2027-1"}
    for record in (first, second):
        assert record["status"] == "unreviewed" and record["era"] == "nextaur"
        assert len(record["links"]) == 1
    pending = tmp_path / "cache" / "pending-editions.json"
    pending_bytes = pending.read_bytes()
    assert list(json.loads(pending_bytes)) == ["2027-2"]
    fetch_rap.merge(found)
    assert source.read_bytes() == new_bytes
    assert pending.read_bytes() == pending_bytes
    monkeypatch.setattr(build_rap, "SITE", tmp_path / "site")
    build_rap.build_page(data)
    page = (build_rap.SITE / "rap.html").read_text(encoding="utf-8")
    assert page.count('class="ed-status badge pending">待人工核对') == 2
    assert "2027-2" not in page
