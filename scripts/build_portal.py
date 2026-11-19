# -*- coding: utf-8 -*-
"""构建离线裁判学习门户，内联判例、资料目录、个人学习记录与两张图片。"""

import base64
import json
import shutil
from html import escape

from lib.seo import jsonld_dataset, jsonld_website, meta_tags
from lib.site_stats import cheatsheet_count, counts
from lib.theme import inject_theme, icon, topbar

from lib.paths import (
    ASSETS,
    DATA,
    CONMEBOL_JSON,
    IFAB_JSON,
    INTL_JSON,
    LAWS_JSON,
    PRO_JSON,
    RAP_JSON,
    RFEF_JSON,
    SCALE_JSON,
    SITE,
    SRC,
    UEFA_JSON,
    WEEKLY_JSON,
    HNS_JSON,
)


def load_stats():
    def season_stats(season):
        d = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        cases = d["cases"]
        return {
            "n": len(cases),
            "issues": len(d["issues"]),
            "wrong": sum(1 for c in cases if c["referee_verdict"] == "wrong"),
            "correct": sum(1 for c in cases if c["referee_verdict"] == "correct"),
            "videos": sum(len(c["video_files"]) for c in cases),
        }

    laws = json.loads(LAWS_JSON.read_text(encoding="utf-8"))
    secs = laws["sections"] if isinstance(laws, dict) else laws
    return {
        "2026": season_stats("2026"),
        "2025": season_stats("2025"),
        "2024": season_stats("2024"),
        "rules": {
            "sections": len(secs),
            "laws": sum(1 for s in secs if isinstance(s, dict) and s.get("law")),
        },
    }


def build_study_index():
    """首页恢复任意判例；有视频及认定原文的记录可供每日轮换。"""
    pool = []
    for season in ("2026", "2025", "2024"):
        d = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        for c in d["cases"]:
            pool.append(
                [
                    season,
                    c["seq"],
                    c.get("comp", ""),
                    bool(c.get("video_files") and (c.get("conclusion") or "").strip()),
                    c.get("home", ""),
                    c.get("away", ""),
                    c["issue"],
                    c["no"],
                    c.get("category_name", ""),
                ]
            )
    return pool


def load_scale_stats():
    """统一尺度页数字从 data/scale.json 计算（场景/分组/视频=例数）。"""
    p = SCALE_JSON
    scenes = groups = 0
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        for yd in d.values():
            if not isinstance(yd, dict):
                continue
            for sec in yd.get("sections", []):
                for g in sec.get("groups", []):
                    groups += 1
                    scenes += len(g.get("items", []))
    return {"scenes": scenes, "groups": groups, "videos": scenes}


def load_uefa_stats():
    """UEFA Clear Line 判例库数字从 data/uefa.json 计算。"""
    p = UEFA_JSON
    cases = groups = 0
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        for g in d.get("groups", []):
            groups += 1
            cases += len(g.get("items", []))
    return {"cases": cases, "groups": groups}


def load_rap_stats():
    """UEFA RAP 训练包数字从 data/rap.json 计算（期数/在线期数）。"""
    eds = online = 0
    if RAP_JSON.exists():
        d = json.loads(RAP_JSON.read_text(encoding="utf-8"))
        eds = len(d.get("editions", []))
        online = sum(1 for e in d.get("editions", []) if e.get("platform") == "nextaur")
    return {"editions": eds, "online": online}


def load_rfef_stats():
    """RFEF 判罚标准手册数字从 data/rfef.json 计算（专题/判例/视频）。"""
    secs = items = vids = 0
    if RFEF_JSON.exists():
        d = json.loads(RFEF_JSON.read_text(encoding="utf-8"))
        for s in d.get("sections", []):
            secs += 1
            for g in s.get("groups", []):
                for it in g.get("items", []):
                    items += 1
                    vids += len(it.get("videos", []))
    return {"secs": secs, "items": items, "vids": vids}


def load_pro_stats():
    """美国 PRO 评议索引数字从 data/pro.json 计算（篇数/MLS/NWSL）。"""
    arts = 0
    mls = nwsl = 0
    if PRO_JSON.exists():
        d = json.loads(PRO_JSON.read_text(encoding="utf-8"))
        arts = len(d.get("articles", []))
        mls = sum(1 for a in d["articles"] if a.get("league") == "MLS")
        nwsl = sum(1 for a in d["articles"] if a.get("league") == "NWSL")
    return {"arts": arts, "mls": mls, "nwsl": nwsl}


