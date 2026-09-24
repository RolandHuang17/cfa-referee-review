# -*- coding: utf-8 -*-
"""人工复核与教学分类：合并到 cases.json
每条: seq -> (类别, 标签列表, 裁判判定, VAR判定)
类别:
  handball        手球犯规
  offside         越位
  penalty_area    罚球区内判罚（点球）
  freekick_foul   罚球区外一般犯规
  spa_tactical    战术犯规与SPA（破坏有希望的进攻）
  dogso           破坏明显进球得分机会（DOGSO）
  sfp_vc          严重犯规与暴力行为（红牌尺度）
  simulation      假摔与欺骗行为
  goal_decision   进球判定与有利条款
  other_program   程序与其他
裁判判定: wrong(认定错漏判) / correct(支持原判) / pending(不予认定)
VAR判定: correct / wrong / none(未涉及) / (unknown不应残留)
"""

CLS = {
    # 期01
    1: ("sfp_vc", ["红牌", "严重犯规", "踩踏", "VAR介入正确"], "wrong", "correct"),
    2: ("sfp_vc", ["红牌", "严重犯规", "VAR介入正确"], "correct", "correct"),
    # 期02
    3: ("penalty_area", [], "correct", "correct"),
    4: ("sfp_vc", ["红牌", "严重犯规", "踩踏", "VAR介入错误"], "wrong", "wrong"),
    5: ("freekick_foul", ["错判犯规"], "wrong", "correct"),
    # 期03
    6: ("handball", ["点球", "漏判"], "wrong", "none"),
    7: ("penalty_area", [], "correct", "none"),
    8: ("goal_decision", ["拉扯", "进球无效"], "correct", "none"),
    9: ("dogso", ["点球", "红牌", "拉扯"], "wrong", "none"),
    10: ("sfp_vc", ["红牌", "严重犯规", "飞铲"], "wrong", "none"),
    11: ("handball", ["自然位置"], "correct", "none"),
    12: ("penalty_area", ["点球", "绊摔"], "wrong", "none"),
    13: ("offside", ["进球无效", "越位位置获利", "受限触球"], "wrong", "none"),
    # 期04
    14: ("penalty_area", ["点球", "DOGSO不成立"], "wrong", "none"),
    15: ("penalty_area", ["点球"], "wrong", "none"),
    # 期05
    16: ("dogso", ["点球", "红牌", "拉扯"], "wrong", "none"),
    17: ("handball", ["证据不足"], "correct", "none"),
    18: ("offside", ["证据不足"], "correct", "none"),
    19: ("handball", ["自然位置"], "correct", "none"),
    20: ("handball", ["点球", "手臂不自然扩大"], "wrong", "none"),
    21: ("penalty_area", ["点球", "争抢方式"], "correct", "none"),
    22: ("goal_decision", ["漏判犯规", "进球无效"], "wrong", "none"),
    23: ("penalty_area", [], "correct", "none"),
    24: ("penalty_area", ["点球", "绊摔"], "correct", "none"),
    # 期06
    25: ("dogso", ["点球", "红牌", "推搡", "VAR未介入错误"], "wrong", "wrong"),
    26: ("penalty_area", [], "correct", "correct"),
    27: ("sfp_vc", ["黄牌", "挥臂", "红牌不成立"], "wrong", "correct"),
    28: ("penalty_area", ["意外接触"], "correct", "correct"),
    29: ("freekick_foul", ["黄牌", "铲球", "红牌不成立"], "wrong", "correct"),
    30: ("offside", ["VAR划线", "进球有效"], "correct", "correct"),
    31: ("penalty_area", ["证据不足"], "correct", "none"),
    32: ("freekick_foul", ["争抢高球"], "correct", "none"),
    # 期07
    33: ("sfp_vc", ["红牌不成立", "争抢手臂"], "correct", "none"),
    34: ("sfp_vc", ["黄牌", "挥臂", "红牌不成立"], "correct", "none"),
    35: ("handball", ["自然位置"], "correct", "none"),
    36: ("penalty_area", ["点球", "踩踏"], "wrong", "none"),
    37: ("offside", ["进球无效", "越位位置获利", "受限触球"], "correct", "none"),
    38: ("penalty_area", [], "correct", "none"),
    39: ("penalty_area", ["主动倒地"], "correct", "none"),
    40: ("penalty_area", ["点球", "拉扯"], "wrong", "none"),
    # 期08
    41: ("penalty_area", ["点球"], "correct", "correct"),
    42: ("sfp_vc", ["红牌", "严重犯规", "蹬踩"], "correct", "correct"),
    43: ("offside", ["VAR划线", "进球无效"], "correct", "correct"),
    44: ("spa_tactical", ["黄牌", "DOGSO不成立", "守门员"], "wrong", "none"),
    # 期09
    45: ("sfp_vc", ["黄牌", "踩踏", "红牌不成立"], "correct", "correct"),
    46: ("sfp_vc", ["黄牌", "铲球", "红牌不成立"], "correct", "correct"),
    47: ("offside", ["VAR划线错误", "证据不足"], "pending", "wrong"),
    48: ("sfp_vc", ["红牌", "严重犯规", "踩踏", "VAR介入正确"], "wrong", "correct"),
    49: ("sfp_vc", ["黄牌", "挥臂", "红牌不成立"], "wrong", "correct"),
    50: ("goal_decision", ["争抢头球"], "correct", "none"),
    51: ("offside", ["越位误判"], "wrong", "none"),
    52: ("handball", ["证据不足"], "correct", "none"),
    53: ("freekick_foul", ["封堵合理"], "correct", "none"),
    54: ("goal_decision", ["推搡", "进球无效"], "wrong", "none"),
    55: ("spa_tactical", ["黄牌", "拉扯"], "wrong", "none"),
    56: ("penalty_area", [], "correct", "none"),
    57: ("penalty_area", [], "correct", "none"),
    # 期10
    58: ("penalty_area", ["拉扯轻微", "主动倒地"], "correct", "correct"),
    59: ("penalty_area", ["点球", "VAR介入正确", "坠球恢复"], "correct", "correct"),
    60: ("penalty_area", ["拉扯", "助理裁判协助"], "correct", "none"),
    61: ("offside", ["越位误判", "进球无效"], "wrong", "none"),
    62: ("simulation", ["点球", "黄牌", "假摔"], "wrong", "none"),
    63: ("penalty_area", ["点球", "绊摔"], "correct", "none"),
    64: ("penalty_area", ["点球", "黄牌", "背后冲撞"], "wrong", "none"),
    # 期11
    65: ("handball", ["证据不足"], "correct", "correct"),
    66: ("offside", ["进球无效", "干扰对方队员", "VAR未介入错误"], "wrong", "wrong"),
    67: ("sfp_vc", ["黄牌", "倒钩", "红牌不成立"], "correct", "correct"),
    68: ("sfp_vc", ["红牌", "暴力行为", "挥臂"], "correct", "none"),
    69: ("penalty_area", ["点球", "守门员"], "wrong", "none"),
    70: ("sfp_vc", ["红牌", "严重犯规", "蹬踹"], "wrong", "none"),
    # 期12
    71: ("handball", ["自然位置"], "correct", "correct"),
    72: ("penalty_area", ["点球", "拉扯"], "wrong", "none"),
    73: ("penalty_area", ["点球", "拉扯", "绊摔"], "wrong", "none"),
    74: ("offside", ["证据不足"], "correct", "none"),
    75: ("penalty_area", ["点球", "绊摔", "假摔不成立"], "correct", "none"),
    76: ("offside", ["守方触球重置"], "correct", "none"),
    77: ("dogso", ["点球", "红牌", "拉扯"], "wrong", "none"),
    78: ("freekick_foul", ["危险方式比赛", "间接任意球"], "correct", "none"),
    79: ("penalty_area", ["点球", "黄牌", "守门员"], "wrong", "none"),
    80: ("penalty_area", ["证据不足"], "correct", "none"),
    # 期13
    81: ("penalty_area", [], "correct", "none"),
    82: ("offside", ["越位误判", "进球无效"], "wrong", "none"),
    83: ("penalty_area", ["点球", "正常接触"], "wrong", "none"),
    84: ("penalty_area", ["地点判定", "直接任意球"], "correct", "none"),
    # 期14
    85: ("goal_decision", ["VAR介入错误", "进球有效", "比赛恢复前"], "wrong", "wrong"),
    86: ("penalty_area", ["点球", "无需红黄牌"], "correct", "correct"),
    87: ("offside", ["VAR划线", "进球有效"], "correct", "correct"),
    88: ("spa_tactical", ["黄牌", "DOGSO不成立"], "correct", "correct"),
    89: ("handball", ["点球", "无需红黄牌"], "correct", "none"),
    90: ("penalty_area", ["证据不足"], "correct", "none"),
    91: ("handball", ["点球", "手臂不自然扩大"], "correct", "none"),
    92: ("handball", ["证据不足"], "correct", "none"),
    93: ("penalty_area", ["点球", "DOGSO应黄牌"], "correct", "none"),
    94: ("penalty_area", ["证据不足"], "correct", "none"),
    95: ("goal_decision", ["球门线", "证据不足"], "correct", "none"),
    96: ("sfp_vc", ["红牌", "严重犯规", "蹬踹", "VAR未介入错误"], "wrong", "wrong"),
    # 期15
    97: ("penalty_area", ["点球", "VAR介入正确"], "correct", "correct"),
    98: ("handball", ["证据不足"], "correct", "none"),
    99: ("handball", ["点球", "手向球移动"], "wrong", "none"),
    100: ("penalty_area", ["铲球先触球"], "correct", "none"),
    101: ("sfp_vc", ["红牌", "严重犯规", "铲球"], "wrong", "none"),
    102: ("goal_decision", ["进球有效", "推人不成立"], "wrong", "none"),
    103: ("penalty_area", ["证据不足"], "pending", "none"),
    104: ("goal_decision", ["进球漏判", "球门线"], "wrong", "none"),
    105: ("offside", ["证据不足"], "correct", "none"),
    106: ("penalty_area", ["点球", "抢截"], "wrong", "none"),
    107: ("penalty_area", ["点球", "绊摔"], "wrong", "none"),
    # 期16
    108: ("penalty_area", [], "correct", "correct"),
    109: ("penalty_area", [], "correct", "correct"),
    110: ("penalty_area", ["比赛停止期间"], "correct", "correct"),
    111: ("penalty_area", ["证据不足"], "correct", "correct"),
    112: ("offside", ["进球无效", "干扰对方队员"], "wrong", "none"),
    113: ("sfp_vc", ["红牌不成立", "蹬踹不成立"], "correct", "none"),
    114: ("penalty_area", ["主动倒地"], "correct", "none"),
    115: ("offside", ["证据不足"], "correct", "none"),
    # 期17
    116: ("goal_decision", ["推击", "进球无效"], "correct", "none"),
    117: ("penalty_area", ["点球", "假摔不成立"], "correct", "none"),
    118: ("offside", ["干扰对方队员", "进球有效"], "correct", "none"),
    119: ("other_program", ["裁判员选位"], "correct", "none"),
    120: ("handball", ["证据不足"], "correct", "none"),
    121: ("dogso", ["点球", "黄牌", "守门员"], "wrong", "none"),
    122: ("offside", ["越位误判", "进球无效"], "wrong", "none"),
    # 期18
    123: ("handball", ["点球", "手向球移动"], "correct", "none"),
    124: ("penalty_area", ["点球", "守门员", "绊摔"], "correct", "none"),
    125: ("penalty_area", ["守门员"], "correct", "none"),
    126: ("penalty_area", ["地点判定", "直接任意球"], "wrong", "none"),
    127: ("penalty_area", ["铲球先触球"], "correct", "none"),
    128: ("offside", ["进球无效", "越位位置干扰比赛"], "wrong", "none"),
    129: ("offside", ["证据不足"], "correct", "none"),
    130: ("penalty_area", ["证据不足"], "pending", "none"),
    # 期19
    131: ("handball", ["点球", "第四官员协助"], "correct", "none"),
    132: ("goal_decision", ["用手控制球", "进球无效"], "correct", "none"),
    133: ("handball", ["意外手球"], "correct", "none"),
    134: ("offside", ["进球有效"], "correct", "none"),
    135: ("handball", ["点球", "手臂不自然扩大"], "wrong", "none"),
    136: ("penalty_area", ["点球", "拉扯", "抱拽"], "wrong", "none"),
    137: ("penalty_area", ["点球", "铲球先触球"], "wrong", "none"),
    # 期20
    138: ("handball", ["进球有效", "意外手球"], "correct", "correct"),
    139: ("goal_decision", ["出界判定", "延迟举旗提示"], "correct", "correct"),
    140: ("penalty_area", ["点球", "地点判定", "VAR介入正确", "电视手势遗漏"], "correct", "correct"),
    141: ("goal_decision", ["进球有效", "守门员"], "wrong", "none"),
    142: ("sfp_vc", ["红牌", "暴力行为", "黄牌"], "wrong", "none"),
    143: ("goal_decision", ["出界判定", "证据不足", "延迟举旗提示"], "pending", "none"),
    144: ("sfp_vc", ["红牌不成立", "踩踏不成立"], "correct", "none"),
    145: ("penalty_area", ["点球", "主动倒地"], "wrong", "none"),
    146: ("goal_decision", ["黄牌", "进球无效", "守门员"], "wrong", "none"),
    147: ("penalty_area", ["点球", "守门员"], "wrong", "none"),
    148: ("goal_decision", ["用手控制球", "进球无效"], "correct", "none"),
    149: ("handball", ["自然位置", "铲球支撑手"], "correct", "none"),
    # 期21
    150: ("penalty_area", ["点球", "VAR未介入错误"], "wrong", "wrong"),
    151: ("goal_decision", ["进球有效"], "correct", "correct"),
    152: ("handball", ["意外手球"], "correct", "correct"),
    153: ("penalty_area", ["互有拉扯"], "correct", "correct"),
    154: ("penalty_area", ["主动倒地"], "correct", "correct"),
    155: ("offside", ["越位重置", "进球有效"], "correct", "correct"),
    156: ("penalty_area", ["点球", "草率冲撞"], "correct", "correct"),
    157: ("dogso", ["红牌", "DOGSO", "VAR介入正确", "守门员"], "correct", "correct"),
    158: ("goal_decision", ["VAR介入错误", "进球有效"], "correct", "wrong"),
    159: ("penalty_area", ["点球", "攻方犯规亦不应判"], "correct", "none"),
    160: ("offside", ["越位误判"], "wrong", "none"),
    161: ("goal_decision", ["证据不足"], "correct", "none"),
    162: ("penalty_area", ["点球", "铲球先触球"], "wrong", "none"),
    # 期22
    163: ("goal_decision", ["VAR介入错误", "进球有效"], "wrong", "wrong"),
    164: ("sfp_vc", ["红牌", "严重犯规", "踩踏", "VAR介入正确"], "correct", "correct"),
    # 期23
    165: ("goal_decision", ["进球无效", "踩踏"], "correct", "correct"),
    166: ("penalty_area", ["主动倒地"], "correct", "correct"),
    167: ("handball", ["意外手球"], "correct", "none"),
    168: ("sfp_vc", ["黄牌", "挥臂", "红牌不成立"], "wrong", "none"),
    169: ("sfp_vc", ["红牌", "暴力行为", "有利条款不适用"], "correct", "none"),
    # 期24
    170: ("sfp_vc", ["红牌不成立", "踩踏"], "correct", "correct"),
    171: ("goal_decision", ["进球无效", "VAR未介入错误", "争顶"], "wrong", "wrong"),
    172: ("offside", ["VAR划线", "折射"], "correct", "correct"),
    173: ("penalty_area", ["争抢高球"], "correct", "correct"),
    174: ("sfp_vc", ["红牌", "严重犯规", "挥臂", "VAR未介入错误"], "wrong", "wrong"),
    175: ("freekick_foul", ["争抢高球", "收脚"], "correct", "correct"),
    176: ("penalty_area", ["铲球"], "correct", "none"),
    177: ("penalty_area", [], "correct", "none"),
    # 期25
    178: ("penalty_area", ["点球", "绊摔", "无需红黄牌"], "correct", "correct"),
    179: ("sfp_vc", ["红牌", "严重犯规", "踩踏", "VAR介入正确"], "wrong", "correct"),
    180: ("penalty_area", ["守门员"], "correct", "none"),
    181: ("goal_decision", ["有利条款", "进球有效", "守门员"], "wrong", "none"),
    # 期26
    182: ("penalty_area", [], "correct", "correct"),
    183: ("handball", ["证据不足", "腋窝以下"], "correct", "correct"),
    184: ("goal_decision", ["守门员", "进球有效"], "correct", "correct"),
    185: ("handball", ["点球", "VAR介入正确"], "wrong", "correct"),
    186: ("penalty_area", ["证据不足"], "correct", "none"),
    187: ("simulation", ["黄牌", "非体育行为", "佯装夸大"], "correct", "none"),
    188: ("sfp_vc", ["红牌", "暴力行为", "比赛停止时"], "wrong", "none"),
    189: ("goal_decision", ["有利条款", "进球有效"], "correct", "none"),
    190: ("offside", ["进球无效", "越位位置获利"], "wrong", "none"),
    191: ("sfp_vc", ["黄牌", "红牌不成立", "铲球"], "correct", "none"),
    192: ("goal_decision", ["进球有效", "鸣哨后进球"], "wrong", "none"),
    193: ("penalty_area", ["证据不足"], "correct", "none"),
    # 期27
    194: ("penalty_area", ["地点判定"], "correct", "correct"),
    195: ("sfp_vc", ["红牌", "暴力行为", "比赛停止时", "手球不犯规"], "wrong", "correct"),
    # 期28
    196: ("sfp_vc", ["红牌", "暴力行为", "挥拳"], "wrong", "none"),
    197: ("sfp_vc", ["红牌", "严重犯规", "抬脚过高", "VAR未介入错误"], "wrong", "wrong"),
    198: ("goal_decision", ["球门线", "证据不足"], "pending", "none"),
    199: ("sfp_vc", ["红牌", "黄牌", "暴力行为不成立"], "wrong", "none"),
    200: ("sfp_vc", ["红牌", "暴力行为"], "correct", "none"),
    201: ("penalty_area", [], "correct", "none"),
    202: ("penalty_area", ["点球", "黄牌", "拉扯"], "correct", "none"),
    203: ("goal_decision", ["进球有效"], "correct", "none"),
    # 期29
    204: ("penalty_area", ["点球", "VAR介入正确"], "correct", "correct"),
    205: ("penalty_area", ["点球", "拉扯", "VAR介入正确"], "wrong", "correct"),
    206: ("handball", ["点球", "手臂不自然扩大"], "wrong", "none"),
    207: ("penalty_area", ["铲球先触球", "通讯程序说明"], "correct", "correct"),
    208: ("sfp_vc", ["黄牌", "红牌不成立"], "correct", "none"),
    # 期30
    209: ("simulation", ["假摔", "黄牌", "VAR介入正确"], "correct", "correct"),
    210: ("penalty_area", ["点球", "跳向对方"], "wrong", "none"),
    211: ("sfp_vc", ["红牌", "球队官员", "暴力行为"], "correct", "none"),
    # 期31
    212: ("penalty_area", ["红牌不成立", "DOGSO不成立", "附应判犯规并黄牌"], "correct", "correct"),
    213: ("offside", ["阻碍视线", "进球无效"], "correct", "correct"),
    214: ("penalty_area", ["点球", "黄牌", "VAR介入正确"], "correct", "correct"),
    215: ("sfp_vc", ["证据不足", "附应黄牌警告"], "pending", "none"),
    216: ("sfp_vc", ["黄牌", "红牌不成立", "铲球"], "correct", "correct"),
    217: ("sfp_vc", ["黄牌", "红牌不成立", "铲球"], "correct", "correct"),
    218: ("penalty_area", ["进球有效"], "correct", "correct"),
    219: ("sfp_vc", ["红牌", "严重犯规", "挥臂"], "correct", "correct"),
    220: ("offside", ["越位误判", "进球有效"], "wrong", "none"),
    221: ("penalty_area", ["点球", "冲撞"], "wrong", "none"),
    # 期32
    222: ("goal_decision", ["有利条款", "手球", "VAR不介入正确"], "wrong", "correct"),
    223: ("handball", ["点球", "手向球移动", "VAR未介入错误"], "wrong", "wrong"),
    224: ("goal_decision", ["球门线", "证据不足"], "pending", "none"),
    225: ("sfp_vc", ["红牌", "黄牌", "暴力行为不成立", "VAR介入错误"], "wrong", "wrong"),
    226: ("offside", ["进球无效", "干扰对方队员"], "wrong", "none"),
    227: ("penalty_area", [], "correct", "none"),
}

