# -*- coding: utf-8 -*-
"""生成各赛季合集页 season-2025.html / season-2024.html（单文件离线可用）
布局: 单行顶栏 | 侧栏(分类/判定) | 播放列表(密集行) | 详情区(大视频+全文)
内存: 详情区唯一<video>, 选中即载入, 切换即替换
用法: python build_page.py [2025] [2024]   # 不带参数=两个赛季都构建
"""
import json
import sys
from datetime import date
from pathlib import Path

from crest_catalog import load_catalog, normalize_team
from theme import inject_theme

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

# 赛季配置（输出文件/存储键/期数/统计页链接）
SEASONS = {
    "2025": {
        "out": "season-2025.html",
        "title": "2025赛季中国足协裁判评议全集 · 新裁判教学合集",
        "brand": "2025评议合集",
        "stats": "stats-2025.html",
        "issueCount": 32,
        "issueDesc": "2025赛季第1—32期（第1—23期原发布于赛事新闻栏目）",
        "favKey": "cfa2025.fav",
        "noteKey": "cfa2025.notes",
    },
    "2024": {
        "out": "season-2024.html",
        "title": "2024赛季中国足协裁判评议全集 · 新裁判教学合集",
        "brand": "2024评议合集",
        "stats": "stats-2024.html",
        "issueCount": 27,
        "issueDesc": "2024赛季第1—27期",
        "favKey": "cfa2024.fav",
        "noteKey": "cfa2024.notes",
    },
}
# comp 安全网归一（parse_issues 已修复，此处兜底）
COMP_ALIAS = {"中超": "中超联赛", "中甲": "中甲联赛", "中乙": "中乙联赛",
              "女超": "女超联赛", "女甲": "女甲联赛", "运动会": "全运会"}

CATEGORY_ORDER = [
    ("handball", "手球犯规", "✋"),
    ("offside", "越位", "🚩"),
    ("penalty_area", "罚球区内判罚（点球）", "⭕"),
    ("freekick_foul", "罚球区外一般犯规", "🦵"),
    ("spa_tactical", "战术犯规与SPA", "🧲"),
    ("dogso", "破坏明显进球得分机会（DOGSO）", "🎯"),
    ("sfp_vc", "严重犯规与暴力行为", "🟥"),
    ("simulation", "假摔与欺骗行为", "🎭"),
    ("goal_decision", "进球判定与有利条款", "🥅"),
    ("other_program", "程序与其他", "📐"),
]

CATEGORY_NOTES = {
    "handball": "统一尺度要点：①判定手球犯规的核心是「手臂是否使身体不自然扩大」以及「是否手向球移动」；手臂处于动作下的自然位置、近距离反弹、意外触球不构成犯规。②手臂范围以腋窝下沿为界。③守方在本方罚球区内手球→罚球点球；手球阻止对方射门（有希望的进攻）但非故意（手未向球移动）→点球且无需红黄牌；故意手球破坏进球或明显得分机会→红牌。④手球队员紧接着进球无效，但队友随后进球有效（手球未立即获益的意外手球不判罚）。",
    "offside": "统一尺度要点：①越位位置以头、躯干（不含手臂）更接近对方球门线为准。②越位犯规三种情形：干扰比赛（触球）、干扰对方队员（明显影响对方处理球能力、阻挡视线、争抢中影响守门员）、利用越位位置获利。③守方「有意触球」后才重置越位——受限触球（来不及调整身体的解围）、折射不算有意触球，不重置。④每次攻方新的触球后越位判定重新计算（越位重置）。⑤VAR越位划线：关键帧选择→有效身体部位选择→落线比对，任一环节错误划线结论即不成立。",
    "penalty_area": "统一尺度要点：①罚球区内点球判罚三问：有无犯规动作（绊摔、推、拉、踢、冲撞）？接触是否达到草率以上？是否属正常争抢/意外接触？②守方先触球且动作合理、轻微接触不影响控球、攻方主动倒地夸大接触→不判点球。③罚球区线属于罚球区内；犯规地点需有清晰证据支持改判。④判罚点球本身不附带红黄牌，除非同时构成SPA、DOGSO或严重犯规。⑤VAR回看改判取消点球后，若球未出界应以坠球恢复（而非角球）。",
    "freekick_foul": "统一尺度要点：直接任意球犯规（踢、绊、推、拉、冲撞、跳向、铲球）按「草率—鲁莽—过分用力」三档把握纪律尺度：草率犯规不出示牌；鲁莽犯规黄牌警告；过分用力危及对方安全为严重犯规红牌。以危险方式比赛（如争抢高球时抬脚过高危及对方）判间接任意球。",
    "spa_tactical": "统一尺度要点：破坏有希望的进攻（SPA）→黄牌。判断要素：犯规地点与对方球门的距离、进攻方向、控球或控球可能性、防守队员人数与位置。拉扯、抱拽、背后冲撞、鲁莽冲撞破坏快攻/突破均属典型战术犯规。",
    "dogso": "统一尺度要点：破坏明显进球得分机会（DOGSO）四要素：①犯规地点与球门距离；②进攻大致朝向球门；③控球或可争得控球；④防守队员人数与位置（通常含守门员在内仅一名防守队员时成立）。以争抢球为目的且判罚球点球→黄牌；否则红牌。守门员在罚球区外犯规破坏明显得分机会→红牌。拉扯、推搡同样可构成DOGSO。",
    "sfp_vc": "统一尺度要点：①严重犯规（SFP）：争抢球中使用过分力量或野蛮方式危及对方安全——鞋钉蹬踹、直腿踩踏小腿跟腱、飞铲、抬脚触头等。②暴力行为（VC）：非争抢球时（或球不在可争抢范围时）击打、挥拳、肘击头面部；比赛停止时的攻击性行为同样可罚；「试图击打」即使未触及也属暴力行为。③挥臂接触但未达过分力量的，按鲁莽犯规黄牌处理。④轻微触碰面部示意对方起身，不构成暴力行为。",
    "simulation": "统一尺度要点：佯装被犯规（假摔）、夸大接触程度、挑衅与欺骗行为→以非体育行为黄牌警告。接触轻微且未影响平衡的主动倒地，既不判对方犯规，也应警示佯装行为。",
    "goal_decision": "统一尺度要点：①进球前提：球整体越过球门线，且进球前攻方无犯规（推搡、拉扯、冲撞守门员等）；裁判员鸣哨停止比赛后的进球无效。②有利条款：被犯规方即将形成明显进球得分机会时，必须掌握有利让进攻完成后再处理犯规——不可提前鸣哨剥夺进球机会；守门员犯规球即将进门时同样先掌握有利。③球出界（整体离开比赛场地）判定：助理裁判员应延迟举旗、裁判员延迟鸣哨，给VAR保留介入空间。",
    "other_program": "统一尺度要点：①VAR介入原则：仅限清晰明显的错漏判以及严重事件（红牌、点球、进球、认错人）；VAR查看≠介入，介入的标志是裁判员做出「电视信号」手势；VAR介入后裁判员可不回看而直接采纳结论，但仍须做出电视手势。②裁判员选位跑位影响判罚质量，虽不构成改判依据，但应持续改进。③耳麦通讯受干扰时，对讲机等备用通讯设备的使用符合VAR操作要求。④球队官员在技术区域外实施暴力行为可被红牌罚令出场。",
}

ISSUE_NOTES = {
    "2025": {
        9: "本期标题认定6例，其中判例三为VAR越位划线错误（评议组对裁判员判定不予认定），本合集计入VAR错误统计。",
        26: "本期判例七（头撞事件）当期未认定，第27期补充认定为漏判红牌；本合集将该错漏判随原判例计入第26期。",
        27: "本期文章的认定1例为对第26期判例七的补充认定（已计入第26期）；本期新增判例二经评议为支持原判。",
    },
    "2024": {},
}

