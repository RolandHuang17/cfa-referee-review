"""在独立临时目录打 ZIP，覆盖轻量发行清单与失败时的旧包保护。"""

import os
import sys
import zipfile
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import package_site
from lib.pages import PAGE_FILES


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    site = tmp_path / "站点"
    dist = tmp_path / "压缩包"
    monkeypatch.setattr(package_site, "SITE", site)
    monkeypatch.setattr(package_site, "DIST", dist)
    monkeypatch.setattr(sys, "argv", ["package_site.py", "2026.11-rc1"])
    for name in package_site.release_members():
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"发行文件 {name}", encoding="utf-8")
    return site, dist / "cfa-referee-site-2026.11-rc1.zip"


def test_zip_keeps_all_entries_and_registered_assets_only(bundle):
    site, out = bundle
    examples = {
        "editor-notes.txt",
        "未完成页面.html",
        ".local/settings.json",
        "assets/review-notes.txt",
        "assets/crests/spare.png",
        "assets/rules/p99999.png",
        "assets/compare/preview.webp",
        "assets/portal/moments/example.js",
        "assets/scale/poster.png",
        "videos/2026/example.mp4",
    }
    for name in examples:
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"local fixture")

    package_site.main()
    with zipfile.ZipFile(out) as archive:
        names = archive.namelist()
        assert sorted(set(names)) == names
        assert examples.isdisjoint(names)
        assert {name for name in names if name.endswith(".html")} == set(PAGE_FILES)
        assert {
            "NOTICE.md",
            "manifest.webmanifest",
            "sw.js",
            "icon.svg",
            "robots.txt",
            "sitemap.xml",
            "feed.xml",
            "assets/og-card.png",
            "assets/crests/beijing-guoan.png",
            "assets/rules/p29.png",
            "assets/rules/p215.png",
            "assets/compare/handball-28-small.webp",
            "assets/portal/referee-match.webp",
            "assets/portal/moments/moments.js",
            "assets/portal/moments/liquid-hover/moment.css",
        } <= set(names)
        for name in names:
            assert archive.read(name) == (site / name).read_bytes()


def test_no_version_uses_date(bundle, monkeypatch):
    _, out = bundle
    monkeypatch.setattr(sys, "argv", ["package_site.py"])
    package_site.main()
    expected = out.with_name(f"cfa-referee-site-{date.today():%Y.%m.%d}.zip")
    assert zipfile.is_zipfile(expected)


def test_identical_files_produce_identical_archive_after_rebuild(bundle):
    site, out = bundle
    package_site.main()
    original = out.read_bytes()
    page = site / "index.html"
    os.utime(page, (1_600_000_000, 1_600_000_000))
    package_site.main()
    assert original == out.read_bytes()
    # A changed page must still change the archive and remain byte-exact.
    page.write_bytes(b"first line\r\nsecond line\n")
    package_site.main()
    assert original != out.read_bytes()
    with zipfile.ZipFile(out) as archive:
        assert archive.read("index.html") == page.read_bytes()


@pytest.mark.parametrize("version", ["", "test/preview", "test\\preview"])
def test_version_is_one_filename_component(bundle, monkeypatch, version):
    _, out = bundle
    monkeypatch.setattr(sys, "argv", ["package_site.py", version])
    with pytest.raises(SystemExit, match="版本"):
        package_site.main()
    assert not out.parent.exists()


def test_incomplete_site_preserves_previous_release(bundle):
    site, out = bundle
    package_site.main()
    original = out.read_bytes()
    (site / "assets/rules/p29.png").unlink()
    with pytest.raises(SystemExit, match="assets/rules/p29.png"):
        package_site.main()
    assert out.read_bytes() == original


def test_oversize_package_preserves_previous_release(bundle, monkeypatch):
    _, out = bundle
    package_site.main()
    original = out.read_bytes()
    monkeypatch.setattr(package_site, "SIZE_LIMIT", 1)
    with pytest.raises(SystemExit, match="60MB"):
        package_site.main()
    assert out.read_bytes() == original
    assert list(out.parent.iterdir()) == [out]


def test_linked_public_filename_is_rejected(bundle, tmp_path):
    site, out = bundle
    elsewhere = tmp_path / "sample-note.txt"
    elsewhere.write_text("example note", encoding="utf-8")
    notice = site / "NOTICE.md"
    notice.unlink()
    try:
        notice.symlink_to(elsewhere)
    except OSError as error:
        pytest.skip(f"当前文件系统不支持创建此测试链接：{error}")
    with pytest.raises(SystemExit, match="NOTICE.md"):
        package_site.main()
    assert not out.exists()
