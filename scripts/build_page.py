# -*- coding: utf-8 -*-
"""生成各赛季合集页 season-2025.html / season-2024.html（单文件离线可用）
布局: 单行顶栏 | 侧栏(分类/判定) | 播放列表(密集行) | 详情区(大视频+全文)
内存: 详情区唯一<video>, 选中即载入, 切换即替换
用法: python build_page.py [2025] [2024]   # 不带参数=两个赛季都构建
"""
import json
import sys
from datetime import date

from lib.crest_catalog import load_catalog, normalize_team
from lib.theme import inject_theme, icon, js_icons, topbar

from lib.paths import DATA, SITE

# 赛季配置（输出文件/存储键/期数/统计页链接）
SEASONS = {
    "2026": {
        "out": "season-2026.html",
        "title": "2026赛季中国足协裁判评议全集 · 新裁判教学合集",
        "brand": "2026评议合集",
        "stats": "stats-2026.html",
        "issueCount": 22,
        "issueDesc": "2026赛季第1—22期（赛季进行中，持续更新）",
        "favKey": "cfa2026.fav",
        "noteKey": "cfa2026.notes",
    },
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
    "2026": {
        3: "本期标题认定7例；合集另计入2例「申诉问题支持原判但漏判黄牌」的纪律处罚漏判（判例四、判例十五），官方标题口径未计入。",
        4: "本期标题认定5例；合集另计入点球重罚程序错误与越位误判等纪律/程序类错误。",
        5: "本期标题认定3例；合集另计入1例漏判黄牌与1例漏判越位进球。",
        6: "本期标题认定6例；合集另计入1例漏判黄牌。",
        7: "本期标题认定8例；合集另计入3例纪律处罚漏判与越位误判类错误。",
        8: "本期标题认定5例；合集另计入1例漏判黄牌。",
        10: "本期标题认定5例；合集另计入1例多余黄牌。",
        11: "本期标题口径为「本轮中超无错漏判」（本期中超判例均支持原判）；合集另计入本期中甲/中乙错漏判6例。",
        13: "本期标题认定5例；合集另计入1例多余黄牌。",
        14: "本期标题认定2例；合集另计入1例漏判黄牌。",
        16: "本期标题认定4例；合集另计入1例漏判黄牌。",
        19: "本期标题认定3例；合集另计入1例多余黄牌。",
        22: "本期标题口径为「本轮中超无错漏判」（本期无中超判例）；合集计入中甲/中乙错漏判2例。",
    },
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
    data = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
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
/* ===== season 页专属布局 (颜色/组件来自 data-cfa-theme 设计系统,此处只管结构) ===== */
body{overflow:hidden}
.workspace{display:grid;grid-template-columns:276px minmax(0,356px) minmax(0,1fr);
  height:calc(100vh - var(--top-h));min-height:0}
body.sb-off .workspace{grid-template-columns:0 minmax(0,356px) minmax(0,1fr)}
body.sb-off .sidebar{display:none}

/* ---- 侧栏筛选 ---- */
.sidebar{background:var(--bg2);border-right:1px solid var(--line);display:flex;flex-direction:column;min-height:0}
.side-scroll{flex:1;min-height:0;overflow-y:auto;padding:10px 12px 18px}
.side-h{font-size:11px;font-weight:700;color:var(--muted);letter-spacing:2px;margin:15px 4px 7px;display:flex;align-items:center;gap:6px}
.side-h:first-child{margin-top:2px}
#verList,#favList,#compList{display:flex;flex-wrap:wrap;gap:6px}
.ver-item{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border:1px solid var(--line);
  border-radius:999px;background:var(--card);color:var(--ink2);font-size:12.5px;cursor:pointer;
  font-family:inherit;transition:.15s;text-align:left}
.ver-item:hover{border-color:var(--brand);color:var(--brand)}
.ver-item.on{background:var(--info-bg);border-color:var(--brand);color:var(--brand);font-weight:600}
.ver-item b{font-size:11px;color:var(--muted);font-weight:600}
.ver-item.on b{color:var(--brand)}
#catList{display:flex;flex-direction:column;gap:2px}
.cat-item{display:flex;align-items:center;gap:8px;width:100%;text-align:left;padding:6.5px 9px;
  border:1px solid transparent;background:none;border-radius:var(--r-sm);cursor:pointer;
  font-size:13px;color:var(--ink2);font-family:inherit;transition:.12s}
.cat-item:hover{background:var(--card2);color:var(--ink)}
.cat-item.on{background:var(--info-bg);color:var(--brand);font-weight:600}
.cat-item .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cat-item b{font-weight:600;font-size:11.5px;color:var(--muted)}
.cat-item small{color:var(--red);font-size:10.5px}
.cat-item.on b{color:var(--brand)}
#issueList{display:grid;grid-template-columns:repeat(6,1fr);gap:5px}
#issueList .cat-item{flex-direction:column;gap:1px;padding:5px 2px;text-align:center;justify-content:center;
  border:1px solid var(--line);background:var(--card);border-radius:var(--r-sm)}
