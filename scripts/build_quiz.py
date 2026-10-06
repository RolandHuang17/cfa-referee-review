# -*- coding: utf-8 -*-
"""考题模式 → site/quiz.html（三赛季判例 + 统一尺度场景 随机出题、判分、错题本）。

题库（build_bank）：
  - 赛季判例：video_files 非空且 conclusion 非空（592 题，含 17 题「证据不足不予认定」）；
    结构化正确答案取自 data/quiz-answers.json（gen_quiz_answers.py 产物，仅收 reviewed 条目，
    未复核或无条目的题只出「复核结论」一问）。
  - 尺度场景：data/scale.json 全部含视频场景（剔除「VAR 机制讲解」伪矩阵项），
    官方 decision 矩阵多选判分。

判分：判例题复核结论 1 分 + 判罚决定 1 分（有答案时）+ 纪律处分 1 分（有答案时）；
尺度题满分 2 分（矩阵完全一致 2 / 无错选有漏选 1 / 有错选 0）。
错题本：localStorage cfa.quiz.wrong（未满分自动记入，含上次错选），导出/导入 JSON。
视频：本地相对路径 → onerror 换官方直链（CDN 拒 Referer，必须 no-referrer）→ 提示条；
轻量版（cfa.lite）不出视频窗口，改官方链接。
"""
import json
from datetime import date

from lib.crest_catalog import load_catalog, normalize_team
from lib.paths import DATA, IFAB_JSON, IFAB_ZH_JSON, SCALE_JSON, SITE
from lib.theme import icon, inject_theme, js_icons, topbar

WRONG_KEY = "cfa.quiz.wrong"
# 与 build_scale.DECISION_ORDER 保持一致的展示顺序
DECISION_ORDER = ["不犯规", "间接任意球", "直接任意球", "罚球点球", "不出牌", "黄牌", "红牌",
                  "不越位犯规", "干扰比赛", "越位犯规", "干扰对方队员", "越位位置获得利益"]
R_OPTIONS = [("playon", "不犯规（比赛继续）"), ("directfk", "直接任意球"), ("indirectfk", "间接任意球"),
             ("penalty", "罚球点球"), ("retake", "重罚球点球"), ("goal_valid", "进球有效"),
             ("goal_invalid", "进球无效")]
C_OPTIONS = [("none", "不出牌"), ("yellow", "黄牌"), ("red", "红牌")]
V_OPTIONS = [("correct", "支持原判"), ("wrong", "判罚错误"), ("pending", "证据不足不予认定")]
COMP_ALIAS = {"中超": "中超联赛", "中甲": "中甲联赛", "中乙": "中乙联赛",
              "女超": "女超联赛", "女甲": "女甲联赛", "运动会": "全运会"}
# VAR 协议题干扰项映射（人工指定：每题 4 选项、ans=正确项下标；正确项全部为官方答案）
VAR_OPTS = {
    "q1": {"ans": 0, "opts": [
        "可以——该黄牌（非第二张黄牌）可回看确认犯规球员身份，黄牌取消并改判 B 队直接任意球",
        "不可以——黄牌判罚一律不可回看，维持原判",
        "可以，但 VAR 只能提示裁判员注意，原判不可更改",
        "可以——直接取消黄牌并判给 A 队点球"]},
    "q2": {"ans": 1, "opts": [
        "不可以——由第二张黄牌引发的红牌不可回看",
        "可以——明显错误的第二张黄牌可由 VAR 协助：红牌取消，假摔球员被警告，进攻方获间接任意球",
        "可以——直接改判进攻方点球",
        "可以——红牌维持，另补判进攻方间接任意球"]},
    "q3": {"ans": 0, "opts": [
        "不可以——VAR 只能纠正「明显错误的第二张黄牌」，不能补漏判第二张黄牌",
        "可以——这属于严重漏判事件，VAR 应建议回看",
        "可以——VAR 直接出示第二张黄牌并罚令出场",
        "不可以——除非裁判员已经出示了红牌"]},
    "q4": {"ans": 2, "opts": [
        "维持点球——回看后非清晰错误不得更改",
        "取消点球，改判防守方球门球",
        "取消点球，改判防守方间接任意球，假摔球员因非体育行为被警告（黄牌）",
        "取消点球，坠球恢复比赛"]},
    "q5": {"ans": 1, "opts": [
        "可以——任何改变比赛进程的判罚都可回看",
        "不可以——仅错罚对象，或与暴力行为、吐口水、咬人、极其攻击性/侮辱性言行相关的罚令出场事件例外",
        "可以——但只能更改纪律处分，不能更改重新开始方式",
        "不可以——比赛重新开始后一律不可回看"]},
    "q6": {"ans": 3, "opts": [
        "必须维持红牌——回看是为红牌发起的，不能降级",
        "由 VAR 决定最终出示红牌还是黄牌",
        "取消处罚但不补牌，比赛照常恢复",
        "以回看所见为准——若裁判员认为该犯规只值警告而非罚令出场，就必须出示黄牌"]},
    "q7": {"ans": 0, "opts": [
        "适用「仅 VAR 回看」——VAR 告知回放内容，裁判员做出电视信号手势后取消点球、改判防守方任意球",
        "必须进行场上回看（OFR）",
        "维持点球——罚球区内外的判断属于裁判员主观裁量",
        "取消点球，坠球恢复比赛"]},
    "q8": {"ans": 3, "opts": [
        "VAR 直接判罚点球并通知裁判员",
        "比赛继续——VAR 无权提示这类情形",
        "立即停止比赛并以坠球恢复",
        "裁判员在球下次进入中立区域/局面时停止比赛、做出电视信号手势，经场上回看（OFR）后再作最终决定"]},
    "q9": {"ans": 0, "opts": [
        "不可以——VAR 只能在裁判员已作出第一决定（包括允许比赛继续）之后使用",
        "可以——这属于「延迟吹罚」的正常执法形态",
        "可以——但仅限进球类判定",
        "不可以——VAR 只能应由队长申请使用"]},
    "q10": {"ans": 1, "opts": [
        "不允许——点球执行阶段的犯规不可回看",
        "允许——罚球点球时守门员和/或主罚队员犯规，裁判员可以获得 VAR 协助",
        "允许——但仅限主罚队员的犯规",
        "允许——且该进球必须判定有效"]},
    "q11": {"ans": 2, "opts": [
        "维持点球，并向防守队员出示黄牌",
        "取消点球，坠球恢复比赛",
        "取消点球，改判防守方间接任意球，假摔球员因非体育行为被警告（黄牌）",
        "取消点球，改判防守方球门球"]},
    "q12": {"ans": 1, "opts": [
        "黄牌维持——已出示的牌不可通过回看取消",
        "取消黄牌并改判点球；犯规的防守队员视情况被警告或罚令出场",
        "取消黄牌并改判点球，但不得再处罚防守队员",
        "维持比赛原样，赛后报告处理"]},
}


