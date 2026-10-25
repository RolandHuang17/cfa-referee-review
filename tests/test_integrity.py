# -*- coding: utf-8 -*-
"""站点完整性断言：页面自包含、数据计数、内部链接、队徽目录。

两种跑法，检查项完全一致：
  python tests/test_integrity.py   逐项打印 PASS/FAIL，末尾汇总全部问题，退出码即结论
  python -m pytest tests/          每个 check 独立报告

fail-collecting：每个 check 把问题攒进局部 list 再一次性 assert，所以一次运行
就能看到全部问题，不必修一个跑一遍。CI 走前一种，退出码非零即拦截部署。
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 插 scripts/ 而不是 scripts/lib/，让 import 写成 from lib.crest_catalog import ...，
# 与入口脚本走完全相同的包布局——lib 包本身坏了这里就会失败，这是特性。
sys.path.insert(0, str(ROOT / "scripts"))

from lib.crest_catalog import load_catalog, normalize_team, validate_catalog  # noqa: E402
from lib.pages import PAGE_FILES  # noqa: E402
from lib.paths import DATA, SITE  # noqa: E402
from lib.team_names import ALIASES  # noqa: E402

# 页面清单唯一权威源在 scripts/lib/pages.py（sitemap/搜索/SEO 同源），此处只消费
PAGES = PAGE_FILES
SEASONS = ("2024", "2025", "2026")
# 每季期望值（人工复核后的基准，改动判例分类或解析需同步更新）
EXPECTED = {
    "2024": (160, 161, {"wrong": 60, "correct": 99, "pending": 1}),
    "2025": (227, 229, {"wrong": 83, "correct": 138, "pending": 6}),
    "2026": (225, 224, {"wrong": 95, "correct": 121, "pending": 9}),
}
# 考题模式题库基准：每季「有视频且有认定原文」的判例数 + 尺度场景数（改口径需同步）。
# 注意 2024 第1期为"结论摘要"式文章，无认定原文的判例（如 seq3）本就不入判例池，属设计内
EXPECTED_QUIZ = {"2024": 141, "2025": 227, "2026": 224}
# VAR 协议题基准：IFAB 协议 FAQ 全部 12 条（与 fetch_ifab.py 的 FAQ 集合一致）
VAR_QUIZ_FAQ_IDS = {f"q{i}" for i in range(1, 13)}

FAILURES = []


def _finish(problems):
    FAILURES.extend(problems)
    assert not problems, "\n".join(problems)


def test_pages_exist_and_are_self_contained():
    problems = []
    for name in PAGES:
        path = SITE / name
        if not path.exists():
            problems.append(f"缺少 site/{name}")
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"__\w+__|\{\{[^}]+\}\}", text):
            problems.append(f"存在模板占位符: site/{name}")
        if re.search(
            r"<script\s+src=|fonts\.googleapis|cdnjs|unpkg|jsdelivr", text, re.I
        ):
            problems.append(f"存在外部脚本或CDN引用: site/{name}")
        # 标签配平护栏：未闭合的 <style>/<script> 会把后续文档吞进 raw-text 块，
        # 造成 token 丢失/页面半瘫（stats 页曾因缺 </style> 丢掉全部 :root tokens）
        for tag in ("style", "script"):
            opened = len(re.findall(rf"<{tag}[\s>]", text))
            closed = text.count(f"</{tag}>")
            if opened != closed:
                problems.append(
                    f"site/{name} <{tag}> 标签不配平: {opened} 开 / {closed} 闭"
                )
    _finish(problems)


def test_season_case_counts():
    problems = []
    for season, (case_count, video_count, verdicts) in EXPECTED.items():
        data = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        cases = data["cases"]
        actual = {
            key: sum(1 for case in cases if case["referee_verdict"] == key)
            for key in verdicts
        }
        videos = sum(len(case["video_files"]) for case in cases)
        if (len(cases), videos, actual) != (case_count, video_count, verdicts):
            problems.append(
                f"{season}数据统计不符: cases={len(cases)} videos={videos} "
                f"verdicts={actual}，期望 {case_count}/{video_count}/{verdicts}"
            )
        # 存档完整性：cases 引用的每期都应有官方页面存档
        issues_dir = DATA / "issues" / season
        if issues_dir.is_dir():
            archived = {
                int(mm.group(1))
                for f in issues_dir.glob("issue_*.html")
                for mm in [re.match(r"issue_(\d+)\.html", f.name)]
                if mm
            }
            case_issues = {c["issue"] for c in cases}
            if not case_issues <= archived:
                problems.append(
                    f"{season} 官方页面存档缺期: {sorted(case_issues - archived)}"
                )
    _finish(problems)


def test_internal_links_resolve():
    problems = []
    for path in SITE.glob("*.html"):
        for target in re.findall(
            r"(?:href|src)=\"([^\"]+)\"", path.read_text(encoding="utf-8")
        ):
            if (
                target.startswith(
                    ("#", "http://", "https://", "data:", "mailto:", "//", "/")
                )
                or "${" in target
            ):
                continue
            if target.startswith("videos/"):
                continue  # 视频为本地 gitignored 资产，线上按需提供
            stem = target.split("#", 1)[0]
            if "?" in stem:
                continue  # 带 query 的链接不经文件系统解析
            if stem and not (path.parent / stem).resolve().exists():
                problems.append(f"{path.name} 引用了不存在的路径: {target}")
    _finish(problems)


def test_team_catalog_complete():
    catalog = load_catalog()
    names = {item["name"] for item in catalog.values()}
    raw_names = set()
    for season in SEASONS:
        data = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        for case in data["cases"]:
            raw_names.update(filter(None, (case.get("home"), case.get("away"))))
    problems = []
    for raw in sorted(raw_names):
        canonical = normalize_team(raw)
        if canonical not in names:
            problems.append(f"队伍未登记: {raw} -> {canonical}")
    slugs = [item.get("slug") for item in catalog.values()]
    if len(slugs) != len(set(slugs)):
        problems.append(
            f"队徽 slug 重复: {sorted({s for s in slugs if slugs.count(s) > 1})}"
        )
    _finish(problems)
    print(f"队徽目录校验通过: {len(raw_names)} 个原始名称 -> {len(names)} 个标准队伍")


def test_crest_files_and_provenance():
    _finish(validate_catalog(load_catalog()))


def test_quiz_bank_pool():
    """考题模式题库回归基准：判例池（有视频+认定原文）与尺度场景池计数。"""
    problems = []
    bank_path = SITE / "quiz.html"
    if not bank_path.exists():
        problems.append("缺少 site/quiz.html")
        _finish(problems)
        return
    per_season = {s: 0 for s in SEASONS}
    for season in SEASONS:
        data = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        per_season[season] = sum(
            1
            for c in data["cases"]
            if c.get("video_files") and (c.get("conclusion") or "").strip()
        )
    text = bank_path.read_text(encoding="utf-8")
    m = re.search(r'"meta":\{"case":(\d+),"scale":(\d+),"var":(\d+)', text)
    if not m:
        problems.append("quiz.html 缺少 meta 题库统计（case/scale/var）")
    else:
        n_case, n_scale, n_var = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if n_case != sum(per_season.values()):
            problems.append(
                f"考题判例池不符: quiz={n_case}，期望 {sum(per_season.values())}（{per_season}）"
            )
        scale_total = 0
        if (DATA / "scale.json").exists():
            sd = json.loads((DATA / "scale.json").read_text(encoding="utf-8"))
            for yd in sd.values():
                if not isinstance(yd, dict):
                    continue
                for sec in yd.get("sections", []):
                    for g in sec.get("groups", []):
                        for it in g.get("items", []):
                            dec = it.get("decision") or []
                            if (
                                dec
                                and not any(
                                    x.get("label") == "VAR 机制讲解" for x in dec
                                )
                                and it.get("video")
                            ):
                                scale_total += 1
        if n_scale != scale_total:
            problems.append(f"考题尺度场景池不符: quiz={n_scale}，期望 {scale_total}")
        if n_var != len(VAR_QUIZ_FAQ_IDS):
            problems.append(
                f"考题 VAR 协议题池不符: quiz={n_var}，期望 {len(VAR_QUIZ_FAQ_IDS)}"
            )
        # 规则理论题：quiz meta 计数与题库文件一致 + 题目结构合法（law 锚点存在）
        theory_path = DATA / "theory-questions.json"
        if not theory_path.exists():
            problems.append("缺少 data/theory-questions.json")
        else:
            tq = json.loads(theory_path.read_text(encoding="utf-8")).get(
                "questions", []
            )
            law_ids = {
                s["id"]
                for s in json.loads((DATA / "laws.json").read_text(encoding="utf-8"))[
                    "sections"
                ]
            }
            seen_ids = set()
            for q in tq:
                where = f"theory {q.get('id')}"
                if q.get("id") in seen_ids:
                    problems.append(f"{where} id 重复")
                seen_ids.add(q.get("id"))
                if len(q.get("opts", [])) != 4:
                    problems.append(f"{where} 选项数不是 4")
                if not (0 <= q.get("ans", -1) < 4):
                    problems.append(f"{where} 答案下标非法")
                if q.get("law") not in law_ids:
                    problems.append(
                        f"{where} law 锚点不存在于 laws.json: {q.get('law')}"
                    )
                if not (q.get("src") or "").strip():
                    problems.append(f"{where} 缺条文出处引文（src）")
            m2 = re.search(r',"theory":(\d+)\}', text)
            if not m2:
                problems.append("quiz.html meta 缺 theory 计数")
            elif int(m2.group(1)) != len(tq):
                problems.append(
                    f"考题理论题池不符: quiz={int(m2.group(1))}，期望 {len(tq)}"
                )
        for season, expected in EXPECTED_QUIZ.items():
            if per_season[season] != expected:
                problems.append(
                    f"{season}考题判例池 {per_season[season]} != 基准 {expected}"
                )
    _finish(problems)
    print(
        f"考题题库校验通过: 判例 {sum(per_season.values())} + 尺度场景 "
        f"{int(m.group(2)) if m else '?'} + VAR 协议 {int(m.group(3)) if m else '?'} 题"
    )


def test_impact_and_scores_consistency():
    """impact/scores 数据护栏：键落在 wrong 判例、items 属对阵双方、队名已归一化、比分键无孤儿。

    队名归一是 AGENTS 硬约束 6：impact/scores 必须存标准名（未归一名会让 stats 页
    查不到队徽、与 season 页队名不一致）。覆盖缺口由各 make_impact 脚本的覆盖率断言负责。
    """
    problems = []
    for season in SEASONS:
        data = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        wrong = {c["seq"] for c in data["cases"] if c["referee_verdict"] == "wrong"}
        imp = json.loads((DATA / f"impact-{season}.json").read_text(encoding="utf-8"))
        match_keys = set()
        for seq_s, rec in imp["impacts"].items():
            seq = int(seq_s)
            where = f"impact-{season} seq{seq}"
            if seq not in wrong:
                problems.append(f"{where} 不是 wrong 判例")
                continue
            match_keys.add(
                f"{rec['league']}|{rec['round']}|{rec['home']}|{rec['away']}"
            )
            if rec["league"] != next(
                c["comp"] for c in data["cases"] if c["seq"] == seq
            ):
                problems.append(f"{where} league 与 cases 不符")
            for n in (rec["home"], rec["away"]):
                if n in ALIASES:
                    problems.append(f"{where} 队名未归一化: {n}")
            for it in rec["items"]:
                if it["team"] not in (rec["home"], rec["away"]):
                    problems.append(f"{where} items 队名不属于对阵双方: {it['team']}")
        sc = json.loads(
            (DATA / f"match-scores-{season}.json").read_text(encoding="utf-8")
        )
        for key in sc.get("scores", {}):
            for n in key.split("|")[2:]:
                if n in ALIASES:
                    problems.append(f"match-scores-{season} 队名未归一化: {key}")
            if key not in match_keys:
                problems.append(
                    f"match-scores-{season} 孤儿比分键（impact 无对应场次）: {key}"
                )
    _finish(problems)
    print("impact/scores 一致性校验通过")


def test_site_pages_in_sync_with_data():
    """stale-build 护栏：site 页内联 meta 计数必须与 data JSON 一致（改数据必须重建页面）。"""
    problems = []
    for season in SEASONS:
        data = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        page = SITE / f"season-{season}.html"
        if page.exists():
            m = re.search(
                r'"meta":\{"n_cases":(\d+),"n_issues":(\d+)\}',
                page.read_text(encoding="utf-8"),
            )
            if not m:
                problems.append(
                    f"season-{season}.html 缺少 meta 计数（页面过旧，需重建）"
                )
            elif (int(m.group(1)), int(m.group(2))) != (
                len(data["cases"]),
                len(data["issues"]),
            ):
                problems.append(
                    f"season-{season}.html 内联数据过期: meta={m.groups()}，"
                    f"实际 cases={len(data['cases'])} issues={len(data['issues'])}，需重建页面"
                )
        imp = json.loads((DATA / f"impact-{season}.json").read_text(encoding="utf-8"))
        spage = SITE / f"stats-{season}.html"
        if spage.exists():
            m2 = re.search(
                r'"overview":\{"cases":(\d+)', spage.read_text(encoding="utf-8")
            )
            if not m2:
                problems.append(
                    f"stats-{season}.html 缺少 overview 计数（页面过旧，需重建）"
                )
            elif int(m2.group(1)) != len(imp["impacts"]):
                problems.append(
                    f"stats-{season}.html 内联数据过期: 影响 {m2.group(1)} != "
                    f"{len(imp['impacts'])}，需重建页面"
                )
    _finish(problems)
    print("site 页面与 data JSON 同步")


def test_weekly_ifab_data_sanity():
    """weekly.json / ifab.json 及其中文层的数据健全性（结构断言，不锁数量）。"""
    problems = []
    wk = json.loads((DATA / "weekly.json").read_text(encoding="utf-8"))
    shows = wk.get("shows", {})
    eps = wk.get("episodes", [])
    if len(shows) < 4:
        problems.append(f"weekly.json 节目数过少: {len(shows)}（应为 7 档左右）")
    if len(eps) < 50:
        problems.append(f"weekly.json 期目数过少: {len(eps)}")
    ids = set()
    for e in eps:
        vid = e.get("id")
        if not vid:
            problems.append(f"weekly.json 期目缺 id: {e}")
            continue
        ids.add(vid)
        for field in ("show", "title", "url"):
            if not e.get(field):
                problems.append(f"weekly.json 期目 {vid} 缺字段 {field}")
        if e.get("date_src") == "exact" and not e.get("date"):
            problems.append(f"weekly.json 期目 {vid} date_src=exact 但无日期")
        if e.get("show") not in shows:
            problems.append(
                f"weekly.json 期目 {vid} 的节目 {e.get('show')} 不在 shows 中"
            )
        if e.get("show") == "uaf":
            ok_url = str(e.get("url", "")).startswith("https://uaf.ua/")
        else:
            ok_url = str(e.get("url", "")).startswith(
                "https://www.youtube.com/watch?v="
            )
        if not ok_url:
            problems.append(
                f"weekly.json 期目 {vid} 的 url 非官方页（{e.get('show')}）"
            )
    wzh = json.loads((DATA / "weekly-zh.json").read_text(encoding="utf-8"))
    for k in wzh.get("items", {}):
        if k not in ids:
            problems.append(f"weekly-zh.json items 键 {k} 不在 weekly.json 中")
    for k in wzh.get("shows", {}):
        if k not in shows:
            problems.append(f"weekly-zh.json shows 键 {k} 不在 weekly.json 中")
    uncovered = [
        e["id"] for e in eps if e.get("id") and e["id"] not in wzh.get("items", {})
    ]
    if uncovered:
        problems.append(
            f"weekly-zh.json 译注未全覆盖: 缺 {len(uncovered)} 期（如 {uncovered[:3]}）"
        )
    ifab = json.loads((DATA / "ifab.json").read_text(encoding="utf-8"))
    secs = ifab.get("sections", [])
    faq = ifab.get("faq", [])
    if len(secs) < 4:
        problems.append(f"ifab.json 大节数过少: {len(secs)}（应为 4）")
    if len(faq) < 10:
        problems.append(f"ifab.json FAQ 数过少: {len(faq)}（应为 12）")
    if not all(s.get("blocks") for s in secs):
        problems.append("ifab.json 存在无内容的大节")
    izh = json.loads((DATA / "ifab-zh.json").read_text(encoding="utf-8"))
    zsecs = izh.get("sections", {})
    for s in secs:
        if s["id"] not in zsecs:
            problems.append(f"ifab-zh.json 缺大节 {s['id']}（{s.get('h')}）")
            continue
        zblocks = zsecs[s["id"]].get("blocks", {})
        for b in s["blocks"]:
            if (b.get("h") or "_head") not in zblocks:
                problems.append(
                    f"ifab-zh.json 缺子节 {s['id']}/{b.get('h') or '_head'}"
                )
    for q in faq:
        if q["id"] not in izh.get("faq", {}):
            problems.append(f"ifab-zh.json 缺 FAQ {q['id']}")
    # HNS《Sudačka analiza》：判例字段齐全 + 译制层全覆盖
    hns = json.loads((DATA / "hns.json").read_text(encoding="utf-8"))
    hrounds = hns.get("rounds", [])
    if not hrounds:
        problems.append("hns.json 无轮次数据")
    hids = set()
    for r in hrounds:
        hids.add(str(r.get("id")))
        if not (r.get("title") and r.get("date") and r.get("url")):
            problems.append(f"hns.json 轮次 {r.get('id')} 缺 title/date/url")
        for inc in r.get("incidents", []):
            if not inc.get("paras") or inc.get("verdict") not in (
                "correct",
                "incorrect",
                "other",
            ):
                problems.append(
                    f"hns.json {r.get('id')} 判例 {inc.get('no')} paras/verdict 异常"
                )
    hzh = json.loads((DATA / "hns-zh.json").read_text(encoding="utf-8"))
    for r in hrounds:
        zr = hzh.get("rounds", {}).get(str(r.get("id")))
        if not zr:
            problems.append(f"hns-zh.json 缺轮次 {r.get('id')}")
            continue
        for inc in r.get("incidents", []):
            zi = zr.get("incidents", {}).get(str(inc.get("no")))
            if not zi or len(zi.get("paras", [])) != len(inc.get("paras", [])):
                problems.append(
                    f"hns-zh.json 译制不齐: {r.get('id')} 判例 {inc.get('no')}"
                )
    for k in hzh.get("rounds", {}):
        if k not in hids:
            problems.append(f"hns-zh.json rounds 键 {k} 不在 hns.json 中")
    _finish(problems)
    print("weekly/ifab/hns 数据与中文层校验通过")


def test_issue_url_tables_in_sync():
    """硬约束 7 的自动化：fetch_issues.ISSUES 与 parse_issues.ISSUE_URL 是同一套 URL 的两份拷贝。

    两脚本均带 __main__ guard，直接 import 取表比对；不一致 = 加新期时漏同步一处，
    会在抓取或解析时静默漏期。顺带断言表中每期都已有官方页面存档。"""
    import fetch_issues
    import parse_issues

    problems = []
    for season in sorted(set(fetch_issues.ISSUES) | set(parse_issues.ISSUE_URL)):
        left = fetch_issues.ISSUES.get(season, {})
        right = parse_issues.ISSUE_URL.get(season, {})
        if set(left) != set(right):
            problems.append(
                f"{season} 两 URL 表期数不一致: fetch_issues={sorted(left)} "
                f"parse_issues={sorted(right)}"
            )
            continue
        for no in sorted(left):
            if fetch_issues.BASE + left[no][0] != right[no]:
                problems.append(
                    f"{season} 第{no}期 URL 不一致: {left[no][0]} vs {right[no]}"
                )
        archived = {
            int(m.group(1))
            for f in (DATA / "issues" / season).glob("issue_*.html")
            for m in [re.match(r"issue_(\d+)\.html", f.name)]
            if m
        }
        missing = sorted(set(left) - archived)
        if missing:
            problems.append(
                f"{season} URL 表中的期尚未抓取存档: {missing}（先跑 fetch_issues）"
            )
    _finish(problems)
    print("两 URL 表同步且每期均有存档")


def test_uefa_rfef_conmebol_zh_aligned():
    """uefa-zh / rfef-zh / conmebol-zh 译文层与源数据对齐（镜像各 builder 的 ⚠ 回退条件）。

    weekly/ifab/hns 的对齐已由 test_weekly_ifab_data_sanity 覆盖；这三个源在 fetch 更新后
    译文缺口只会以构建 ⚠ 打印出现、CI 不拦——这里把「构建零警告」变成硬断言。"""
    problems = []
    # --- UEFA：组按 key、criteria 按块序对齐、判例按 id（镜像 build_uefa.apply_zh）---
    uefa = json.loads((DATA / "uefa.json").read_text(encoding="utf-8"))
    uzh = json.loads((DATA / "uefa-zh.json").read_text(encoding="utf-8"))
    zg, zi = uzh.get("groups", {}), uzh.get("items", {})
    used_g = set()
    for g in uefa.get("groups", []):
        key = g.get("key", "")
        z = zg.get(key)
        if not z:
            problems.append(f"uefa-zh 缺组译文: {key}")
            continue
        used_g.add(key)
        if g.get("intro") and not z.get("intro"):
            problems.append(f"uefa-zh 组 {key} 缺 intro 译文")
        en_c = g.get("criteria") or []
        zc = z.get("criteria") or []
        if en_c and not zc:
            problems.append(f"uefa-zh 组 {key} 缺 criteria 译文")
        elif zc and not (
            len(zc) == len(en_c)
            and all(
                len(b.get("items") or []) == len(a.get("items") or [])
                for a, b in zip(en_c, zc)
            )
        ):
            problems.append(f"uefa-zh 组 {key} criteria 块数/条数与英文不一致")
        for it in g.get("items", []):
            if not (zi.get(it.get("id", "")) or {}).get("title"):
                problems.append(f"uefa-zh 缺判例标题译文: {it.get('id', '')}")
    for k in sorted(set(zg) - used_g):
        problems.append(f"uefa-zh 组 key 不在 uefa.json 中（疑似过期）: {k}")
    src_ids = {
        it.get("id") for g in uefa.get("groups", []) for it in g.get("items", [])
    }
    for k in sorted(set(zi) - src_ids):
        problems.append(f"uefa-zh items 键不在 uefa.json 中（疑似过期）: {k}")
    # --- RFEF：栏目按 key、分组 notes 条数、判例按 id（镜像 build_rfef.apply_zh）---
    rfef = json.loads((DATA / "rfef.json").read_text(encoding="utf-8"))
    rzh = json.loads((DATA / "rfef-zh.json").read_text(encoding="utf-8"))
    zs, zitems = rzh.get("sections", {}), rzh.get("items", {})
    used_s, src_items, src_vids = set(), set(), set()
    for s in rfef.get("sections", []):
        key = s.get("key", "")
        z = zs.get(key)
        if not z:
            problems.append(f"rfef-zh 缺栏目译文: {key}")
            continue
        used_s.add(key)
        for g in s.get("groups", []):
            zg_ = (z.get("groups") or {}).get(g.get("code", ""))
            if (
                zg_
                and zg_.get("notes") is not None
                and len(zg_["notes"]) != len(g.get("notes_es") or [])
            ):
                problems.append(f"rfef-zh 分组 {g.get('code')} notes 条数与西语不一致")
            for it in g.get("items", []):
                if it.get("situation_es") and not (
                    zitems.get(it.get("id", "")) or {}
                ).get("situation"):
                    problems.append(f"rfef-zh 缺判例情形译文: {it.get('id', '')}")
                src_items.add(it.get("id", ""))
                for v in it.get("videos", []):
                    src_vids.add(v.get("id", ""))
    for k in sorted(set(zs) - used_s):
        problems.append(f"rfef-zh sections 键不在 rfef.json 中（疑似过期）: {k}")
    for k in sorted(set(zitems) - src_items - src_vids):
        problems.append(f"rfef-zh items 键不在 rfef.json 中（疑似过期）: {k}")
    # --- CONMEBOL：按 url 键，有官方情境的案子必须有中文（镜像 build_conmebol 回退警告）---
    con = json.loads((DATA / "conmebol.json").read_text(encoding="utf-8"))
    czh = json.loads((DATA / "conmebol-zh.json").read_text(encoding="utf-8"))
    zcases = czh.get("cases", {})
    applied = set()
    for c in con.get("cases", []):
        url = c.get("url", "")
        if (zcases.get(url) or {}).get("situation"):
            applied.add(url)
        elif c.get("situacion_es"):
            problems.append(f"conmebol-zh 缺情境译文（构建时会回退西语）: {url[:70]}")
    for k in sorted(set(zcases) - applied):
        problems.append(
            f"conmebol-zh cases 键未生效（源无此案或译文缺 situation）: {k[:70]}"
        )
    _finish(problems)
    print("uefa/rfef/conmebol 译文层与源数据对齐")


def test_data_conform_to_schemas():
    """数据 JSON 契约（schemas/*.schema.json，校验器 validate_schemas.py）。"""
    import validate_schemas

    _finish(validate_schemas.validate_all())
    print("cases/impact/quiz-answers/weekly 符合 schema 契约")


def _safe_xml(path):
    """防 XML 实体扩展（与 fetch_weekly.parse_rss 同一防线）：拒绝 DTD/实体 + 限输入大小。

    sitemap/feed 虽是本仓库构建产物，但测试按不可信输入处理——防御式解析零成本。
    """
    import xml.etree.ElementTree as ET

    raw = path.read_bytes()
    if len(raw) > 2_000_000:
        raise ValueError(f"{path.name} 超过 2MB")
    head = raw[:2048]
    if b"<!DOCTYPE" in head or b"<!ENTITY" in head:
        raise ValueError(f"{path.name} 含 DTD/实体声明")
    return ET.fromstring(raw)


def test_xlinks_references_resolve():
    """互链策表（data/xlinks.json）：law id/尺度组名引用可解析 + 分类键与三季数据一致。"""
    from lib.xlinks import load_table, resolve

    problems = []
    table = load_table()
    cats = set()
    for season in SEASONS:
        data = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        cats.update(c["category"] for c in data["cases"])
    if set(table["law_of_category"]) != cats:
        problems.append(
            f"xlinks 分类键与教学分类不一致: {sorted(set(table['law_of_category']) ^ cats)}"
        )
    try:
        by_cat, _ = resolve()
    except KeyError as exc:
        problems.append(f"xlinks 引用失配: {exc}")
    else:
        empty = [c for c, v in by_cat.items() if not v["laws"]]
        if empty:
            problems.append(f"xlinks 分类缺规则章节链接: {empty}")
    _finish(problems)
    print("互链策表（规则/尺度/分类）引用全部可解析")


def test_seo_discovery_layer():
    """发现层护栏：每页 meta/canonical/favicon/feed 链接 + sitemap/robots/feed 文件健全。"""
    problems = []
    for name in PAGES:
        path = SITE / name
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if not text:
            continue
        if name == "404.html":
            if 'name="robots"' not in text:
                problems.append("404.html 缺 robots noindex")
        else:
            if '<meta name="description"' not in text:
                problems.append(f"{name} 缺 meta description")
            if 'rel="canonical"' not in text:
                problems.append(f"{name} 缺 canonical")
        if "data:image/svg+xml" not in text:
            problems.append(f"{name} 缺 favicon（data-URI）")
        if 'type="application/atom+xml"' not in text:
            problems.append(f"{name} 缺 feed 发现链接")
    try:
        root = _safe_xml(SITE / "sitemap.xml")
    except (FileNotFoundError, ValueError) as exc:
        problems.append(f"sitemap 异常: {exc}")
    else:
        locs = {
            el.text
            for el in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        }
        from lib.seo import SITE_URL

        for name in PAGES:
            if name == "404.html":
                continue
            if f"{SITE_URL}/{name}" not in locs:
                problems.append(f"sitemap 缺少 {name}")
    robots = SITE / "robots.txt"
    if not robots.exists():
        problems.append("缺少 site/robots.txt")
    elif "sitemap.xml" not in robots.read_text(encoding="utf-8"):
        problems.append("robots.txt 未指向 sitemap")
    try:
        froot = _safe_xml(SITE / "feed.xml")
    except (FileNotFoundError, ValueError) as exc:
        problems.append(f"feed.xml 异常: {exc}")
    else:
        ns = "{http://www.w3.org/2005/Atom}"
        ids = [el.text for el in froot.iter(f"{ns}id")]
        if len(ids) < 2:
            problems.append("feed.xml entry 过少")
        if len(ids) != len(set(ids)):
            problems.append("feed.xml entry id 重复")
    _finish(problems)
    print("发现层校验通过: meta/sitemap/robots/feed")


def test_pwa_offline_layer():
    """PWA 离线层：sw.js/manifest/icon 存在且策略正确；每页有注册片段与 manifest 链接。"""
    problems = []
    sw = SITE / "sw.js"
    if not sw.exists():
        problems.append("缺少 site/sw.js")
    else:
        text = sw.read_text(encoding="utf-8")
        for token, what in (
            ("/videos/", "跳过 videos"),
            ("navigate", "导航策略"),
            ("VERSION", "版本戳"),
            ("caches.delete", "旧缓存清理"),
        ):
            if token not in text:
                problems.append(f"sw.js 缺 {what}")
    mf = SITE / "manifest.webmanifest"
    if not mf.exists():
        problems.append("缺少 site/manifest.webmanifest")
    else:
        m = json.loads(mf.read_text(encoding="utf-8"))
        if m.get("start_url") != "index.html" or not m.get("icons"):
            problems.append("manifest 异常（start_url/icons）")
    if not (SITE / "icon.svg").exists():
        problems.append("缺少 site/icon.svg")
    for name in PAGES:
        path = SITE / name
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if not text:
            continue
        if "serviceWorker.register" not in text:
            problems.append(f"{name} 缺 SW 注册片段")
        if 'rel="manifest"' not in text:
            problems.append(f"{name} 缺 manifest 链接")
    _finish(problems)
    print("PWA 离线层校验通过: sw/manifest/icon + 全页注册")


def test_bat_file_gbk_encoded():
    """硬约束 4：启动合集网页.bat 必须存为 GBK（cmd 按 ANSI 码页解析，UTF-8 会乱码中断）。"""
    raw = (ROOT / "启动合集网页.bat").read_bytes()
    problems = []
    if raw.startswith(b"\xef\xbb\xbf"):
        problems.append("启动合集网页.bat 带 UTF-8 BOM（必须 GBK 无 BOM）")
    try:
        text = raw.decode("gbk")
    except UnicodeDecodeError as e:
        problems.append(f"启动合集网页.bat 不是合法 GBK: {e}")
        _finish(problems)
        return
    if not text.lstrip().startswith("@echo off"):
        problems.append("启动合集网页.bat 内容异常（未见 @echo off 开头）")
    _finish(problems)
    print("启动合集网页.bat 为 GBK 编码")


CHECKS = [
    test_pages_exist_and_are_self_contained,
    test_season_case_counts,
    test_impact_and_scores_consistency,
    test_site_pages_in_sync_with_data,
    test_quiz_bank_pool,
    test_weekly_ifab_data_sanity,
    test_issue_url_tables_in_sync,
    test_uefa_rfef_conmebol_zh_aligned,
    test_data_conform_to_schemas,
    test_xlinks_references_resolve,
    test_seo_discovery_layer,
    test_pwa_offline_layer,
    test_bat_file_gbk_encoded,
    test_internal_links_resolve,
    test_team_catalog_complete,
    test_crest_files_and_provenance,
]


def main():
    for check in CHECKS:
        try:
            check()
        except AssertionError:
            print(f"FAIL {check.__name__}")
        else:
            print(f"PASS {check.__name__}")
    if FAILURES:
        print(f"\n校验失败，共 {len(FAILURES)} 项：")
        for item in FAILURES:
            print(f"  - {item}")
        return 1
    print(
        f"\n项目校验通过: {len(PAGES)}个页面、三赛季数据、离线资源路径和外部引用均正常"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
