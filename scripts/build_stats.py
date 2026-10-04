# -*- coding: utf-8 -*-
"""生成错漏判影响统计页 stats-2026.html / stats-2025.html / stats-2024.html（单文件离线可用）
用法: python build_stats.py [赛季]   # 不带参数=三个赛季都构建
数据: data/cases-{s}.json + data/impact-{s}.json + data/match-scores-{s}.json
口径:
  - 确定得失球修正仅含进球判定类错误（漏判进球/对方进球应无效）
  - 点球为机会类, 不折算进球
  - 结果影响判定: 修正比分后受影响球队积分提高 -> "结果或被改变";
    未提高但存在点球/红牌机会因素且修正后分差<=1 -> "存在影响可能"; 否则"未改变结果"
  - 比分缺失的场次显示"待补"并优雅降级
"""
import json
import sys
from datetime import date

from lib.crest_catalog import load_catalog
from lib.team_names import normalize_name
from lib.theme import inject_theme, icon, js_icons, topbar

from lib.paths import DATA, SITE

SEASONS = {
    "2026": {
        "cases": "cases-2026.json", "impact": "impact-2026.json",
        "scores": "match-scores-2026.json",
        "out": "stats-2026.html", "page": "season-2026.html",
        "season": "2026", "issueDesc": "2026赛季第1—22期（赛季进行中）",
    },
    "2025": {
        "cases": "cases-2025.json", "impact": "impact-2025.json",
        "scores": "match-scores-2025.json",
        "out": "stats-2025.html", "page": "season-2025.html",
        "season": "2025", "issueDesc": "2025赛季第1—32期",
    },
    "2024": {
        "cases": "cases-2024.json", "impact": "impact-2024.json",
        "scores": "match-scores-2024.json",
        "out": "stats-2024.html", "page": "season-2024.html",
        "season": "2024", "issueDesc": "2024赛季第1—27期",
    },
}

# type -> (本队进球修正, 对方进球修正)
GOAL_DELTA = {"denied_goal": (1, 0), "opp_goal_should_disallow": (0, -1)}

TYPE_LABEL = {
    "denied_goal": "漏判进球（应有效）",
    "opp_goal_should_disallow": "对方进球应无效",
    "missed_penalty": "漏判点球（机会）",
    "wrong_penalty_against": "错判点球",
    "missed_red_opponent": "漏判对方红牌",
    "wrong_red_self": "错判本队红牌",
    "missed_yellow_opponent": "漏判对方黄牌",
    "wrong_yellow_self": "错判本队黄牌",
    "wrong_foul_called_self": "错判犯规",
    "wrong_offside_self": "误判越位",
    "missed_foul_called": "漏判犯规（漏吹）",
}
TYPE_LABEL_BENEFIT = {
    "denied_goal": "取消对方应得进球",
    "opp_goal_should_disallow": "获得应无效进球",
    "missed_penalty": "对方漏判点球（获益）",
    "wrong_penalty_against": "获得不应得点球",
    "missed_red_opponent": "对方漏判红牌（获益）",
    "wrong_red_self": "对方被错罚红牌（获益）",
    "missed_yellow_opponent": "对方漏判黄牌（获益）",
    "wrong_yellow_self": "对方被错罚黄牌（获益）",
    "wrong_foul_called_self": "对方被错判犯规",
    "wrong_offside_self": "对方被误判越位",
    "missed_foul_called": "漏判本队犯规（获益）",
}
LEAGUE_SHORT = {"中超联赛": "中超", "中甲联赛": "中甲", "中乙联赛": "中乙",
                "中国足协杯": "足协杯", "足协杯": "足协杯",
                "女超联赛": "女超", "女甲联赛": "女甲",
                "全运会": "全运会", "三大球运动会": "三大球"}
TYPE_ORDER = ["denied_goal", "opp_goal_should_disallow", "missed_penalty",
              "wrong_penalty_against", "missed_red_opponent", "wrong_red_self",
              "missed_yellow_opponent", "wrong_yellow_self",
              "wrong_foul_called_self", "missed_foul_called", "wrong_offside_self"]


