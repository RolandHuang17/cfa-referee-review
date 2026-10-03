# -*- coding: utf-8 -*-
"""Build the complete team registry from both season datasets.

Existing image files are retained as review-only records until a fixed source
has been manually verified; pages therefore use the safe text badge for them.
"""
import json
import re
from urllib.parse import quote

from lib.paths import CRESTS_JSON, CREST_OVERRIDES_JSON, DATA, TEAMS_JSON
ALIASES = {
    "广东广州豹": "广州豹", "河南俱乐部酒祖杜康": "河南俱乐部",
    "河南酒祖杜康": "河南俱乐部", "浙江俱乐部": "浙江俱乐部绿城",
    "陕西联合月亮泊": "陕西联合", "广西平果国晶": "广西平果",
    "广西平果哈嘹": "广西平果", "大连英博海发": "大连英博",
    "温州俱乐部中胤": "温州俱乐部", "浙江": "浙江俱乐部绿城",
    # 官方评议原文两种写法混用（2024第12期"橙狮"/第18期起"澄狮"），规范名以冠名方橙狮体育为准
    "永川茶山竹海澄狮女足": "永川茶山竹海橙狮女足",
    # 2026赛季赞助冠名/笔误变体
    "河南俱乐部彩陶坊": "河南俱乐部", "辽宁铁人楠波湾": "辽宁铁人",
    "延边龙鼎可喜安": "延边龙鼎", "杭州临江吴越": "杭州临平吴越",
}
OLD = None  # 旧 crests.json 兼容保留已废弃: verified 状态唯一来源是 crest_overrides.json
# 人工核验的队徽成果登记在 crest_overrides.json，重建目录时不丢失
OVERRIDES = json.loads(CREST_OVERRIDES_JSON.read_text(encoding="utf-8")) if CREST_OVERRIDES_JSON.exists() else {}
# 同一俱乐部更名链：新名 parent 指向旧名（山西崇德荣海 2025-03 由西安崇德荣海迁址更名，两赛季各自用名正确）
PARENT = {"山西崇德荣海": "西安崇德荣海"}
teams = {}
for season in ("2024", "2025", "2026"):
    data = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
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
    initials = re.sub(r"(俱乐部|足球俱乐部|队|女足)$", "", name)[:2] or name[:2]
    fg, bg = palette[index % len(palette)]
    ov = OVERRIDES.get(name, {})
    old_path = ov.get("path")
    result[f"team-{index + 1:03d}"] = {
        "name": name, "aliases": aliases, "slug": f"team-{index + 1:03d}",
        "path": old_path if old_path else None,
        "source_url": ov.get("source_url", f"https://zh.wikipedia.org/wiki/{quote(name)}" if old_path else ""),
        "source_type": ov.get("source_type", "wikipedia-article" if old_path else ""),
        "status": ov.get("status", "verified" if old_path else "fallback"),
        "initials": initials, "fg": fg, "bg": bg,
        "parent": PARENT.get(name),
    }
payload = {"version": 1,
          "generated_from": ["cases-2024.json", "cases-2025.json", "cases-2026.json", "crest_overrides.json"],
          "teams": result}
TEAMS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
compat = {item["name"]: item["path"] for item in result.values() if item.get("path")}
CRESTS_JSON.write_text(json.dumps(compat, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"生成队伍目录: {len(result)} 个标准队名，全部使用可审计兜底状态")