VERDICT_NAME = {"wrong": "错漏判", "correct": "支持原判", "pending": "不予认定"}
VAR_NAME = {"correct": "VAR正确", "wrong": "VAR错误", "none": ""}


def build_data(season):
    data = json.loads((ROOT / "data" / f"cases-{season}.json").read_text(encoding="utf-8"))
    cases = []
    for c in data["cases"]:
        comp = COMP_ALIAS.get(c.get("comp", ""), c.get("comp", ""))
        if not comp:
            mi = c.get("match_info", "")
            for k, v in (("中超", "中超联赛"), ("中甲", "中甲联赛"), ("中乙", "中乙联赛"),
                         ("女超", "女超联赛"), ("女甲", "女甲联赛"), ("足协杯", "中国足协杯"),
                         ("运动会", "全运会")):
                if k in mi:
                    comp = v
                    break
        cases.append({
            "seq": c["seq"], "issue": c["issue"], "no": c["no"],
            "comp": comp, "round": c.get("round", ""),
            "home": normalize_team(c.get("home", "")),
            "away": normalize_team(c.get("away", "")),
            "minute": c.get("minute", ""), "match_info": c["match_info"],
            "desc": c["desc"], "appeal": c.get("appeal", ""),
            "conclusion": c["conclusion"],
            "videos": c["video_files"], "video_urls": c["video_urls"],
            "category": c["category"], "tags": c.get("tags", []),
            "v": c["referee_verdict"], "var": c["var_verdict"],
        })
    catalog = load_catalog()
    teams = {item["name"]: item for item in catalog.values()}
    issues = {i["no"]: {"title": i["title"], "date": i["date"], "url": i["url"],
                        "expected": i["expected_wrong"], "summary": i.get("summary", "")}
              for i in data["issues"]}
    cfg = SEASONS[season]
    return {"cfg": {"season": season, "favKey": cfg["favKey"], "noteKey": cfg["noteKey"],
                    "issueCount": cfg["issueCount"], "issueDesc": cfg["issueDesc"],
                    "stats": cfg["stats"]},
            "cases": cases, "issues": issues, "crests": {}, "teams": teams,
            "categories": [{"id": k, "name": n, "icon": ic} for k, n, ic in CATEGORY_ORDER],
            "notes": CATEGORY_NOTES, "issueNotes": ISSUE_NOTES.get(season, {}),
            "verdictNames": VERDICT_NAME, "varNames": VAR_NAME,
            "built": date.today().isoformat()}


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{
  --bg:#eef2f7; --card:#fff; --ink:#1c2733; --muted:#5c6b7a; --line:#e3e9f0;
  --brand:#0b4c8c; --brand2:#1266b5;
  --red:#c0392b; --redbg:#fdeceb; --green:#1e7e34; --greenbg:#e9f6ec;
  --amber:#9a6700; --amberbg:#fff5e0; --bluebg:#eef4fb;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);overflow:hidden;
  font-family:"Microsoft YaHei","PingFang SC","Segoe UI",system-ui,sans-serif;font-size:15px;line-height:1.7}

