# -*- coding: utf-8 -*-
"""2026赛季错漏判影响标注：data/impact-2026.json
范围：仅男子中超/中甲/中乙的官方认定错漏判（女超不计，与2024/2025口径一致）
每例 items[].type（受损队视角）与 make_impact.py 相同。
逐条标注依据 cases-2026.json 的评议组认定原文（AI复核口径，与 CLS_2026 一致）。
"""
import json
import re

from lib.paths import DATA

IMPACT = {
    # 期01
    1:   [{"team": "北京国安", "type": "missed_penalty", "note": "山东泰山8号手臂抬起使身体不自然扩大触球，漏判手球犯规和点球"}],
    # 期02
    2:   [{"team": "陕西联合", "type": "missed_penalty", "note": "深圳青年人42号铲球草率绊倒7号，应判点球"},
          {"team": "陕西联合", "type": "wrong_yellow_self", "note": "7号被错判佯装出示黄牌"}],
    3:   [{"team": "河南俱乐部彩陶坊", "type": "missed_penalty", "note": "武汉三镇8号犯规接触点在罚球区内，应判点球"}],
    4:   [{"team": "北京国安", "type": "denied_goal", "note": "37号被错判犯规且鸣哨时机不当，进球无法追认"}],
    6:   [{"team": "长春喜都", "type": "missed_yellow_opponent", "note": "兰州陇原竞技39号故意挥臂击打，漏判犯规及红/黄牌"}],
    7:   [{"team": "无锡吴钩", "type": "missed_penalty", "note": "宁波俱乐部队员罚球区内拉扯犯规，应判点球"}],
    # 期03
    11:  [{"team": "北京国安", "type": "missed_yellow_opponent", "note": "成都蓉城10号鞋钉踩踏属鲁莽犯规，漏判黄牌"}],
    15:  [{"team": "深圳新鹏城", "type": "missed_penalty", "note": "云南玉昆34号手臂扩张不自然扩大触球，漏判手球和点球"}],
    16:  [{"team": "陕西联合", "type": "missed_penalty", "note": "长春亚泰队员罚球区内草率绊倒对方，应判点球"}],
    17:  [{"team": "大连鲲城", "type": "missed_penalty", "note": "延边龙鼎队员手臂上扬不自然扩大触球，应判点球"}],
    19:  [{"team": "石家庄功夫", "type": "missed_penalty", "note": "佛山南狮队员手臂不自然扩大触球，应判点球"}],
    20:  [{"team": "北京理工", "type": "missed_red_opponent", "note": "泰安天贶29号铲球使用过分力量属严重犯规，仅黄牌"}],
    22:  [{"team": "北京理工", "type": "missed_yellow_opponent", "note": "泰安天贶20号凌空踢触对方躯干属鲁莽犯规，漏判黄牌"}],
    23:  [{"team": "厦门飞鹭", "type": "wrong_penalty_against", "note": "防守无犯规动作，对方跑动造成接触，点球错误"}],
    24:  [{"team": "温州俱乐部", "type": "missed_penalty", "note": "赣州瑞狮26号防守绊倒突破队员，应判点球"}],
    # 期04
    27:  [{"team": "青岛海牛", "type": "missed_penalty", "note": "青岛西海岸22号铲球犯规，回看后仍维持不判，漏判点球"}],
    37:  [{"team": "无锡吴钩", "type": "opp_goal_should_disallow", "note": "双方均有队员提前进入罚球区，应重罚点球而非判补射进球有效"}],
    39:  [{"team": "石家庄功夫", "type": "denied_goal", "note": "7号未越位，助理裁判员误判致进球被吹无效"}],
    40:  [{"team": "贵州贵阳竞技", "type": "wrong_penalty_against", "note": "44号手球地点在罚球区外，应判直接任意球而非点球"}],
    42:  [{"team": "泰安天贶", "type": "wrong_offside_self", "note": "33号未越位被误判，进攻被终止"}],
    44:  [{"team": "山东泰山B队", "type": "missed_red_opponent", "note": "兰州陇原竞技17号铲球属严重犯规，仅判犯规无牌"}],
    45:  [{"team": "成都蓉城B队", "type": "wrong_penalty_against", "note": "45号防守先触球无附加动作，不犯规，点球错误"}],
    # 期05
    47:  [{"team": "北京国安", "type": "missed_red_opponent", "note": "深圳新鹏城36号鞋钉踩踏跟腱且二次踩踏属严重犯规，仅黄牌"}],
    51:  [{"team": "北京国安", "type": "missed_yellow_opponent", "note": "天津津门虎5号前脚掌蹬踏小腿属鲁莽犯规，漏判黄牌"}],
    57:  [{"team": "大连可为", "type": "missed_yellow_opponent", "note": "上海赛更达队员背后草率绊倒且破坏有希望进攻，漏判犯规、任意球和黄牌"}],
    58:  [{"team": "江西庐山", "type": "missed_penalty", "note": "湖北青年星14号过度拉扯抱摔，应判点球"},
          {"team": "江西庐山", "type": "missed_yellow_opponent", "note": "该抱摔属鲁莽犯规，应出示黄牌"}],
    59:  [{"team": "海门珂缔缘", "type": "opp_goal_should_disallow", "note": "北京理工6号越位位置干扰对方队员，进球应无效"}],
    # 期06
    62:  [{"team": "天津津门虎", "type": "missed_penalty", "note": "武汉三镇19号踢倒31号属鲁莽犯规，应判点球"},
          {"team": "天津津门虎", "type": "missed_yellow_opponent", "note": "该犯规应出示黄牌"}],
    65:  [{"team": "定南赣联", "type": "wrong_penalty_against", "note": "守门员出击触球无附加动作，不犯规，点球错误"}],
    67:  [{"team": "厦门飞鹭", "type": "wrong_red_self", "note": "15号腿部下落接触属鲁莽犯规，红牌错误、应黄牌"}],
    68:  [{"team": "杭州临平吴越", "type": "wrong_penalty_against", "note": "4号先触球并收脚躲避，不犯规，点球错误"}],
    69:  [{"team": "杭州临平吴越", "type": "denied_goal", "note": "20号未越位，助理裁判员误判致进球无效"}],
    71:  [{"team": "泰安天贶", "type": "missed_yellow_opponent", "note": "青岛红狮32号比赛停止后接触属非体育行为，漏判黄牌"}],
    73:  [{"team": "江西庐山", "type": "missed_penalty", "note": "广东铭途队员罚球区内拉扯致失去重心倒地，应判点球"}],
    # 期07
    75:  [{"team": "青岛西海岸", "type": "wrong_penalty_against", "note": "攻方主动倒地在先，守门员无犯规，回看维持点球错误"}],
    76:  [{"team": "大连英博海发", "type": "wrong_offside_self", "note": "未越位被误判，进攻被终止"},
          {"team": "大连英博海发", "type": "missed_yellow_opponent", "note": "青岛海牛28号守门员比赛停止后接触属非体育行为，漏判黄牌"}],
    77:  [{"team": "浙江俱乐部绿城", "type": "denied_goal", "note": "36号手臂属合理位置，近距离变线后意外触球，误判手球致进球无效"}],
    79:  [{"team": "广东广州豹", "type": "opp_goal_should_disallow", "note": "大连鲲城21号手臂扩张触球犯规在先，进球应无效"}],
    80:  [{"team": "广东广州豹", "type": "missed_yellow_opponent", "note": "大连鲲城3号持续拉扯属SPA，漏判黄牌"}],
    81:  [{"team": "厦门飞鹭", "type": "opp_goal_should_disallow", "note": "杭州临平吴越33号犯规在先，经争抢后进球应无效"}],
    84:  [{"team": "武汉三镇B队", "type": "missed_penalty", "note": "广州蒲公英48号草率绊人，应判点球"}],
    85:  [{"team": "武汉三镇B队", "type": "missed_yellow_opponent", "note": "广州蒲公英3号比赛停止期间接触属非体育行为，漏判黄牌"}],
    87:  [{"team": "广东铭途", "type": "missed_red_opponent", "note": "湖北青年星8号铲球属严重犯规，仅黄牌"}],
    88:  [{"team": "大连英博B队", "type": "missed_penalty", "note": "上海海港富盛经开51号铲倒12号，应判点球"}],
    89:  [{"team": "长春喜都", "type": "opp_goal_should_disallow", "note": "上海赛更达9号越位位置射门干扰比赛，进球应无效"}],
    # 期08
    91:  [{"team": "天津津门虎", "type": "missed_penalty", "note": "河南俱乐部彩陶坊22号手臂向球移动触球，应判点球"}],
    93:  [{"team": "成都蓉城", "type": "missed_yellow_opponent", "note": "上海海港31号违规使用手臂阻挡属鲁莽犯规，漏判黄牌"}],
    97:  [{"team": "天津津门虎", "type": "missed_penalty", "note": "上海海港3号罚球区内草率踢倒对方，应判点球"}],
    99:  [{"team": "山东泰山", "type": "wrong_penalty_against", "note": "武汉三镇29号主动跳向制造接触属佯装，点球错误"}],
    102: [{"team": "青岛红狮", "type": "missed_penalty", "note": "海门珂缔缘23号手臂向球移动触球，应判点球"}],
    103: [{"team": "广西平果呗侬女足", "type": "missed_penalty", "note": "女超判例（不在本页统计范围）"}],
    # 期09
    109: [{"team": "梅州客家犀旺", "type": "missed_penalty", "note": "定南赣联7号身后具有一定力度冲撞，应判点球"}],
    112: [{"team": "青岛红狮", "type": "wrong_red_self", "note": "4号手臂动作非故意击打头面部，属非体育行为，红牌错误"}],
    115: [{"team": "赣州瑞狮", "type": "wrong_penalty_against", "note": "正常争抢接触，攻方亦无假摔，点球错误"}],
    # 期10
    118: [{"team": "南京城市", "type": "denied_goal", "note": "10号未对守门员犯规，误判致进球无效"}],
    121: [{"team": "兰州陇原竞技", "type": "missed_penalty", "note": "大连可为27号手臂上扬触球，应判点球"}],
    123: [{"team": "山东泰山B队", "type": "denied_goal", "note": "23号正常起跳无犯规，误判且鸣哨在先，进球无法追认"}],
    124: [{"team": "广东铭途", "type": "wrong_red_self", "note": "守门员手臂收拢于身体未触球，手球与红牌均为错误"}],
    125: [{"team": "厦门飞鹭", "type": "missed_yellow_opponent", "note": "温州俱乐部8号接触属鲁莽犯规，漏判黄牌"},
          {"team": "温州俱乐部", "type": "wrong_yellow_self", "note": "28号拉扯未破坏有希望进攻，黄牌错误"}],
    126: [{"team": "厦门飞鹭", "type": "wrong_red_self", "note": "7号非法使用手臂属鲁莽犯规，红牌错误、应黄牌"}],
    # 期11
    131: [{"team": "南京城市", "type": "missed_penalty", "note": "石家庄功夫16号晚到踢人，犯规地点在罚球区内，应判点球"}],
    132: [{"team": "南京城市", "type": "opp_goal_should_disallow", "note": "石家庄功夫10号越位位置触球，进球应无效"}],
    133: [{"team": "定南赣联", "type": "missed_yellow_opponent", "note": "无锡吴钩5号故意将球踢走延误恢复，漏判黄牌"}],
    134: [{"team": "泰安天贶", "type": "missed_red_opponent", "note": "山西崇德荣海16号鞋钉踩踏腹部属暴力行为，无牌"}],
    136: [{"team": "泰安天贶", "type": "missed_penalty", "note": "北京理工54号跳向冲撞，应判点球"}],
    # 期12
    142: [{"team": "石家庄功夫", "type": "wrong_penalty_against", "note": "18号手臂紧贴身体属自然位置，点球错误"}],
    # 期13
    153: [{"team": "梅州客家", "type": "opp_goal_should_disallow", "note": "双方均有队员提前进入罚球区，应重罚点球而非判补射进球有效"}],
    154: [{"team": "江西庐山", "type": "denied_goal", "note": "18号未干扰比赛或对方，越位误判致进球无效"}],
    155: [{"team": "大连可为", "type": "wrong_penalty_against", "note": "14号铲球动作合理未接触对方，点球错误"}],
    156: [{"team": "大连可为", "type": "missed_penalty", "note": "上海赛更达11号未触球踢到对方，应判点球"}],
    157: [{"team": "大连可为", "type": "missed_penalty", "note": "上海赛更达15号鞋钉踩到脚踝脚面，应判点球"},
          {"team": "大连可为", "type": "missed_yellow_opponent", "note": "该踩踏属鲁莽犯规，应出示黄牌"}],
    158: [{"team": "上海赛更达", "type": "opp_goal_should_disallow", "note": "大连可为29号越位位置射门干扰比赛，进球应无效"}],
    # 期14
    159: [{"team": "石家庄功夫", "type": "missed_red_opponent", "note": "延边龙鼎37号故意击打属暴力行为，仅黄牌"}],
    162: [{"team": "定南赣联", "type": "missed_yellow_opponent", "note": "宁波俱乐部5号违规使用手臂属鲁莽犯规，掌握有利后漏判黄牌"}],
    164: [{"team": "北京城建女足", "type": "missed_penalty", "note": "女超判例（不在本页统计范围）"}],
    # 期15
    165: [{"team": "深圳新鹏城", "type": "opp_goal_should_disallow", "note": "云南玉昆9号越位位置跑动影响守门员，回看维持进球有效错误"}],
    167: [{"team": "石家庄功夫", "type": "denied_goal", "note": "无人越位，误判越位且鸣哨在先，进球无法追认"}],
    168: [{"team": "石家庄功夫", "type": "denied_goal", "note": "正常争顶不犯规，误判且鸣哨在先，进球无法追认"}],
    170: [{"team": "大连英博B队", "type": "missed_penalty", "note": "大连可为35号踢倒45号，误判攻方手球，应判点球"}],
    172: [{"team": "厦门飞鹭", "type": "wrong_penalty_against", "note": "8号接触力度未达犯规程度，点球错误"}],
    # 期16
    176: [{"team": "陕西联合", "type": "denied_goal", "note": "20号未越位，助理裁判员误判致进球无效"}],
    177: [{"team": "陕西联合", "type": "missed_penalty", "note": "大连鲲城13号手臂环绕颈部拉扯，应判点球"}],
    179: [{"team": "南京城市", "type": "missed_red_opponent", "note": "延边龙鼎10号无球状态挥臂击打头部属暴力行为，仅判犯规无牌"}],
    181: [{"team": "延边龙鼎可喜安", "type": "missed_yellow_opponent", "note": "南京城市9号违规使用手臂属鲁莽犯规，漏判犯规和黄牌"}],
    185: [{"team": "泰安天贶", "type": "missed_penalty", "note": "兰州陇原竞技39号推人致失去控球权倒地，应判点球"},
          {"team": "泰安天贶", "type": "missed_yellow_opponent", "note": "该推人属SPA，应出示黄牌"}],
    # 期18
    205: [{"team": "江西庐山", "type": "opp_goal_should_disallow", "note": "厦门飞鹭7号越位位置获利，进球应无效"}],
    # 期19
    208: [{"team": "石家庄功夫", "type": "missed_red_opponent", "note": "定南赣联16号发力蹬踹胸腹部属严重犯规，仅黄牌"}],
    209: [{"team": "石家庄功夫", "type": "missed_red_opponent", "note": "定南赣联队员非争抢时故意撩踹属暴力行为，漏判红牌"}],
    211: [{"team": "山东泰山B队", "type": "wrong_yellow_self", "note": "5号绊摔判点球正确，但无需出示黄牌"}],
    212: [{"team": "贵州贵阳竞技", "type": "missed_red_opponent", "note": "广州蒲公英22号挥臂击打头部属暴力行为，漏判红牌"}],
    # 期21
    216: [{"team": "延边龙鼎", "type": "opp_goal_should_disallow", "note": "广西恒宸36号手臂触球后立即进球，应判手球进球无效"}],
    217: [{"team": "石家庄功夫", "type": "denied_goal", "note": "无人越位，助理裁判员误判致进球无效"}],
    # 期22
    223: [{"team": "南通支云", "type": "missed_yellow_opponent", "note": "广西恒宸18号脚底剐蹭属鲁莽犯规，漏判犯规和黄牌"}],
    225: [{"team": "杭州临平吴越", "type": "wrong_foul_called_self", "note": "56号正常争抢碰撞，攻方犯规误判"}],
}

