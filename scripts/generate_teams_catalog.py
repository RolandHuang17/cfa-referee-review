# -*- coding: utf-8 -*-
"""Build the complete team registry from both season datasets.

Existing image files are retained as review-only records until a fixed source
has been manually verified; pages therefore use the safe text badge for them.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALIASES = {
    "广东广州豹": "广州豹", "河南俱乐部酒祖杜康": "河南俱乐部",
    "河南酒祖杜康": "河南俱乐部", "浙江俱乐部": "浙江俱乐部绿城",
    "陕西联合月亮泊": "陕西联合", "广西平果国晶": "广西平果",
    "广西平果哈嘹": "广西平果", "大连英博海发": "大连英博",
    "温州俱乐部中胤": "温州俱乐部", "浙江": "浙江俱乐部绿城",
}
OLD = json.loads((ROOT / "data" / "crests.json").read_text(encoding="utf-8"))
teams = {}
for season in ("2024", "2025"):
    data = json.loads((ROOT / "data" / f"cases-{season}.json").read_text(encoding="utf-8"))
    for case in data["cases"]:
        for raw in (case.get("home"), case.get("away")):
            if not raw:
                continue
            name = ALIASES.get(raw, raw)
            teams.setdefault(name, {"aliases": []})["aliases"].append(raw)

palette = [("#0b4c8c", "#e9f2fb"), ("#9c2f2f", "#fbe9e7"),
           ("#176b4d", "#e7f5ee"), ("#7b4b9a", "#f3eafa"),
           ("#a56816", "#fff3dc"), ("#315b86", "#e8f0f8")]
result = {}
for index, name in enumerate(sorted(teams)):
    aliases = sorted(set(teams[name]["aliases"]) - {name})
    old_path = OLD.get(name)
    initials = re.sub(r"(俱乐部|足球俱乐部|队|女足)$", "", name)[:2] or name[:2]
    fg, bg = palette[index % len(palette)]
    result[f"team-{index + 1:03d}"] = {
        "name": name, "aliases": aliases, "slug": f"team-{index + 1:03d}",
        "path": old_path if old_path else None,
        "source_url": "", "source_type": "", "status": "fallback",
        "initials": initials, "fg": fg, "bg": bg,
        "parent": None,
    }
payload = {"version": 1, "generated_from": ["cases-2024.json", "cases-2025.json"],
          "teams": result}
(ROOT / "data" / "teams.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
compat = {item["name"]: item["path"] for item in result.values() if item.get("path")}
(ROOT / "data" / "crests.json").write_text(json.dumps(compat, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"生成队伍目录: {len(result)} 个标准队名，全部使用可审计兜底状态")