def _comp(c):
    comp = COMP_ALIAS.get(c.get("comp", ""), c.get("comp", ""))
    if comp:
        return comp
    for k, v in (("中超", "中超联赛"), ("中甲", "中甲联赛"), ("中乙", "中乙联赛"),
                 ("女超", "女超联赛"), ("女甲", "女甲联赛"), ("足协杯", "中国足协杯"),
                 ("运动会", "全运会")):
        if k in c.get("match_info", ""):
            return v
    return ""


def build_bank():
    answers = {}
    if (DATA / "quiz-answers.json").exists():
        answers = json.loads((DATA / "quiz-answers.json").read_text(encoding="utf-8")).get("answers", {})
    catalog = load_catalog()
    teams = {item["name"]: item for item in catalog.values()}
    bank = []
    for season in ("2026", "2025", "2024"):
        d = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        for c in d["cases"]:
            if not (c.get("video_files") and (c.get("conclusion") or "").strip()):
                continue
            item = {
                "k": f"{season}-{c['seq']}", "t": "case", "s": season,
                "issue": c["issue"], "no": c["no"], "seq": c["seq"],
                "comp": _comp(c), "round": c.get("round", ""),
                "home": normalize_team(c.get("home", "")), "away": normalize_team(c.get("away", "")),
                "minute": c.get("minute", ""), "desc": c["desc"], "appeal": c.get("appeal", ""),
                "concl": c["conclusion"], "v": c["referee_verdict"],
                "videos": c["video_files"], "vurls": c["video_urls"],
                "cat": c["category"], "catname": c.get("category_name", ""),
            }
            ans = answers.get(item["k"])
            if ans and ans.get("reviewed"):
                a = {}
                if ans.get("r"):
                    a["r"] = ans["r"]
                if ans.get("c"):
                    a["c"] = ans["c"]
                if a:
                    item["ans"] = a
            bank.append(item)
    n_scale = 0
    if SCALE_JSON.exists():
        sd = json.loads(SCALE_JSON.read_text(encoding="utf-8"))
        for year, ydata in sd.items():
            if not isinstance(ydata, dict) or "sections" not in ydata:
                continue
            for sec in ydata["sections"]:
                for g in sec["groups"]:
                    for it in g["items"]:
                        dec = it.get("decision") or []
                        if not dec or any(x.get("label") == "VAR 机制讲解" for x in dec):
                            continue
                        if not it.get("video"):
                            continue
                        bank.append({
                            "k": f"sc-{year}-{it['id']}", "t": "scale", "s": year,
                            "id": it["id"], "series": it["series"],
                            "title": it["title"], "group": g["name"],
                            "note": it.get("note", ""), "reason": it.get("reason", ""),
                            "varrule": it.get("varrule", ""),
                            "video": it["video"], "poster": it.get("poster", ""),
                            "dec": sorted(dec, key=lambda x: DECISION_ORDER.index(x["label"])
                                          if x["label"] in DECISION_ORDER else 99),
                        })
                        n_scale += 1
    # 第三题型：VAR 协议题（IFAB 协议 FAQ：场景 → 官方决定，四选一）
    n_var = 0
    if IFAB_JSON.exists():
        d = json.loads(IFAB_JSON.read_text(encoding="utf-8"))
        zh = {}
        if IFAB_ZH_JSON.exists():
            zh = json.loads(IFAB_ZH_JSON.read_text(encoding="utf-8")).get("faq", {})
        for q in d.get("faq", []):
            zq = zh.get(q["id"], {})
            cfg = VAR_OPTS.get(q["id"])
            if not cfg or not zq:
                continue
            bank.append({
                "k": f"var-{q['id']}", "t": "var", "s": "ifab",
                "qid": q["id"], "q": zq["q"], "q_en": q["q"],
                "a": zq["a"], "a_en": q["a"],
                "opts": cfg["opts"], "ans": cfg["ans"],
                "link": f"ifab.html#faq-{q['id']}",
            })
            n_var += 1
    return bank, teams, n_scale, n_var