def load(season):
    cfg = SEASONS[season]
    cases = json.loads((DATA / cfg["cases"]).read_text(encoding="utf-8"))
    impact = json.loads((DATA / cfg["impact"]).read_text(encoding="utf-8"))
    scores = json.loads((DATA / cfg["scores"]).read_text(encoding="utf-8"))["scores"]
    cmap = {c["seq"]: c for c in cases["cases"]}
    return impact, scores, cmap


def result_of(h, a):
    return "win" if h > a else ("loss" if h < a else "draw")


def build_matches(impact, scores, cmap):
    """按场聚合 -> 每场: cases, items, actual, corrected, 每支受影响球队的结果判定"""
    matches = {}
    for seq_s, imp in impact["impacts"].items():
        seq = int(seq_s)
        # 归一化兜底：数据层应已存标准名（test_integrity 强制），这里再保一道，
        # 防未来泄漏导致页面查不到队徽、与 season 页队名不一致
        home, away = normalize_name(imp["home"]), normalize_name(imp["away"])
        key = f"{imp['league']}|{imp['round']}|{home}|{away}"
        m = matches.setdefault(key, {
            "league": imp["league"], "round": imp["round"], "home": home,
            "away": away, "match_note": imp.get("match_note", ""),
            "cases": [], "items": [], "seqs": [],
        })
        for it in imp["items"]:
            it = dict(it, seq=seq, team=normalize_name(it["team"]))
            m["items"].append(it)
        m["seqs"].append(seq)
        m["cases"].append(f"期{imp['issue']:02d}判例{imp['case_no']}")

    for key, m in matches.items():
        sc = scores.get(key)
        m["score"] = {"h": sc["h"], "a": sc["a"], "source": sc.get("source", ""),
                      "date": sc.get("date", ""), "note": sc.get("note", "")} if sc else None
        if not m["score"]:
            for t in {i["team"] for i in m["items"]}:
                m.setdefault("status", {})[t] = "pending"
                m.setdefault("corrected", {})[t] = None
            continue
        h_c, a_c = m["score"]["h"], m["score"]["a"]
        for it in m["items"]:
            df, do = GOAL_DELTA.get(it["type"], (0, 0))
            if it["team"] == m["home"]:
                h_c += df
                a_c += do
            else:
                a_c += df
                h_c += do
        m["corrected_score"] = (h_c, a_c)
        act_res = result_of(m["score"]["h"], m["score"]["a"])
        cor_res = result_of(h_c, a_c)
        has_opp_factor = any(i["type"] in (
            "missed_penalty", "wrong_penalty_against", "missed_red_opponent",
            "wrong_red_self", "missed_yellow_opponent", "wrong_yellow_self",
            "wrong_foul_called_self", "missed_foul_called", "wrong_offside_self")
            for i in m["items"])
        for t in {i["team"] for i in m["items"]}:
            act_pts = {"win": 3, "draw": 1, "loss": 0}[
                "win" if (act_res == "win" and t == m["home"]) or
                         (act_res == "loss" and t == m["away"]) else
                "loss" if (act_res == "loss" and t == m["home"]) or
                          (act_res == "win" and t == m["away"]) else "draw"]
            cor_pts = {"win": 3, "draw": 1, "loss": 0}[
                "win" if (cor_res == "win" and t == m["home"]) or
                         (cor_res == "loss" and t == m["away"]) else
                "loss" if (cor_res == "loss" and t == m["home"]) or
                          (cor_res == "win" and t == m["away"]) else "draw"]
            own = [i for i in m["items"] if i["team"] == t]
            if cor_pts > act_pts:
                st = "changed"
            elif cor_pts == act_pts and act_pts == 3:
                st = "no_change_win"       # 本队仍获胜
            elif cor_pts == act_pts and has_opp_factor and abs(h_c - a_c) <= 1:
                st = "possible"            # 存在影响可能（机会因素+分差小）
            else:
                st = "no_change"
            m.setdefault("status", {})[t] = st
            m.setdefault("corrected_for", {})[t] = (h_c, a_c, own)
    return matches


