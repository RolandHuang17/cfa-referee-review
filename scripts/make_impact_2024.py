# -*- coding: utf-8 -*-
"""2024赛季错漏判影响标注 -> data/impact-2024.json（仅男子中超/中甲/中乙）"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

IMPACT = {
    4:   [{"team": "青岛海牛", "type": "missed_yellow_opponent", "note": "西海岸33号向后挥手击打裆部，应黄牌（非体育行为）"}],
    5:   [{"team": "无锡吴钩", "type": "opp_goal_should_disallow", "note": "平果哈嘹角球进球前攻方犯规漏判，进球应无效"}],
    7:   [{"team": "广西平果哈嘹", "type": "missed_red_opponent", "note": "吴钩5号肘击面部构成暴力行为，漏判红牌"}],
    8:   [{"team": "湖南湘涛", "type": "wrong_penalty_against", "note": "视频无法证明手球接触，点球错判"}],
    12:  [{"team": "青岛西海岸", "type": "wrong_red_self", "note": "争抢动作为鲁莽犯规，红牌错误应黄牌"}],
    19:  [{"team": "浙江俱乐部绿城", "type": "wrong_penalty_against", "note": "浙江45号犯规在先，国安17号不犯规，点球改判错误"}],
    21:  [{"team": "湖北青年星", "type": "opp_goal_should_disallow", "note": "鲲城13号越位位置影响守门员，漏判越位进球应无效"}],
    25:  [{"team": "上海嘉定汇龙", "type": "wrong_red_self", "note": "嘉定7号行为非暴力行为，红牌错误应黄牌"}],
    27:  [{"team": "上海嘉定汇龙", "type": "wrong_penalty_against", "note": "球未接触10号手臂，手球点球错判"}],
    30:  [{"team": "河南俱乐部", "type": "missed_yellow_opponent", "note": "浙江29号不合理挥臂击打，漏判黄牌"}],
    31:  [{"team": "浙江俱乐部绿城", "type": "missed_yellow_opponent", "note": "河南3号手球阻挡射门，漏判黄牌"}],
    39:  [{"team": "成都蓉城", "type": "missed_yellow_opponent", "note": "国安23号鲁莽犯规，漏判黄牌"}],
    40:  [{"team": "黑龙江冰城", "type": "missed_penalty", "note": "延边守门员犯规漏判点球（DOGSO以争抢为目的应黄牌）"},
          {"team": "黑龙江冰城", "type": "missed_yellow_opponent", "note": "同一犯规应出示黄牌"}],
    41:  [{"team": "黑龙江冰城", "type": "opp_goal_should_disallow", "note": "延边9号进球前推人犯规漏判，进球应无效"}],
    42:  [{"team": "青岛红狮", "type": "missed_penalty", "note": "云南30号手球漏判，应判点球（另有攻方27号手球为错判）"}],
    43:  [{"team": "广州俱乐部", "type": "missed_red_opponent", "note": "英博17号守门员故意击打面部，暴力行为漏判红牌"}],
    53:  [{"team": "南京城市", "type": "wrong_penalty_against", "note": "铜梁龙10号佯装，守门员无犯规，点球错判"},
          {"team": "南京城市", "type": "missed_yellow_opponent", "note": "铜梁龙10号佯装应黄牌"}],
    54:  [{"team": "北京理工", "type": "wrong_penalty_against", "note": "犯规地点在罚球区外，应直接任意球而非点球"},
          {"team": "北京理工", "type": "missed_red_opponent", "note": "青年星守门员DOGSO应红牌"}],
    58:  [{"team": "沧州雄狮", "type": "opp_goal_should_disallow", "note": "守门员已控球被侵犯，进球应无效"},
          {"team": "沧州雄狮", "type": "missed_foul_called", "note": "攻方犯规漏判"}],
    65:  [{"team": "赣州瑞狮", "type": "wrong_red_self", "note": "铲球草率犯规+起身挑衅，红牌错误应黄牌"}],
    67:  [{"team": "江西庐山", "type": "wrong_penalty_against", "note": "守门员先触球无犯规，点球错判"}],
    69:  [{"team": "廊坊荣耀之城", "type": "wrong_red_self", "note": "撞击属情绪宣泄非暴力行为，红牌错误应黄牌"}],
    70:  [{"team": "大连英博", "type": "denied_goal", "note": "球击中横梁弹地已整体过线，漏判进球"}],
    73:  [{"team": "延边龙鼎", "type": "wrong_penalty_against", "note": "2号主动摔倒佯装，点球错判"}],
    78:  [{"team": "梅州客家", "type": "opp_goal_should_disallow", "note": "海港18号手球后进球（其他渠道视频确认），进球应无效"}],
    79:  [{"team": "梅州客家", "type": "opp_goal_should_disallow", "note": "海港3号拉扯犯规在先，进球应无效"},
          {"team": "梅州客家", "type": "missed_foul_called", "note": "拉扯犯规漏判"}],
    80:  [{"team": "武汉三镇", "type": "missed_yellow_opponent", "note": "海港19号正面踢人鲁莽犯规，漏判犯规和黄牌"}],
    81:  [{"team": "广西平果哈嘹", "type": "opp_goal_should_disallow", "note": "铜梁龙31号越位位置参与争抢，漏判越位进球应无效"}],
    87:  [{"team": "赣州瑞狮", "type": "missed_penalty", "note": "海港B队60号手臂不自然扩大手球，漏判点球"},
          {"team": "赣州瑞狮", "type": "missed_yellow_opponent", "note": "手球阻挡射门应黄牌"}],
    90:  [{"team": "大连鲲城", "type": "opp_goal_should_disallow", "note": "青年星41号越位位置干扰，漏判越位犯规在先"}],
    95:  [{"team": "北京理工", "type": "missed_red_opponent", "note": "泰安11号恶意踢倒地球员属严重犯规，漏判红牌"},
          {"team": "北京理工", "type": "wrong_foul_called_self", "note": "60号无危险方式比赛，错判间接任意球"}],
    97:  [{"team": "湖南湘涛", "type": "missed_penalty", "note": "海口名城20号跨步绊摔，漏判点球"}],
    98:  [{"team": "海门珂缔缘", "type": "wrong_penalty_against", "note": "拉拽非倒地主因+主动倒地，点球错判"}],
    99:  [{"team": "大连鲲城", "type": "wrong_foul_called_self", "note": "手臂为身体带动合理位置非手球，且地点判断错误"}],
    101: [{"team": "南京城市", "type": "missed_penalty", "note": "延边37号踢倒对方，草率犯规漏判点球"}],
    102: [{"team": "广西平果哈嘹", "type": "missed_red_opponent", "note": "英博40号击打面部暴力行为，漏判红牌"},
          {"team": "广西平果哈嘹", "type": "missed_foul_called", "note": "漏判直接任意球"}],
    107: [{"team": "无锡吴钩", "type": "missed_yellow_opponent", "note": "拉扯推搡不足以犯规，点球正确但黄牌错误"}],
    109: [{"team": "广西蓝航", "type": "wrong_penalty_against", "note": "守门员先触球无犯规，点球错判"},
          {"team": "广西蓝航", "type": "wrong_yellow_self", "note": "守门员无犯规不应黄牌"}],
    110: [{"team": "广西蓝航", "type": "missed_yellow_opponent", "note": "守门员罚点球时提前离线缺乏尊重，漏判黄牌"}],
    127: [{"team": "黑龙江冰城", "type": "missed_foul_called", "note": "侧后方冲撞漏判犯规（地点在罚球区外应直接任意球）"},
          {"team": "黑龙江冰城", "type": "missed_yellow_opponent", "note": "该犯规阻止有希望的进攻应黄牌"}],
    128: [{"team": "大连英博", "type": "missed_penalty", "note": "铁人5号手臂不自然扩大手球，漏判点球（VAR角度所限）"}],
    132: [{"team": "北京理工", "type": "missed_penalty", "note": "蓝航拉扯犯规漏判点球"},
          {"team": "北京理工", "type": "missed_yellow_opponent", "note": "拉扯阻止有希望的进攻应黄牌"}],
    134: [{"team": "日照宇启", "type": "wrong_red_self", "note": "倒地过程无附加动作非暴力行为，红牌错误"}],
    138: [{"team": "北京理工", "type": "missed_penalty", "note": "赣州瑞狮手球手臂向球移动，漏判点球"}],
    139: [{"team": "赣州瑞狮", "type": "wrong_foul_called_self", "note": "攻方先触球被错判犯规（反判）"},
          {"team": "北京理工", "type": "missed_penalty", "note": "守方草率犯规漏判点球"}],
    141: [{"team": "青岛海牛", "type": "missed_red_opponent", "note": "南通支云10号直腿抢截危及安全，严重犯规漏判红牌"},
          {"team": "青岛海牛", "type": "missed_foul_called", "note": "VAR未介入错误"}],
    143: [{"team": "广西平果哈嘹", "type": "missed_penalty", "note": "嘉定汇龙30号背后拉拽，草率犯规漏判点球"}],
    144: [{"team": "泰安天贶", "type": "missed_red_opponent", "note": "泉州亚新26号抢截犯规满足DOGSO四要素，漏判红牌"},
          {"team": "泰安天贶", "type": "missed_foul_called", "note": "犯规本身漏判"}],
    145: [{"team": "成都蓉城", "type": "wrong_foul_called_self", "note": "正常争抢接触，判攻方蓉城31号犯规错误（足协杯半决赛）"}],
    145: [{"team": "成都蓉城", "type": "wrong_foul_called_self", "note": "正常争抢接触，判攻方蓉城31号犯规错误（足协杯半决赛）"}],
    150: [{"team": "北京理工", "type": "wrong_penalty_against", "note": "守门员铲球清晰触球无附加动作，点球错判"}],
    151: [{"team": "浙江俱乐部", "type": "missed_red_opponent", "note": "三镇23号踩踏脚踝构成严重犯规，漏判红牌"}],
    156: [{"team": "赣州瑞狮", "type": "opp_goal_should_disallow", "note": "北理工52号越位位置进球，漏判越位"}],
    158: [{"team": "大连英博", "type": "denied_goal", "note": "球未触手臂进球有效，VAR错误介入致进球被取消"}],
}

# 2024赛季男子三级联赛以外的错漏判（女超/女甲/足协杯女子/三大球），不纳入影响统计
OUT_OF_SCOPE = {
    47: "女超", 55: "女超", 60: "女甲", 88: "女超", 92: "足协杯（女子）",
    159: "三大球运动会", 160: "三大球运动会",
}


def main():
    src = json.loads((ROOT / "data" / "cases-2024.json").read_text(encoding="utf-8"))
    cases = {c["seq"]: c for c in src["cases"]}
    NV = {
        "河南俱乐部酒祖杜康": "河南俱乐部", "河南酒祖杜康": "河南俱乐部",
        "浙江俱乐部": "浙江俱乐部绿城", "陕西联合月亮泊": "陕西联合",
        "广西平果国晶": "广西平果", "大连英博海发": "大连英博",
        "温州俱乐部中胤": "温州俱乐部",
        # 2024赛季特有写法
        "浙江": "浙江俱乐部绿城",
        "广西平果哈嘹": "广西平果",
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
        "missed_foul_called": "漏判犯规",
        "wrong_offside_self": "误判越位",
    }
    SWING = {"denied_goal": 1, "opp_goal_should_disallow": -1}

    out = {"scope": ["中超联赛", "中甲联赛", "中乙联赛", "中国足协杯"],
           "type_labels": TYPE_LABEL, "swing": SWING,
           "team_normalize": NV, "match_notes": {}, "impacts": {}}
    skipped = []
    for seq, items in IMPACT.items():
        c = cases[seq]
        assert c["referee_verdict"] == "wrong", seq
        league = c["comp"]
        if league not in out["scope"]:
            skipped.append((seq, league))
            continue
        rnd = c.get("round", "")
        rm = re.search(r"第(\d+)轮", rnd or "")
        round_no = int(rm.group(1)) if rm else 0
        home = NV.get(c["home"], c["home"])
        away = NV.get(c["away"], c["away"])
        norm = []
        for it in items:
            team = NV.get(it["team"], it["team"])
            assert team in (home, away), (seq, team, home, away)
            norm.append({"team": team, "type": it["type"],
                         "swing": SWING.get(it["type"], 0), "note": it["note"]})
        out["impacts"][str(seq)] = {
            "league": league, "round": round_no, "home": home, "away": away,
            "issue": c["issue"], "case_no": c["no"], "match_note": "",
            "items": norm}
    assert not skipped, skipped
    path = ROOT / "data" / "impact-2024.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    matches = sorted({(v["league"], v["round"], v["home"], v["away"])
                      for v in out["impacts"].values()})
    print(f"标注 {len(out['impacts'])} 例 / {len(matches)} 场比赛")
    print("类型分布:", Counter(i["type"] for v in out["impacts"].values() for i in v["items"]))


if __name__ == "__main__":
    main()
