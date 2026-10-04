# -*- coding: utf-8 -*-
"""一次性修正：拆分第27期判例2（误合并了26期两个判例的补充认定），
把补充认定文本与补充视频归还给 #183(期26判例2手球) 和 #188(期26判例7头撞)"""
import json

from lib.paths import DATA

path = DATA / "cases-2025.json"
data = json.loads(path.read_text(encoding="utf-8"))
cases = {c["seq"]: c for c in data["cases"]}

c183, c188, c195 = cases[183], cases[188], cases[195]

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
c183["conclusion"] = (c183["conclusion"].rstrip()
                      + "\n【第27期补充认定】" + part183.replace(SPLIT3, "", 1).strip())
c188["conclusion"] = (c188["conclusion"].rstrip()
                      + "\n【第27期补充认定】" + part188.replace(SPLIT4, "", 1).strip())

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
path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

# 校验输出
from collections import Counter
print("裁判判定:", Counter(c["referee_verdict"] for c in data["cases"]))
print("VAR判定:", Counter(c["var_verdict"] for c in data["cases"]))
for n in (9, 26, 27):
    cs = [c for c in data["cases"] if c["issue"] == n]
    w = sum(1 for c in cs if c["referee_verdict"] == "wrong")
    exp = next(i["expected_wrong"] for i in data["issues"] if i["no"] == n)
    print(f"期{n}: 判例{len(cs)} 错误{w} 标题认定{exp}")
print("#195 videos:", c195["video_files"])
print("#183 videos:", c183["video_files"])
print("#188 videos:", c188["video_files"])