def team_stats(matches, view):
    """view='victim' 受损 / 'benefit' 获益"""
    teams = {}
    for key, m in matches.items():
        for it in m["items"]:
            victim = it["team"]
            benefit = m["away"] if victim == m["home"] else m["home"]
            team = victim if view == "victim" else benefit
            t = teams.setdefault(team, {
                "leagues": set(), "cases": 0, "matches": set(), "types": {},
                "result": {"changed": 0, "possible": 0, "no_change": 0,
                           "no_change_win": 0, "pending": 0},
                "detail": [], "swing": 0, "match_status": {},
            })
            t["leagues"].add(LEAGUE_SHORT[m["league"]])
            t["cases"] += 1
            t["matches"].add(key)
            t["types"][it["type"]] = t["types"].get(it["type"], 0) + 1
            if it["type"] in GOAL_DELTA:
                t["swing"] += 1
            st = m["status"].get(victim, "pending")
            t["match_status"][key] = st  # 按场次去重计数
            t["detail"].append({
                "seq": it["seq"], "league": LEAGUE_SHORT[m["league"]],
                "round": m["round"], "home": m["home"], "away": m["away"],
                "opp": benefit if view == "victim" else victim,
                "score": m["score"], "corrected": m.get("corrected_score"),
                "corrected_for": m.get("corrected_for", {}).get(victim),
                "status": st, "type": it["type"], "note": it["note"],
                "issue": None, "match_note": m.get("match_note", ""),
            })
    for t in teams.values():
        t["leagues"] = sorted(t["leagues"])
        t["n_matches"] = len(t["matches"])
        del t["matches"]
        for st in t["match_status"].values():
            t["result"][st] += 1
        del t["match_status"]
        t["detail"].sort(key=lambda d: (d["league"],
                                        d["round"] if isinstance(d["round"], int) else 9999,
                                        d["seq"]))
    return teams


def build_data(season):
    impact, scores, cmap = load(season)
    matches = build_matches(impact, scores, cmap)
    victims = team_stats(matches, "victim")
    benefits = team_stats(matches, "benefit")
    catalog = load_catalog()
    teams = {item["name"]: item for item in catalog.values()}

    # 补充期数信息用于链接展示
    cases = json.loads((DATA / SEASONS[season]["cases"]).read_text(encoding="utf-8"))["cases"]
    cmap2 = {c["seq"]: c for c in cases}
    for view_teams in (victims, benefits):
        for t in view_teams.values():
            for d in t["detail"]:
                c = cmap2[d["seq"]]
                d["issue"] = c["issue"]
                d["case_no"] = c["no"]

    n_items = sum(len(m["items"]) for m in matches.values())
    overview = {
        "cases": sum(len(m["seqs"]) for m in matches.values()),
        "matches": len(matches),
        "items": n_items,
        "swing": sum(1 for m in matches.values() for i in m["items"]
                     if i["type"] in GOAL_DELTA),
        "red": sum(1 for m in matches.values() for i in m["items"]
                   if i["type"] in ("missed_red_opponent", "wrong_red_self")),
        "yellow": sum(1 for m in matches.values() for i in m["items"]
                      if i["type"] in ("missed_yellow_opponent", "wrong_yellow_self")),
        "penalty": sum(1 for m in matches.values() for i in m["items"]
                       if i["type"] in ("missed_penalty", "wrong_penalty_against")),
        "changed": sum(1 for m in matches.values()
                       for t, s in m["status"].items() if s == "changed"),
        "possible": sum(1 for m in matches.values()
                        for t, s in m["status"].items() if s == "possible"),
        "teams": len(victims),
    }
    type_counts = {}
    for m in matches.values():
        for i in m["items"]:
            type_counts[i["type"]] = type_counts.get(i["type"], 0) + 1

    return {
        "built": date.today().isoformat(),
        "season": season,
        "page": SEASONS[season]["page"],
        "issueDesc": SEASONS[season]["issueDesc"],
        "overview": overview,
        "typeCounts": type_counts,
        "typeOrder": TYPE_ORDER,
        "typeLabels": TYPE_LABEL,
        "typeLabelsBenefit": TYPE_LABEL_BENEFIT,
        "victims": victims,
        "benefits": benefits,
        "crests": {}, "teams": teams,
        "scoreSource": json.loads((DATA / SEASONS[season]["scores"])
                                  .read_text(encoding="utf-8"))["note"],
    }


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__SEASON__赛季错漏判影响统计 · 各队得失盘点</title>
<style>
/* ===== stats 页专属布局 (颜色/组件来自 data-cfa-theme 设计系统) ===== */
.page-head{border-bottom:1px solid var(--line);background:var(--bg2)}
.page-head .wrap{padding-top:22px;padding-bottom:18px}
.page-head h1{margin:0 0 4px;font-family:var(--font-display);font-size:24px;letter-spacing:.4px}
.page-head .sub{color:var(--muted);font-size:13.5px}
.page-head .sub a{color:var(--brand);text-decoration:none}
.page-head .sub a:hover{text-decoration:underline}
.wrap{max-width:1180px;margin:0 auto;padding:0 16px}
.statbar{display:grid;grid-template-columns:repeat(auto-fit,minmax(128px,1fr));gap:10px;margin-top:16px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);
  padding:10px 14px;box-shadow:var(--shadow-sm);
  animation:fadeUp .4s var(--ease) backwards}
