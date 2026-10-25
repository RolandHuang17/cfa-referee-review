# -*- coding: utf-8 -*-
"""教学分类 ↔ 规则章节 ↔ 尺度场景组 互链解析器。

策表在 data/xlinks.json（人工维护），本模块把它解析成可直接渲染的链接结构：
- by_category: {cat: {"laws": [{id,title,url}], "scale": [{label,url}]}}
- sections_to_cats: {law_id: [cat_id,...]}（rules 页「相关判例」反链用）

锚点约定：rules.html#<章节id>（build_rules 初始化已支持 hash 选章）；
scale.html#s<年>-<节序>-<组序>（build_scale 的组锚点，深链自动切页签）。
引用失配（law id 不存在 / 组名在该年找不到）抛 KeyError——构建即失败，
test_integrity 另有独立断言（不依赖页面构建路径）。
"""
import json

from lib.paths import DATA, LAWS_JSON, SCALE_JSON

XLINKS_JSON = DATA / "xlinks.json"


def load_table():
    return json.loads(XLINKS_JSON.read_text(encoding="utf-8"))


def resolve(table=None, laws=None, scale=None):
    table = table or load_table()
    laws = laws if laws is not None else json.loads(LAWS_JSON.read_text(encoding="utf-8"))
    scale = scale if scale is not None else json.loads(SCALE_JSON.read_text(encoding="utf-8"))

    law_titles = {s["id"]: s["title"] for s in laws.get("sections", [])}

    def scale_anchor(year, group_name):
        year_data = scale.get(year)
        if not isinstance(year_data, dict):
            raise KeyError(f"xlinks: scale.json 无 {year} 年数据")
        for si, sec in enumerate(year_data.get("sections", [])):
            for gi, g in enumerate(sec.get("groups", [])):
                if g.get("name") == group_name:
                    return f"s{year}-{si}-{gi}", len(g.get("items", []))
        raise KeyError(f"xlinks: {year} 年找不到尺度组「{group_name}」")

    by_category = {}
    sections_to_cats = {}
    for cat, law_ids in table["law_of_category"].items():
        laws_out = []
        for lid in law_ids:
            if lid not in law_titles:
                raise KeyError(f"xlinks: laws.json 无章节 {lid}")
            laws_out.append({"id": lid, "title": law_titles[lid], "url": f"rules.html#{lid}"})
            sections_to_cats.setdefault(lid, []).append(cat)
        scale_out = []
        for year, gname in table["scale_groups_of_category"].get(cat, []):
            anchor, n = scale_anchor(year, gname)
            scale_out.append({"label": f"{year}·{gname}（{n}例）", "url": f"scale.html#{anchor}"})
        by_category[cat] = {"laws": laws_out, "scale": scale_out}
    return by_category, sections_to_cats
