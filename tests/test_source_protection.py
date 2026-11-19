"""私有审核成果、来源快照和素材的发布边界。"""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_scale
import fetch_conmebol
import fetch_crests_online
import fetch_crests_round2
import fetch_ifab
import fetch_rfef
import fetch_uefa
import gen_quiz_answers
from lib import crest_candidates
from lib.source_snapshot import SnapshotReads, publish


def snapshot_copy(module, attr, path, monkeypatch):
    original = getattr(module, attr).read_bytes()
    path.write_bytes(original)
    monkeypatch.setattr(module, attr, path)
    return original


def test_quiz_default_preserves_approved_and_preview_is_separate(tmp_path, monkeypatch):
    output = tmp_path / "quiz.json"
    original = snapshot_copy(gen_quiz_answers, "OUT", output, monkeypatch)
    before = json.loads(original)["answers"]
    monkeypatch.setattr(gen_quiz_answers, "REVIEW_DIR", tmp_path / "review")
    monkeypatch.setattr(sys, "argv", ["gen_quiz_answers.py"])
    gen_quiz_answers.main()
    after = json.loads(output.read_bytes())["answers"]
    for key, entry in before.items():
        if entry["reviewed"]:
            assert after[key] == entry
    latest = output.read_bytes()
    gen_quiz_answers.main()
    assert output.read_bytes() == latest
    monkeypatch.setattr(sys, "argv", ["gen_quiz_answers.py", "--preview-all"])
    gen_quiz_answers.main()
    assert output.read_bytes() == latest
    draft = json.loads((tmp_path / "review/draft-answers.json").read_bytes())
    assert draft["answers"] and not any(
        a["reviewed"] for a in draft["answers"].values()
    )


@pytest.mark.parametrize("module,attr", [(fetch_uefa, "UEFA"), (fetch_rfef, "RFEF")])
def test_empty_cache_keeps_published_snapshot(module, attr, tmp_path, monkeypatch):
    dest = tmp_path / "snapshot.json"
    original = snapshot_copy(module, attr + "_JSON", dest, monkeypatch)
    monkeypatch.setattr(module, attr + "_CACHE", tmp_path / "missing")
    with pytest.raises(ValueError):
        module.parse_all()
    assert dest.read_bytes() == original


def test_ifab_partial_protocol_preserves_all_sections(tmp_path, monkeypatch):
    output = tmp_path / "ifab.json"
    old = snapshot_copy(fetch_ifab, "IFAB_JSON", output, monkeypatch)
    existing = json.loads(old)
    monkeypatch.setattr(
        fetch_ifab,
        "fetch_page",
        lambda url=None: "" if url else "Video Assistant Referee (VAR) protocol",
    )
    monkeypatch.setattr(fetch_ifab, "parse_sections", lambda _: existing["sections"])
    monkeypatch.setattr(fetch_ifab, "parse_qna", lambda _: existing["faq"])
    with pytest.raises(ValueError, match="配套页"):
        fetch_ifab.parse_all()
    assert output.read_bytes() == old


def test_conmebol_partial_list_keeps_case_archive(tmp_path, monkeypatch):
    dest = tmp_path / "conmebol.json"
    original = snapshot_copy(fetch_conmebol, "CONMEBOL_JSON", dest, monkeypatch)
    item = json.loads(original)["cases"][0]
    monkeypatch.setattr(
        fetch_conmebol,
        "fetch_page",
        lambda url: "index" if url == fetch_conmebol.COLUMN else "",
    )
    monkeypatch.setattr(
        fetch_conmebol, "parse_page", lambda page: ([item], "second", 2)
    )
    monkeypatch.setattr(sys, "argv", ["fetch_conmebol.py", "parse"])
    with pytest.raises(ValueError, match="第 2 页"):
        fetch_conmebol.main()
    assert dest.read_bytes() == original


@pytest.mark.parametrize(
    "module,attr,key",
    [
        (fetch_uefa, "UEFA_JSON", "groups"),
        (fetch_rfef, "RFEF_JSON", "sections"),
        (fetch_ifab, "IFAB_JSON", "extras"),
        (fetch_conmebol, "CONMEBOL_JSON", "cases"),
    ],
)
def test_source_keys_reject_partial_parse_and_cached_date_stays(
    module, attr, key, tmp_path
):
    dest = tmp_path / "snapshot.json"
    old = getattr(module, attr).read_bytes()
    dest.write_bytes(old)
    original = json.loads(old)
    partial = copy.deepcopy(original)
    partial[key].pop()
    with pytest.raises(ValueError, match="缺少"):
        publish(dest, partial, module.identities, checked=True)
    assert dest.read_bytes() == old
    complete = copy.deepcopy(original)
    complete["source_name"] += " test"
    publish(dest, complete, module.identities, checked=False)
    assert json.loads(dest.read_bytes())["fetched"] == original["fetched"]