.stat:nth-child(2){animation-delay:40ms}.stat:nth-child(3){animation-delay:80ms}
.stat:nth-child(4){animation-delay:120ms}.stat:nth-child(5){animation-delay:160ms}
.stat:nth-child(6){animation-delay:200ms}.stat:nth-child(7){animation-delay:240ms}
.stat:nth-child(8){animation-delay:280ms}
.stat b{display:block;font-family:var(--font-display);font-size:22px;line-height:1.3;color:var(--brand);font-variant-numeric:tabular-nums}
.stat.hot b{color:var(--red)}
.stat span{font-size:12px;color:var(--muted)}
.controls{position:sticky;top:var(--top-h);z-index:50;background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:10px 0}
.row{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:999px;background:var(--card);padding:3px;gap:3px}
.viewbtn{padding:6px 18px;border-radius:999px;border:none;background:none;cursor:pointer;
  font-size:14px;color:var(--muted);font-family:inherit;transition:.15s}
.viewbtn.on{background:var(--brand-strong);color:var(--on-brand);font-weight:600}
.lg-chip{padding:5px 14px;border-radius:999px;border:1px solid var(--line);background:var(--card);
  cursor:pointer;font-size:13px;color:var(--ink2);font-family:inherit;transition:.15s}
.lg-chip.on{border-color:var(--brand);color:var(--brand);background:var(--info-bg);font-weight:600}
.lg-label{color:var(--muted);font-size:13px}
main{padding:20px 0 60px}
.note{background:var(--card);border:1px dashed var(--line);border-radius:var(--r-md);
  padding:10px 14px;color:var(--ink2);font-size:13.5px;line-height:1.9;margin-bottom:20px}
.note b{color:var(--brand)}
.teamcard{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:15px 18px;margin-bottom:13px;box-shadow:var(--shadow-sm);transition:border-color .15s;
  animation:fadeUp .4s var(--ease) backwards;animation-delay:calc(var(--i,0)*30ms)}