TEAM_NORMALIZE = {
    "广东广州豹": "广州豹",
    "大连英博海发": "大连英博",
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


def main():
    data = json.loads((DATA / "cases-2026.json").read_text(encoding="utf-8"))
    cases = {c["seq"]: c for c in data["cases"]}

    out = {"scope": ["中超联赛", "中甲联赛", "中乙联赛"],
           "type_labels": TYPE_LABEL, "swing": SWING,
           "team_normalize": TEAM_NORMALIZE, "match_notes": {},
           "impacts": {}}

    skipped = []
    for seq, items in IMPACT.items():
        c = cases[seq]
        assert c["referee_verdict"] == "wrong", f"seq {seq} 非 wrong"
        league = c["comp"]
        if league not in out["scope"]:
            skipped.append(seq)
            continue
        rnd = c.get("round", "")
        rm = re.search(r"第(\d+)轮", rnd or "")
        round_no = int(rm.group(1)) if rm else None
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
    assert not skipped or all(cases[s]["comp"] not in out["scope"] for s in skipped), skipped
    (DATA / "impact-2026.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter
    matches = sorted({(v["league"], v["round"], v["home"], v["away"])
                      for v in out["impacts"].values()})
    print(f"标注 {len(out['impacts'])} 例 / {len(matches)} 场比赛（范围外跳过: {skipped}）")
    print("类型分布:", Counter(i["type"] for v in out["impacts"].values() for i in v["items"]))
    swing_matches = sorted({(v["league"], v["round"], v["home"], v["away"])
                            for v in out["impacts"].values()
                            if any(i["swing"] for i in v["items"])})
    print(f"确定得失球修正涉及 {len(swing_matches)} 场：")
    for lg, rd, h, a in swing_matches:
        print(f"  {lg}|{rd}|{h}|{a}")


if __name__ == "__main__":
    main()