def load_intl_stats():
    """国际评议导航数字从 data/intl.json 计算（资源数/国家机构数）。"""
    res = orgs = 0
    if INTL_JSON.exists():
        d = json.loads(INTL_JSON.read_text(encoding="utf-8"))
        for g in d.get("groups", []):
            res += len(g.get("resources", []))
            orgs += len({r.get("org") for r in g.get("resources", [])})
    return {"res": res, "orgs": orgs}


def load_conmebol_stats():
    """南美 VAR 判例数字从 data/conmebol.json 计算（案数/赛事数）。"""
    cases = 0
    comps = set()
    if CONMEBOL_JSON.exists():
        d = json.loads(CONMEBOL_JSON.read_text(encoding="utf-8"))
        cases = len(d.get("cases", []))
        comps = {c.get("comp") for c in d["cases"] if c.get("comp")}
    return {"cases": cases, "comps": len(comps)}


def load_weekly_stats():
    """周更评议节目判例库数字从 data/weekly.json 计算（期数/节目数/语言数）。"""
    eps = shows = 0
    langs = set()
    if WEEKLY_JSON.exists():
        d = json.loads(WEEKLY_JSON.read_text(encoding="utf-8"))
        eps = len(d.get("episodes", []))
        shows = len(d.get("shows", {}))
        langs = {s.get("lang") for s in d.get("shows", {}).values() if s.get("lang")}
    return {"eps": eps, "shows": shows, "langs": len(langs)}


def load_ifab_stats():
    """IFAB 材料数字从 data/ifab.json 计算（大节/FAQ/条目）。"""
    secs = faq = items = 0
    if IFAB_JSON.exists():
        d = json.loads(IFAB_JSON.read_text(encoding="utf-8"))
        secs = len(d.get("sections", []))
        faq = len(d.get("faq", []))
        items = sum(
            len(b.get("items", []))
            for s in d.get("sections", [])
            for b in s.get("blocks", [])
        )
        items += sum(
            len(b.get("items", []))
            for ex in d.get("extras", [])
            for b in ex.get("blocks", [])
        )
    return {"secs": secs, "faq": faq, "items": items}


def load_hns_stats():
    """克罗地亚 HNS 判例数字从 data/hns.json 计算（轮数/判例/视频）。"""
    rounds = incs = vids = 0
    if HNS_JSON.exists():
        d = json.loads(HNS_JSON.read_text(encoding="utf-8"))
        rounds = len(d.get("rounds", []))
        for r in d.get("rounds", []):
            for i in r.get("incidents", []):
                incs += 1
                vids += len(i.get("videos", []))
    return {"rounds": rounds, "incs": incs, "vids": vids}