.teamcard:hover{border-color:var(--brand)}
.thead{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline;cursor:pointer;user-select:none}
.thead h3{margin:0;font-size:18px;display:flex;align-items:center}
.thead .crest{background:#fff;border-radius:4px;height:24px}
.thead .lg{font-size:12.5px;color:var(--brand);background:var(--info-bg);border-radius:6px;padding:1px 9px}
.thead .tot{color:var(--muted);font-size:13.5px}
.thead .arrow{margin-left:auto;color:var(--faint);transition:transform .15s;font-size:12px}
.teamcard.open .thead .arrow{transform:rotate(180deg)}
.tchips{display:flex;flex-wrap:wrap;gap:6px;margin-top:11px}
.tchip{font-size:12.5px;border-radius:6px;padding:2px 9px;border:1px solid transparent}
.tc-goal{background:var(--red-bg);color:var(--red);border-color:var(--red-line)}
.tc-pen{background:var(--amber-bg);color:var(--amber);border-color:var(--amber-line)}
.tc-red{background:var(--red-bg);color:var(--red);border-color:var(--red-line);font-weight:600}
.tc-yellow{background:var(--amber-bg);color:var(--amber);border-color:var(--amber-line)}
.tc-foul{background:var(--card2);color:var(--muted);border-color:var(--line)}
.tres{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;font-size:13px}
.rbadge{border-radius:6px;padding:2px 10px}
.r-changed{background:var(--red-bg);color:var(--red);border:1px solid var(--red-line);font-weight:600}
.r-possible{background:var(--amber-bg);color:var(--amber);border:1px solid var(--amber-line)}
.r-nochange{background:var(--green-bg);color:var(--green);border:1px solid var(--green-line)}
.r-pending{background:var(--card2);color:var(--muted);border:1px solid var(--line)}
.detail{display:none;margin-top:14px;border-top:1px dashed var(--line);padding-top:12px}
.teamcard.open .detail{display:block;animation:fadeUp var(--t-med) var(--ease)}
.drow{padding:9px 0;border-bottom:1px solid var(--line2);font-size:14px;display:flex;flex-wrap:wrap;gap:4px 8px;align-items:baseline}
.drow:last-child{border-bottom:none}
.drow .mt{font-weight:600}
.drow .sc{color:var(--brand);font-weight:600}
.drow .corr{color:var(--red);font-weight:600}
.drow .badge{display:inline-block;font-size:12px;border-radius:5px;padding:0 8px;
  background:var(--card2);color:var(--muted);border:1px solid var(--line2)}
.drow .note{display:block;flex-basis:100%;font-size:13px;color:var(--muted);margin-top:2px}
.drow a{color:var(--brand);text-decoration:none;font-size:12.5px;white-space:nowrap}
.drow a:hover{text-decoration:underline}
footer{background:var(--top-bg);color:var(--top-muted);padding:24px 0;font-size:13px;line-height:1.9}
footer b{color:var(--top-ink)}
footer a{color:var(--brand)}
.noresult{padding:40px;text-align:center;color:var(--muted)}
.top-btn{position:fixed;right:20px;bottom:24px;display:inline-flex;align-items:center;gap:6px;
  background:var(--brand-strong);color:var(--on-brand);border:none;border-radius:999px;
  padding:10px 17px;font-size:13.5px;cursor:pointer;box-shadow:var(--shadow-sm)}
@media (max-width:640px){
  .page-head h1{font-size:18px}
  .stat b{font-size:18px}
  .teamcard{padding:12px 13px}
  .thead h3{font-size:16px}
}
</style>
</head>
<body class="page-stats">
__TOPBAR__
<header class="page-head">
  <div class="wrap">
    <h1>__SEASON__赛季官方认定错漏判 · 各队得失盘点</h1>
    <div class="sub">
      仅统计男子中超/中甲/中乙/足协杯 · 依据评议组认定结论与最终比分修正比对 ·
      数据生成于 __BUILT__ · <a href="__PAGE__">← 返回判例合集</a>
    </div>
    <div class="statbar" id="statbar"></div>
  </div>
</header>

<div class="controls">
  <div class="wrap">
    <div class="row">
      <span class="seg" role="group" aria-label="视角切换">
        <button class="viewbtn on" id="btnVictim" aria-pressed="true">受损方视角</button>
        <button class="viewbtn" id="btnBenefit" aria-pressed="false">获益方视角</button>
      </span>
      <span class="lg-label">按联赛筛选：</span>
      <button class="lg-chip on" data-lg="" aria-pressed="true">全部</button>
      <button class="lg-chip" data-lg="中超">中超</button>
      <button class="lg-chip" data-lg="中甲">中甲</button>
      <button class="lg-chip" data-lg="中乙">中乙</button>
      <button class="lg-chip" data-lg="足协杯">足协杯</button>
    </div>
  </div>
</div>

<main class="wrap">
  <div class="note">
    <b>统计口径：</b>①仅计入评议组明确认定的错漏判（支持原判与不予认定的不计）；②「确定得失球」修正仅含进球判定类错误——被漏判的进球（认定应有效）计为本队应得1球、被错判有效的对方进球计为对方应扣除1球；③点球不折算进球，计为「机会因素」；④红黄牌类错误全部计入，无论是否影响比分；⑤「结果或被改变」＝修正比分后该队积分提高（如负变平、平变胜）；「存在影响可能」＝修正后积分不变，但另有漏判点球/红牌等机会因素且分差≤1；⑥同一比赛多个错漏判先合并再判定；⑦本页不推算积分榜连锁影响。
  </div>
  <div id="teamList"></div>
  <div class="noresult" id="noResult" style="display:none">该联赛下没有数据。</div>
</main>

<footer>
  <div class="wrap">
    <p><b>数据来源：</b>判例与认定结论来自中国足协官网裁判评议（__ISSUEDESC__，详见
      <a href="__PAGE__">判例合集</a>）；最终比分来自公开赛程赛果检索核对（懂球帝、直播吧、新华社、中新网、俱乐部官网等），缺失比分以「待补」标注。</p>
    <p id="scoreNote"></p>
    <p><b>声明：</b>本页为教学研究用途的客观盘点，错漏判认定权属于中国足协裁判委员会评议组；比分修正为假设性推演，仅用于说明判罚影响的量级与方向。</p>
  </div>
</footer>
<button class="top-btn" id="btnTop">回到顶部</button>

<script>
const DATA = __DATA__;
const IC = __ICONS__;
const TL = DATA.typeLabels, TLB = DATA.typeLabelsBenefit, ORDER = DATA.typeOrder;

// ---------- 总览 ----------
document.getElementById("statbar").innerHTML = [
  `<div class="stat"><b>${DATA.overview.cases}</b><span>错漏判例数</span></div>`,
  `<div class="stat"><b>${DATA.overview.matches}</b><span>涉及比赛</span></div>`,
  `<div class="stat"><b>${DATA.overview.teams}</b><span>涉及球队</span></div>`,
  `<div class="stat"><b>${DATA.overview.swing}</b><span>确定得失球修正</span></div>`,
  `<div class="stat"><b>${DATA.overview.penalty}</b><span>点球机会因素</span></div>`,
  `<div class="stat"><b>${DATA.overview.red} / ${DATA.overview.yellow}</b><span>红牌 / 黄牌错误</span></div>`,
  `<div class="stat"><b>${DATA.overview.changed}</b><span>结果或被改变的判定</span></div>`,
  `<div class="stat"><b>${DATA.overview.possible}</b><span>存在影响可能</span></div>`,
].join("");
// 数字滚动: 只滚纯数字项 (reduced-motion 直出终值; CSS 全局熄火再兜底)
const _rm = matchMedia("(prefers-reduced-motion: reduce)").matches;
document.querySelectorAll("#statbar .stat b").forEach(el=>{
  const txt = el.textContent;
  if (_rm || !/^\d+$/.test(txt)) return;
  const end = parseInt(txt, 10), t0 = performance.now(), dur = 650;
  (function tick(t){
    const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    el.textContent = String(Math.round(end * e));
    if (p < 1) requestAnimationFrame(tick); else el.textContent = txt;
  })(t0);
});
document.getElementById("scoreNote").innerHTML = "<b>比分来源说明：</b>" + DATA.scoreSource;

const TC = {
  "denied_goal":"tc-goal","opp_goal_should_disallow":"tc-goal",
  "missed_penalty":"tc-pen","wrong_penalty_against":"tc-pen",
  "missed_red_opponent":"tc-red","wrong_red_self":"tc-red",
  "missed_yellow_opponent":"tc-yellow","wrong_yellow_self":"tc-yellow",
  "wrong_foul_called_self":"tc-foul","missed_foul_called":"tc-foul","wrong_offside_self":"tc-foul"};
const RS = {
  changed:['r-changed','结果或被改变'],
  possible:['r-possible','存在影响可能'],
  no_change:['r-nochange','未改变结果'],
  no_change_win:['r-nochange','未改变结果（本队仍获胜）'],
  pending:['r-pending','比分待补']};

let curView = 'victims', curLg = '';

function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
  .replace(/"/g,"&quot;").replace(/'/g,"&#39;")}

function chip(t, n, benefit){
  if(!n) return "";
  const label = (benefit?TLB:TL)[t];
  return `<span class="tchip ${TC[t]}">${label} ×${n}</span>`;
}

function renderTeam(name, t, idx){
  const chips = ORDER.map(k=>chip(k, t.types[k]||0, curView==='benefits')).join("");
  const r = t.result;
  const rbadges = [
    r.changed?`<span class="rbadge r-changed">结果或被改变 ×${r.changed}</span>`:"",
    r.possible?`<span class="rbadge r-possible">存在影响可能 ×${r.possible}</span>`:"",
    (r.no_change+r.no_change_win)?`<span class="rbadge r-nochange">未改变结果 ×${r.no_change+r.no_change_win}</span>`:"",
    r.pending?`<span class="rbadge r-pending">比分待补 ×${r.pending}</span>`:""
  ].join("");
  const rows = t.detail.map(d=>{
    let corrLine = "";
    if(d.score && (d.status==='changed'||d.status==='no_change')
       && (d.corrected[0]!==d.score.h || d.corrected[1]!==d.score.a)){
      const c = d.corrected;
      corrLine = ` <span class="corr">修正比分 ${c[0]}:${c[1]}</span>`;
    }
    const label = (curView==='benefits'?TLB:TL)[d.type];
    return `<div class="drow">
      <span class="badge">${d.league}${typeof d.round==="number" ? "第"+d.round+"轮" : "·"+d.round}</span>
      <span class="mt">${esc(d.home)} ${d.score?d.score.h+" : "+d.score.a:"—"} ${esc(d.away)}</span>
      ${d.match_note?`<span class="badge">${esc(d.match_note)}</span>`:""}
      ${corrLine}
      <span class="badge">${label}</span>
      <a href="${DATA.page}#case-${d.seq}" target="_blank">期${String(d.issue).padStart(2,'0')}判例${d.case_no} ↗</a>
      <span class="note">${esc(d.note)}</span>
    </div>`;
  }).join("");
  const inLg = !curLg || t.leagues.includes(curLg);
  const sortKey = -(t.swing*1000 + t.cases);
  const team = DATA.teams && DATA.teams[name];
  const crest = team && team.status === 'verified' && team.path
    ? `<img class="crest" src="${team.path}" alt="${esc(name)}队徽" style="height:24px;vertical-align:-5px;margin-right:6px">`
    : `<span class="team-dot" style="width:22px;height:22px;background:${(team&&team.bg)||'#e9f2fb'};border:1px solid ${(team&&team.fg)||'#0b4c8c'}" title="${esc(name)}：队徽待核验" aria-label="${esc(name)}"></span>`;
  return `<div class="teamcard" data-lg='${JSON.stringify(t.leagues)}' data-sort="${sortKey}" style="${inLg?'':'display:none'};--i:${Math.min(idx||0,12)}">
    <div class="thead" onclick="this.parentElement.classList.toggle('open')">
      <h3>${crest}${esc(name)}</h3>
      <span class="lg">${t.leagues.join(" / ")}</span>
      <span class="tot">错漏判 ${t.cases} 例 · ${t.n_matches} 场</span>
      <span class="arrow">${IC["chev-d"]}</span>
    </div>
    <div class="tchips">${chips}</div>
    <div class="tres">${rbadges}</div>
    <div class="detail">${rows}</div>
  </div>`;
}

function render(){
  const data = DATA[curView];
  const names = Object.keys(data).sort((a,b)=>{
    const A=data[a], B=data[b];
    return (B.swing*1000+B.cases) - (A.swing*1000+A.cases) || a.localeCompare(b);
  });
  document.getElementById("teamList").innerHTML =
    names.map((n,idx)=>renderTeam(n, data[n], idx)).join("") ||
    `<div class="noresult">该联赛下没有数据。</div>`;
}

document.getElementById("btnVictim").onclick = e=>{
  curView='victims';
  e.target.classList.add('on'); e.target.setAttribute('aria-pressed','true');
  const b=document.getElementById('btnBenefit');
  b.classList.remove('on'); b.setAttribute('aria-pressed','false');
  render();
};
document.getElementById("btnBenefit").onclick = e=>{
  curView='benefits';
  e.target.classList.add('on'); e.target.setAttribute('aria-pressed','true');
  const v=document.getElementById('btnVictim');
  v.classList.remove('on'); v.setAttribute('aria-pressed','false');
  render();
};
document.getElementById("btnTop").onclick = ()=>scrollTo({top:0,behavior:'smooth'});
document.querySelectorAll(".lg-chip").forEach(b=>{
  b.onclick = ()=>{
    curLg = b.dataset.lg;
    document.querySelectorAll(".lg-chip").forEach(x=>x.classList.toggle('on', x===b));
    document.querySelectorAll(".teamcard").forEach(c=>{
      const lgs = JSON.parse(c.dataset.lg);
      c.style.display = (!curLg || lgs.includes(curLg)) ? "" : "none";
    });
  };
});

render();
</script>
</body>
</html>
"""


def build_season(season):
    cfg = SEASONS[season]
    data = build_data(season)
    tb = topbar(active=cfg["out"], stats=cfg["out"], brand_sub=f"{season}赛季 · 得失盘点",
                seasons=tuple(sorted(SEASONS)))
    html = inject_theme(HTML.replace("__DATA__",
                        # "</" 转义为合法 JSON 的 "<\/"，防正文提前闭合 </script>
                        json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
                        .replace("__ICONS__", js_icons())
                        .replace("__TOPBAR__", tb))
    html = (html.replace("__SEASON__", season)
                .replace("__PAGE__", cfg["page"])
                .replace("__ISSUEDESC__", cfg["issueDesc"])
                .replace("__BUILT__", date.today().isoformat()))
    SITE.mkdir(parents=True, exist_ok=True)
    out = SITE / cfg["out"]
    out.write_text(html, encoding="utf-8")
    ov = data["overview"]
    print(f"[{season}] 生成 {out} ({len(html.encode('utf-8'))/1024:.0f} KB)")
    print(f"  总览: {ov['cases']}例 / {ov['matches']}场 / {ov['teams']}队 / "
          f"确定得失球{ov['swing']} / 点球{ov['penalty']} / 红{ov['red']}黄{ov['yellow']} / "
          f"或改变{ov['changed']} / 可能{ov['possible']}")
    print("  类型分布:", data["typeCounts"])


def main():
    seasons = sys.argv[1:] or ["2026", "2025", "2024"]
    for season in seasons:
        if season not in SEASONS:
            raise SystemExit(f"未知赛季: {season}（可选: {'/'.join(SEASONS)}）")
        build_season(season)


if __name__ == "__main__":
    main()
