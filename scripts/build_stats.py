# -*- coding: utf-8 -*-
"""生成错漏判影响统计页 stats-2025.html / stats-2024.html（单文件离线可用）
用法: python build_stats.py [2025] [2024]   # 不带参数=两个赛季都构建
数据: data/cases-{s}.json + data/impact[-{s}].json + data/match[-]scores[-{s}].json
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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SEASONS = {
    "2025": {
        "cases": "cases-2025.json", "impact": "impact.json",
        "scores": "match_scores.json",
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
                "中国足协杯": "足协杯", "足协杯": "足协杯"}
TYPE_ORDER = ["denied_goal", "opp_goal_should_disallow", "missed_penalty",
              "wrong_penalty_against", "missed_red_opponent", "wrong_red_self",
              "missed_yellow_opponent", "wrong_yellow_self",
              "wrong_foul_called_self", "missed_foul_called", "wrong_offside_self"]


def load(season):
    cfg = SEASONS[season]
    cases = json.loads((ROOT / "data" / cfg["cases"]).read_text(encoding="utf-8"))
    impact = json.loads((ROOT / "data" / cfg["impact"]).read_text(encoding="utf-8"))
    scores = json.loads((ROOT / "data" / cfg["scores"]).read_text(encoding="utf-8"))["scores"]
    cmap = {c["seq"]: c for c in cases["cases"]}
    return impact, scores, cmap


def result_of(h, a):
    return "win" if h > a else ("loss" if h < a else "draw")


def build_matches(impact, scores, cmap):
    """按场聚合 -> 每场: cases, items, actual, corrected, 每支受影响球队的结果判定"""
    matches = {}
    for seq_s, imp in impact["impacts"].items():
        seq = int(seq_s)
        key = f"{imp['league']}|{imp['round']}|{imp['home']}|{imp['away']}"
        m = matches.setdefault(key, {
            "league": imp["league"], "round": imp["round"], "home": imp["home"],
            "away": imp["away"], "match_note": imp.get("match_note", ""),
            "cases": [], "items": [], "seqs": [],
        })
        for it in imp["items"]:
            it = dict(it, seq=seq)
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
        t["detail"].sort(key=lambda d: (d["league"], d["round"], d["seq"]))
    return teams


def build_data(season):
    impact, scores, cmap = load(season)
    matches = build_matches(impact, scores, cmap)
    victims = team_stats(matches, "victim")
    benefits = team_stats(matches, "benefit")
    crest_path = ROOT / "data" / "crests.json"
    crests = json.loads(crest_path.read_text(encoding="utf-8")) if crest_path.exists() else {}

    issues = {i["no"]: i for i in impact.get("issues", [])} if "issues" in impact else {}
    # 补充期数信息用于链接展示
    cases = json.loads((ROOT / "data" / SEASONS[season]["cases"]).read_text(encoding="utf-8"))["cases"]
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
        "crests": crests,
        "scoreSource": json.loads((ROOT / "data" / SEASONS[season]["scores"])
                                  .read_text(encoding="utf-8"))["note"],
    }


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__SEASON__赛季错漏判影响统计 · 各队得失盘点</title>
<style>
:root{
  --bg:#f4f6f9; --card:#fff; --ink:#1c2733; --muted:#5c6b7a; --line:#e3e9f0;
  --brand:#0b4c8c; --brand2:#1266b5;
  --red:#c0392b; --redbg:#fdeceb; --green:#1e7e34; --greenbg:#e9f6ec;
  --amber:#9a6700; --amberbg:#fff5e0; --blue:#1266b5; --bluebg:#eef4fb;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Microsoft YaHei","PingFang SC","Segoe UI",system-ui,sans-serif;
  font-size:16px;line-height:1.75}
header.top{background:linear-gradient(135deg,#0b3d73,#0b4c8c 55%,#1266b5);color:#fff;
  padding:26px 20px 20px}
.wrap{max-width:1180px;margin:0 auto;padding:0 16px}
header.top h1{margin:0 0 6px;font-size:25px;letter-spacing:1px}
header.top .sub{color:#cfe2f5;font-size:14px}
header.top .sub a{color:#ffd9a0;text-decoration:none}
.statbar{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}
.stat{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.22);
  border-radius:10px;padding:8px 14px;min-width:104px}
.stat b{display:block;font-size:22px;line-height:1.25}
.stat span{font-size:12.5px;color:#d7e7f7}
.controls{position:sticky;top:0;z-index:50;background:#ffffffee;backdrop-filter:blur(6px);
  border-bottom:1px solid var(--line);padding:10px 0}
.row{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.viewbtn{padding:8px 20px;border-radius:20px;border:1px solid #cbd5e1;background:#fff;
  cursor:pointer;font-size:15px;color:var(--muted)}
.viewbtn.on{background:var(--brand);border-color:var(--brand);color:#fff}
.lg-chip{padding:6px 14px;border-radius:8px;border:1px solid var(--line);background:#fff;
  cursor:pointer;font-size:14px;color:var(--ink)}
.lg-chip.on{border-color:var(--brand2);color:var(--brand2);background:var(--bluebg)}
main{padding:20px 0 60px}
.note{background:var(--card);border:1px dashed #b8cada;border-radius:10px;padding:10px 14px;
  color:#33475b;font-size:14.5px;margin-bottom:20px}
.note b{color:var(--brand)}
.teamcard{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px;margin-bottom:14px;box-shadow:0 1px 3px rgba(15,40,80,.05)}
.thead{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline;cursor:pointer}
.thead h3{margin:0;font-size:19px}
.thead .crest{background:#fff;border-radius:4px}
.thead .lg{font-size:13px;color:var(--brand2);background:var(--bluebg);
  border-radius:6px;padding:1px 8px}
.thead .tot{color:var(--muted);font-size:14px}
.tchips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.tchip{font-size:13px;border-radius:6px;padding:2px 9px;border:1px solid transparent}
.tc-goal{background:var(--redbg);color:var(--red);border-color:#f2c4bf}
.tc-pen{background:var(--amberbg);color:var(--amber);border-color:#ecd9a0}
.tc-red{background:#fbe3e0;color:var(--red);border-color:#f2c4bf;font-weight:600}
.tc-yellow{background:#fff8dc;color:#8a6d00;border-color:#ecd9a0}
.tc-foul{background:#f1f5f9;color:var(--muted);border-color:var(--line)}
.tres{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;font-size:13.5px}
.rbadge{border-radius:6px;padding:2px 10px}
.r-changed{background:var(--redbg);color:var(--red);border:1px solid #f2c4bf;font-weight:600}
.r-possible{background:var(--amberbg);color:var(--amber);border:1px solid #ecd9a0}
.r-nochange{background:var(--greenbg);color:var(--green);border:1px solid #bfe3c8}
.r-pending{background:#f1f5f9;color:var(--muted);border:1px solid var(--line)}
.detail{display:none;margin-top:14px;border-top:1px dashed var(--line);padding-top:12px}
.teamcard.open .detail{display:block}
.drow{padding:9px 0;border-bottom:1px solid var(--line);font-size:14.5px}
.drow:last-child{border-bottom:none}
.drow .mt{font-weight:600}
.drow .sc{color:var(--brand2);font-weight:600}
.drow .corr{color:var(--red);font-weight:600}
.drow .badge{display:inline-block;font-size:12.5px;border-radius:5px;padding:0 8px;
  margin-right:6px;background:#f1f5f9;color:var(--muted)}
.drow .note{display:block;font-size:13.5px;color:#4a5a6a;margin-top:2px}
.drow a{color:var(--brand2);text-decoration:none;font-size:13px}
.drow a:hover{text-decoration:underline}
footer{background:#0e1b2a;color:#9db4c9;padding:22px 0;font-size:13.5px}
footer a{color:#7fb3e0}
.noresult{padding:40px;text-align:center;color:var(--muted)}
.top-btn{position:fixed;right:22px;bottom:26px;background:var(--brand);color:#fff;
  border:none;border-radius:24px;padding:10px 18px;font-size:14px;cursor:pointer}
</style>
</head>
<body>
<header class="top">
  <div class="wrap">
    <h1>__SEASON__赛季官方认定错漏判 · 各队得失盘点</h1>
    <div class="sub">
      仅统计男子中超/中甲/中乙/足协杯 · 依据评议组认定结论与最终比分修正比对 ·
      <a href="index.html">🏠 首页</a> · <a href="season-2024.html">24评议</a> · <a href="season-2025.html">25评议</a> ·
      <a href="__PAGE__">← 返回判例合集</a> · <a href="rules.html">📖 竞赛规则</a> · 数据生成于 __BUILT__
    </div>
    <div class="statbar" id="statbar"></div>
  </div>
</header>

<div class="controls">
  <div class="wrap">
    <div class="row">
      <button class="viewbtn on" id="btnVictim">受损方视角</button>
      <button class="viewbtn" id="btnBenefit">获益方视角</button>
      <span style="color:var(--muted);font-size:13.5px">按联赛筛选：</span>
      <button class="lg-chip on" data-lg="">全部</button>
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
    <p><b>数据来源：</b>判例与认定结论来自中国足协官网裁判评议（${DATA.issueDesc}，详见
      <a href="${DATA.page}">判例合集</a>）；最终比分来自公开赛程赛果检索核对（懂球帝、直播吧、新华社、中新网、俱乐部官网等），缺失比分以「待补」标注。</p>
    <p id="scoreNote"></p>
    <p><b>声明：</b>本页为教学研究用途的客观盘点，错漏判认定权属于中国足协裁判委员会评议组；比分修正为假设性推演，仅用于说明判罚影响的量级与方向。</p>
  </div>
</footer>
<button class="top-btn" onclick="scrollTo({top:0,behavior:'smooth'})">回到顶部</button>

<script>
const DATA = __DATA__;
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

function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}

function chip(t, n, benefit){
  if(!n) return "";
  const label = (benefit?TLB:TL)[t];
  return `<span class="tchip ${TC[t]}">${label} ×${n}</span>`;
}

function renderTeam(name, t){
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
      <span class="badge">${d.league}第${d.round}轮</span>
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
  return `<div class="teamcard" data-lg='${JSON.stringify(t.leagues)}' data-sort="${sortKey}" style="${inLg?'':'display:none'}">
    <div class="thead" onclick="this.parentElement.classList.toggle('open')">
      <h3>${(DATA.crests&&DATA.crests[name])?`<img class="crest" src="${DATA.crests[name]}" style="height:24px;vertical-align:-5px;margin-right:6px">`:""}${esc(name)}</h3>
      <span class="lg">${t.leagues.join(" / ")}</span>
      <span class="tot">错漏判 ${t.cases} 例 · ${t.n_matches} 场</span>
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
    names.map(n=>renderTeam(n, data[n])).join("") ||
    `<div class="noresult">该联赛下没有数据。</div>`;
}

document.getElementById("btnVictim").onclick = e=>{
  curView='victims';
  e.target.classList.add('on');
  document.getElementById('btnBenefit').classList.remove('on');
  render();
};
document.getElementById("btnBenefit").onclick = e=>{
  curView='benefits';
  e.target.classList.add('on');
  document.getElementById('btnVictim').classList.remove('on');
  render();
};
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
    html = HTML.replace("__DATA__",
                        json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    html = (html.replace("__SEASON__", season)
                .replace("__PAGE__", cfg["page"])
                .replace("__BUILT__", date.today().isoformat()))
    out = ROOT / cfg["out"]
    out.write_text(html, encoding="utf-8")
    ov = data["overview"]
    print(f"[{season}] 生成 {out} ({len(html.encode('utf-8'))/1024:.0f} KB)")
    print(f"  总览: {ov['cases']}例 / {ov['matches']}场 / {ov['teams']}队 / "
          f"确定得失球{ov['swing']} / 点球{ov['penalty']} / 红{ov['red']}黄{ov['yellow']} / "
          f"或改变{ov['changed']} / 可能{ov['possible']}")
    print("  类型分布:", data["typeCounts"])


def main():
    seasons = sys.argv[1:] or ["2025", "2024"]
    for season in seasons:
        if season not in SEASONS:
            raise SystemExit(f"未知赛季: {season}（可选: {'/'.join(SEASONS)}）")
        build_season(season)


if __name__ == "__main__":
    main()
