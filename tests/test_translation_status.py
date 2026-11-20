"""从实际 CLI 核对当前配对范围、所有缺口及单项维护输出。"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "scripts/translation_status.py"


def cli(root, *args, check=True):
    return subprocess.run(
        [sys.executable, "-X", "utf8", SCRIPT, *args],
        cwd=root,
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=check,
    )


def read(root, name):
    return json.loads((root / "data" / name).read_text(encoding="utf-8"))


def write(root, name, data):
    (root / "data" / name).write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )


@pytest.fixture
def sample(tmp_path):
    (tmp_path / "scripts/lib").mkdir(parents=True)
    (tmp_path / "data").mkdir()
    shutil.copy2(ROOT / SCRIPT, tmp_path / SCRIPT)
    (tmp_path / "src").mkdir()
    shutil.copy2(ROOT / "src/theme.css", tmp_path / "src/theme.css")
    for name in (
        "paths",
        "ifab_content",
        "uefa_content",
        "translation_versions",
        "conmebol_evidence",
        "pagelib",
        "theme",
    ):
        rel = f"scripts/lib/{name}.py"
        shutil.copy2(ROOT / rel, tmp_path / rel)
    for layer in ("uefa", "ifab", "weekly", "hns", "conmebol", "rfef"):
        for suffix in (".json", "-zh.json"):
            rel = "data/" + layer + suffix
            shutil.copy2(ROOT / rel, tmp_path / rel)
    return tmp_path


def counts(text):
    return {
        (layer, label.strip()): (int(done), int(total))
        for layer, label, done, total in re.findall(
            r"^([a-z]+-zh)\s+(.+?)\s+(\d+)/\s*(\d+)\s+", text, re.MULTILINE
        )
    }


def test_real_cli_covers_published_translations_and_protected_sections():
    text = cli(ROOT, "-v").stdout
    rows = counts(text)
    assert rows and all(
        done == total
        for (layer, _), (done, total) in rows.items()
        if layer != "conmebol-zh"
    )
    con = read(ROOT, "conmebol.json")["cases"]
    total = sum(bool(e["situacion_es"]) for c in con for e in c["events"])
    pending = read(ROOT, "conmebol-zh.json")["untranslated"]
    assert rows["conmebol-zh", "情境描述"] == (total - len(pending), total)
    assert all(anchor in text and label in text for anchor, label in pending.items())
    groups = read(ROOT, "uefa.json")["groups"]
    assert rows["uefa-zh", "判例标题"][0] == sum(len(g["items"]) for g in groups)
    assert rows["uefa-zh", "准则块"][0] == sum(len(g["criteria"]) for g in groups)
    assert rows["uefa-zh", "组名"][0] == rows["uefa-zh", "组导语"][0] == len(groups)
    doc = read(ROOT, "ifab.json")
    for field, scope in (("sections", "主协议"), ("extras", "配套")):
        blocks = [b for section in doc[field] for b in section["blocks"]]
        assert rows["ifab-zh", scope + "标题"][0] == len(doc[field])
        assert rows["ifab-zh", scope + "条款"][0] == sum(
            len(b["items"]) for b in blocks
        )
        assert rows["ifab-zh", scope + "小节标题"][0] == sum(
            bool(b["h"]) for b in blocks
        )
    assert rows["ifab-zh", "主协议 FAQ"][0] == len(doc["faq"])
    assert rows["ifab-zh", "配套 FAQ"][0] == sum(
        len(s.get("faq", [])) for s in doc["extras"]
    )
    assert {layer for layer, _ in rows} == {
        "uefa-zh",
        "ifab-zh",
        "weekly-zh",
        "rfef-zh",
        "conmebol-zh",
        "hns-zh",
    }


def test_unmodified_chinese_is_pending_after_official_edits(sample):
    uefa = read(sample, "uefa.json")
    g = next(g for g in uefa["groups"] if g["criteria"])
    g["intro"] += " Updated."
    g["name_en"] += " (updated)"
    g["criteria"][0]["items"][0] += " Updated."
    g["items"][0]["title"] += " Updated."
    write(sample, "uefa.json", uefa)
    ifab = read(sample, "ifab.json")
    doc = next(d for d in ifab["extras"] if d.get("faq"))
    doc["h"] += " (updated)"
    block = doc["blocks"][0]
    block["items"][0]["t"] += " Updated."
    doc["faq"][0]["a"] += " Updated."
    write(sample, "ifab.json", ifab)
    result = cli(sample, "-v").stdout
    keys = [
        g["key"] + "/intro",
        g["key"] + "/name_en",
        g["key"] + "/criteria/1",
        "items/" + g["items"][0]["id"],
        doc["id"] + "/title",
        doc["id"] + "/faq/" + doc["faq"][0]["id"],
    ]
    for key in keys:
        assert "待复核  " + key in result
    slot = f"{doc['id']}/block/{block['h'] or '_head'}"
    for n in range(1, len(block["items"]) + 1):
        assert f"待复核  {slot} · 第{n}条\n" in result
    assert "全部译文层覆盖完整" not in result
    quiet = cli(sample).stdout
    assert "有缺口" in quiet and "待复核  " not in quiet


def test_verbose_prints_every_missing_key_in_source_order_and_full_urls(sample):
    weekly = read(sample, "weekly.json")
    zh = read(sample, "weekly-zh.json")
    keys = [e["id"] for e in weekly["episodes"][:8]]
    for key in keys:
        del zh["items"][key]
    write(sample, "weekly-zh.json", zh)
    # 真实南美待译与本次人为制造的八个周更缺口应全部逐项显示。
    pending = read(sample, "conmebol-zh.json")["untranslated"]
    text = cli(sample, "-v").stdout
    assert text == cli(sample, "-v").stdout
    lines = [line.strip() for line in text.splitlines() if line.startswith("    缺译")]
    assert lines[-len(keys) :] == ["缺译  " + key for key in keys]
    con_lines = lines[: -len(keys)]
    assert len(con_lines) == len(pending)
    assert all(
        any(anchor in line and label in line for line in con_lines)
        for anchor, label in pending.items()
    )
    n = len(weekly["episodes"])
    assert counts(text)["weekly-zh", "期目译注"] == (n - len(keys), n)


def test_version_lookup_uses_one_official_unit_and_leaves_files_untouched(sample):
    before = {p: p.read_bytes() for p in (sample / "data").iterdir()}
    official = read(sample, "uefa.json")
    g = next(g for g in official["groups"] if g["criteria"])
    key = g["key"] + "/criteria/1"
    result = cli(sample, "--source-version", "uefa", key).stdout
    pin = read(sample, "uefa-zh.json")["source_versions"]["groups"][g["key"]][
        "criteria"
    ][0]
    assert g["criteria"][0]["items"][0] in result and pin in result
    key = "s1/title"
    result = cli(sample, "--source-version", "ifab", key).stdout
    assert read(sample, "ifab-zh.json")["source_versions"][key] in result
    missing = cli(sample, "--source-version", "ifab", "missing/title", check=False)
    assert missing.returncode == 2 and "匹配 0 条" in missing.stderr
    assert all(path.read_bytes() == data for path, data in before.items())


def test_ambiguous_key_cannot_supply_a_review_fingerprint(sample):
    ifab = read(sample, "ifab.json")
    question = ifab["faq"][0]
    ifab["faq"].append({**question, "a": "Another official answer."})
    write(sample, "ifab.json", ifab)
    key = "faq/" + question["id"]
    result = cli(sample, "--source-version", "ifab", key, check=False)
    assert result.returncode == 2 and "匹配 2 条" in result.stderr
    assert "当前原文指纹" not in result.stdout
    assert cli(sample, "-v").stdout.count("待复核  " + key + "\n") == 2
