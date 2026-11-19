# -*- coding: utf-8 -*-
"""拆分 2025 第27期补充认定，可重复调用。"""

import json

from lib.atomic_json import write_json
from lib.paths import DATA


def fix_data(data):
    cases = {c["seq"]: c for c in data["cases"]}

    c183, c188, c195 = cases[183], cases[188], cases[195]

    if "判例三（第二十六期判例二）：" not in c195["conclusion"]:
        assert "【第27期补充认定】" in c183["conclusion"]
        assert "【第27期补充认定】" in c188["conclusion"]
        assert len(c195["video_files"]) == 1
        return data
    # 1) 拆分 #195 结论
    SPLIT3 = "判例三（第二十六期判例二）："
    SPLIT4 = "判例四（第二十六期判例七）："
    conc = c195["conclusion"]
    i3 = conc.find(SPLIT3)
    i4 = conc.find(SPLIT4)
    assert i3 > 0 and i4 > i3, "未找到拆分标记"
    part195 = conc[:i3].strip()
    part183 = conc[i3:i4].strip()
    part188 = conc[i4:].strip()
    c195["conclusion"] = part195
    c183["conclusion"] = (
        c183["conclusion"].rstrip()
        + "\n【第27期补充认定】"
        + part183.replace(SPLIT3, "", 1).strip()
    )
    c188["conclusion"] = (
        c188["conclusion"].rstrip()
        + "\n【第27期补充认定】"
        + part188.replace(SPLIT4, "", 1).strip()
    )

    # 2) #195 申诉只保留广西恒宸部分
    ap = c195["appeal"]
    j = ap.find("山东泰山俱乐部申诉意见认为")
    if j > 0:
        c195["appeal"] = ap[:j].strip()

    # 3) #195 的归类/判定修正不在本脚本：语义层校正在 classify_cases.py 末尾的
    #    2025 赛季特判里（管线顺序 fix → classify，只留一处防止双份漂移）

    # 4) 视频归还：#195 保留第1个；第2、3个分别给 #183、#188 作补充角度
    u195 = c195["video_urls"]
    assert len(u195) == 3, f"#195视频数异常: {u195}"
    v183, v188 = u195[1], u195[2]
    c195["video_urls"] = [u195[0]]
    f195 = c195["video_files"]
    assert len(f195) == 3, f"#195视频文件数异常: {f195}"

    # 现行 schema 的 video_files 带赛季前缀（如 "2025/i27c02-1.mp4"），从既有值推导而不是硬编码，
    # 否则重跑会把无前缀路径混进 JSON 且下面的整串比较断言恒真、静默损坏
    def pf(fname):
        return f"{f195[0].rsplit('/', 1)[0]}/{fname}" if "/" in f195[0] else fname

    c195["video_files"] = [f195[0]]
    assert not any(f.endswith("i26c02-2.mp4") for f in c183["video_files"])
    assert not any(f.endswith("i26c07-2.mp4") for f in c188["video_files"])
    c183["video_urls"].append(v183)
    c183["video_files"].append(pf("i26c02-2.mp4"))
    c188["video_urls"].append(v188)
    c188["video_files"].append(pf("i26c07-2.mp4"))
    c183["tags"] = ["证据不足", "腋窝以下", "第27期补充认定"]
    c188["tags"] = ["红牌", "暴力行为", "比赛停止时", "第27期补充认定"]

    data["cases"] = [cases[c["seq"]] for c in data["cases"]]
    return data


def main():
    path = DATA / "cases-2025.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    fix_data(data)
    write_json(path, data)


if __name__ == "__main__":
    main()