def portal_catalog(stats, bank_size):
    """Render every destination as a usable offline link within its subject shelf."""
    seasons = ("2026", "2025", "2024")
    shelves = [
        (
            "domestic",
            "国内赛季评议",
            [
                (
                    f"season-{y}.html",
                    f"{y} 赛季评议",
                    f"{stats[y]['issues']} 期 · {stats[y]['n']} 判例",
                )
                for y in seasons
            ],
        ),
        (
            "teams",
            "各队得失盘点",
            [
                (f"stats-{y}.html", f"{y} 各队得失", f"{stats[y]['wrong']} 个错漏判")
                for y in seasons
            ],
        ),
        (
            "study",
            "规则与练习",
            [
                ("rules.html", "足球竞赛规则", f"{stats['rules']['sections']} 章"),
                (
                    "scale.html",
                    "统一判罚尺度",
                    f"{load_scale_stats()['scenes']} 个场景",
                ),
                ("quiz.html", "考题与限时模考", f"{bank_size} 道题"),
                ("compare.html", "裁判尺度对照课", "双案盲判与自由配对"),
                ("cheatsheet.html", "考点速查卡", f"{cheatsheet_count()} 张"),
                ("search.html", "全站搜索", "判例与条文"),
            ],
        ),
        (
            "europe",
            "欧洲判例与协议",
            [
                ("uefa.html", "UEFA Clear Line", f"{load_uefa_stats()['cases']} 判例"),
                ("rap.html", "UEFA RAP 训练包", f"{load_rap_stats()['editions']} 期"),
                (
                    "rfef.html",
                    "西班牙判罚标准手册",
                    f"{load_rfef_stats()['items']} 判例",
                ),
                ("hns.html", "克罗地亚逐轮分析", f"{load_hns_stats()['incs']} 判例"),
                (
                    "ifab.html",
                    "IFAB 视频助理裁判协议",
                    f"{load_ifab_stats()['faq']} 个常见问题",
                ),
            ],
        ),
        (
            "world",
            "美洲与全球评议",
            [
                ("pro.html", "美国 PRO 评议", f"{load_pro_stats()['arts']} 篇"),
                (
                    "conmebol.html",
                    "南美 VAR 判例",
                    f"{load_conmebol_stats()['cases']} 判例",
                ),
                ("weekly.html", "全球周更评议", f"{load_weekly_stats()['eps']} 期"),
                ("intl.html", "国际评议资源导航", f"{load_intl_stats()['res']} 项"),
            ],
        ),
    ]
    options = []
    groups = []
    arrow = icon("right", 15)
    for number, (key, title, links) in enumerate(shelves):
        group_id = f"shelf-{key}"
        options.append(f'<option value="{group_id}">{escape(title)}</option>')
        entries = "".join(
            f'<li><a href="{href}"><strong>{escape(label)}</strong>'
            f"<small>{escape(detail)}</small>{arrow}</a></li>"
            for href, label, detail in links
        )
        hidden = " hidden" if number else ""
        groups.append(
            f'<ul class="shelf-list" id="{group_id}" aria-label="{escape(title)}"{hidden}>{entries}</ul>'
        )
    return "".join(options), "".join(groups)


def inline_asset(name, mime):
    content = (ASSETS / "portal" / name).read_bytes()
    return f"data:{mime};base64," + base64.b64encode(content).decode("ascii")


def js_value(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )


def main():
    from build_quiz import build_bank

    options, groups = portal_catalog(load_stats(), len(build_bank()[0]))
    sample_data = json.loads((DATA / "cases-2026.json").read_text(encoding="utf-8"))
    sample = next(case for case in sample_data["cases"] if case["seq"] == 183)
    html = (SRC / "portal.html").read_text(encoding="utf-8")
    content = {
        "__PORTAL_CSS__": (SRC / "portal.css").read_text(encoding="utf-8"),
        "__TOPBAR__": topbar(active="index.html", stats="stats-2026.html", portal=True),
        "__TOTAL__": str(counts()["cases"]),
        "__GROUPS__": groups,
        "__OPTIONS__": options,
        "__CASE_PHOTO__": inline_asset("case-study.webp", "image/webp"),
        "__REF_PHOTO__": inline_asset("referee-match.webp", "image/webp"),
        "__REF_MOBILE_PHOTO__": inline_asset("referee-match-small.webp", "image/webp"),
        "__STUDY_CALENDAR__": (SRC / "study-calendar.js").read_text(encoding="utf-8"),
        "__LEARNING_RECORDS__": (SRC / "learning-records.js").read_text(
            encoding="utf-8"
        ),
        "__PORTAL_JS__": (SRC / "portal.js").read_text(encoding="utf-8"),
        "__STUDY_INDEX__": js_value(build_study_index()),
        "__SAMPLE_REVIEW__": js_value(sample["conclusion"]),
        "__PORTAL_EFFECT__": (SRC / "portal-liquid.js").read_text(encoding="utf-8"),
        "__LIQUID_MODULE__": inline_asset(
            "moments/liquid-hover/moment.js", "text/javascript"
        ),
        "__MOTION_HELPERS__": inline_asset("moments/lib.js", "text/javascript"),
        "__ARROW__": icon("right", 16),
        "__BOOK__": icon("book", 22),
        "__SEARCH__": icon("search", 20),
    }
    for token, value in content.items():
        html = html.replace(token, value)
    html = inject_theme(
        html,
        meta=meta_tags("index.html", extra_jsonld=[jsonld_website(), jsonld_dataset()]),
    )
    SITE.mkdir(parents=True, exist_ok=True)
    # A direct portal build also refreshes the four local enhancement files.
    shutil.copytree(
        ASSETS / "portal" / "moments",
        SITE / "assets" / "portal" / "moments",
        dirs_exist_ok=True,
    )
    out = SITE / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"生成 {out}  ({len(html.encode('utf-8')) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