def test_snapshot_reads_require_every_page_to_be_verified(tmp_path):
    reads = SnapshotReads(refresh=True)
    for key in ("one", "two"):
        assert reads.cached(key, tmp_path / key, 1) is None
    reads.store("one", tmp_path / "one", "body")
    assert not reads.checked
    reads.store("two", tmp_path / "two", "body")
    assert reads.checked


def test_conmebol_published_classification():
    data = json.loads(fetch_conmebol.CONMEBOL_JSON.read_bytes())
    for case in data["cases"]:
        assert case["situacion_norm"] == fetch_conmebol.norm_situation(
            case["situacion_es"]
        )
    assert fetch_conmebol.norm_situation("No Penal") == "no_penalty"
    assert fetch_conmebol.norm_situation("No fuera de juego") == "no_offside"
    assert fetch_conmebol.norm_situation("Invasión en el área penal") == "other"


@pytest.mark.parametrize("module", [fetch_crests_online, fetch_crests_round2])
def test_candidate_collection_never_publishes_unreviewed_crest(
    module, tmp_path, monkeypatch
):
    catalog = tmp_path / "teams.json"
    previous = {
        "teams": {
            "team-023": {
                "slug": "team-023",
                "name": "四川",
                "status": "fallback",
                "path": None,
            }
        }
    }
    catalog.write_text(json.dumps(previous), encoding="utf-8")
    monkeypatch.setattr(module, "TEAMS_JSON", catalog)
    monkeypatch.setattr(crest_candidates, "LOCAL", tmp_path / "local")
    monkeypatch.setattr(
        module,
        "lookup",
        lambda team: ("https://example.com/a.png", "https://example.com/article"),
    )

    def download(url, dest, **kw):
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"x" * 2000)
        return 200, 2000

    monkeypatch.setattr(crest_candidates, "download", download)
    module.main()
    assert json.loads(catalog.read_bytes()) == previous
    (candidate,) = (tmp_path / "local/crest-candidates").glob("*/source.json")
    record = json.loads(candidate.read_bytes())
    assert record["team"] == "四川"
    assert (candidate.parent / record["file"]).exists()


def test_normal_scale_build_ignores_incomplete_package(tmp_path, monkeypatch):
    dest = tmp_path / "scale.json"
    original = snapshot_copy(build_scale, "SCALE_JSON", dest, monkeypatch)
    package = tmp_path / "pack"
    (package / "files/categories").mkdir(parents=True)
    monkeypatch.setattr(build_scale, "PACKAGES", {"2026": package})
    monkeypatch.setattr(build_scale, "SITE", tmp_path / "site")
    build_scale.main(["--from-json"])
    html = (tmp_path / "site/scale.html").read_bytes()
    assert html.count(b'<article class="hcard"') == 104
    assert dest.read_bytes() == original
    with pytest.raises(ValueError):
        build_scale.main(["--extract"])
    assert dest.read_bytes() == original
    assert (tmp_path / "site/scale.html").read_bytes() == html


def test_explicit_scale_extract_validates_media_before_publish(tmp_path, monkeypatch):
    dest = tmp_path / "scale.json"
    package = tmp_path / "pack"
    series = package / "files/categories/fouls-misconduct/highlights"
    series.mkdir(parents=True)
    (series / "A1.html").write_text("<h1>A1 - 手球</h1>", encoding="utf-8")
    monkeypatch.setattr(build_scale, "SCALE_JSON", dest)
    monkeypatch.setattr(build_scale, "PACKAGES", {"2026": package})
    monkeypatch.setattr(build_scale, "SITE", tmp_path / "site")
    monkeypatch.setattr(build_scale, "SCALE_VIDEOS", tmp_path / "videos")
    monkeypatch.setattr(build_scale, "SCALE_POSTERS", tmp_path / "posters")
    with pytest.raises(ValueError, match="原包素材"):
        build_scale.main(["--extract"])
    assert not dest.exists()
    assert not (tmp_path / "videos").exists()
    (series / "A1.mp4").write_bytes(b"video")
    (series / "A1.png").write_bytes(b"poster")
    build_scale.main(["--extract"])
    assert len(build_scale.scene_keys(json.loads(dest.read_bytes())["2026"])) == 1
    assert (tmp_path / "videos/2026/highlights-A1.mp4").read_bytes() == b"video"
    assert (tmp_path / "site/scale.html").exists()