/* ---------- 顶栏(单行) ---------- */
.topbar{height:54px;display:flex;align-items:center;gap:10px;padding:0 14px;
  background:linear-gradient(90deg,#0b3d73,#0b4c8c 60%,#1266b5);color:#fff;
  position:relative;z-index:40;overflow-x:auto;scrollbar-width:none}
.topbar::-webkit-scrollbar{display:none}
.topbar a.tbtn{text-decoration:none}
.topbar .tbtn.cur{background:rgba(255,255,255,.28);font-weight:700}
.topbar .brand{display:flex;align-items:baseline;gap:8px;white-space:nowrap}
.topbar .brand b{font-size:17px;letter-spacing:.5px}
.topbar .brand span{font-size:12.5px;color:#cfe2f5}
.topbar input[type=search]{flex:1;max-width:430px;min-width:120px;padding:7px 12px;
  border:1px solid #3a6ea8;border-radius:8px;background:rgba(255,255,255,.94);
  font-size:14px;color:var(--ink)}
.topbar select{padding:7px 8px;border:1px solid #3a6ea8;border-radius:8px;
  background:rgba(255,255,255,.94);font-size:13.5px;color:var(--ink);max-width:130px}
.tbtn{padding:7px 14px;border-radius:8px;border:1px solid #3a6ea8;cursor:pointer;
  background:rgba(255,255,255,.12);color:#e8f1fa;font-size:13.5px;white-space:nowrap}
.tbtn:hover{background:rgba(255,255,255,.22)}
.tbtn.stat b{color:#ffd2cc}.tbtn.stat i{font-style:normal;color:#c9f0d2}

/* ---------- 三栏布局 ---------- */
.layout{display:grid;grid-template-columns:238px 336px 1fr;height:calc(100vh - 54px)}
body.sb-off .layout{grid-template-columns:0 336px 1fr}
body.sb-off .sidebar{display:none}

/* ---------- 侧栏 ---------- */
.sidebar{overflow-y:auto;background:#f8fafc;border-right:1px solid var(--line);
  padding:12px 10px 20px}
.side-h{font-size:12px;color:var(--muted);letter-spacing:1px;margin:14px 6px 6px;
  text-transform:uppercase}
.side-h:first-child{margin-top:2px}
.cat-item,.ver-item{display:flex;align-items:center;gap:7px;width:100%;text-align:left;
  padding:7px 10px;border:none;background:none;border-radius:8px;cursor:pointer;
  font-size:13.8px;color:var(--ink);font-family:inherit}
.cat-item:hover,.ver-item:hover{background:#eef3f9}
.cat-item.on,.ver-item.on{background:var(--brand);color:#fff}
.cat-item.on small,.ver-item.on small{color:#cfe2f5}
.cat-item .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cat-item b,.ver-item b{font-weight:600;font-size:12.5px}
.cat-item small,.ver-item small{color:var(--muted);font-size:11.5px}
.ver-item .vdot{width:9px;height:9px;border-radius:50%;flex:none}
.side-link{display:block;margin:16px 6px 0;padding:8px 10px;border-radius:8px;
  background:var(--bluebg);color:var(--brand2);text-decoration:none;font-size:13px}
.side-link:hover{background:#dfeafa}
.sidebox{max-height:236px;overflow-y:auto;border:1px solid var(--line);border-radius:8px;
  background:#fff;padding:4px}
.sidebox .cat-item{padding:5px 8px;font-size:13px}
.tav{display:inline-flex;width:18px;height:18px;border-radius:50%;background:#e2e8f0;
  color:#475569;font-size:11px;align-items:center;justify-content:center;
  margin-right:3px;vertical-align:-4px;flex:none}
#compList .cat-item .nm, #teamList .cat-item .nm, #issueList .cat-item .nm{font-size:13px}

/* ---------- 播放列表 ---------- */
.plist{overflow-y:auto;background:#fff;border-right:1px solid var(--line)}
.plist-head{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid var(--line);
  padding:8px 14px;font-size:12.5px;color:var(--muted)}
.ph{position:sticky;top:33px;z-index:4;padding:7px 14px 5px;font-size:13px;font-weight:700;
  color:var(--brand);background:#f4f8fc;border-bottom:1px solid var(--line)}
.ph b{color:var(--muted);font-weight:500;font-size:12px}
.prow{display:flex;align-items:center;gap:9px;padding:8px 12px;cursor:pointer;
  border-bottom:1px solid #f1f5f9}
.prow:hover{background:#f6f9fc}
.prow.sel{background:var(--bluebg);box-shadow:inset 3px 0 0 var(--brand2)}
.prow .dot{width:10px;height:10px;border-radius:50%;flex:none}
.dot.wrong{background:var(--red)}.dot.correct{background:#3a9d55}.dot.pending{background:#d9a514}
.prow .ptxt{flex:1;min-width:0}
.prow .ptxt b{display:block;font-size:13.5px;font-weight:600;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.prow .ptxt i{display:block;font-style:normal;font-size:11.5px;color:var(--muted);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prow .ptxt .p-source{font-family:Georgia,"Times New Roman","Noto Serif SC",serif;
  font-style:italic;font-weight:600;color:#456b92}
.prow .ptxt .p-case-id{color:#8a9bad;font-style:normal;font-weight:400}
.prow .ptxt .p-verdict{font-style:normal;font-weight:500}
.prow .rv{flex:none;font-size:11px;border-radius:5px;padding:0 6px;
  background:var(--bluebg);color:var(--brand2)}
.prow .rv.bad{background:var(--redbg);color:var(--red)}
.prow .pmark{flex:none;font-size:12px}
.crest{width:auto;border-radius:3px;vertical-align:-3px;margin-right:3px;background:#fff}
.team-badge{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;
  border-radius:4px;margin-right:3px;vertical-align:-4px;font-size:8px;font-weight:700;
  line-height:1;color:var(--badge-fg,#0b4c8c);background:var(--badge-bg,#e9f2fb)}
.plist-empty{padding:40px 16px;text-align:center;color:var(--muted)}

/* ---------- 详情区 ---------- */
.detail{overflow-y:auto;padding:18px 24px 40px}
.detail-empty{height:70vh;display:flex;align-items:center;justify-content:center;
  color:var(--muted);font-size:15px}
.d-card{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:18px 22px;box-shadow:0 1px 3px rgba(15,40,80,.05);max-width:1080px}
.d-head{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:4px}
.cid{color:var(--muted);font-size:13px;background:#f1f5f9;border-radius:6px;padding:2px 10px}
.d-head .match{flex-basis:100%;margin:2px 0 0;font-size:20px;font-weight:700;line-height:1.4}
.badge{padding:3px 13px;border-radius:16px;font-size:14px;font-weight:600;white-space:nowrap}
.b-wrong{background:var(--redbg);color:var(--red);border:1px solid #f2c4bf}
.b-correct{background:var(--greenbg);color:var(--green);border:1px solid #bfe3c8}
.b-pending{background:var(--amberbg);color:var(--amber);border:1px solid #ecd9a0}
.b-var{background:var(--bluebg);color:var(--brand2);border:1px solid #c9dcf2;font-weight:500}
.b-var.bad{background:var(--redbg);color:var(--red);border-color:#f2c4bf}
.d-video{margin:14px 0 4px}
.d-video video{width:100%;aspect-ratio:16/9;background:#0d1420;border-radius:10px;display:block}
.vsw-row{display:flex;gap:8px;margin:8px 0 2px}
.vsw{padding:3px 14px;border-radius:14px;border:1px solid #cbd5e1;background:#fff;
  cursor:pointer;font-size:13px;color:var(--muted)}
.vsw.on{background:var(--brand);border-color:var(--brand);color:#fff}
.d-note{font-size:13px;color:var(--muted);margin:6px 0 0}
.txt{font-size:15.5px;margin-top:10px}
.txt .lbl{color:var(--brand);font-weight:700}
.txt p{margin:8px 0;white-space:pre-wrap}
.txt .concl{background:#f6f9fc;border-left:3px solid var(--brand2);
  padding:10px 14px;border-radius:0 8px 8px 0}
.d-note-box{margin-top:12px;font-size:14px;background:#f6f9fc;border:1px solid var(--line);
  border-radius:8px;padding:8px 14px}
.d-note-box summary{cursor:pointer;color:var(--brand);font-weight:600;user-select:none}
.d-note-box div{margin-top:6px;color:#33475b}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.tag{font-size:12.5px;color:var(--muted);background:#f1f5f9;border-radius:5px;padding:2px 9px}
.d-foot{font-size:13px;margin-top:12px}
.d-foot a{color:var(--brand2);text-decoration:none}
.d-foot a:hover{text-decoration:underline}
.d-nav{display:flex;gap:10px;margin-top:16px}
.d-nav button{flex:1;padding:10px;border-radius:9px;border:1px solid #cbd5e1;background:#fff;
  cursor:pointer;font-size:14.5px;color:var(--ink)}
.d-nav button:hover{border-color:var(--brand2);color:var(--brand2)}
.favbtn{padding:4px 16px;border-radius:16px;border:1px solid #cbd5e1;background:#fff;
  cursor:pointer;font-size:14px;color:var(--muted)}
.favbtn.on{background:#fff7d6;border-color:#e6c34a;color:#9a6700;font-weight:700}
.favtags{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px}
.ftag{padding:3px 12px;border-radius:14px;border:1px solid #cbd5e1;background:#fff;
  cursor:pointer;font-size:13px;color:var(--muted)}
.ftag.on{background:var(--brand);border-color:var(--brand);color:#fff}
.favtags input{padding:4px 8px;border:1px solid #cbd5e1;border-radius:6px;font-size:12.5px;width:110px}
.notewrap{margin-top:14px}
.notewrap textarea{width:100%;min-height:74px;padding:10px 12px;border:1px solid #cbd5e1;
  border-radius:9px;font-size:14px;font-family:inherit;resize:vertical;background:#fffdf5}
.notewrap .nstatus{font-size:12px;color:var(--muted)}
.kbd{font-size:11.5px;color:var(--muted);border:1px solid #cbd5e1;border-bottom-width:2px;
  border-radius:4px;padding:0 5px;margin:0 2px}

/* ---------- 弹层 ---------- */
.modal-mask{position:fixed;inset:0;background:rgba(8,20,38,.55);z-index:90;
  display:none;align-items:flex-start;justify-content:center;overflow-y:auto;padding:44px 16px}
.modal-mask.open{display:flex}
.modal{background:#fff;border-radius:14px;max-width:980px;width:100%;padding:22px 26px}
.modal h3{margin:0 0 12px;font-size:18px}
.modal .close{float:right;border:none;background:#f1f5f9;color:var(--muted);
  border-radius:8px;padding:4px 12px;cursor:pointer;font-size:13px}
.matrix table{border-collapse:collapse;width:100%;font-size:13.8px}
.matrix th,.matrix td{border-bottom:1px solid var(--line);padding:6px 10px;text-align:center}
.matrix th:first-child,.matrix td:first-child{text-align:left}
.matrix tr:hover td{background:#f6f9fc}
.matrix .w{color:var(--red);font-weight:600}.matrix .g{color:var(--green);font-weight:600}
.matrix .p{color:var(--amber);font-weight:600}
.matrix tfoot td{font-weight:700;background:#f6f9fc}
.help p{margin:8px 0;font-size:14.5px}
.help b{color:var(--brand)}
.top-btn{position:fixed;right:22px;bottom:24px;background:var(--brand);color:#fff;
  border:none;border-radius:24px;padding:9px 18px;font-size:13.5px;cursor:pointer;z-index:30}

/* ---------- 响应式 ---------- */
@media (max-width:1180px){
  .layout{grid-template-columns:250px 1fr}
  .plist{grid-column:1 / 3}
  .detail{grid-column:1 / 3}
  body.detail-open .plist{display:none}
  body.detail-open .detail{grid-column:1 / 3}
}
@media (max-width:860px){
  .layout{grid-template-columns:1fr}
  body{overflow:auto}
  .layout{height:auto}
  .sidebar{position:fixed;left:0;top:54px;bottom:0;width:260px;z-index:60;
    transform:translateX(-105%);transition:.15s;box-shadow:4px 0 14px rgba(0,0,0,.15)}
  body.sb-off .sidebar{display:block;transform:none}
  body.sb-off .layout{grid-template-columns:1fr}
  .plist{max-height:46vh}
  .topbar .brand span{display:none}
}
</style>
</head>
<body class="page-season">
<header class="topbar">
  <div class="brand"><b>__BRAND__</b><span id="totalBadge"></span></div>
  <input id="fSearch" type="search" placeholder="搜索：球队、判例内容、关键词…  (按 / 聚焦)">
  <a class="tbtn" href="index.html">🏠 首页</a>
  <a class="tbtn" href="season-2024.html">24评议</a>
  <a class="tbtn" href="season-2025.html">25评议</a>
  <a class="tbtn" href="__STATS__">📊 得失盘点</a>
  <a class="tbtn" href="rules.html">📖 竞赛规则</a>
  <button class="tbtn" id="btnHelp">？说明</button>
  <button class="tbtn" id="btnSb" title="收起/展开筛选">☰ 筛选</button>
</header>

<div class="filterbar" id="filterbar">
  <div class="filter-primary">
    <span class="filter-label">判定</span><div id="verList"></div>
    <span class="filter-label filter-label-fav">学习</span><div id="favList"></div>
    <button class="filter-action" id="btnExport">导出</button>
    <button class="filter-action" id="btnImport">导入</button>
    <input type="file" id="importFile" accept=".json,application/json" style="display:none">
  </div>
  <div class="filter-secondary">
    <span class="filter-label">筛选</span>
    <button class="filter-toggle" data-filter="compList">赛事 <span>⌄</span></button>
    <button class="filter-toggle" data-filter="teamList">球队 <span>⌄</span></button>
    <button class="filter-toggle" data-filter="issueList">期数 <span>⌄</span></button>
    <button class="filter-toggle" data-filter="catList">分类 <span>⌄</span></button>
    <a class="filter-stats" href="__STATS__">查看得失盘点 →</a>
  </div>
  <div class="filter-menus">
    <div id="compList" class="filter-menu"></div>
    <div id="teamList" class="filter-menu"></div>
    <div id="issueList" class="filter-menu"></div>
    <div id="catList" class="filter-menu"></div>
  </div>
</div>

<div class="layout">

  <section class="plist">
    <div class="plist-head" id="plistHead"><span id="issueTitle"></span><span>显示 <b id="shownCount">0</b> 例 · 点击行在右侧查看，<span class="kbd">↑</span><span class="kbd">↓</span> 切换</span></div>
    <div id="plistRows"></div>
  </section>

  <section class="detail" id="detail">
    <button class="mobile-back" id="mobileBack">← 返回判例列表</button>
    <div class="detail-empty" id="detailEmpty">← 从左侧列表选择判例开始学习</div>
    <div class="d-card" id="dcard" style="display:none">
      <div class="d-head" id="dHead"></div>
      <div class="d-video"><video id="dvid" controls preload="metadata" playsinline></video></div>
      <div class="vsw-row" id="vswRow" style="display:none"></div>
      <p class="d-note" id="dNote"></p>
      <div class="txt" id="dText"></div>
      <details class="d-note-box" id="dCatNote"><summary></summary><div></div></details>
      <div class="favtags" id="favTags" style="display:none"></div>
      <div class="notewrap" id="noteWrap" style="display:none">
        <textarea id="noteBox" placeholder="✏️ 写下你的学习笔记…（自动保存）"></textarea>
        <span class="nstatus" id="noteStatus"></span>
      </div>
      <div class="tags" id="dTags"></div>
      <div class="d-foot" id="dFoot"></div>
      <div class="d-nav">
        <button id="prevBtn">◀ 上一个 <span class="kbd">↑</span></button>
        <button id="nextBtn">下一个 <span class="kbd">↓</span> ▶</button>
      </div>
    </div>
  </section>
</div>

<!-- 统计弹层 -->
<div class="modal-mask" id="modalStats">
  <div class="modal matrix">
    <button class="close" data-close>关闭 ✕</button>
    <h3>判罚认定统计总表（按教学分类）</h3>
    <table><thead><tr>
      <th>分类</th><th>错漏判</th><th>支持原判</th><th>不予认定</th><th>小计</th>
      <th>其中 VAR错误</th><th>其中 涉及红牌</th><th>其中 涉及点球</th>
    </tr></thead><tbody id="mxBody"></tbody><tfoot id="mxFoot"></tfoot></table>
  </div>
</div>

<!-- 说明弹层 -->
<div class="modal-mask" id="modalHelp">
  <div class="modal help">
    <button class="close" data-close>关闭 ✕</button>
    <h3>使用说明与统计口径</h3>
    <div id="helpBody"></div>
  </div>
</div>

<button class="top-btn" onclick="document.getElementById('detail').scrollTo({top:0,behavior:'smooth'})">回到顶部</button>

<script>
const DATA = __DATA__;
const CATS = DATA.categories;
const VN = {wrong:"错漏判", correct:"支持原判", pending:"不予认定"};
const VICON = {wrong:"❌", correct:"✅", pending:"⚪"};
const VCLS = {wrong:"b-wrong", correct:"b-correct", pending:"b-pending"};
const bySeq = {};
DATA.cases.forEach(c => bySeq[c.seq] = c);
// 必须在applyFilter的自动选中改写hash之前捕获初始锚点
const initialHashSeq = (location.hash.match(/^#case-(\d+)$/)||[])[1];

// ---------- 收藏与笔记（localStorage 持久化，键按赛季隔离） ----------
const CFG = DATA.cfg;
const FAV_KEY = CFG.favKey, NOTE_KEY = CFG.noteKey;
const TAG_PRESETS = ["精选", "有疑问", "尺度标杆", "易错点", "课堂讨论"];
let fav = {}, notes = {};
try { fav = JSON.parse(localStorage.getItem(FAV_KEY) || "{}") || {}; } catch(_) { fav = {}; }
try { notes = JSON.parse(localStorage.getItem(NOTE_KEY) || "{}") || {}; } catch(_) { notes = {}; }
function persistFav() {
  try { localStorage.setItem(FAV_KEY, JSON.stringify(fav));
        localStorage.setItem(NOTE_KEY, JSON.stringify(notes)); } catch(_) {}
}
function isFav(seq) { return !!fav[seq]; }
function hasNote(seq) { return !!(notes[seq] && notes[seq].text && notes[seq].text.trim()); }
function crest(team, h) {
  const item = DATA.teams && DATA.teams[team];
  if (!item) return `<span class="team-badge" title="${esc(team)}：未登记">?</span>`;
  if (item.status === "verified" && item.path)
    return `<img class="crest" style="height:${h}px" src="${item.path}" alt="${esc(team)}队徽">`;
  const scale = Math.max(16, h);
  return `<span class="team-badge" style="width:${scale}px;height:${scale}px;--badge-fg:${item.fg};--badge-bg:${item.bg}" title="${esc(team)}：文字徽章（队徽待核验）" aria-label="${esc(team)}文字徽章">${esc(item.initials)}</span>`;
}

// 预聚合搜索串
for (const c of DATA.cases) {
  const match = [c.comp, c.round, (c.home&&c.away)?`${c.home} VS ${c.away}`:"", c.minute?`第${c.minute}分钟`:""]
    .filter(Boolean).join(" · ");
  c.search = (match+" "+c.desc+" "+c.appeal+" "+c.conclusion+" "+(c.tags||[]).join(" ")).toLowerCase();
}

// ---------- 侧栏 ----------
const catCount = {}, catWrong = {};
for (const c of DATA.cases) {
  catCount[c.category] = (catCount[c.category]||0)+1;
  if (c.v==="wrong") catWrong[c.category] = (catWrong[c.category]||0)+1;
}
const verCount = {all:DATA.cases.length, wrong:0, correct:0, pending:0};
for (const c of DATA.cases) verCount[c.v]++;

document.getElementById("totalBadge").textContent =
  `${DATA.cases.length}例 · 错漏判${verCount.wrong} · 支持原判${verCount.correct}`;
const badge = document.getElementById("totalBadge");
badge.style.cursor = "pointer";
badge.title = "点击查看分类统计总表";
badge.onclick = ()=>openModal("modalStats");
document.getElementById("catList").innerHTML =
  `<button class="cat-item on" data-cat=""><span class="nm">全部分类</span><b>${DATA.cases.length}</b></button>` +
  CATS.filter(k=>catCount[k.id]).map(k=>
    `<button class="cat-item" data-cat="${k.id}"><span class="nm">${k.icon} ${k.name}</span>` +
    `<b>${catCount[k.id]}</b><small>错${catWrong[k.id]||0}</small></button>`).join("");
document.getElementById("verList").innerHTML =
  `<button class="ver-item on" data-v=""><span class="vdot" style="background:#94a3b8"></span><span class="nm">全部判定</span><b>${verCount.all}</b></button>` +
  `<button class="ver-item" data-v="wrong"><span class="vdot" style="background:var(--red)"></span><span class="nm">❌ 错漏判</span><b>${verCount.wrong}</b></button>` +
  `<button class="ver-item" data-v="correct"><span class="vdot" style="background:#3a9d55"></span><span class="nm">✅ 支持原判</span><b>${verCount.correct}</b></button>` +
  `<button class="ver-item" data-v="pending"><span class="vdot" style="background:#d9a514"></span><span class="nm">⚪ 不予认定</span><b>${verCount.pending}</b></button>`;

// ---------- 状态与筛选 ----------
const state = {cat:"", v:"", issue:"", q:"", sel:null, vIdx:0, fav:null,
               comp:"", team:""};
const fSearch = document.getElementById("fSearch");

const COMP_ORDER = [["中超联赛","中超"],["中甲联赛","中甲"],["中乙联赛","中乙"],
                    ["女超联赛","女超"],["女甲联赛","女甲"],["中国足协杯","足协杯"],
                    ["全运会","全运会"],["三大球运动会","三大球"]];
const COMP_SHORT = Object.fromEntries(COMP_ORDER);
const teamComps = {};
for (const c of DATA.cases) {
  for (const t of new Set([c.home, c.away].filter(Boolean))) {
    (teamComps[t] = teamComps[t] || new Set()).add(c.comp);
  }
}
function teamBadge(t){
  return crest(t, 18);
}

// 除 skip 维度外的全部筛选（用于分面计数；skip 可为字符串或数组）
function baseMatch(c, skip){
  skip = Array.isArray(skip) ? skip : (skip ? [skip] : []);
  const sk = k => skip.includes(k);
  if (!sk("cat") && state.cat && c.category!==state.cat) return false;
  if (!sk("v") && state.v && c.v!==state.v) return false;
  if (!sk("issue") && state.issue && String(c.issue)!==state.issue) return false;
  if (!sk("comp") && state.comp && c.comp!==state.comp) return false;
  if (!sk("team") && state.team && c.home!==state.team && c.away!==state.team) return false;
  if (!sk("fav")){
    if (state.fav==="all" && !isFav(c.seq)) return false;
    if (state.fav==="note" && !hasNote(c.seq)) return false;
    if (state.fav && state.fav.startsWith("tag:")) {
      const t = state.fav.slice(4);
      if (!(fav[c.seq] && (fav[c.seq].tags||[]).includes(t))) return false;
    }
  }
  if (!sk("q")){ const q=state.q.trim().toLowerCase(); if(q && !c.search.includes(q)) return false; }
  return true;
}

function visibleCases(){
  return DATA.cases.filter(c => baseMatch(c, null));
}

// ---------- 侧栏：赛事/球队/期数（计数随其他筛选联动） ----------
function renderSidebar(){
  document.getElementById("compList").innerHTML =
    `<button class="cat-item ${state.comp===""?"on":""}" data-comp=""><span class="nm">全部赛事</span><b>${DATA.cases.filter(c=>baseMatch(c,["comp","team"])).length}</b></button>` +
    COMP_ORDER.map(([full,short])=>{
      const n = DATA.cases.filter(c=>baseMatch(c,["comp","team"]) && c.comp===full).length;
      return {full, short, n};
    }).filter(x=>x.n>0 || state.comp===x.full)
      .map(x=>`<button class="cat-item ${state.comp===x.full?"on":""}" data-comp="${x.full}"><span class="nm">${x.short}</span><b>${x.n}</b></button>`).join("");
  const teams = {};
  for (const c of DATA.cases) {
    if (!baseMatch(c,"team")) continue;
    if (state.comp && c.comp!==state.comp) continue;
    for (const t of new Set([c.home,c.away].filter(Boolean))) teams[t]=(teams[t]||0)+1;
  }
  document.getElementById("teamList").innerHTML =
    Object.entries(teams).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).map(([t,n])=>
      `<button class="cat-item ${state.team===t?"on":""}" data-team="${esc(t)}">${teamBadge(t)}<span class="nm">${esc(t)}</span><b>${n}</b></button>`).join("") ||
    `<div style="font-size:12.5px;color:var(--muted);padding:6px 8px">该赛事下无判例</div>`;
  document.getElementById("issueList").innerHTML =
    Array.from({length:CFG.issueCount},(_,k)=>k+1).map(i=>{
      const n = DATA.cases.filter(c=>baseMatch(c,"issue") && String(c.issue)===String(i)).length;
      return `<button class="cat-item ${String(state.issue)===String(i)?"on":""}" data-issue="${i}"><span class="nm">第${i}期</span><b>${n}</b></button>`;
    }).join("");
}

function renderList(){
  const list = visibleCases();
  const issueTitle = document.getElementById("issueTitle");
  if (state.issue) {
    const iss = DATA.issues[state.issue];
    issueTitle.innerHTML = `第${state.issue}期 · ${esc(iss.title)} · ${iss.date.slice(0,4)}-${iss.date.slice(4,6)}-${iss.date.slice(6,8)}发布 · `;
  } else {
    issueTitle.innerHTML = "";
  }
  document.getElementById("shownCount").textContent = list.length;
  const groups = {};
  list.forEach(c => (groups[c.category] = groups[c.category]||[]).push(c));
  const rows = CATS.filter(k=>groups[k.id]).map(k =>
    `<div class="ph">${k.icon} ${k.name} <b>${groups[k.id].length}例</b></div>` +
    groups[k.id].map(c=>{
      const short = (c.comp||"").replace("联赛","");
      const varChip = c.var==="none" ? "" :
        `<span class="rv ${c.var==="wrong"?"bad":""}">V${c.var==="wrong"?"✗":"✓"}</span>`;
      return `<div class="prow ${state.sel===c.seq?"sel":""}" data-seq="${c.seq}">
        <span class="dot ${c.v}"></span>
        <span class="ptxt"><b>${crest(c.home,16)}${esc(c.home)} <span style="color:var(--muted);font-weight:400">vs</span> ${crest(c.away,16)}${esc(c.away)}</b>
        <i><span class="p-source">${esc(short)}${c.round?esc(c.round):""}${c.minute?" · 第"+c.minute+"分钟":""}</span> · <span class="p-case-id">第${c.issue}期-判例${c.no}</span> · <span class="p-verdict">${VN[c.v]}</span></i></span>
        <span class="pmark">${isFav(c.seq)?"★":""}${hasNote(c.seq)?"📝":""}</span>
        ${varChip}</div>`;
    }).join("")).join("");
  document.getElementById("plistRows").innerHTML = rows ||
    `<div class="plist-empty">没有符合条件的判例，请调整筛选。</div>`;
}

function applyFilter(){
  renderSidebar();
  renderFavList();
  renderList();
  const list = visibleCases();
  if (!list.some(c=>c.seq===state.sel)) {
    if (list.length) select(list[0].seq, false); else clearDetail();
  }
}

function clearDetail(){
  state.sel = null;
  document.getElementById("dcard").style.display = "none";
  document.getElementById("detailEmpty").style.display = "flex";
  const v = document.getElementById("dvid");
  try{ v.pause(); }catch(_){}
  v.removeAttribute("src"); v.load();
}

function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}

// ---------- 选中判例 ----------
function select(seq, scrollRow=true){
  const c = bySeq[seq]; if (!c) return;
  if (window.matchMedia && window.matchMedia("(max-width:900px)").matches)
    document.body.classList.add("detail-open");
  state.sel = seq;
  const iss = DATA.issues[c.issue];
  document.getElementById("detailEmpty").style.display = "none";
  document.getElementById("dcard").style.display = "block";
  const match = [c.comp, c.round, (c.home&&c.away)?`${c.home} VS ${c.away}`:"", c.minute?`第${c.minute}分钟`:""]
    .filter(Boolean).join(" · ");
  const matchHTML = match
    .replace(c.home, `${crest(c.home,22)}${esc(c.home)}`)
    .replace(c.away, `${crest(c.away,22)}${esc(c.away)}`);
  const varBadge = c.var==="none" ? "" :
    `<span class="badge b-var ${c.var==="wrong"?"bad":""}">VAR${c.var==="wrong"?"错误":"正确"}</span>`;
  document.getElementById("dHead").innerHTML =
    `<span class="cid">第${c.issue}期 · 判例${c.no}</span>
     <span class="badge ${VCLS[c.v]}">${VICON[c.v]} ${VN[c.v]}</span>${varBadge}
     <button class="favbtn ${isFav(c.seq)?"on":""}" id="favBtn" title="收藏该判例">${isFav(c.seq)?"★ 已收藏":"☆ 收藏"}</button>
     <h2 class="match">${matchHTML}</h2>`;
  renderFavUI(c);
  renderNoteUI(c);
  // 视频（唯一播放器，切换即替换）
  state.vIdx = 0;
  const vid = document.getElementById("dvid");
  try{ vid.pause(); }catch(_){}
  vid.src = "videos/" + c.videos[0];
  const vsr = document.getElementById("vswRow");
  if (c.videos.length > 1) {
    vsr.style.display = "flex";
    vsr.innerHTML = c.videos.map((f,i)=>
      `<button class="vsw ${i===0?"on":""}" data-i="${i}">${/-(2|3)\.mp4$/.test(f)&&i>0?"补充角度":"视频"+(i+1)}</button>`).join("");
  } else { vsr.style.display = "none"; vsr.innerHTML = ""; }
  document.getElementById("dNote").textContent =
    c.videos.length>1 ? "同判例存在多个角度视频，可切换：" : "";
  // 正文
  document.getElementById("dText").innerHTML =
    `<p>${esc(c.desc.replace(/^判例[一二三四五六七八九十百]+[：:]/,"").trim())}</p>` +
    (c.appeal?`<p><span class="lbl">申诉意见：</span>${esc(c.appeal.replace(/^[^：]*申诉意见认为：/,"").trim())}</p>`:"") +
    `<p class="concl"><span class="lbl">评议组认定：</span>${esc(c.conclusion
      .replace(/^对于此判[例罚]，评议组[^：]*认为：/,"").trim())}</p>`;
  const catMeta = CATS.find(k=>k.id===c.category);
  document.getElementById("dCatNote").querySelector("summary").textContent =
    `📏 ${catMeta ? catMeta.name : ""} · 统一尺度要点`;
  document.getElementById("dCatNote").querySelector("div").textContent =
    DATA.notes[c.category] || "";
  document.getElementById("dTags").innerHTML =
    (c.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join("");
  document.getElementById("dFoot").innerHTML =
    `来源：<a href="${iss.url}" target="_blank" rel="noopener">${esc(iss.title)}</a>（${iss.date.slice(0,4)}-${iss.date.slice(4,6)}-${iss.date.slice(6,8)}发布）`;
  document.getElementById("detail").scrollTop = 0;
  // 列表高亮
  document.querySelectorAll(".prow.sel").forEach(e=>e.classList.remove("sel"));
  const row = document.querySelector(`.prow[data-seq="${seq}"]`);
  if (row && scrollRow) row.scrollIntoView({block:"nearest"});
  if (row) row.classList.add("sel");
  history.replaceState(null, "", "#case-"+seq);
}

function step(dir){
  const list = visibleCases();
  if (!list.length) return;
  let i = list.findIndex(c=>c.seq===state.sel);
  i = i<0 ? 0 : Math.min(list.length-1, Math.max(0, i+dir));
  select(list[i].seq);
}

// ---------- 收藏与笔记 ----------
function toggleFav(seq){
  const c = bySeq[seq]; if(!c) return;
  if (isFav(seq)) delete fav[seq];
  else fav[seq] = {tags: [], ts: Date.now()};
  persistFav();
  renderFavUI(c); renderFavList();
  const row = document.querySelector(`.prow[data-seq="${seq}"] .pmark`);
  if (row) row.textContent = (isFav(seq)?"★":"") + (hasNote(seq)?"📝":"");
}
function renderFavUI(c){
  const btn = document.getElementById("favBtn");
  if (!btn) return;
  btn.classList.toggle("on", isFav(c.seq));
  btn.innerHTML = isFav(c.seq) ? "★ 已收藏" : "☆ 收藏";
  const box = document.getElementById("favTags");
  if (!isFav(c.seq)) { box.style.display = "none"; return; }
  box.style.display = "flex";
  const cur = (fav[c.seq].tags||[]);
  const customs = cur.filter(t=>!TAG_PRESETS.includes(t));
  box.innerHTML =
    `<span style="font-size:13px;color:var(--muted)">收藏标签:</span>` +
    TAG_PRESETS.map(t=>`<span class="ftag ${cur.includes(t)?"on":""}" data-tag="${t}">${t}</span>`).join("") +
    customs.map(t=>`<span class="ftag on" data-tag="${esc(t)}">${esc(t)} <b data-del="${esc(t)}" style="cursor:pointer">✕</b></span>`).join("") +
    `<input id="customTag" placeholder="自定义标签"><button class="ftag" id="addTag">添加</button>`;
}
document.getElementById("favTags").addEventListener("click", e=>{
  const del = e.target.closest("[data-del]");
  if (del) {
    const c = bySeq[state.sel]; if(!c) return;
    const arr = fav[c.seq]?.tags || [];
    fav[c.seq].tags = arr.filter(t=>t!==del.dataset.del);
    persistFav(); renderFavUI(c); renderFavList();
    return;
  }
  if (e.target.id === "addTag") {
    const c = bySeq[state.sel]; if(!c) return;
    const inp = document.getElementById("customTag");
    const t = (inp.value||"").trim();
    if (!t) return;
    if (!fav[c.seq]) fav[c.seq] = {tags:[], ts:Date.now()};
    fav[c.seq].tags = fav[c.seq].tags||[];
    if (!fav[c.seq].tags.includes(t)) fav[c.seq].tags.push(t);
    persistFav(); renderFavUI(c); renderFavList();
    return;
  }
  const chip = e.target.closest(".ftag[data-tag]");
  if (chip) {
    const c = bySeq[state.sel]; if(!c) return;
    if (!fav[c.seq]) fav[c.seq] = {tags:[], ts:Date.now()};
    fav[c.seq].tags = fav[c.seq].tags||[];
    const t = chip.dataset.tag;
    if (fav[c.seq].tags.includes(t)) fav[c.seq].tags = fav[c.seq].tags.filter(x=>x!==t);
    else fav[c.seq].tags.push(t);
    persistFav(); renderFavUI(c); renderFavList();
  }
});
document.getElementById("dHead").addEventListener("click", e=>{
  if (e.target.closest("#favBtn")) toggleFav(state.sel);
});
function renderNoteUI(c){
  const wrap = document.getElementById("noteWrap");
  wrap.style.display = "block";
  document.getElementById("noteBox").value = (notes[c.seq]&&notes[c.seq].text)||"";
  document.getElementById("noteStatus").textContent =
    hasNote(c.seq) ? "已保存" : "自动保存，无需手动确认";
}
let noteTimer = null;
document.getElementById("noteBox").addEventListener("input", ()=>{
  const seq = state.sel; if(!seq) return;
  document.getElementById("noteStatus").textContent = "正在保存…";
  clearTimeout(noteTimer);
  noteTimer = setTimeout(()=>{
    const t = document.getElementById("noteBox").value;
    if (t.trim()) notes[seq] = {text: t, ts: Date.now()};
    else delete notes[seq];
    persistFav();
    const d = new Date();
    document.getElementById("noteStatus").textContent =
      "已保存 " + String(d.getHours()).padStart(2,"0") + ":" + String(d.getMinutes()).padStart(2,"0");
    renderFavList();
    const row = document.querySelector(`.prow[data-seq="${seq}"] .pmark`);
    if (row) row.textContent = (isFav(seq)?"★":"") + (hasNote(seq)?"📝":"");
  }, 800);
});
function renderFavList(){
  const tags = {};
  for (const f of Object.values(fav)) for (const t of (f.tags||[])) tags[t]=(tags[t]||0)+1;
  const nAll = Object.keys(fav).length;
  const nNote = Object.values(notes).filter(n=>n.text&&n.text.trim()).length;
  const cur = state.fav;
  const item = (val, label, n) =>
    `<button class="ver-item ${cur===val?"on":""}" data-fav="${val}"><span class="nm">${label}</span><b>${n}</b></button>`;
  let h = item("", "全部", DATA.cases.length) + item("all", "★ 收藏", nAll) + item("note", "📝 笔记", nNote);
  for (const t of TAG_PRESETS) h += item("tag:"+t, t, tags[t]||0);
  for (const t of Object.keys(tags)) if (!TAG_PRESETS.includes(t)) h += item("tag:"+t, t, tags[t]);
  document.getElementById("favList").innerHTML = h;
}
document.getElementById("favList").addEventListener("click", e=>{
  const b = e.target.closest("[data-fav]"); if(!b) return;
  state.fav = (state.fav === b.dataset.fav) ? null : b.dataset.fav;
  renderFavList();
  applyFilter();
});
document.getElementById("btnExport").onclick = ()=>{
  const blob = new Blob([JSON.stringify({fav, notes, exported: new Date().toISOString(), app:"cfa-referee-review-"+CFG.season}, null, 1)],
    {type:"application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = CFG.season + "赛季-收藏与笔记.json";
  a.click();
  URL.revokeObjectURL(a.href);
};
document.getElementById("btnImport").onclick = ()=>document.getElementById("importFile").click();
document.getElementById("importFile").addEventListener("change", e=>{
  const f = e.target.files[0]; if(!f) return;
  const rd = new FileReader();
  rd.onload = () => {
    try {
      const d = JSON.parse(rd.result);
      let n = 0;
      for (const [s, v] of Object.entries(d.fav||{})) {
        if (!fav[s] || (v.ts||0) > (fav[s].ts||0)) { fav[s] = v; n++; }
      }
      for (const [s, v] of Object.entries(d.notes||{})) {
        if (!notes[s] || (v.ts||0) > (notes[s].ts||0)) { notes[s] = v; n++; }
      }
      persistFav(); renderFavList(); applyFilter();
      alert(`导入完成：合并了 ${n} 条记录`);
    } catch(err) { alert("导入失败：文件不是有效的导出JSON"); }
  };
  rd.readAsText(f, "utf-8");
  e.target.value = "";
});

// ---------- 事件绑定 ----------
document.getElementById("plistRows").addEventListener("click", e=>{
  const row = e.target.closest(".prow");
  if (row) select(+row.dataset.seq);
});
document.getElementById("catList").addEventListener("click", e=>{
  const b = e.target.closest(".cat-item"); if(!b) return;
  state.cat = b.dataset.cat;
  document.querySelectorAll(".cat-item").forEach(x=>x.classList.toggle("on", x===b));
  applyFilter();
});
document.getElementById("verList").addEventListener("click", e=>{
  const b = e.target.closest(".ver-item"); if(!b) return;
  state.v = b.dataset.v;
  document.querySelectorAll(".ver-item").forEach(x=>x.classList.toggle("on", x===b));
  applyFilter();
});
fSearch.addEventListener("input", ()=>{ state.q = fSearch.value; applyFilter(); });
fSearch.addEventListener("search", ()=>{ state.q = fSearch.value; applyFilter(); }); // 搜索框✕清空按钮
fSearch.addEventListener("search", ()=>{ state.q = fSearch.value; applyFilter(); }); // 搜索框✕清空按钮
document.getElementById("compList").addEventListener("click", e=>{
  const b = e.target.closest("[data-comp]"); if(!b) return;
  state.comp = (state.comp===b.dataset.comp) ? "" : b.dataset.comp;
  state.team = "";   // 切回按赛事浏览
  applyFilter();
});
document.getElementById("teamList").addEventListener("click", e=>{
  const b = e.target.closest("[data-team]"); if(!b) return;
  state.team = (state.team===b.dataset.team) ? "" : b.dataset.team;
  state.comp = "";   // 球队跨赛事聚合：显示该队全部判例
  applyFilter();
});
document.getElementById("issueList").addEventListener("click", e=>{
  const b = e.target.closest("[data-issue]"); if(!b) return;
  state.issue = (String(state.issue)===b.dataset.issue) ? "" : b.dataset.issue;
  applyFilter();
});
document.getElementById("prevBtn").onclick = ()=>step(-1);
document.getElementById("nextBtn").onclick = ()=>step(1);
document.getElementById("vswRow").addEventListener("click", e=>{
  const b = e.target.closest(".vsw"); if(!b) return;
  const c = bySeq[state.sel]; if(!c) return;
  state.vIdx = +b.dataset.i;
  const vid = document.getElementById("dvid");
  try{ vid.pause(); }catch(_){}
  vid.src = "videos/" + c.videos[state.vIdx];
  document.querySelectorAll(".vsw").forEach(x=>x.classList.toggle("on", x===b));
});
document.getElementById("btnSb").onclick = ()=>{
  document.body.classList.toggle("filters-off");
};
document.getElementById("mobileBack").onclick = ()=>document.body.classList.remove("detail-open");
document.querySelectorAll(".filter-toggle").forEach(btn=>{
  btn.onclick = e=>{
    e.stopPropagation();
    const menu = document.getElementById(btn.dataset.filter);
    const open = menu.classList.toggle("open");
    document.querySelectorAll(".filter-menu").forEach(other=>{ if(other!==menu) other.classList.remove("open"); });
    document.querySelectorAll(".filter-toggle").forEach(other=>other.classList.toggle("on", other===btn && open));
  };
});
document.addEventListener("click", e=>{
  if (!e.target.closest(".filterbar")) {
    document.querySelectorAll(".filter-menu").forEach(menu=>menu.classList.remove("open"));
    document.querySelectorAll(".filter-toggle").forEach(btn=>btn.classList.remove("on"));
  }
});
document.getElementById("btnHelp").onclick = ()=>openModal("modalHelp");
document.querySelectorAll("[data-close]").forEach(b=>
  b.onclick = ()=>b.closest(".modal-mask").classList.remove("open"));
document.querySelectorAll(".modal-mask").forEach(m=>
  m.addEventListener("click", e=>{ if(e.target===m) m.classList.remove("open"); }));
function openModal(id){ document.getElementById(id).classList.add("open"); }

document.addEventListener("keydown", e=>{
  const tag = (e.target.tagName||"").toLowerCase();
  if (tag==="input"||tag==="select"||tag==="textarea") {
    if (e.key==="Escape") e.target.blur();
    return;
  }
  if (e.key==="/"){ e.preventDefault(); fSearch.focus(); return; }
  if (e.key==="Escape"){ document.querySelectorAll(".modal-mask.open")
      .forEach(m=>m.classList.remove("open")); return; }
  if (e.key==="ArrowDown"){ e.preventDefault(); step(1); }
  if (e.key==="ArrowUp"){ e.preventDefault(); step(-1); }
});

// ---------- 统计弹层 ----------
const hasRed = t => (t||[]).includes("红牌");
const hasPen = t => (t||[]).includes("点球");
{
  const byCat = {};
  CATS.forEach(k=>byCat[k.id]=[]);
  DATA.cases.forEach(c=>byCat[c.category].push(c));
  let rows="", sW=0,sG=0,sP=0,sV=0,sR=0,sPen=0;
  for (const k of CATS){
    const list = byCat[k.id]; if(!list.length) continue;
    const w=list.filter(c=>c.v==="wrong").length, g=list.filter(c=>c.v==="correct").length,
          p=list.filter(c=>c.v==="pending").length,
          vw=list.filter(c=>c.var==="wrong").length,
          r=list.filter(c=>(c.tags||[]).includes("红牌")).length,
          pen=list.filter(c=>(c.tags||[]).includes("点球")).length;
    sW+=w;sG+=g;sP+=p;sV+=vw;sR+=r;sPen+=pen;
    rows += `<tr><td>${k.icon} ${k.name}</td><td class="w">${w}</td><td class="g">${g}</td>
      <td class="p">${p}</td><td>${list.length}</td><td>${vw}</td><td>${r}</td><td>${pen}</td></tr>`;
  }
  document.getElementById("mxBody").innerHTML = rows;
  document.getElementById("mxFoot").innerHTML =
    `<tr><td>合计</td><td class="w">${sW}</td><td class="g">${sG}</td><td class="p">${sP}</td>
     <td>${sW+sG+sP}</td><td>${sV}</td><td>${sR}</td><td>${sPen}</td></tr>`;
}

// ---------- 说明弹层 ----------
{
  const issNotes = Object.entries(DATA.issueNotes)
    .map(([k,v])=>`第${k}期：${v.replace(/。$/,"")}`).join("；");
  document.getElementById("helpBody").innerHTML = `
    <p><b>判定口径：</b>「错漏判」指评议组认定裁判员（或助理裁判员）判罚决定错误/漏判；「支持原判」指评议组支持临场决定；「不予认定」指现有视频无法判断、评议组不做认定。VAR错误单独标注。</p>
    <p><b>操作方法：</b>左侧自上而下：赛事（中超/中甲/中乙等）→ 球队（跨赛事聚合，如广州豹同时列出其中甲与足协杯判例）→ 评议期数（按原网页一期一期浏览，选中后列表头显示该期官方标题）→ 犯规分类 → 判定 → 我的收藏；中间列表点选判例，右侧大屏学习；<span class="kbd">↑</span><span class="kbd">↓</span> 键切换上一个/下一个判例，<span class="kbd">/</span> 聚焦搜索，<span class="kbd">Esc</span> 关闭弹层；「☰ 侧栏」可收起侧栏获得更宽画面。</p>
    <p><b>收藏与笔记：</b>在详情区点「☆ 收藏」收藏判例并可打多个标签（精选/有疑问/尺度标杆/易错点/课堂讨论/自定义），笔记自动保存。收藏的判例在列表中显示★，可通过左侧「我的收藏」按标签筛选。数据存于浏览器 localStorage；用「导出/导入」按钮可在不同浏览器或 file:// 与 http:// 两种打开方式之间同步。</p>
    <p><b>数据来源：</b>中国足球协会官方网站「裁判评议结果发布」栏目，${CFG.issueDesc}。每条判例附原文链接。</p>
    <p><b>期数口径注释：</b>${issNotes ? issNotes + "。" : ""}其余各期与官方标题认定数一致。</p>
    <p><b>离线使用：</b>将本页 HTML 与 videos 文件夹放在一起，双击即可离线学习；配套页面 <a href="${CFG.stats}" target="_blank">${CFG.stats}</a> 为各队得失盘点。</p>
    <p><b>声明：</b>本合集为教学研究用途，判罚认定权属于中国足协裁判委员会评议组。</p>`;
}

// ---------- 初始化 ----------
applyFilter();
{ // 支持 #case-N 锚点（来自 stats.html 的跳转或刷新恢复）
  const target = initialHashSeq ? bySeq[+initialHashSeq] : null;
  if (target && !visibleCases().some(x=>x.seq===target.seq)) {
    // 目标判例被当前筛选挡住时，清空各筛选（锚点跳转优先）
    state.cat = target.category; state.v = ""; state.issue = ""; state.q = "";
    state.comp = ""; state.team = "";
    fSearch.value = "";
    document.querySelectorAll(".cat-item").forEach(x=>
      x.classList.toggle("on", x.dataset.cat===target.category));
    document.querySelectorAll(".ver-item").forEach(x=>
      x.classList.toggle("on", x.dataset.v===""));
    applyFilter();
  }
  const list = visibleCases();
  if (target && bySeq[target.seq]) {
    select(target.seq);
    const row = document.querySelector(`.prow[data-seq="${target.seq}"]`);
    if (row) row.scrollIntoView({block:"center"});
  } else if (list.length) {
    select(list[0].seq, false);
  }
}
// 同文档hash变化（如页面内跳转/前进后退）时同步选中
window.addEventListener("hashchange", () => {
  const m = location.hash.match(/^#case-(\d+)$/);
  if (m && bySeq[+m[1]] && state.sel !== +m[1]) select(+m[1]);
});
</script>
</body>
</html>
"""


def build_season(season):
    cfg = SEASONS[season]
    data = build_data(season)
    data_js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = inject_theme(HTML
            .replace("__DATA__", data_js)
            .replace("__TITLE__", cfg["title"])
            .replace("__BRAND__", cfg["brand"])
            .replace("__STATS__", cfg["stats"]))
    SITE.mkdir(parents=True, exist_ok=True)
    out = SITE / cfg["out"]
    out.write_text(html, encoding="utf-8")
    print(f"[{season}] 生成 {out}  ({len(html.encode('utf-8'))/1024:.0f} KB, "
          f"{len(data['cases'])}判例)")


def main():
    seasons = sys.argv[1:] or ["2025", "2024"]
    for season in seasons:
        if season not in SEASONS:
            raise SystemExit(f"未知赛季: {season}（可选: {'/'.join(SEASONS)}）")
        build_season(season)


if __name__ == "__main__":
    main()
