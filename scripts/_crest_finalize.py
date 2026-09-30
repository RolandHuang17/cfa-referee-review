# -*- coding: utf-8 -*-
"""队徽收口(终版):回退本次自动转正但语境错配的队伍——
广州豹(采到的是广州富力R&F旧徽,广州豹为2024年新俱乐部)、
新疆/云南(判例中为全运会省队,采到的是天山雪豹/云南飞虎俱乐部徽)、
沧州雄狮(采到的是更名前石家庄永昌Ever Bright旧徽)。
仅保留河北(红金龙CFFC为该俱乐部正确队徽)。随后重播种 overrides 并重建目录。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
teams_p = ROOT / "data" / "teams.json"
ov_p = ROOT / "data" / "crest_overrides.json"
REVERT = ("广州豹", "新疆", "云南", "沧州雄狮")

payload = json.loads(teams_p.read_text(encoding="utf-8"))
for item in payload["teams"].values():
    if item["name"] in REVERT and item["status"] == "verified":
        if item.get("path"):
            (ROOT / item["path"]).unlink(missing_ok=True)
        item.update({"path": None, "source_url": "", "source_type": "", "status": "fallback"})
teams_p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

ov = {}
for item in payload["teams"].values():
    if item["status"] == "verified":
        ov[item["name"]] = {k: item[k] for k in ("path", "source_url", "source_type", "status")}
ov_p.write_text(json.dumps(ov, ensure_ascii=False, indent=1), encoding="utf-8")
print("回退:", len(REVERT), "overrides 重播种:", len(ov))
