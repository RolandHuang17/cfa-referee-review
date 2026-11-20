"""官方媒体、本地档案与现有离线文件名应保持一一对应。"""

import json
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_rfef
import download_rfef_videos
import fetch_rfef
from lib.rfef_media import assign_local_file, destination, media_url

BASE = "https://www.card.rfef.es/wp-content/uploads/"
FILE = "videos/rfef/MD.1.1.mp4"


class Videos(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag == "video":
            self.items.append(dict(attrs))


def test_existing_manifest_and_all_rendered_local_files_agree(tmp_path, monkeypatch):
    monkeypatch.setattr(build_rfef, "SITE", tmp_path)
    monkeypatch.setattr(download_rfef_videos, "VID_DIR", tmp_path / "videos" / "rfef")
    build_rfef.main()
    videos = Videos()
    videos.feed((tmp_path / "rfef.html").read_text(encoding="utf8"))
    downloads = download_rfef_videos.load_videos()
    assert {(v["src"], v["data-rfef-url"]) for v in videos.items} == {
        (v["file"], v["url"]) for v in downloads
    }
    assert len(downloads) == len(videos.items) > 0
    for v in downloads:
        assert v["destination"] == tmp_path / Path(v["file"])
    assert all("onerror" not in v for v in videos.items)


def test_official_monthly_and_manual_media_paths_and_encoded_attributes():
    md = BASE + "manual-videos/MD.1.1.mp4"
    dated = BASE + "2026/08/Review-2.MP4"
    assert fetch_rfef._norm_url(md.replace("https:", "http:")) == md
    assert media_url(dated.replace(".es/", ".es:443/")) == dated
    assert media_url(md.replace("www.card.rfef.es", "example.org")) == ""
    assert media_url(BASE + "2026/15/Review.mp4") == ""
    assert media_url(BASE + "manual-videos/Fixture.pdf") == ""
    url = md + "?season=2026&edition=summer"
    videos = Videos()
    videos.feed(build_rfef.video_markup({"file": FILE, "url": url}))
    assert videos.items[0]["data-rfef-url"] == url
    assert "onerror" not in videos.items[0]
    # An older local-only copy can play even when the remote source is unknown.
    assert 'data-rfef-url=""' in build_rfef.video_markup(
        {"file": FILE, "url": "https://example.org/Review.mp4"}
    )
    assert "<video" not in build_rfef.video_markup(
        {"file": "other/MD.1.1.mp4", "url": md}
    )
    assert 'href="' + md + '"' in build_rfef.video_markup(
        {"file": "other/MD.1.1.mp4", "url": md}
    )


def test_download_manifest_validates_all_source_file_pairs_before_work(
    tmp_path, monkeypatch
):
    manifest = tmp_path / "media.json"
    monkeypatch.setattr(download_rfef_videos, "RFEF_JSON", manifest)
    monkeypatch.setattr(download_rfef_videos, "VID_DIR", tmp_path / "video")
    md = BASE + "manual-videos/MD.1.1.mp4"
    for bad in (
        {"url": "https://example.org/Review.mp4", "file": FILE},
        {"url": md, "file": "videos/rfef/other/Review.mp4"},
        {"url": md, "file": "videos/rfef/Another.mp4"},
        {"url": BASE + "2026/08/MD.1.1.mp4", "file": FILE},
    ):
        manifest.write_text(
            json.dumps(
                {
                    "sections": [
                        {
                            "groups": [
                                {
                                    "items": [
                                        {
                                            "id": "MD.1",
                                            "videos": [{"url": md, "file": FILE}, bad],
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ),
            encoding="utf8",
        )
        with pytest.raises(ValueError, match="RFEF"):
            download_rfef_videos.load_videos()
    assert not (tmp_path / "video").exists()
    for relative in (
        r"videos/rfef/archive\Review.mp4",
        "Review.mp4",
        "videos/rfef/Review.pdf",
    ):
        with pytest.raises(ValueError, match="MP4"):
            destination(tmp_path, relative)


def test_linked_media_and_partial_files_are_not_download_targets(tmp_path):
    root = tmp_path / "video"
    root.mkdir()
    external = tmp_path / "existing.mp4"
    external.write_bytes(b"local fixture")
    for name in ("MD.1.1.mp4", "MD.1.1.mp4.part"):
        link = root / name
        try:
            link.symlink_to(external)
        except OSError:
            pytest.skip("local account cannot create symbolic links")
        with pytest.raises(ValueError, match="RFEF"):
            destination(root, FILE)
        link.unlink()
    assert external.read_bytes() == b"local fixture"


def test_older_local_names_survive_a_same_named_clip_in_another_section():
    dated = BASE + "2026/08/MD.1.1.mp4"
    manual = BASE + "manual-videos/MD.1.1.mp4"
    used = {FILE.lower(): manual}
    assert assign_local_file(dated, used) == "videos/rfef/2026-08-MD.1.1.mp4"
    assert assign_local_file(manual, used) == FILE
    assert assign_local_file(dated, used) == "videos/rfef/2026-08-MD.1.1.mp4"


@pytest.mark.parametrize("suffix", [".mp4", ".mp4.part"])
def test_reparse_target_check_also_covers_the_partial_file(
    tmp_path, monkeypatch, suffix
):
    original = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: path.name == "MD.1.1" + suffix or original(path),
    )
    with pytest.raises(ValueError, match="RFEF"):
        destination(tmp_path, FILE)
