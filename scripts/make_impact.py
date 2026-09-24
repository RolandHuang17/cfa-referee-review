# -*- coding: utf-8 -*-
"""错漏判影响标注：data/impact.json
范围：仅男子中超/中甲/中乙的官方认定错漏判（67例）
每例 items[].type（受损队视角）:
  denied_goal                漏判进球（本队进球被误判无效，确定+1球）
  opp_goal_should_disallow   对方进球被误判有效（应无效，确定-1球）
  missed_penalty             应得点球未判（机会）
  wrong_penalty_against      对方不应得的点球被判（机会）
  missed_red_opponent        对方球员应红牌未罚下
  wrong_red_self             本队球员被错罚红牌
  missed_yellow_opponent     对方球员应黄牌未出示
  wrong_yellow_self          本队球员被错罚黄牌
  wrong_foul_called_self     本队被错判犯规
  wrong_offside_self         本队被误判越位
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

IMPACT = {
    1:   [{"team": "长春亚泰", "type": "missed_red_opponent", "note": "上海申花4号踩踏守门员小腿属严重犯规，回看后仅出示黄牌"}],
    4:   [{"team": "成都蓉城", "type": "wrong_red_self", "note": "蓉城8号踩踏未达严重犯规程度，红牌错误、应黄牌"}],
    5:   [{"team": "天津津门虎", "type": "wrong_foul_called_self", "note": "评议组认定双方均不犯规，津门虎4号被错判犯规"}],
    6:   [{"team": "上海嘉定汇龙", "type": "missed_penalty", "note": "南通支云33号手球（手臂不自然扩大）漏判，应判点球"}],
    9:   [{"team": "佛山南狮", "type": "missed_penalty", "note": "深圳青年人26号拉扯破坏明显进球得分机会，应判点球"},
          {"team": "佛山南狮", "type": "missed_red_opponent", "note": "同一犯规符合DOGSO，应出示红牌"}],
    10:  [{"team": "南京城市", "type": "missed_red_opponent", "note": "大连鲲城26号腾空飞铲蹬踹属严重犯规，仅出示黄牌"}],
    14:  [{"team": "北京理工", "type": "missed_penalty", "note": "无锡吴钩防守犯规漏判，应判点球"}],
    16:  [{"team": "南通支云", "type": "missed_penalty", "note": "石家庄功夫36号拉扯犯规结束在罚球区内，应判点球"},
          {"team": "南通支云", "type": "missed_red_opponent", "note": "该拉扯破坏明显进球得分机会，应出示红牌"}],
    20:  [{"team": "佛山南狮", "type": "missed_penalty", "note": "苏州东吴26号手臂不自然扩大触球，应判点球"}],
    22:  [{"team": "广东铭途", "type": "opp_goal_should_disallow", "note": "成都蓉城B队进球前争抢犯规漏判，进球应无效"}],
    25:  [{"team": "武汉三镇", "type": "missed_penalty", "note": "长春亚泰4号推搡破坏明显进球得分机会，应判点球"},
          {"team": "武汉三镇", "type": "missed_red_opponent", "note": "同一犯规符合DOGSO，应出示红牌"}],
    27:  [{"team": "武汉三镇", "type": "missed_yellow_opponent", "note": "长春亚泰9号有意不合理挥臂，漏判犯规和黄牌"}],
    29:  [{"team": "云南玉昆", "type": "missed_yellow_opponent", "note": "上海申花23号铲球后接触腿部属鲁莽犯规，漏判犯规和黄牌"}],
    36:  [{"team": "上海嘉定汇龙", "type": "missed_penalty", "note": "南京城市4号踩到其脚部，应判点球"}],
    40:  [{"team": "成都蓉城B队", "type": "missed_penalty", "note": "广西恒宸33号拉扯致失去控球权，应判点球"}],
    48:  [{"team": "山东泰山", "type": "missed_red_opponent", "note": "青岛西海岸56号鞋钉踩踏小腿跟腱属严重犯规，回看后仍仅黄牌"}],
    49:  [{"team": "大连英博", "type": "missed_yellow_opponent", "note": "深圳新鹏城27号挥臂属鲁莽犯规，漏判犯规和黄牌"}],
    51:  [{"team": "南通支云", "type": "wrong_offside_self", "note": "越位误判致进攻被终止；其后守门员犯规发生在比赛停止后，进球不予讨论认定"}],
    54:  [{"team": "南通支云", "type": "opp_goal_should_disallow", "note": "大连鲲城17号推搡头顶球队员，犯规漏判，其后进球应无效"}],
    55:  [{"team": "定南赣联", "type": "missed_yellow_opponent", "note": "广西平果7号拉扯破坏有希望的进攻，漏判犯规和黄牌"}],
    61:  [{"team": "陕西联合", "type": "denied_goal", "note": "33号头球进球被误判越位，进球应有效"}],
    62:  [{"team": "广东铭途", "type": "wrong_penalty_against", "note": "广西恒宸7号轻微接触后夸大倒地，点球错误"},
          {"team": "广东铭途", "type": "wrong_yellow_self", "note": "铭途5号不应被出示黄牌"}],
    64:  [{"team": "广州蒲公英", "type": "missed_penalty", "note": "贵州筑城竞技17号从背后冲撞，应判点球"},
          {"team": "广州蒲公英", "type": "missed_yellow_opponent", "note": "该冲撞属鲁莽犯规，应出示黄牌"}],
    66:  [{"team": "梅州客家", "type": "opp_goal_should_disallow", "note": "上海申花27号越位位置干扰对方队员，进球应无效"}],
    69:  [{"team": "广东铭途", "type": "wrong_penalty_against", "note": "守门员出击铲球先触球无犯规，点球错误"}],
    70:  [{"team": "成都蓉城B队", "type": "missed_red_opponent", "note": "贵州筑城竞技49号鞋底蹬踹头颈部属严重犯规，仅黄牌"}],
    72:  [{"team": "深圳青年人", "type": "missed_penalty", "note": "大连鲲城24号拉扯犯规，应判点球"}],
    73:  [{"team": "深圳青年人", "type": "missed_penalty", "note": "大连鲲城24号拉扯+绊摔，应判点球"}],
    77:  [{"team": "辽宁铁人", "type": "missed_penalty", "note": "定南赣联3号拉扯破坏明显进球得分机会，应判点球"},
          {"team": "辽宁铁人", "type": "missed_red_opponent", "note": "该犯规符合DOGSO标准，应出示红牌"}],
    79:  [{"team": "赣州瑞狮", "type": "wrong_penalty_against", "note": "守门员出击扑到球且无附加动作，点球错误"},
          {"team": "赣州瑞狮", "type": "wrong_yellow_self", "note": "守门员不应被出示黄牌"}],
    82:  [{"team": "南京城市", "type": "denied_goal", "note": "10号进球被误判越位，进球应有效"}],
    83:  [{"team": "南通支云", "type": "wrong_penalty_against", "note": "双方正常争抢均不犯规，点球错误"}],
    85:  [{"team": "浙江俱乐部绿城", "type": "denied_goal", "note": "VAR对比赛恢复前事件错误介入，进球应有效"}],
    96:  [{"team": "武汉三镇", "type": "missed_red_opponent", "note": "青岛海牛7号鞋钉蹬踹跟腱属严重犯规，未出示红黄牌"}],
    99:  [{"team": "辽宁铁人", "type": "missed_penalty", "note": "南通支云队员手臂向球移动触球，应判点球"}],
    101: [{"team": "广西平果", "type": "missed_red_opponent", "note": "延边龙鼎33号铲抢过分力量属严重犯规，仅黄牌"}],
    112: [{"team": "苏州东吴", "type": "opp_goal_should_disallow", "note": "重庆铜梁龙8号越位位置干扰守门员，进球应无效"}],
    126: [{"team": "山东泰山B队", "type": "wrong_penalty_against", "note": "犯规地点在罚球区外，应判直接任意球而非点球"}],
    128: [{"team": "杭州临平吴越", "type": "opp_goal_should_disallow", "note": "山东泰山B队49号越位位置回接射门，进球应无效"}],
    135: [{"team": "兰州陇原竞技", "type": "missed_penalty", "note": "山西崇德荣海36号手球漏判，应判点球"}],
    136: [{"team": "无锡吴钩", "type": "missed_penalty", "note": "长春喜都29号持续环抱拉扯，应判点球"}],
    141: [{"team": "南京城市", "type": "denied_goal", "note": "进球前攻方正常争抢不犯规，进球应有效"}],
    142: [{"team": "南京城市", "type": "missed_red_opponent", "note": "南通支云10号企图击打属暴力行为，无论是否击中均应红牌"},
          {"team": "南通支云", "type": "missed_yellow_opponent", "note": "南京城市19号犯规应以非体育行为黄牌警告"}],
    145: [{"team": "湖北青年星", "type": "wrong_penalty_against", "note": "接触属可接受程度，对方借助接触主动倒地，点球错误"}],
    146: [{"team": "武汉三镇B队", "type": "opp_goal_should_disallow", "note": "守门员率先触球后被鲁莽犯规，进球应无效"},
          {"team": "武汉三镇B队", "type": "missed_yellow_opponent", "note": "赣州瑞狮59号争抢动作属鲁莽犯规，应黄牌"}],
    147: [{"team": "武汉三镇B队", "type": "missed_penalty", "note": "赣州瑞狮守门员出击未触球且犯规，应判点球"},
          {"team": "武汉三镇B队", "type": "wrong_foul_called_self", "note": "本队队员正常争抢被错判犯规"}],
    150: [{"team": "河南俱乐部", "type": "missed_penalty", "note": "青岛西海岸6号草率踢人犯规，应判点球"}],
    160: [{"team": "延边龙鼎", "type": "wrong_offside_self", "note": "38号被误判越位、进攻被终止；鸣哨停止后的进球不予认定"}],
    162: [{"team": "海门珂缔缘", "type": "wrong_penalty_against", "note": "守方先触球并成功处理，不犯规，点球错误"}],
    163: [{"team": "天津津门虎", "type": "denied_goal", "note": "进球前正常争抢不犯规，VAR错误介入致进球被取消"}],
    168: [{"team": "定南赣联", "type": "missed_yellow_opponent", "note": "广西平果43号故意冲撞属鲁莽犯规，漏判犯规和黄牌"}],
    171: [{"team": "深圳新鹏城", "type": "opp_goal_should_disallow", "note": "长春亚泰2号争顶时手臂限制+身体压制，犯规在先，进球应无效"}],
    174: [{"team": "天津津门虎", "type": "missed_red_opponent", "note": "浙江俱乐部20号手臂击打头部属严重犯规，无牌（第23轮调赛）"}],
    179: [{"team": "武汉三镇", "type": "missed_red_opponent", "note": "上海申花10号鞋钉直腿蹬踏属严重犯规，回看后仍仅黄牌"}],
    181: [{"team": "昆明城星", "type": "denied_goal", "note": "应掌握有利使进球有效，进球被误判无效"},
          {"team": "山西崇德荣海", "type": "wrong_red_self", "note": "按修正流程守门员应黄牌警告而非红牌"}],
    185: [{"team": "深圳新鹏城", "type": "wrong_penalty_against", "note": "手臂处于合理位置且为近距离意外来球，不构成手球，点球错误"}],
    188: [{"team": "石家庄功夫", "type": "missed_red_opponent", "note": "广州豹7号比赛停止时头撞对方属暴力行为，应红牌（第27期补充认定）"},
          {"team": "广东广州豹", "type": "missed_yellow_opponent", "note": "石家庄功夫14号疑似挑衅/还击，至少应黄牌警告"}],
    190: [{"team": "苏州东吴", "type": "opp_goal_should_disallow", "note": "南通支云20号越位位置触球，进球应无效"}],
    196: [{"team": "陕西联合月亮泊", "type": "missed_red_opponent", "note": "南通支云15号无球状态挥拳击打属暴力行为，仅黄牌"}],
    197: [{"team": "广西平果", "type": "missed_red_opponent", "note": "佛山南狮25号抬脚触对方头部属严重犯规，仅黄牌"}],
    199: [{"team": "南京城市", "type": "wrong_red_self", "note": "接触力度轻微属非体育行为，红牌错误、应黄牌"}],
    205: [{"team": "大连英博", "type": "missed_penalty", "note": "青岛西海岸36号拉扯犯规，应判点球"}],
    206: [{"team": "上海嘉定汇龙", "type": "missed_penalty", "note": "陕西联合35号手球漏判，应判点球"}],
    210: [{"team": "广东铭途", "type": "missed_penalty", "note": "杭州临平吴越队员跳向对方属草率犯规，应判点球"}],
    222: [{"team": "成都蓉城", "type": "denied_goal", "note": "对方手球应掌握有利使进球有效；因鸣哨在先无法改判进球"}],
    223: [{"team": "成都蓉城", "type": "missed_penalty", "note": "河南俱乐部11号手球漏判，应判点球"}],
    225: [{"team": "上海嘉定汇龙", "type": "wrong_red_self", "note": "9号挥臂不构成暴力行为，红牌错误、应黄牌"},
          {"team": "上海嘉定汇龙", "type": "missed_yellow_opponent", "note": "广西平果5号持续拉扯抱摔，应黄牌警告"}],
}

TEAM_NORMALIZE = {
    "河南酒祖杜康": "河南俱乐部",
    "河南队": "河南俱乐部",
    "陕西联合月亮泊": "陕西联合",
    "广西平果国晶": "广西平果",
    "浙江俱乐部": "浙江俱乐部绿城",
}

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
}

SWING = {"denied_goal": 1, "opp_goal_should_disallow": -1}

# 比分查证备注：第23轮调赛场次需要按实际补赛日期检索；深圳青年人场次的轮次出入
MATCH_NOTES = {
    "中超|23|浙江俱乐部绿城|天津津门虎": "第23轮调赛，实际比赛日期早于原轮次",
    "中甲|1|深圳青年人|佛山南狮": "评估文写第1轮，赛程记录为第2轮（3月16日），为同一场首次交锋",
}


def main():
    data = json.loads((ROOT / "data" / "cases.json").read_text(encoding="utf-8"))
    cases = {c["seq"]: c for c in data["cases"]}

    # 修正 #48 的赛事字段（"中超第7轮"未带"联赛"导致提取为空）
    c48 = cases[48]
    c48["comp"] = "中超联赛"

    out = {"scope": ["中超联赛", "中甲联赛", "中乙联赛"],
           "type_labels": TYPE_LABEL, "swing": SWING,
           "team_normalize": TEAM_NORMALIZE,
           "match_notes": MATCH_NOTES,
           "impacts": {}}

    missing = []
    for seq, items in IMPACT.items():
        c = cases[seq]
        assert c["referee_verdict"] == "wrong", seq
        league = c["comp"]
        if league not in out["scope"]:
            missing.append(seq)
            continue
        rnd = c.get("round", "")
        m = None
        for ch in "0123456789":
            pass
        import re
        rm = re.search(r"第(\d+)轮", rnd or "")
        round_no = int(rm.group(1)) if rm else None
        if round_no is None:
            # 中文数字轮次（第一轮等）
            cn = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
                  "八": 8, "九": 9, "十": 10}
            r2 = re.search(r"第([一二三四五六七八九十]+)轮", rnd or "")
            if r2:
                s = r2.group(1)
                if s in cn:
                    round_no = cn[s]
                elif s.startswith("十"):
                    round_no = 10 + cn.get(s[1:], 0)
                elif "十" in s:
                    a, _, b = s.partition("十")
                    round_no = cn.get(a, 0) * 10 + (cn.get(b, 0) if b else 0)
        assert round_no, (seq, rnd)
        home = TEAM_NORMALIZE.get(c["home"], c["home"])
        away = TEAM_NORMALIZE.get(c["away"], c["away"])
        norm_items = []
        for it in items:
            team = TEAM_NORMALIZE.get(it["team"], it["team"])
            assert team in (home, away), (seq, team, home, away)
            norm_items.append({"team": team, "type": it["type"],
                               "swing": SWING.get(it["type"], 0), "note": it["note"]})
        out["impacts"][str(seq)] = {
            "league": league, "round": round_no, "home": home, "away": away,
            "issue": c["issue"], "case_no": c["no"], "match_note": "",
            "items": norm_items,
        }
    assert not missing, missing
    # 调赛备注挂到对应比赛
    for key, note in MATCH_NOTES.items():
        lg, rd, h, a = key.split("|")
        for v in out["impacts"].values():
            if (v["league"], str(v["round"]), v["home"], v["away"]) == (lg, rd, h, a):
                v["match_note"] = note
    (ROOT / "data" / "impact.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # 汇总
    from collections import Counter
    matches = sorted({(v["league"], v["round"], v["home"], v["away"])
                      for v in out["impacts"].values()})
    print(f"标注 {len(out['impacts'])} 例 / {len(matches)} 场比赛")
    print("类型分布:", Counter(i["type"] for v in out["impacts"].values() for i in v["items"]))
    print("球队数:", len({i["team"] for v in out["impacts"].values() for i in v["items"]}
                     | {v["home"] for v in out["impacts"].values()}
                     | {v["away"] for v in out["impacts"].values()}))
    for lg, rd, h, a in matches:
        print(f"  {lg} 第{rd}轮 {h} vs {a}")


if __name__ == "__main__":
    main()
