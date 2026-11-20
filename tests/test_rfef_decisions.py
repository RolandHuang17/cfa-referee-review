"""西班牙判例的判罚决定与纪律处分应在默认中文视图完整呈现。"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_rfef
import fetch_rfef


def test_indirect_free_kick_with_caution(tmp_path, monkeypatch):
    original = "Tiro libre indirecto y tarjeta amarilla"
    assert fetch_rfef.norm_decision(original) == "ifk_yellow"
    assert fetch_rfef.norm_decision("Tiro libre indirecto") == "ifk"
    data = json.loads(build_rfef.RFEF_JSON.read_text(encoding="utf-8"))
    items = {
        item["id"]: item
        for section in data["sections"]
        for group in section["groups"]
        for item in group["items"]
    }
    monkeypatch.setattr(build_rfef, "SITE", tmp_path)
    build_rfef.main()
    page = (tmp_path / "rfef.html").read_text(encoding="utf-8")
    for key in ("CAEF.3", "PD.6"):
        assert items[key]["decision_es"] == original
        assert items[key]["decision_norm"] == "ifk_yellow"
        card = page.split(f'id="r-{key}"', 1)[1].split("</article>", 1)[0]
        assert '>间接任意球+黄牌<span class="es"' in card
        assert original in card
