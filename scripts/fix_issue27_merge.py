# -*- coding: utf-8 -*-
"""一次性修正：拆分第27期判例2（误合并了26期两个判例的补充认定），
把补充认定文本与补充视频归还给 #183(期26判例2手球) 和 #188(期26判例7头撞)"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
path = ROOT / "data" / "cases-2025.json"
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

# 3) #195 归类修正：本身是无锡吴钩越位申诉，评议组支持进球有效
c195["category"] = "offside"
c195["category_name"] = "越位"
c195["tags"] = ["证据不足"]
c195["referee_verdict"] = "correct"
c195["referee_verdict_name"] = "支持原判"
c195["var_verdict"] = "none"
c195["var_verdict_name"] = "未涉及"

# 4) 视频归还：#195 保留第1个；第2、3个分别给 #183、#188 作补充角度
u195 = c195["video_urls"]
assert len(u195) == 3, f"#195视频数异常: {u195}"
v183, v188 = u195[1], u195[2]
c195["video_urls"] = [u195[0]]
c195["video_files"] = ["i27c02-1.mp4"]
assert "i26c02-2.mp4" not in c183["video_files"]
assert "i26c07-2.mp4" not in c188["video_files"]
c183["video_urls"].append(v183)
c183["video_files"].append("i26c02-2.mp4")
c188["video_urls"].append(v188)
c188["video_files"].append("i26c07-2.mp4")
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
