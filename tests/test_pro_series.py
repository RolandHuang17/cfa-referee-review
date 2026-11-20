"""PRO 西语节目的官网分类和节目语言是两个维度。"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_pro
import build_search
import fetch_pro
from lib.pagelib import article_anchor
from lib.pro_series import series_name


def test_pro_search_and_index_match_article_series(tmp_path, monkeypatch):
    data = json.loads(build_pro.PRO_JSON.read_text(encoding="utf-8"))
    docs = {d[3]: d[2] for d in build_search.build_docs() if d[1] == "PRO"}
    spanish = [a for a in data["articles"] if a["kind"] == "vaf"]
    assert spanish
    for article in spanish:
        parsed = fetch_pro.classify(article["title"])
        assert parsed["lang"] == article["lang"] == "es"
        assert parsed["series_name"] == article["series_name"] == "VAR a Fondo（西）"
        target = "pro.html#" + article_anchor(article["url"])
        assert docs[target].startswith(article["series_name"] + " · ")
    sample = dict(spanish[0], series_name="Inside Video Review（VAR 评析·英）")
    assert series_name(sample) == "VAR a Fondo（西）"
    monkeypatch.setattr(build_pro, "SITE", tmp_path)
    build_pro.build_page(data)
    html = (tmp_path / "pro.html").read_text(encoding="utf-8")
    assert html.count(">VAR a Fondo（西）</span>") == len(spanish)