#issueList .cat-item .nm{flex:none;font-size:11.5px}
#issueList .cat-item b{font-size:10px}
#issueList .cat-item.on{background:var(--brand-strong);color:var(--on-brand)}
#issueList .cat-item.on b{color:var(--on-brand);opacity:.85}
#teamList{display:flex;flex-direction:column;gap:1px;max-height:232px;overflow-y:auto;
  border:1px solid var(--line2);border-radius:var(--r-sm);background:var(--card);padding:3px}
#teamList .cat-item{padding:4.5px 7px;font-size:12.5px}
#teamList .crest{height:16px}
.team-empty{font-size:12px;color:var(--muted);padding:7px 9px}
.side-actions{display:flex;gap:7px;margin-top:9px}
.side-actions .btn{flex:1;padding:6px 8px;font-size:12.5px}
.side-link{display:flex;align-items:center;justify-content:center;gap:7px;width:100%;margin-top:14px;
  padding:8px;border-radius:var(--r-sm);border:1px dashed var(--line);background:none;
  color:var(--brand);cursor:pointer;font-size:13px;font-weight:600;font-family:inherit}
.side-link:hover{border-color:var(--brand);background:var(--info-bg)}

/* ---- 播放列表 ---- */
.plist{display:flex;flex-direction:column;min-height:0;border-right:1px solid var(--line);background:var(--bg2)}
.plist-head{flex:none;display:flex;flex-direction:column;gap:2px;padding:9px 14px 8px;
  border-bottom:1px solid var(--line);background:var(--bg2)}