def build_data():
    bank, teams, n_scale, n_var = build_bank()
    n_case = sum(1 for b in bank if b["t"] == "case")
    return {"cfg": {"wrongKey": WRONG_KEY, "built": date.today().isoformat()},
            "bank": bank, "teams": teams,
            "opts": {"r": R_OPTIONS, "c": C_OPTIONS, "v": V_OPTIONS},
            "meta": {"case": n_case, "scale": n_scale, "var": n_var}}


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>考题模式 · 裁判学习平台</title>
<style>
/* ===== quiz 页专属布局 (tokens/组件来自 data-cfa-theme) ===== */
body{overflow:hidden}
.layout{display:grid;grid-template-columns:minmax(0,1fr);height:calc(100vh - var(--top-h));overflow:hidden}
.scroll{overflow-y:auto;padding:22px 18px 60px}
.wrap{max-width:900px;margin:0 auto}
.page-h{font-family:var(--font-display);font-size:22px;margin:0 0 4px;letter-spacing:.4px}
.page-sub{color:var(--muted);font-size:13px;margin:0 0 18px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);padding:18px 20px;margin-bottom:14px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden;background:var(--card2)}
.seg button{border:none;background:none;padding:7px 16px;font-size:13px;cursor:pointer;color:var(--ink2);font-family:inherit}
.seg button.on{background:var(--ink);color:var(--bg);font-weight:600}
.frow{display:flex;flex-wrap:wrap;align-items:center;gap:9px;margin:12px 0}
.flbl{font-size:12.5px;color:var(--muted);letter-spacing:1px;min-width:52px}
.stat{display:flex;gap:22px;margin:4px 0 14px;flex-wrap:wrap}
.stat b{font-size:20px;font-family:var(--font-display)}
.stat span{font-size:12px;color:var(--muted);display:block}
/* 题卡 */
.qhead{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:10px}
.qhead .match{font-size:16.5px;font-weight:600;font-family:var(--font-display);margin:0}
.qmeta{font-size:12.5px;color:var(--muted)}
.qvideo video{width:100%;max-width:820px;aspect-ratio:16/9;background:#000;border-radius:var(--r-md);display:block}
.qtext{font-size:14.5px;line-height:1.9;margin:12px 0 0}
.qtext .lbl{color:var(--muted)}
details.qappeal{margin-top:8px;font-size:13.5px;color:var(--ink2)}
details.qappeal summary{cursor:pointer;color:var(--brand);font-size:13px}
.axis{margin-top:14px}
.axis .ah{font-size:13px;font-weight:700;margin-bottom:7px}
.axis .ah small{color:var(--muted);font-weight:400}
.optrow{display:flex;flex-wrap:wrap;gap:7px}
.opt{cursor:pointer;user-select:none}
.opt b{pointer-events:none}
.ansgate{margin:16px 0 0;padding:11px 14px;border:1px dashed var(--line);border-radius:var(--r-md);
  color:var(--muted);font-size:13px;display:none;align-items:center;gap:8px}
.ansgate.on{display:flex}
.qbtns{display:flex;gap:9px;margin-top:18px;flex-wrap:wrap}
/* 反馈 */
.fb{margin-top:16px;border-top:1px dashed var(--line);padding-top:14px;display:none}
.fb.on{display:block}
/* ---- 动效 (backwards 填充: 结束后释放 transform; reduced-motion 由 theme 全局熄火) ---- */
#scrStart,#scrQuiz,#scrResult{animation:fadeUp .35s var(--ease)}
.qhead,.qtext,.qappeal{animation:fadeUp var(--t-med) var(--ease) backwards}
#qForm .axis{animation:fadeUp var(--t-med) var(--ease) backwards}
#qForm .axis:nth-child(2){animation-delay:50ms}
#qForm .axis:nth-child(3){animation-delay:100ms}
.opt.on{animation:optPop .18s var(--ease-spring)}
.fb.fb-ok{animation:pulseOk .6s var(--ease)}
.fb.fb-part{animation:fadeUp var(--t-med) var(--ease)}
.fb.fb-miss{animation:shake .4s var(--ease)}
.rrow{animation:fadeUp .35s var(--ease) backwards;animation-delay:calc(var(--i,0)*40ms)}
.fb .verdict{margin-bottom:8px}
.fb .fitem{display:flex;gap:8px;font-size:13.5px;margin:5px 0;flex-wrap:wrap}
.fb .ok{color:var(--green);font-weight:700}
.fb .bad{color:var(--red);font-weight:700}
.fb .concl{font-size:13.5px;line-height:1.85;background:var(--card2);border-left:3px solid var(--brand);
  padding:9px 12px;border-radius:0 var(--r-sm) var(--r-sm) 0;margin-top:9px}
.fb .srclinks{margin-top:9px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
/* 结果 */
.bigscore{display:flex;align-items:baseline;gap:12px;margin:6px 0 2px}
.bigscore b{font-size:44px;font-family:var(--font-display)}
.bigscore span{color:var(--muted);font-size:14px}
.rrow{display:flex;gap:10px;align-items:flex-start;padding:9px 0;border-bottom:1px solid var(--line2);font-size:13.5px}
.rrow .rmark{flex:none;font-weight:700;width:34px}
.rrow .rmain{min-width:0;flex:1}
.rrow .rt{color:var(--muted);font-size:12.5px}
.miss{color:var(--red)}
.hit{color:var(--green)}
/* 错题本 */
.wbitem{display:flex;gap:9px;align-items:flex-start;padding:8px 0;border-bottom:1px solid var(--line2);font-size:13px}
.wbitem .wbm{flex:1;min-width:0}
.wbitem .wbyour{color:var(--red);font-size:12px}
.wbbtn{flex:none}
.topbtn{position:fixed;right:20px;bottom:22px;display:none;align-items:center;gap:6px;
  background:var(--brand-strong);color:var(--on-brand);border:none;border-radius:999px;
  padding:9px 16px;font-size:13px;cursor:pointer;z-index:30;box-shadow:var(--shadow-sm)}
@media (max-width:640px){.scroll{padding:14px 10px 60px}.panel{padding:14px}}
</style>
</head>
<body class="page-quiz">
<a class="skip-link" href="#scrStart">跳到内容</a>
__TOPBAR__

<div class="layout"><div class="scroll" id="scroll"><div class="wrap">

<!-- 开始屏 -->
<section id="scrStart">
  <h1 class="page-h">考题模式</h1>
  <p class="page-sub">从三赛季评议判例与官方统一尺度场景中随机出题——先看视频做出你的判罚，再对照评议组认定算分。错题自动进错题本，记住你的错选，方便查缺补漏。</p>
  <div class="panel">
    <div class="stat">
      <div><b>__N_CASE__</b><span>赛季判例</span></div>
      <div><b>__N_SCALE__</b><span>尺度场景</span></div>
      <div><b>__N_VAR__</b><span>VAR 协议题</span></div>
      <div><b id="nWrong">0</b><span>错题本</span></div>
      <div><b id="nStar">0</b><span>收藏错题</span></div>
    </div>
    <div class="frow"><span class="flbl">模式</span>
      <div class="seg" id="segMode">
        <button data-v="practice" class="on">练习（每题即时反馈）</button>
        <button data-v="exam">考试（做完统一出分）</button>
      </div>
    </div>
    <div class="frow"><span class="flbl">题数</span>
      <div class="seg" id="segCount">
        <button data-v="5">5</button><button data-v="10" class="on">10</button>
        <button data-v="20">20</button><button data-v="50">50</button><button data-v="0">全部</button>
      </div>
    </div>
    <div class="frow"><span class="flbl">题源</span>
      <div class="seg" id="segSrc">
        <button data-v="all" class="on">全部</button><button data-v="case">赛季判例</button>
        <button data-v="scale">尺度场景</button><button data-v="var">VAR 协议题</button>
      </div>
    </div>
    <div class="frow"><span class="flbl">赛季</span>
      <div id="seasonChips"></div>
    </div>
    <div class="frow"><span class="flbl">范围</span>
      <div class="seg" id="segRange">
        <button data-v="all" class="on">全部题库</button>
        <button data-v="wrong">错题重练</button>
        <button data-v="star">收藏错题</button>
      </div>
    </div>
    <div class="frow">
      <button class="btn primary" id="btnStart">开始答题</button>
      <button class="btn" id="btnWb">错题本管理</button>
      <button class="btn" id="btnExport">导出</button>
      <button class="btn" id="btnImport">导入</button>
      <input type="file" id="importFile" accept=".json,application/json" style="display:none">
      <span id="poolTip" style="font-size:12.5px;color:var(--muted)"></span>
    </div>
    <div id="wbBox" style="display:none">
      <div class="frow" style="justify-content:space-between">
        <b style="font-size:14px">错题本（<span id="wbCount">0</span>）</b>
        <button class="btn" id="btnWbClear">清空错题本</button>
      </div>
      <div id="wbList"></div>
    </div>
  </div>
</section>

<!-- 答题屏 -->
<section id="scrQuiz" style="display:none">
  <div class="panel">
    <div class="frow" style="justify-content:space-between;margin-top:0">
      <b id="qProgress" style="font-size:14px"></b>
      <span id="qScore" style="font-size:13px;color:var(--muted)"></span>
    </div>
    <div id="qCard"></div>
    <div class="ansgate" id="ansGate">🤔 先看视频、读完事件经过，在心里做出你的判罚，再作答。</div>
    <div id="qForm"></div>
    <div class="fb" id="qFb"></div>
    <div class="qbtns">
      <button class="btn" id="btnPrev">上一题</button>
      <button class="btn" id="btnSkip">跳过</button>
      <button class="btn primary" id="btnSubmit">提交答案</button>
    </div>
  </div>
</section>

<!-- 结果屏 -->
<section id="scrResult" style="display:none">
  <div class="panel">
    <div class="bigscore"><b id="rScore">0</b><span id="rPct"></span></div>
    <p id="rRate" style="margin:0 0 10px;font-size:14px"></p>
    <div class="frow">
      <button class="btn primary" id="btnAgain">再来一轮</button>
      <button class="btn" id="btnWrongRedo">错题重练</button>
      <button class="btn" id="btnBack">返回开始屏</button>
    </div>
  </div>
  <div class="panel"><div id="rList"></div></div>
</section>

</div></div></div>
<button class="top-btn" id="btnTop">__I_UP__ 回到顶部</button>

<script>
const DATA = __DATA__;
const IC = __ICONS__;
const CFG = DATA.cfg;
const R_OPTS = DATA.opts.r, C_OPTS = DATA.opts.c, V_OPTS = DATA.opts.v;
const VNAME = Object.fromEntries(V_OPTS);
const RNAME = Object.fromEntries(R_OPTS);
const CNAME = Object.fromEntries(C_OPTS);
const BANK = {};
DATA.bank.forEach(q => BANK[q.k] = q);
let LITE = document.documentElement.dataset.lite === "1";

function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
  .replace(/"/g,"&quot;").replace(/'/g,"&#39;")}
function crest(team, h, mark){
  const item = DATA.teams && DATA.teams[team];
  if (!item) return `<span class="team-badge" title="${esc(team)}：未登记">?</span>`;
  if (item.status === "verified" && item.path)
    return `<img class="crest" style="height:${h}px" src="${item.path}" alt="${esc(team)}队徽">`;
  if (mark)
    return `<span class="team-dot" style="width:${h}px;height:${h}px;background:${item.bg};border:1px solid ${item.fg}" title="${esc(team)}：队徽待核验"></span>`;
  const scale = Math.max(16, h);
  return `<span class="team-badge" style="width:${scale}px;height:${scale}px;--badge-fg:${item.fg};--badge-bg:${item.bg}" title="${esc(team)}：文字徽章（队徽待核验）">${esc(item.initials)}</span>`;
}

// ---------- 错题本 ----------
let wrong = {};
try { wrong = JSON.parse(localStorage.getItem(CFG.wrongKey) || "{}") || {}; } catch(_) { wrong = {}; }
function persistWrong(){ try { localStorage.setItem(CFG.wrongKey, JSON.stringify(wrong)); } catch(_) {} }
function recordWrong(q, your, score){
  const e = wrong[q.k] || {t:q.t, s:q.s, star:false, wrong:0};
  // 记下正确答案文本，错题本才能对照复盘（旧版本条目无此字段，渲染时兼容）
  e.correct = score && score.detail
    ? score.detail.map(d=>d.right).join(q.t==="case" ? " + " : "、") : "";
  e.t = q.t; e.s = q.s; e.your = your;
  e.wrong = (e.wrong||0) + 1; e.last = Date.now(); e.done = false;
  wrong[q.k] = e; persistWrong();
}
function qTitle(q){
  if (q.t === "case")
    return `${esc(q.comp)}${q.round?esc(q.round):""}${q.minute?" · 第"+q.minute+"分钟":""} · ${q.s}赛季第${q.issue}期-判例${q.no}`;
  if (q.t === "var")
    return `VAR 协议题 ${esc(q.qid)} · IFAB 协议官方 FAQ`;
  return `尺度场景 ${esc(q.id)} · ${esc(q.title)}（${q.s}）`;
}
function qLink(q){
  if (q.t === "var") return q.link;
  return q.t === "case" ? `season-${q.s}.html#case-${q.seq}`
                        : `scale.html#h${q.s}-${q.series}-${q.id}`;
}

// ---------- 开始屏状态 ----------
const sel = {mode:"practice", count:10, src:"all", seasons:new Set(), range:"all"};
function renderSeasonChips(){
  const seasons = ["2026","2025","2024"];
  document.getElementById("seasonChips").innerHTML =
    `<button class="chip on" data-s="">全部</button>` +
    seasons.map(s=>`<button class="chip" data-s="${s}">${s}</button>`).join("");
}
function pool(){
  let list = DATA.bank;
  if (sel.src !== "all") list = list.filter(q=>q.t===sel.src);
  if (sel.seasons.size) list = list.filter(q=>sel.seasons.has(q.s));
  if (sel.range === "wrong") list = list.filter(q=>wrong[q.k]);
  if (sel.range === "star") list = list.filter(q=>wrong[q.k] && wrong[q.k].star);
  return list;
}
function updatePoolTip(){
  const n = pool().length;
  document.getElementById("poolTip").textContent = `当前范围 ${n} 题`;
  document.getElementById("btnStart").disabled = !n;
}
function renderWbStats(){
  const n = Object.keys(wrong).length;
  const st = Object.values(wrong).filter(e=>e.star).length;
  document.getElementById("nWrong").textContent = n;
  document.getElementById("nStar").textContent = st;
  document.getElementById("wbCount").textContent = n;
}
function renderWbList(){
  const entries = Object.entries(wrong);
  document.getElementById("wbList").innerHTML = entries.length ? entries.map(([k,e])=>{
    const q = BANK[k]; if (!q) return "";
    const yourTxt = e.t==="case" ? axisText(e.your) : e.t==="var" ? (q.opts && q.opts[+e.your] || "（未作答）") : (e.your||[]).join("、") || "（未作答）";
    const corrTxt = e.t==="case" ? (e.correct||"") : (e.correct&&e.correct.join ? e.correct.join("、") : (e.correct||""));
    return `<div class="wbitem">
      <div class="wbm"><div>${qTitle(q)}</div>
      <div class="wbyour">上次错选：${esc(yourTxt)}${corrTxt?` · 正确：${esc(corrTxt)}`:""}${e.done?" · 已掌握":""}</div></div>
      <button class="btn wbbtn" data-star="${k}">${e.star?"★":"☆"}</button>
      <button class="btn wbbtn" data-del="${k}">移除</button>
      <a class="btn wbbtn" href="${qLink(q)}">查看</a>
    </div>`;
  }).join("") : `<p style="color:var(--muted);font-size:13px">错题本为空——完成一轮答题后，未得满分的题会自动记入。</p>`;
}
function axisText(y){
  if (!y) return "（未作答）";
  const parts = [];
  if (y.v) parts.push(VNAME[y.v]||y.v);
  if (y.r) parts.push(RNAME[y.r]||y.r);
  if (y.c) parts.push(CNAME[y.c]||y.c);
  return parts.join(" + ") || "（未作答）";
}

// ---------- 出题 ----------
let round = null;
function shuffle(a){ for(let i=a.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [a[i],a[j]]=[a[j],a[i]]; } return a; }
function startRound(list){
  let qs = shuffle(list.slice());
  if (sel.count > 0) qs = qs.slice(0, sel.count);
  round = {qs, i:0, mode:sel.mode, answers:qs.map(()=>null), scores:qs.map(()=>null), locked:false};
  showScreen("quiz");
  renderQuestion();
}
function showScreen(name){
  document.getElementById("scrStart").style.display = name==="start"?"":"none";
  document.getElementById("scrQuiz").style.display = name==="quiz"?"":"none";
  document.getElementById("scrResult").style.display = name==="result"?"":"none";
  document.getElementById("scroll").scrollTop = 0;
}
function stopVideo(){
  const v = document.getElementById("qvid");
  if (!v) return;
  try { v.pause(); } catch(_){}
  v.removeAttribute("src"); v.load();
}

function renderQuestion(){
  const q = round.qs[round.i];
  round.locked = false;
  const done = round.scores[round.i] != null;
  document.getElementById("qProgress").textContent = `第 ${round.i+1} / ${round.qs.length} 题`;
  const gotSoFar = round.scores.filter(Boolean).reduce((s,x)=>s+x.got,0);
  document.getElementById("qScore").textContent = round.mode==="practice" ? `当前得分 ${gotSoFar}` : "考试模式 · 交卷后出分";
  // 题头
  let head = "";
  if (q.t === "case"){
    const match = [q.comp, q.round, (q.home&&q.away)?`${crest(q.home,20,true)}${esc(q.home)} vs ${crest(q.away,20,true)}${esc(q.away)}`:"", q.minute?`第${q.minute}分钟`:""]
      .filter(Boolean).join(" · ");
    head = `<span class="badge info">判例</span><h2 class="match">${match}</h2>
      <span class="qmeta">${q.s}赛季第${q.issue}期-判例${q.no}${q.catname?" · "+esc(q.catname):""}</span>`;
  } else if (q.t === "var"){
    head = `<span class="badge info">VAR 协议题</span><h2 class="match">IFAB 协议场景 ${esc(q.qid)}</h2>
      <span class="qmeta">《竞赛规则》VAR 协议官方 FAQ · 四选一 · 1分</span>`;
  } else {
    head = `<span class="badge info">尺度场景</span><h2 class="match">${esc(q.title)}</h2>
      <span class="qmeta">${q.s}赛季 · ${esc(q.group)} · 编号 ${esc(q.id)}</span>`;
  }
  // 视频（var 为纯场景题，无视频）
  let vidHtml = "";
  if (q.t === "var"){
    vidHtml = `<div class="src-actions" style="display:flex"><a class="srcbtn" href="${esc(q.link)}" target="_blank">${IC.external} 前往 IFAB 协议页查看该 FAQ</a><span class="srcsub">纯场景判断题——先想好你的决定再作答</span></div>`;
  } else if (!LITE){
    const src = q.t==="case" ? "videos/"+q.videos[0] : q.video;
    const poster = q.poster ? ` poster="${esc(q.poster)}"` : "";
    vidHtml = `<div class="qvideo"><video id="qvid" controls preload="metadata" playsinline referrerpolicy="no-referrer"${poster}></video></div>
      <p class="qmeta" id="vidTip" style="display:none;margin-top:6px"></p>`;
  } else {
    const links = q.t==="case"
      ? (q.vurls||[]).map((u,i)=>`<a class="srcbtn" href="${esc(u)}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">${IC.play} 官方视频${i+1}</a>`).join("")
      : `<a class="srcbtn" href="scale.html#h${q.s}-${q.series}-${q.id}" target="_blank">前往统一尺度页查看该场景</a>`;
    vidHtml = `<div class="src-actions" style="display:flex">${links}<span class="srcsub">轻量版：请在线观看视频后作答</span></div>`;
  }
  // 题面
  const text = q.t==="case"
    ? `<p class="qtext">${esc(q.desc.replace(/^判例[一二三四五六七八九十百]+[：:]/,"").trim())}</p>`
    : q.t==="var"
    ? `<p class="qtext">${esc(q.q)}</p>`
    : `<p class="qtext">${esc(q.note)}</p>`;
  const appeal = (q.t==="case" && q.appeal)
    ? `<details class="qappeal"><summary>查看申诉方主张（提示）</summary><p>${esc(q.appeal.replace(/^[^：]*申诉意见认为：/,"").trim())}</p></details>` : "";
  document.getElementById("qCard").innerHTML = `<div class="qhead">${head}</div>${vidHtml}${text}${appeal}`;
  // 视频接线（本地 404 → 官方直链）
  if (!LITE){
    const v = document.getElementById("qvid");
    const tip = document.getElementById("vidTip");
    if (q.t==="case" && vidsMissing && (q.vurls||[])[0]){
      v.dataset.oss = "1";
      v.src = q.vurls[0];
      if (tip){ tip.textContent = "本地视频缺失，已自动改用官方直链在线播放。"; tip.style.display = ""; }
    }
    else if (q.t==="case") v.src = "videos/"+q.videos[0];
    else v.src = q.video;
  }
  // 表单（已作答且练习已提交时还原为锁定态）
  const saved = round.answers[round.i];
  if (q.t === "case"){
    const axes = [`<div class="axis"><div class="ah">① 评议组复核结论 <small>必答 · 1分</small></div><div class="optrow">` +
      V_OPTS.map(([v,n])=>`<button class="chip opt ${saved&&saved.v===v?"on":""}" data-axis="v" data-v="${v}">${n}</button>`).join("") + `</div></div>`];
    if (q.ans && q.ans.r)
      axes.push(`<div class="axis"><div class="ah">② 正确的判罚决定 <small>1分</small></div><div class="optrow">` +
        R_OPTS.map(([v,n])=>`<button class="chip opt ${saved&&saved.r===v?"on":""}" data-axis="r" data-v="${v}">${n}</button>`).join("") + `</div></div>`);
    if (q.ans && q.ans.c)
      axes.push(`<div class="axis"><div class="ah">③ 纪律处分 <small>1分</small></div><div class="optrow">` +
        C_OPTS.map(([v,n])=>`<button class="chip opt ${saved&&saved.c===v?"on":""}" data-axis="c" data-v="${v}">${n}</button>`).join("") + `</div></div>`);
    document.getElementById("qForm").innerHTML = axes.join("");
  } else if (q.t === "var"){
    document.getElementById("qForm").innerHTML = `<div class="axis"><div class="ah">官方决定 <small>四选一 · 1分</small></div><div class="optrow">` +
      q.opts.map((o,i)=>`<button class="chip opt ${saved&&+saved===i?"on":""}" data-axis="o" data-v="${i}">${esc(o)}</button>`).join("") + `</div></div>`;
  } else {
    document.getElementById("qForm").innerHTML = `<div class="axis"><div class="ah">判罚决定 <small>多选 · 满分2分：完全一致2分，无错选有漏选1分，有错选0分</small></div><div class="optrow">` +
      q.dec.map(d=>`<button class="chip opt ${saved&&saved.includes(d.label)?"on":""}" data-dec="${esc(d.label)}">${esc(d.label)}</button>`).join("") + `</div></div>`;
  }
  document.getElementById("ansGate").classList.add("on");
  const fb = document.getElementById("qFb");
  fb.classList.remove("on"); fb.innerHTML = "";
  if (done){ round.locked = true; renderFeedback(q, saved); }
  syncButtons();
}
function currentAnswer(){
  const q = round.qs[round.i];
  if (q.t === "case"){
    const a = {v:null, r:null, c:null};
    document.querySelectorAll("#qForm .opt.on").forEach(b=>{
      a[b.dataset.axis] = b.dataset.v;
    });
    return a;
  }
  if (q.t === "var"){
    const b = document.querySelector("#qForm .opt.on");
    return b ? b.dataset.v : null;
  }
  return Array.from(document.querySelectorAll("#qForm .opt.on")).map(b=>b.dataset.dec);
}
function syncButtons(){
  const done = round.scores[round.i] != null && round.mode==="practice";
  document.getElementById("btnPrev").disabled = round.i===0;
  document.getElementById("btnSkip").style.display = done ? "none" : "";
  const submit = document.getElementById("btnSubmit");
  if (round.mode === "practice"){
    submit.textContent = done ? (round.i===round.qs.length-1 ? "查看结果" : "下一题")
                              : (round.i===round.qs.length-1 ? "提交并查看结果" : "提交答案");
  } else {
    submit.textContent = round.i===round.qs.length-1 ? "交卷查看结果" : "下一题";
  }
}

// ---------- 判分 ----------
function scoreCase(q, a){
  const detail = [];
  let max = 1, got = 0;
  detail.push({name:"复核结论", ok:a.v===q.v, yours:a.v?VNAME[a.v]:"（未答）", right:VNAME[q.v]});
  if (a.v===q.v) got++;
  if (q.ans && q.ans.r){ max++;
    detail.push({name:"判罚决定", ok:a.r===q.ans.r, yours:a.r?RNAME[a.r]:"（未答）", right:RNAME[q.ans.r]});
    if (a.r===q.ans.r) got++;
  }
  if (q.ans && q.ans.c){ max++;
    detail.push({name:"纪律处分", ok:a.c===q.ans.c, yours:a.c?CNAME[a.c]:"（未答）", right:CNAME[q.ans.c]});
    if (a.c===q.ans.c) got++;
  }
  return {got, max, detail};
}
function scoreScale(q, selArr){
  const active = q.dec.filter(d=>d.active).map(d=>d.label);
  const fp = selArr.filter(x=>!active.includes(x));
  const miss = active.filter(x=>!selArr.includes(x));
  const got = (!fp.length && !miss.length) ? 2 : (!fp.length ? 1 : 0);
  return {got, max:2, detail:[
    {name:"判罚决定", ok:got===2, yours:selArr.length?selArr.join("、"):"（未答）", right:active.join("、")||"（无）"},
    {name:"错选/漏选", ok:!fp.length, yours:fp.length?("错选 "+fp.join("、")):"无错选", right:miss.length?("漏选 "+miss.join("、")):"无漏选"}
  ]};
}
function scoreVar(q, a){
  const idx = (a===null || a===undefined || a==="") ? -1 : +a;
  const ok = idx === q.ans;
  return {got: ok?1:0, max:1, detail:[
    {name:"官方决定", ok, yours: idx>=0 && q.opts[idx] ? q.opts[idx] : "（未答）", right: q.opts[q.ans]}
  ]};
}
function renderFeedback(q, a){
  const s = round.scores[round.i];
  const allOk = s.got === s.max;
  let h = `<div class="verdict"><span class="badge ${allOk?"correct":s.got>0?"pending":"wrong"}">${allOk?"完全正确":s.got>0?"部分正确":"错误"}</span>
    <b style="margin-left:8px">得分 ${s.got} / ${s.max}</b></div>`;
  h += s.detail.map(d=>`<div class="fitem"><span class="${d.ok?"ok":"bad"}">${d.ok?"✓":"✗"} ${d.name}</span>
    <span>你的答案：${esc(d.yours)}</span>${d.ok?"":`<span>正确：${esc(d.right)}</span>`}</div>`).join("");
  if (q.t === "case"){
    h += `<div class="concl"><b>评议组认定：</b>${esc(q.concl.replace(/^对于此判[例罚]，评议组[^：]*认为：/,"").trim())}</div>`;
  } else if (q.t === "var"){
    h += `<div class="concl"><b>官方答案（VAR 协议 FAQ）：</b>${esc(q.a)}</div>`;
    h += `<details class="qappeal"><summary>English original</summary><p>${esc(q.a_en)}</p></details>`;
  } else {
    if (q.reason) h += `<div class="concl"><b>Reason：</b>${esc(q.reason)}</div>`;
    if (q.varrule) h += `<div class="concl"><b>⚖ VAR 介入：</b>${esc(q.varrule)}</div>`;
  }
  const e = wrong[q.k];
  h += `<div class="srclinks">
    <button class="btn" id="fbStar">${e&&e.star?IC["star-f"]+" 已收藏":IC.star+" 收藏错题"}</button>
    <a class="btn" href="${qLink(q)}" target="_blank">${IC.external} 查看原判例</a>
    ${wrong[q.k]&&wrong[q.k].wrong>1?`<span style="font-size:12px;color:var(--muted)">已错 ${wrong[q.k].wrong} 次</span>`:""}
  </div>`;
  const fb = document.getElementById("qFb");
  fb.classList.remove("fb-ok", "fb-part", "fb-miss");
  fb.innerHTML = h;
  fb.classList.add("on", s.got===s.max ? "fb-ok" : s.got>0 ? "fb-part" : "fb-miss");
  document.getElementById("fbStar").onclick = ()=>toggleStar(q.k);
}
function toggleStar(k){
  if (!wrong[k]) return;
  wrong[k].star = !wrong[k].star; persistWrong(); renderWbStats();
  const btn = document.getElementById("fbStar");
  if (btn) btn.innerHTML = wrong[k].star ? IC["star-f"]+" 已收藏" : IC.star+" 收藏错题";
}

// ---------- 提交与导航 ----------
function submitAnswer(){
  const q = round.qs[round.i];
  if (round.mode === "practice"){
    const done = round.scores[round.i] != null;
    if (!done){
      const a = currentAnswer();
      const s = q.t==="case" ? scoreCase(q, a) : q.t==="var" ? scoreVar(q, a) : scoreScale(q, a);
      round.answers[round.i] = a; round.scores[round.i] = s;
      if (s.got < s.max) recordWrong(q, a, s);
      else if (wrong[q.k]){ wrong[q.k].done = true; persistWrong(); }
      round.locked = true;
      renderFeedback(q, a);
      syncButtons();
      return;
    }
    if (round.i < round.qs.length-1){ round.i++; renderQuestion(); }
    else showResult();
    return;
  }
  // 考试模式：只记录答案，可返回修改，交卷时统一判分与记错题
  round.answers[round.i] = currentAnswer();
  if (round.i < round.qs.length-1){ round.i++; renderQuestion(); }
  else finishExam();
}
function finishExam(){
  round.qs.forEach((q,i)=>{
    const a = round.answers[i] ?? (q.t==="case" ? {v:null,r:null,c:null} : q.t==="var" ? null : []);
    const s = q.t==="case" ? scoreCase(q, a) : q.t==="var" ? scoreVar(q, a) : scoreScale(q, a);
    round.scores[i] = s;
    if (s.got < s.max) recordWrong(q, a, s);
    else if (wrong[q.k]){ wrong[q.k].done = true; }
  });
  persistWrong();
  showResult();
}
function gotoPrev(){
  if (round.i>0){
    // 暂存当前作答再离开：考试模式来回查看、练习模式未提交返回都不丢
    if (round.scores[round.i] == null) round.answers[round.i] = currentAnswer();
    round.i--; renderQuestion();
  }
}
function skipQuestion(){
  const q = round.qs[round.i];
  const a = q.t==="case" ? {v:null,r:null,c:null} : q.t==="var" ? null : [];
  const s = q.t==="case" ? scoreCase(q, a) : q.t==="var" ? scoreVar(q, a) : scoreScale(q, a);
  round.answers[round.i] = a; round.scores[round.i] = s;
  recordWrong(q, a, s);
  if (round.i < round.qs.length-1){ round.i++; renderQuestion(); }
  else showResult();
}
function countUp(el, got, max){
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return; // 文本已是终值
  const t0 = performance.now(), dur = 700;
  (function tick(t){
    const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    el.textContent = `${Math.round(got * e)} / ${max}`;
    if (p < 1) requestAnimationFrame(tick);
  })(t0);
}
function showResult(){
  stopVideo();
  const totalGot = round.scores.reduce((s,x)=>s+(x?x.got:0),0);
  const totalMax = round.scores.reduce((s,x)=>s+(x?x.max:0),0);
  const pct = totalMax ? Math.round(totalGot/totalMax*100) : 0;
  document.getElementById("rScore").textContent = `${totalGot} / ${totalMax}`;
  countUp(document.getElementById("rScore"), totalGot, totalMax);
  document.getElementById("rPct").textContent = `得分率 ${pct}%`;
  document.getElementById("rRate").textContent =
    pct>=90 ? "优秀——尺度把握扎实，继续保持！" :
    pct>=75 ? "良好——注意复盘错题，堵上薄弱点。" :
    pct>=60 ? "及格——建议把错题加入收藏反复练习。" :
              "还需要加油——先从错题重练开始，逐类攻克。";
  document.getElementById("rList").innerHTML = round.qs.map((q,i)=>{
    const s = round.scores[i] || {got:0, max:0, detail:[]};
    const a = round.answers[i];
    const allOk = s.got===s.max;
    const missTxt = s.detail.filter(d=>!d.ok).map(d=>`${d.name}：正确 ${d.right}`).join("；");
    return `<div class="rrow" style="--i:${Math.min(i,12)}"><span class="rmark ${allOk?"hit":"miss"}">${allOk?"✓":s.got>0?"△":"✗"}</span>
      <div class="rmain"><div>${qTitle(q)}</div>
      <div class="rt">你的答案：${esc(q.t==="case"?axisText(a):q.t==="var"?(q.opts&&q.opts[+a])||"（未答）":(a||[]).join("、")||"（未答）")} ｜ 得分 ${s.got}/${s.max}${!allOk&&missTxt?` ｜ <span class="miss">${esc(missTxt)}</span>`:""}</div></div>
      <a class="btn wbbtn" href="${qLink(q)}">查看</a></div>`;
  }).join("");
  renderWbStats();
  showScreen("result");
}

// ---------- 事件绑定 ----------
document.querySelectorAll(".seg").forEach(seg=>{
  seg.addEventListener("click", e=>{
    const b = e.target.closest("button"); if (!b) return;
    seg.querySelectorAll("button").forEach(x=>x.classList.toggle("on", x===b));
    const id = seg.id;
    if (id==="segMode") sel.mode = b.dataset.v;
    if (id==="segCount") sel.count = +b.dataset.v;
    if (id==="segSrc") sel.src = b.dataset.v;
    if (id==="segRange") sel.range = b.dataset.v;
    updatePoolTip();
  });
});
document.getElementById("seasonChips").addEventListener("click", e=>{
  const b = e.target.closest("[data-s]"); if (!b) return;
  const s = b.dataset.s;
  if (!s){ sel.seasons.clear(); }
  else if (sel.seasons.has(s)) sel.seasons.delete(s);
  else sel.seasons.add(s);
  // 高亮跟随 sel.seasons 状态（多选可同时亮多个），不能只亮最后点击的一个
  document.querySelectorAll("#seasonChips .chip").forEach(x=>
    x.classList.toggle("on", (!x.dataset.s && !sel.seasons.size) || sel.seasons.has(x.dataset.s)));
  updatePoolTip();
});
document.getElementById("btnStart").onclick = ()=>startRound(pool());
document.getElementById("btnWb").onclick = ()=>{
  const box = document.getElementById("wbBox");
  box.style.display = box.style.display==="none" ? "" : "none";
  renderWbList();
};
document.getElementById("btnWbClear").onclick = ()=>{
  if (!Object.keys(wrong).length) return;
  if (confirm("确定清空整个错题本？此操作不可恢复。")){ wrong = {}; persistWrong(); renderWbStats(); renderWbList(); }
};
document.getElementById("wbList").addEventListener("click", e=>{
  const st = e.target.closest("[data-star]");
  if (st){ const k = st.dataset.star; wrong[k].star = !wrong[k].star; persistWrong(); renderWbStats(); renderWbList(); return; }
  const del = e.target.closest("[data-del]");
  if (del){ delete wrong[del.dataset.del]; persistWrong(); renderWbStats(); renderWbList(); }
});
document.getElementById("btnExport").onclick = ()=>{
  const blob = new Blob([JSON.stringify({wrong, exported:new Date().toISOString(), app:"cfa-referee-quiz"}, null, 1)],
    {type:"application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "考题错题本.json";
  a.click(); URL.revokeObjectURL(a.href);
};
document.getElementById("btnImport").onclick = ()=>document.getElementById("importFile").click();
document.getElementById("importFile").addEventListener("change", e=>{
  const f = e.target.files[0]; if (!f) return;
  const rd = new FileReader();
  rd.onload = ()=>{
    try {
      const d = JSON.parse(rd.result);
      let n = 0;
      for (const [k, v] of Object.entries(d.wrong||{})){
        if (!BANK[k]) continue;
        if (!wrong[k] || (v.last||0) >= (wrong[k].last||0)){ wrong[k] = v; n++; }
      }
      persistWrong(); renderWbStats();
      if (document.getElementById("wbBox").style.display !== "none") renderWbList();
      alert(`导入完成：合并了 ${n} 条错题记录`);
    } catch(err){ alert("导入失败：文件不是有效的错题本 JSON"); }
  };
  rd.readAsText(f, "utf-8");
  e.target.value = "";
});
// 答题表单：单选/多选 chips
document.getElementById("qForm").addEventListener("click", e=>{
  const b = e.target.closest(".opt"); if (!b || round.locked) return;
  const q = round.qs[round.i];
  if (q.t === "case" || q.t === "var"){   // 单选轴（var 的四选项也是单选）
    const axis = b.dataset.axis;
    document.querySelectorAll(`#qForm .opt[data-axis="${axis}"]`).forEach(x=>x.classList.toggle("on", x===b));
  } else {
    b.classList.toggle("on");
  }
});
document.getElementById("btnSubmit").onclick = submitAnswer;
document.getElementById("btnSkip").onclick = skipQuestion;
document.getElementById("btnPrev").onclick = gotoPrev;
document.getElementById("btnAgain").onclick = ()=>startRound(round.qs);
document.getElementById("btnWrongRedo").onclick = ()=>{
  const list = round.qs.filter(q=>wrong[q.k]);
  if (list.length) startRound(list); else startRound(round.qs);
};
document.getElementById("btnBack").onclick = ()=>{ renderWbStats(); updatePoolTip(); showScreen("start"); };
document.getElementById("btnTop").onclick = ()=>document.getElementById("scroll").scrollTo({top:0,behavior:"smooth"});

// 视频两级回退（本地缺失 → 官方直链）
let vidsMissing = false;
document.getElementById("qCard").addEventListener("error", e=>{
  if (e.target.id !== "qvid") return;
  const q = round && round.qs[round.i];
  if (!q || q.t !== "case") return;
  const url = (q.vurls||[])[0];
  const v = document.getElementById("qvid");
  const tip = document.getElementById("vidTip");
  if (url && v.dataset.oss !== "1"){
    v.dataset.oss = "1"; vidsMissing = true;
    v.src = url;
    if (tip){ tip.textContent = "本地视频缺失，已自动改用官方直链在线播放。"; tip.style.display = ""; }
  } else if (v.dataset.oss === "1" && tip){
    // 官方直链也失败：不再无提示地静默卡死
    tip.textContent = "官方直链播放失败，可从判例页打开官方评议页观看。";
    tip.style.display = "";
  }
}, true);

// ---------- 初始化 ----------
document.addEventListener("cfa:lite", ()=>{
  LITE = document.documentElement.dataset.lite==="1";
  // 答题中途切轻量版：暂存当前作答并重渲染，让视频窗口按新模式显隐
  if (round && document.getElementById("scrQuiz").style.display !== "none"){
    if (round.scores[round.i] == null) round.answers[round.i] = currentAnswer();
    renderQuestion();
  }
});
renderSeasonChips(); renderWbStats(); updatePoolTip();
</script>
</body>
</html>
"""


def main():
    data = build_data()
    # "</" 转义为合法 JSON 的 "<\/"，防正文里出现 </script> 提前闭合注入点
    data_js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    tb = topbar(active="quiz.html", stats="stats-2026.html", brand_sub="考题模式",
                seasons=("2024", "2025", "2026"), help_btn=False, lite_btn=True)
    html = inject_theme(HTML
                        .replace("__DATA__", data_js)
                        .replace("__ICONS__", js_icons())
                        .replace("__TOPBAR__", tb)
                        .replace("__I_UP__", icon("up", 14))
                        .replace("__N_CASE__", str(data["meta"]["case"]))
                        .replace("__N_SCALE__", str(data["meta"]["scale"]))
                        .replace("__N_VAR__", str(data["meta"]["var"])))
    SITE.mkdir(parents=True, exist_ok=True)
    out = SITE / "quiz.html"
    out.write_text(html, encoding="utf-8")
    print(f"生成 {out}（判例 {data['meta']['case']} 题 + 尺度场景 {data['meta']['scale']} 题 "
          f"+ VAR 协议 {data['meta']['var']} 题, {len(html.encode('utf-8'))/1024:.0f} KB）")


if __name__ == "__main__":
    main()
