"""Verify the shipped, standalone classroom against its editorial and seasonal sources."""

import base64
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from lib.compare import load_compare
from lib.paths import SITE
from lib.theme import inject_theme


def test_theme_script_is_appended_to_the_outer_document():
    export = '<script>const page = "<html><body>讲义</body></html>";</script>'
    html = inject_theme(f"<html><head></head><body>{export}</body></html>")
    assert export in html
    assert html.index(export) < html.index("navigator.serviceWorker.register")


def test_shipped_case_index_round_trips_all_records():
    html = (SITE / "compare.html").read_text(encoding="utf-8")
    raw = re.search(
        r'<script id="compare-data" type="application/json">(.*?)</script>', html, re.S
    )
    payload = json.loads(raw.group(1))
    index = payload["caseIndex"]
    dictionary = [bytes([i]) for i in range(256)]
    previous = b""
    decoded = bytearray()
    for (code,) in struct.iter_unpack(
        ">H", base64.b64decode(index["codes"], validate=True)
    ):
        phrase = (
            previous + previous[:1] if code == len(dictionary) else dictionary[code]
        )
        decoded.extend(phrase)
        if previous and len(dictionary) < 65536:
            dictionary.append(previous + phrase[:1])
        previous = phrase
    assert len(decoded) == index["bytes"]
    cases = json.loads(decoded)
    source = load_compare()
    assert cases.keys() == source["cases"].keys()
    assert len(cases) == payload["caseCount"]
    assert payload["lessons"] == source["lessons"]
    for key, row in cases.items():
        official = source["cases"][key]
        assert row == {field: official[field] for field in row}
        assert row["conclusion"] == official["conclusion"]
        assert row.get("supplement") == official.get("supplement")
        assert payload["rulesByCategory"][row["category"]] == official["rules"]
