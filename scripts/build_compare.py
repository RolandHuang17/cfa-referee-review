# -*- coding: utf-8 -*-
"""Build the offline comparison classroom with local case data and observation clips."""

import base64
import struct

from build_portal import inline_asset, js_value
from lib.compare import load_compare
from lib.paths import ASSETS, SITE, SRC
from lib.seo import meta_tags
from lib.theme import inject_theme, topbar


def pack_case_index(cases):
    """Fixed-width LZW over UTF-8. One self-contained file, including offline browsers."""
    raw = js_value(cases).encode("utf-8")
    alphabet = tuple(bytes([i]) for i in range(256))
    dictionary = {symbol: i for i, symbol in enumerate(alphabet)}
    codes = []
    phrase = b""
    for byte in raw:
        symbol = alphabet[byte]
        extended = phrase + symbol
        if extended in dictionary:
            phrase = extended
            continue
        codes.append(dictionary[phrase])
        if len(dictionary) < 65536:
            dictionary[extended] = len(dictionary)
        phrase = symbol
    if phrase:
        codes.append(dictionary[phrase])
    packed = struct.pack(f">{len(codes)}H", *codes)
    return {"bytes": len(raw), "codes": base64.b64encode(packed).decode("ascii")}


def page_payload():
    data = load_compare()
    # The classroom needs facts, sources and media. Full case details stay one link away.
    fields = (
        "season",
        "seq",
        "issue",
        "no",
        "category",
        "home",
        "away",
        "comp",
        "desc",
        "conclusion",
        "source",
        "source_date",
        "video_files",
        "video_urls",
    )
    source = data.pop("cases")
    data["rulesByCategory"] = {
        case["category"]: case["rules"] for case in source.values()
    }
    data["caseCount"] = len(source)
    cases = {
        key: {
            **{name: case[name] for name in fields},
            **({"supplement": case["supplement"]} if case.get("supplement") else {}),
        }
        for key, case in source.items()
    }
    data["caseIndex"] = pack_case_index(cases)
    return data


def compare_image(name):
    image = (ASSETS / "compare" / name).read_bytes()
    return "data:image/webp;base64," + base64.b64encode(image).decode("ascii")


def main():
    data = page_payload()
    template = (SRC / "compare.html").read_text(encoding="utf-8")
    script = "\n".join(
        (SRC / file).read_text(encoding="utf-8")
        for file in (
            "learning-records.js",
            "compare-records.js",
            "coach-handout.js",
            "coach-model.js",
            "coach.js",
            "compare.js",
        )
    )
    content = {
        "__TOPBAR__": topbar(active="compare.html", portal=True),
        "__CSS__": "\n".join(
            (SRC / name).read_text(encoding="utf-8")
            for name in ("compare.css", "coach.css")
        ),
        "__SCRIPTS__": script,
        "__DATA__": js_value(data),
        "__PORTAL_EFFECT__": (SRC / "portal-liquid.js").read_text(encoding="utf-8"),
        "__LIQUID_MODULE__": inline_asset(
            "moments/liquid-hover/moment.js", "text/javascript"
        ),
        "__MOTION_HELPERS__": inline_asset("moments/lib.js", "text/javascript"),
        "__REF_PHOTO__": compare_image("referee-large.webp"),
        "__REF_MOBILE_PHOTO__": compare_image("referee-mobile.webp"),
    }
    for letter, case in (("A", 1), ("B", 28)):
        for token, suffix in (("PHOTO", ""), ("SMALL", "-small")):
            content[f"__COMPARE_{letter}_{token}__"] = compare_image(
                f"handball-{case}{suffix}.webp"
            )
    for key, value in content.items():
        template = template.replace(key, value)
    out = SITE / "compare.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        inject_theme(template, meta=meta_tags("compare.html")), encoding="utf-8"
    )
    print(
        f"生成 {out.name}（{len(data['lessons'])} 课，{data['caseCount']} 个自由配对判例）"
    )


if __name__ == "__main__":
    main()