.plist-head .iss{font-size:12.5px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.plist-head .cnt{font-size:12px;color:var(--muted)}
.plist-head .cnt b{color:var(--brand);font-weight:700}
.plist-rows{flex:1;min-height:0;overflow-y:auto;background:var(--card)}
.ph{position:sticky;top:0;z-index:4;display:flex;align-items:center;gap:8px;padding:6px 14px;
  font-family:var(--font-display);font-size:12.5px;font-weight:700;letter-spacing:.8px;
  color:var(--ink);background:var(--card2);border-bottom:1px solid var(--line2)}
.ph b{color:var(--brand);font-weight:600}
.prow{display:flex;align-items:center;gap:9px;padding:8px 13px;cursor:pointer;
  border-bottom:1px solid var(--line2);transition:background .12s}
.prow:hover{background:var(--card2)}
.prow.sel{background:var(--info-bg);box-shadow:inset 3px 0 0 var(--brand)}
.prow .ptxt{flex:1;min-width:0}
.prow .ptxt b{display:flex;align-items:center;font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden}
.prow .ptxt .vs{color:var(--faint);font-weight:400;font-size:11.5px;margin:0 2px}
.prow .ptxt i{display:block;font-style:normal;font-size:11.5px;color:var(--muted);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prow .rv{flex:none;font-size:10.5px;border-radius:5px;padding:1px 6px;background:var(--info-bg);color:var(--info);font-weight:600}
.prow .rv.bad{background:var(--red-bg);color:var(--red)}
.prow .pmark{flex:none;display:inline-flex;color:var(--amber);gap:2px}
.prow .pmark .ic{vertical-align:0}
.plist-empty{padding:48px 16px;text-align:center;color:var(--muted)}

/* ---- 详情区 ---- */
.detail{min-width:0;min-height:0;overflow-y:auto;padding:16px 20px 44px}
.detail-empty{height:70vh;display:flex;flex-direction:column;gap:12px;align-items:center;justify-content:center;color:var(--faint);font-size:14.5px}
.d-card{max-width:1120px;background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:18px 22px 16px;box-shadow:var(--shadow-sm)}
.d-head{display:flex;flex-wrap:wrap;align-items:center;gap:9px;margin-bottom:2px}
.cid{color:var(--muted);font-size:12.5px;background:var(--card2);border:1px solid var(--line);
  border-radius:6px;padding:2px 10px;white-space:nowrap}
.d-head .match{flex-basis:100%;display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin:2px 0 0;
  font-family:var(--font-display);font-size:21px;font-weight:700;line-height:1.5;letter-spacing:.3px}
.d-head .match .crest{height:24px}
.d-video{max-width:960px;margin:13px auto 6px}
.d-video video{width:100%;aspect-ratio:16/9;background:#000;border-radius:var(--r-md);display:block}
.vsw-row{display:flex;gap:8px;margin:9px 0 2px}
.vsw{padding:3px 13px;border-radius:999px;border:1px solid var(--line);background:var(--card2);
  cursor:pointer;font-size:12.5px;color:var(--muted);font-family:inherit}
.vsw.on{background:var(--brand-strong);border-color:var(--brand-strong);color:var(--on-brand)}
.d-note{font-size:12.5px;color:var(--muted);margin:4px 0 0}
.txt{font-size:15px;margin-top:10px;max-width:960px;margin-left:auto;margin-right:auto}
.txt .lbl{color:var(--brand);font-weight:700}
.txt p{margin:9px 0;white-space:pre-wrap}
.txt .concl{background:var(--card2);border-left:3px solid var(--brand);
  padding:11px 15px;border-radius:0 var(--r-md) var(--r-md) 0;font-size:15.5px}
.d-note-box{margin-top:13px;font-size:13.5px;background:var(--card2);border:1px solid var(--line);
  border-radius:var(--r-md);padding:9px 14px;max-width:960px;margin-left:auto;margin-right:auto}
.d-note-box summary{cursor:pointer;color:var(--brand);font-weight:600;user-select:none}
.d-note-box div{margin-top:7px;color:var(--ink2);line-height:1.8}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.tag{font-size:12px;color:var(--muted);background:var(--card2);border:1px solid var(--line2);
  border-radius:5px;padding:2px 9px}
.d-foot{font-size:13px;margin-top:13px;color:var(--muted)}
.d-foot a{color:var(--brand);text-decoration:none}
.d-foot a:hover{text-decoration:underline}
.d-nav{display:flex;gap:10px;margin-top:15px;max-width:960px}
.d-nav button{flex:1;display:flex;align-items:center;justify-content:center;gap:7px;padding:10px;
  border-radius:var(--r-md);border:1px solid var(--line);background:var(--card2);cursor:pointer;
  font-size:14px;color:var(--ink2);font-family:inherit}
.d-nav button:hover{border-color:var(--brand);color:var(--brand)}
.favbtn{display:inline-flex;align-items:center;gap:5px;padding:3.5px 13px;border-radius:999px;
  border:1px solid var(--line);background:var(--card2);cursor:pointer;font-size:13px;color:var(--muted);font-family:inherit}
.favbtn.on{background:var(--amber-bg);border-color:var(--amber);color:var(--amber);font-weight:700}
.favtags{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px}
.ftag{padding:3px 12px;border-radius:999px;border:1px solid var(--line);background:var(--card2);
  cursor:pointer;font-size:12.5px;color:var(--muted);font-family:inherit}
.ftag.on{background:var(--info-bg);border-color:var(--brand);color:var(--brand);font-weight:600}
.ftag b{cursor:pointer;font-weight:400;margin-left:3px}
.favtags input{padding:4px 9px;border:1px solid var(--line);border-radius:var(--r-sm);
  font-size:12.5px;width:110px;background:var(--card2);color:var(--ink)}
.notewrap{margin-top:14px;max-width:960px}
.notewrap textarea{width:100%;min-height:76px;padding:10px 12px;border:1px solid var(--line);
  border-radius:var(--r-md);font-size:14px;font-family:inherit;resize:vertical;background:var(--card2);color:var(--ink)}
.notewrap .nstatus{font-size:12px;color:var(--muted)}
.mobile-back{display:none}

/* ---- 轻量版(html[data-lite]) 与 视频回退提示 ---- */
.src-actions{display:none;flex-wrap:wrap;align-items:center;gap:8px;margin:11px auto 0;max-width:960px}
.src-actions .srcbtn{display:inline-flex;align-items:center;gap:6px;padding:7px 15px;border-radius:999px;
  border:1px solid var(--brand);background:var(--info-bg);color:var(--brand);
  font-size:13.5px;font-weight:600;text-decoration:none}
.src-actions .srcbtn:hover{background:var(--brand-strong);border-color:var(--brand-strong);color:var(--on-brand)}
.src-actions .srcsub{font-size:12px;color:var(--muted)}
.vfail-tip{display:none;flex-wrap:wrap;align-items:center;gap:9px;margin:13px auto 0;max-width:960px;
  padding:9px 14px;border:1px solid var(--amber-line);background:var(--amber-bg);
  border-radius:var(--r-md);font-size:13px;color:var(--ink2)}
.vfail-tip button{padding:4px 13px;border-radius:999px;border:1px solid var(--brand);
  background:var(--card);color:var(--brand);font-size:12.5px;font-weight:600;cursor:pointer}
.vfail-tip .vx{margin-left:auto;border:none;background:none;color:var(--muted);font-size:14px;padding:2px 6px;cursor:pointer}
html[data-lite] .src-actions{display:flex}
html[data-lite] .d-video,html[data-lite] .vsw-row,html[data-lite] .d-note,
html[data-lite] .vfail-tip{display:none!important}
html[data-lite] .txt{font-size:15.5px;line-height:1.95}
html[data-lite] .txt .concl{font-size:16px}
html[data-lite] .notewrap textarea{min-height:180px;font-size:14.5px;line-height:1.8}

/* ---- 统计矩阵 / 帮助 / 回顶 ---- */
.matrix table{border-collapse:collapse;width:100%;font-size:13.5px}
.matrix th,.matrix td{border-bottom:1px solid var(--line2);padding:6px 10px;text-align:center}
.matrix th:first-child,.matrix td:first-child{text-align:left}
.matrix tr:hover td{background:var(--card2)}
.matrix .w{color:var(--red);font-weight:600}.matrix .g{color:var(--green);font-weight:600}
.matrix .p{color:var(--amber);font-weight:600}
.matrix tfoot td{font-weight:700;background:var(--card2)}
.help p{margin:9px 0;font-size:14px;line-height:1.8}
.help b{color:var(--brand)}
.top-btn{position:fixed;right:20px;bottom:22px;display:none;align-items:center;gap:6px;
  background:var(--brand-strong);color:var(--on-brand);border:none;border-radius:999px;
  padding:9px 16px;font-size:13px;cursor:pointer;z-index:30;box-shadow:var(--shadow-sm)}

/* ---- 响应式: 统一断点 1280 / 1080 / 640 ---- */
@media (max-width:1280px){.workspace{grid-template-columns:244px minmax(0,320px) minmax(0,1fr)}}
@media (max-width:1080px){
  .workspace{grid-template-columns:minmax(0,1fr)}
  .detail{display:none}
  body.detail-open .workspace{grid-template-columns:minmax(0,1fr)}
  body.detail-open .detail{display:block}
  .sidebar{position:fixed;left:0;top:var(--top-h);bottom:0;width:284px;z-index:70;
    transform:translateX(-105%);transition:transform .18s;box-shadow:var(--shadow)}
  body.sb-open .sidebar{transform:none}
  body.detail-open .plist{display:none}
  .mobile-back{display:inline-flex;align-items:center;gap:6px;border:0;background:none;
    color:var(--brand);padding:2px 0 10px;font-weight:700;cursor:pointer;font-family:inherit;font-size:14px}
  body.detail-open .top-btn{display:inline-flex}
}
@media (max-width:640px){
  .detail{padding:12px 12px 40px}
  .d-card{padding:14px 14px 12px}
  .d-head .match{font-size:17px}
  .d-video video{max-height:44vh}
  #issueList{grid-template-columns:repeat(5,1fr)}
}
</style>
</head>
<body class="page-season">
<a class="skip-link" href="#plistRows">跳到判例列表</a>
__TOPBAR__

<div class="workspace">

  <aside class="sidebar" id="sidebar" aria-label="筛选侧栏">
    <div class="side-scroll">
      <h3 class="side-h">判定</h3>
      <div id="verList"></div>
      <h3 class="side-h">我的收藏</h3>
      <div id="favList"></div>
      <div class="side-actions">
        <button class="btn" id="btnExport">__I_UP__ 导出</button>
        <button class="btn" id="btnImport">__I_DOWN__ 导入</button>
        <input type="file" id="importFile" accept=".json,application/json" style="display:none">
      </div>
      <h3 class="side-h">赛事</h3>
      <div id="compList"></div>
      <h3 class="side-h">球队</h3>
      <div id="teamList"></div>
      <h3 class="side-h">期数</h3>
      <div id="issueList"></div>
      <h3 class="side-h">教学分类</h3>
      <div id="catList"></div>
      <button class="side-link" id="btnStats">__I_CHART__ 分类统计总表</button>
    </div>
  </aside>

  <section class="plist" aria-label="判例列表">
    <div class="plist-head">
      <div class="iss" id="issueTitle"></div>
      <div class="cnt">显示 <b id="shownCount">0</b> 例 · 点击行查看详情 · <span class="kbd">↑</span><span class="kbd">↓</span> 切换 · <span class="kbd">/</span> 搜索</div>
    </div>
    <div class="plist-rows" id="plistRows"></div>
  </section>

  <section class="detail" id="detail">
    <button class="mobile-back" id="mobileBack">__I_LEFT__ 返回列表</button>
    <div class="detail-empty" id="detailEmpty">__I_FILM_B__<span>从中间列表选择判例开始学习</span></div>
    <div class="d-card" id="dcard" style="display:none">
      <div class="d-head" id="dHead"></div>
      <div class="src-actions" id="srcActions"></div>
      <div class="vfail-tip" id="vfailTip"></div>
      <div class="d-video"><video id="dvid" controls preload="metadata" playsinline referrerpolicy="no-referrer"></video></div>
      <div class="vsw-row" id="vswRow" style="display:none"></div>
      <p class="d-note" id="dNote"></p>
      <div class="txt" id="dText"></div>
      <details class="d-note-box" id="dCatNote"><summary></summary><div></div></details>
      <div class="favtags" id="favTags" style="display:none"></div>
      <div class="notewrap" id="noteWrap" style="display:none">
        <textarea id="noteBox" placeholder="写下你的学习笔记…（自动保存）"></textarea>
        <span class="nstatus" id="noteStatus"></span>
      </div>
      <div class="tags" id="dTags"></div>
      <div class="d-foot" id="dFoot"></div>
      <div class="d-nav">
        <button id="prevBtn">__I_UP__ 上一个 <span class="kbd">↑</span></button>
        <button id="nextBtn">下一个 <span class="kbd">↓</span> __I_DOWN__</button>
      </div>
    </div>
  </section>
</div>

<!-- 统计弹层 -->
<div class="modal-mask" id="modalStats">
  <div class="modal matrix">
    <button class="close" data-close>关闭</button>
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
    <button class="close" data-close>关闭</button>
    <h3>使用说明与统计口径</h3>
    <div id="helpBody"></div>
  </div>
</div>

<button class="top-btn" id="btnTop">__I_UP__ 回到顶部</button>

<script>
const DATA = __DATA__;
const IC = __ICONS__;
const CATS = DATA.categories;
const VN = {wrong:"错漏判", correct:"支持原判", pending:"不予认定"};
const VCLS = {wrong:"wrong", correct:"correct", pending:"pending"};
const bySeq = {};
DATA.cases.forEach(c => bySeq[c.seq] = c);
// 必须在applyFilter的自动选中改写hash之前捕获初始锚点
const initialHashSeq = (location.hash.match(/^#case-(\d+)$/)||[])[1];
// 轻量版（cfa.lite，theme.py 首帧前设置 dataset.lite）：纯文字+官方链接笔记本模式，无视频窗口
let LITE = document.documentElement.dataset.lite === "1";

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
function crest(team, h, mark) {
  const item = DATA.teams && DATA.teams[team];
  if (!item) return `<span class="team-badge" title="${esc(team)}：未登记">?</span>`;
  if (item.status === "verified" && item.path)
    return `<img class="crest" style="height:${h}px" src="${item.path}" alt="${esc(team)}队徽">`;
  // fallback 文字徽章：与完整队名相邻时用色块标记，避免首字与队名重复（如"黑龙黑龙江冰城"）
  if (mark)
    return `<span class="team-dot" style="width:${h}px;height:${h}px;background:${item.bg};border:1px solid ${item.fg}" title="${esc(team)}：队徽待核验" aria-label="${esc(team)}"></span>`;
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

document.getElementById("btnStats").onclick = ()=>openModal("modalStats");
document.getElementById("catList").innerHTML =
  `<button class="cat-item on" data-cat=""><span class="nm">全部分类</span><b>${DATA.cases.length}</b></button>` +
  CATS.filter(k=>catCount[k.id]).map(k=>
    `<button class="cat-item" data-cat="${k.id}"><span class="nm">${k.name}</span>` +
    `<b>${catCount[k.id]}</b><small>错${catWrong[k.id]||0}</small></button>`).join("");
document.getElementById("verList").innerHTML =
  `<button class="ver-item on" data-v=""><span class="dot" style="background:var(--muted)"></span><span class="nm">全部</span><b>${verCount.all}</b></button>` +
  `<button class="ver-item" data-v="wrong"><span class="dot wrong"></span>错漏判<b>${verCount.wrong}</b></button>` +
  `<button class="ver-item" data-v="correct"><span class="dot correct"></span>支持原判<b>${verCount.correct}</b></button>` +
  `<button class="ver-item" data-v="pending"><span class="dot pending"></span>不予认定<b>${verCount.pending}</b></button>`;

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
  return crest(t, 18, true);
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
      return `<button class="cat-item ${String(state.issue)===String(i)?"on":""}" data-issue="${i}" title="第${i}期 · ${n}例"><span class="nm">${i}</span><b>${n}</b></button>`;
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
    `<div class="ph">${k.name} <b>${groups[k.id].length} 例</b></div>` +
    groups[k.id].map(c=>{
      const short = (c.comp||"").replace("联赛","");
      const varChip = c.var==="none" ? "" :
        `<span class="rv ${c.var==="wrong"?"bad":""}">V${c.var==="wrong"?"✗":"✓"}</span>`;
      return `<div class="prow ${state.sel===c.seq?"sel":""}" data-seq="${c.seq}" aria-current="${state.sel===c.seq}">
        <span class="dot ${c.v}"></span>
        <span class="ptxt"><b>${crest(c.home,16,true)}${esc(c.home)} <span class="vs">vs</span> ${crest(c.away,16,true)}${esc(c.away)}</b>
        <i>${esc(short)}${c.round?esc(c.round):""}${c.minute?" · 第"+c.minute+"分钟":""} · 第${c.issue}期-判例${c.no} · ${VN[c.v]}</i></span>
        <span class="pmark">${isFav(c.seq)?IC["star-f"]:""}${hasNote(c.seq)?IC.note:""}</span>
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

function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
  .replace(/"/g,"&quot;").replace(/'/g,"&#39;")}

// ---------- 视频源与回退（完整版：本地缺失 → 官方直链在线播放） ----------
let vidsMissing = false;  // 会话级：本地视频目录不可用（404 过一次后全程直连官方直链）
let ossTried = false;     // 当前 <video> 是否已在官方直链上
function hasVideos(c){ return !!(c.videos && c.videos.length); }
function videoSrc(c, i){
  const url = (c.video_urls || [])[i];
  if (vidsMissing && url) return url;
  return "videos/" + c.videos[i];
}
let vfailDismissed = false;
try { vfailDismissed = sessionStorage.getItem("cfa.vfail") === "1"; } catch(_) {}
function showVFailTip(msg, offerLite){
  if (offerLite && vfailDismissed) return;
  const tip = document.getElementById("vfailTip");
  tip.innerHTML = `<span>${esc(msg)}</span>` +
    (offerLite ? `<button id="vfailGoLite">切换轻量版</button>` +
      `<button class="vx" id="vfailX" title="本次会话不再提示">✕</button>` : "");
  tip.style.display = "flex";
}
document.getElementById("vfailTip").addEventListener("click", e=>{
  if (e.target.id === "vfailGoLite") { goLite(); return; }
  if (e.target.id === "vfailX") {
    vfailDismissed = true;
    try { sessionStorage.setItem("cfa.vfail", "1"); } catch(_) {}
    document.getElementById("vfailTip").style.display = "none";
  }
});
document.getElementById("dvid").addEventListener("error", ()=>{
  if (LITE) return;
  const c = bySeq[state.sel];
  if (!c || !hasVideos(c)) return;
  if (!ossTried) {
    const url = (c.video_urls || [])[state.vIdx];
    if (url) {
      vidsMissing = true; ossTried = true;
      document.getElementById("dvid").src = url;
      showVFailTip("本地视频缺失，已自动改用官方直链在线播放。");
      return;
    }
  }
  showVFailTip("视频无法播放（本地缺失且官方直链不可达）。可切换轻量版：纯文字 + 官方链接，无需视频。", true);
});

// ---------- 轻量版切换 ----------
function syncEmptyState(){
  document.getElementById("detailEmpty").innerHTML = LITE
    ? `${IC.note}<span>轻量版：从中间列表选择判例即可阅读与记笔记；视频请点详情里的「官方评议页 / 官方视频」链接到官方页面观看。顶栏「轻量版」按钮可切回完整版。</span>`
    : `__I_FILM_B__<span>从中间列表选择判例开始学习</span>`;
}
function stopVideo(){
  const vid = document.getElementById("dvid");
  try { vid.pause(); } catch(_) {}
  vid.removeAttribute("src"); vid.load();
}
function applyLite(){  // 模式切换后原地重渲染（无需刷新页面）
  LITE = document.documentElement.dataset.lite === "1";
  stopVideo();
  document.getElementById("vfailTip").style.display = "none";
  syncEmptyState();
  if (state.sel) select(state.sel, false); else clearDetail();
}
function goLite(){
  document.documentElement.dataset.lite = "1";
  try { localStorage.setItem("cfa.lite", "1"); } catch(_) {}
  applyLite();
}
document.addEventListener("cfa:lite", applyLite);  // theme.py 顶栏 #btnLite 切换时派发

// ---------- 选中判例 ----------
function select(seq, scrollRow=true){
  const c = bySeq[seq]; if (!c) return;
  if (window.matchMedia && window.matchMedia("(max-width:1080px)").matches)
    document.body.classList.add("detail-open");
  state.sel = seq;
  const iss = DATA.issues[c.issue];
  document.getElementById("detailEmpty").style.display = "none";
  document.getElementById("dcard").style.display = "block";
  const match = [c.comp, c.round, (c.home&&c.away)?`${c.home} VS ${c.away}`:"", c.minute?`第${c.minute}分钟`:""]
    .filter(Boolean).join(" · ");
  const matchHTML = match
    .replace(c.home, `${crest(c.home,22,true)}${esc(c.home)}`)
    .replace(c.away, `${crest(c.away,22,true)}${esc(c.away)}`);
  const varBadge = c.var==="none" ? "" :
    `<span class="badge ${c.var==="wrong"?"wrong":"info"}">VAR${c.var==="wrong"?"错误":"正确"}</span>`;
  document.getElementById("dHead").innerHTML =
    `<span class="cid">第${c.issue}期 · 判例${c.no}</span>
     <span class="badge ${VCLS[c.v]}">${VN[c.v]}</span>${varBadge}
     <button class="favbtn ${isFav(c.seq)?"on":""}" id="favBtn" title="收藏该判例" aria-pressed="${isFav(c.seq)}">${isFav(c.seq)?IC["star-f"]+" 已收藏":IC.star+" 收藏"}</button>
     <h2 class="match">${matchHTML}</h2>`;
  renderFavUI(c);
  renderNoteUI(c);
  // 视频区：轻量版无视频窗口，改放官方链接；完整版唯一播放器，切换即替换
  state.vIdx = 0;
  const vid = document.getElementById("dvid");
  const srcActs = document.getElementById("srcActions");
  const vfail = document.getElementById("vfailTip");
  const dvidWrap = document.querySelector(".d-video");
  const vsr = document.getElementById("vswRow");
  if (LITE) {
    stopVideo();
    dvidWrap.style.display = "none";
    vsr.style.display = "none"; vsr.innerHTML = "";
    document.getElementById("dNote").textContent = "";
    vfail.style.display = "none";
    srcActs.style.display = "flex";
    srcActs.innerHTML =
      `<a class="srcbtn" href="${esc(iss.url)}" target="_blank" rel="noopener">${IC.external} 打开官方评议页</a>` +
      (c.video_urls||[]).map((u,i)=>
        // 官方 CDN 拒绝带 Referer 的请求（403），直链必须免 Referer 打开
        `<a class="srcbtn" href="${esc(u)}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">${IC.play} 官方视频${i+1}</a>`).join("") +
      `<span class="srcsub">轻量版：到官方页面观看视频，收藏与笔记两种模式共用</span>`;
  } else {
    srcActs.style.display = "none"; srcActs.innerHTML = "";
    vfail.style.display = "none";
    if (!hasVideos(c)) {
      dvidWrap.style.display = "none";
      vsr.style.display = "none"; vsr.innerHTML = "";
      document.getElementById("dNote").textContent = "该判例无视频片段";
    } else {
      dvidWrap.style.display = "";
      try{ vid.pause(); }catch(_){}
      ossTried = !!(vidsMissing && (c.video_urls||[])[0]);
      vid.src = videoSrc(c, 0);
      if (c.videos.length > 1) {
        vsr.style.display = "flex";
        vsr.innerHTML = c.videos.map((f,i)=>
          `<button class="vsw ${i===0?"on":""}" data-i="${i}">${/-(2|3)\.mp4$/.test(f)&&i>0?"补充角度":"视频"+(i+1)}</button>`).join("");
      } else { vsr.style.display = "none"; vsr.innerHTML = ""; }
      document.getElementById("dNote").textContent =
        c.videos.length>1 ? "同判例存在多个角度视频，可切换：" : "";
    }
  }
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
  let h = item("", "全部", DATA.cases.length) + item("all", IC["star-f"]+" 收藏", nAll) + item("note", IC.note+" 笔记", nNote);
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
  const c = bySeq[state.sel]; if(!c || LITE || !hasVideos(c)) return;
  state.vIdx = +b.dataset.i;
  const vid = document.getElementById("dvid");
  try{ vid.pause(); }catch(_){}
  ossTried = !!(vidsMissing && (c.video_urls||[])[state.vIdx]);
  vid.src = videoSrc(c, state.vIdx);
  document.querySelectorAll(".vsw").forEach(x=>x.classList.toggle("on", x===b));
});
document.getElementById("btnSb").onclick = ()=>{
  // 桌面端收起/展开侧栏; 窄屏(≤1080px)侧栏为抽屉,切换其开合
  if (window.matchMedia && matchMedia("(max-width:1080px)").matches)
    document.body.classList.toggle("sb-open");
  else
    document.body.classList.toggle("sb-off");
};
document.getElementById("mobileBack").onclick = ()=>document.body.classList.remove("detail-open");
document.getElementById("btnTop").onclick = ()=>document.getElementById("detail").scrollTo({top:0,behavior:"smooth"});
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
    <p><b>操作方法：</b>左侧自上而下：判定 → 我的收藏（按标签筛选）→ 赛事（中超/中甲/中乙等）→ 球队（跨赛事聚合，如广州豹同时列出其中甲与足协杯判例）→ 期数（按原网页一期一期浏览，选中后列表头显示该期官方标题）→ 教学分类；中间列表点选判例，右侧大屏学习；<span class="kbd">↑</span><span class="kbd">↓</span> 键切换上一个/下一个判例，<span class="kbd">/</span> 聚焦搜索，<span class="kbd">Esc</span> 关闭弹层；顶栏按钮可收起侧栏获得更宽画面，右上角可切换明暗主题。</p>
    <p><b>收藏与笔记：</b>在详情区点「☆ 收藏」收藏判例并可打多个标签（精选/有疑问/尺度标杆/易错点/课堂讨论/自定义），笔记自动保存。收藏的判例在列表中显示★，可通过左侧「我的收藏」按标签筛选。数据存于浏览器 localStorage；用「导出/导入」按钮可在不同浏览器或 file:// 与 http:// 两种打开方式之间同步。</p>
    <p><b>轻量版模式：</b>门户首页的分段开关或顶栏「轻量版」按钮可切换（自动记忆）。轻量版去掉视频窗口，详情变为纯文字阅读 + 加大的笔记区，并提供「打开官方评议页」（按期跳转官方文章）与每条判例的官方视频直链（新标签页在线播放，官方 videooss 服务器支持拖进度条）——适合纯在线访问、不下载视频的用法。收藏与笔记在两种模式下共用同一份。</p>
    <p><b>视频播放：</b>完整版优先播放本地 videos 文件夹；在线访问（如 GitHub Pages）本地视频缺失时，会自动改用官方直链在线播放，离线用户不受任何影响。</p>
    <p><b>数据来源：</b>中国足球协会官方网站「裁判评议结果发布」栏目，${CFG.issueDesc}。每条判例附原文链接。</p>
    <p><b>期数口径注释：</b>${issNotes ? issNotes + "。" : ""}其余各期与官方标题认定数一致。</p>
    <p><b>离线使用：</b>将本页 HTML 与 videos 文件夹放在一起，双击即可离线学习；配套页面 <a href="${CFG.stats}" target="_blank">${CFG.stats}</a> 为各队得失盘点。</p>
    <p><b>声明：</b>本合集为教学研究用途，判罚认定权属于中国足协裁判委员会评议组。</p>`;
}

// ---------- 初始化 ----------
syncEmptyState();
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
    search_html = (f'<div class="search-wrap">{icon("search")}'
                   f'<input id="fSearch" type="search" placeholder="搜索球队 / 判例内容 / 关键词…" aria-label="搜索判例"></div>')
    tb = topbar(active=cfg["out"], right=search_html, stats=cfg["stats"],
                brand_sub=f"{season}赛季 · {len(data['cases'])}判例", seasons=tuple(sorted(SEASONS)),
                sb_btn=True, help_btn=True, lite_btn=True)
    sub = {"__I_UP__": icon("up"), "__I_DOWN__": icon("down"), "__I_LEFT__": icon("left", 14),
           "__I_CHART__": icon("chart", 14), "__I_FILM_B__": icon("film", 30)}
    html = inject_theme(HTML
            .replace("__DATA__", data_js)
            .replace("__ICONS__", js_icons())
            .replace("__TOPBAR__", tb)
            .replace("__TITLE__", cfg["title"])
            .replace("__STATS__", cfg["stats"])
            .replace("__BRAND__", cfg["brand"])
            .replace("__I_FILM_B__", sub["__I_FILM_B__"])
            .replace("__I_CHART__", sub["__I_CHART__"])
            .replace("__I_LEFT__", sub["__I_LEFT__"])
            .replace("__I_DOWN__", sub["__I_DOWN__"])
            .replace("__I_UP__", sub["__I_UP__"]))
    SITE.mkdir(parents=True, exist_ok=True)
    out = SITE / cfg["out"]
    out.write_text(html, encoding="utf-8")
    print(f"[{season}] 生成 {out}  ({len(html.encode('utf-8'))/1024:.0f} KB, "
          f"{len(data['cases'])}判例)")


def main():
    seasons = sys.argv[1:] or ["2026", "2025", "2024"]
    for season in seasons:
        if season not in SEASONS:
            raise SystemExit(f"未知赛季: {season}（可选: {'/'.join(SEASONS)}）")
        build_season(season)


if __name__ == "__main__":
    main()