CATEGORY_NAMES = {
    "handball": "手球犯规",
    "offside": "越位",
    "penalty_area": "罚球区内判罚（点球）",
    "freekick_foul": "罚球区外一般犯规",
    "spa_tactical": "战术犯规与SPA",
    "dogso": "破坏明显进球得分机会（DOGSO）",
    "sfp_vc": "严重犯规与暴力行为",
    "simulation": "假摔与欺骗行为",
    "goal_decision": "进球判定与有利条款",
    "other_program": "程序与其他",
}

VERDICT_NAMES = {"wrong": "错漏判", "correct": "支持原判", "pending": "不予认定"}
VAR_NAMES = {"correct": "VAR正确", "wrong": "VAR错误", "none": "未涉及"}


def main():
    import json
    from pathlib import Path
    from collections import Counter

    root = Path(__file__).resolve().parent.parent
    path = root / "data" / "cases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data["cases"]
    assert len(CLS) == len(cases), f"分类条目{len(CLS)} != 判例{len(cases)}"
    missing = [c["seq"] for c in cases if c["seq"] not in CLS]
    assert not missing, f"缺少分类: {missing}"

    for c in cases:
        cat, tags, rv, vv = CLS[c["seq"]]
        c["category"] = cat
        c["category_name"] = CATEGORY_NAMES[cat]
        c["tags"] = tags
        c["referee_verdict"] = rv
        c["referee_verdict_name"] = VERDICT_NAMES[rv]
        c["var_verdict"] = vv
        c["var_verdict_name"] = VAR_NAMES[vv]
        c.pop("need_manual", None)

    # 每期核对
    print(f"{'期':>3} {'判例':>4} {'标题认定':>6} {'复核错误':>6}  差异说明")
    for it in data["issues"]:
        n = it["no"]
        cs = [c for c in cases if c["issue"] == n]
        w = sum(1 for c in cs if c["referee_verdict"] == "wrong")
        note = ""
        if w != it["expected_wrong"]:
            note = f"标题{it['expected_wrong']}例（差异见页面注释）"
        print(f"{n:>3} {len(cs):>4} {it['expected_wrong']:>8} {w:>8}  {note}")

    print("\n裁判判定:", Counter(c["referee_verdict"] for c in cases))
    print("VAR判定:", Counter(c["var_verdict"] for c in cases))
    print("分类分布:")
    for cat, name in CATEGORY_NAMES.items():
        cnt = sum(1 for c in cases if c["category"] == cat)
        print(f"  {name}: {cnt}")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写回 {path}")


if __name__ == "__main__":
    main()
