"""The same published files produce the same offline version on every build host."""

import json
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_pwa


def test_cache_version_uses_published_pages_and_registered_assets(
    tmp_path, monkeypatch
):
    site = tmp_path / "site"
    site.mkdir()
    monkeypatch.setattr(build_pwa, "SITE", site)
    scale = tmp_path / "scale.json"
    poster = "assets/scale/讲义图.png"
    scale.write_text(
        json.dumps(
            {"2025": {"sections": [{"groups": [{"items": [{"poster": poster}]}]}]}}
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(build_pwa, "SCALE_JSON", scale)
    for name in build_pwa.PAGE_FILES:
        (site / name).write_bytes((name + "\r\n测试页面\r\n").encode("utf-8"))
    build_pwa.main()
    initial = (site / "sw.js").read_bytes()
    assert quote(poster).encode("ascii") in initial
    assert b"assets/og-card.png" in initial

    for name in build_pwa.PAGE_FILES:
        path = site / name
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    (site / "classroom-draft.html").write_text("sample", encoding="utf-8")
    extra = tmp_path / "assets" / "portal" / "classroom-draft.png"
    extra.parent.mkdir(parents=True)
    extra.write_bytes(b"local PNG fixture")
    build_pwa.main()
    assert (site / "sw.js").read_bytes() == initial
    assert b"classroom-draft" not in initial

    (site / "quiz.html").write_text("updated quiz", encoding="utf-8")
    build_pwa.main()
    assert (site / "sw.js").read_bytes() != initial
