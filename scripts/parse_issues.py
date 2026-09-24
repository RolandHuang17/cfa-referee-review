# -*- coding: utf-8 -*-
"""解析32期HTML -> data/cases.json（判例结构化 + 视频映射 + 自动结论归类 + 标题交叉校验）"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "issues_raw"
OUT = ROOT / "data" / "cases.json"

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
          "八": 8, "九": 9, "十": 10}
ISSUE_URL = {
    1: "https://www.thecfa.cn/zyls1/20250227/35667.html",
    2: "https://www.thecfa.cn/zyls1/20250305/35703.html",
    3: "https://www.thecfa.cn/zyls1/20250319/35769.html",
    4: "https://www.thecfa.cn/zyls1/20250328/35803.html",
    5: "https://www.thecfa.cn/zyls1/20250402/35819.html",
    6: "https://www.thecfa.cn/zyls1/20250409/35844.html",
    7: "https://www.thecfa.cn/zyls1/20250416/35868.html",
    8: "https://www.thecfa.cn/zyls1/20250423/35901.html",
    9: "https://www.thecfa.cn/zyls1/20250501/35914.html",
    10: "https://www.thecfa.cn/zyls1/20250507/36449.html",
    11: "https://www.thecfa.cn/zyls1/20250514/36471.html",
    12: "https://www.thecfa.cn/zyls1/20250521/36493.html",
    13: "https://www.thecfa.cn/zyls1/20250604/36545.html",
    14: "https://www.thecfa.cn/zyls1/20250618/36597.html",
    15: "https://www.thecfa.cn/zyls1/20250625/36616.html",
    16: "https://www.thecfa.cn/zyls1/20250703/36647.html",
    17: "https://www.thecfa.cn/zyls1/20250709/36668.html",
    18: "https://www.thecfa.cn/zyls1/20250718/36707.html",
    19: "https://www.thecfa.cn/zyls1/20250724/36722.html",
    20: "https://www.thecfa.cn/zyls1/20250730/36757.html",
    21: "https://www.thecfa.cn/zyls1/20250806/36774.html",
    22: "https://www.thecfa.cn/zyls1/20250813/36785.html",
    23: "https://www.thecfa.cn/zyls1/20250820/36819.html",
    24: "https://www.thecfa.cn/cppy/20250827/36854.html",
    25: "https://www.thecfa.cn/cppy/20250903/36876.html",
    26: "https://www.thecfa.cn/cppy/20250917/36917.html",
    27: "https://www.thecfa.cn/cppy/20250924/36927.html",
    28: "https://www.thecfa.cn/cppy/20251001/36955.html",
    29: "https://www.thecfa.cn/cppy/20251008/36962.html",
    30: "https://www.thecfa.cn/cppy/20251022/37010.html",
    31: "https://www.thecfa.cn/cppy/20251029/37036.html",
    32: "https://www.thecfa.cn/cppy/20251105/37055.html",
}

COMP_KEYWORDS = ["中超联赛", "中甲联赛", "中乙联赛", "中国足协杯", "足协杯",
                 "全国运动会", "全运会", "女超联赛", "女甲联赛", "女乙联赛",
                 "中冠联赛", "U21联赛", "U19联赛", "U17联赛", "锦标赛",
                 "青少年联赛", "超级杯"]


def cn2int(s: str) -> int:
    if not s:
        return 0
    if s in CN_NUM:
        return CN_NUM[s]
    if s.startswith("十"):
        return 10 + cn2int(s[1:])
    if "十" in s:
        a, _, b = s.partition("十")
        return CN_NUM.get(a, 0) * 10 + (CN_NUM.get(b, 0) if b else 0)
    return 0


def clean(text: str) -> str:
    text = text.replace("\xa0", " ").replace("&nbsp;", " ")
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\s*\n\s*", "\n", text).strip()


def extract_content(html: str) -> str:
    """取 news_right_list div 内部HTML（文章正文区，到 news_sidebar 为止）"""
    a = html.find('<div class="news_right_list">')
    if a < 0:
        return ""
    b = html.find('<div class="news_sidebar"', a)
    return html[a + len('<div class="news_right_list">'):b] if b > a else ""


def split_paragraphs(content_html: str):
    """按 <p ...>...</p> 切分，返回 [(text, [video_urls])]"""
    paras = []
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", content_html, re.S):
        inner = m.group(1)
        vids = re.findall(r'(?:<video|<source)[^>]+src="(https://videooss\.thecfa\.cn[^"]+)"', inner)
        vids = list(dict.fromkeys(vids))
        text = clean(inner)
        paras.append((text, vids))
    return paras


def parse_case_head(text: str):
    """判例描述段 -> (match_info, comp, round, home, away, minute)"""
    head = text.split("。")[0]
    head = re.sub(r"^判例[一二三四五六七八九十百]+[：:]", "", head).strip()
    comp = next((k for k in COMP_KEYWORDS if k in head), "")
    rnd = ""
    m = re.search(r"第[0-9一二三四五六七八九十百]+轮", head)
    if m:
        rnd = m.group(0)
    home = away = ""
    m = re.search(r"([^，,。\s]+?)\s*(?:VS|vs|Vs)\s*([^，,。\s]+)", head)
    if m:
        home, away = m.group(1), m.group(2)
    minute = ""
    m = re.search(r"比赛第\s*(\d+)\s*分钟", text)
    if m:
        minute = m.group(1)
    return head, comp, rnd, home, away, minute


def strip_var_parts(text: str) -> str:
    """去掉VAR相关分句，便于判断裁判员本身的判定"""
    text = re.sub(r"(?:VAR|视频助理裁判)[^。；;]*", "", text)
    text = re.sub(r"(?:未|不)?介入[^。；;]*", "", text)
    return text


def classify(conc: str):
    """返回 (referee_verdict, var_verdict, need_manual)"""
    var = "none"
    if re.search(r"VAR|视频助理裁判", conc):
        if re.search(r"(?:介入|未介入|不介入)(?:错误)", conc):
            var = "wrong"
        elif re.search(r"(?:介入|不介入)(?:正确|恰当|无误)", conc):
            var = "correct"
        else:
            var = "unknown"  # 提及VAR但未明说对错
    if re.search(r"不予认定|无法判断|无法认定", conc):
        return "pending", var, var == "unknown"
    body = strip_var_parts(conc)
    wrong = re.search(r"决定错误|判罚错误|错判|漏判|误判|认定.{0,6}为犯规|应为|属于犯规", body)
    correct = re.search(r"支持|正确|并无不当|不构成犯规|不属犯规|并无犯规|并无明显犯规", body)
    if wrong and not correct:
        return "wrong", var, False
    if correct and not wrong:
        return "correct", var, False
    if wrong and correct:
        # 复合表述，如“错判红牌漏判黄牌”仍属错误；先自动归wrong，人工复核
        return "wrong", var, True
    return "unclear", var, True


def main():
    issues = []
    cases = []
    seq = 0
    for n in range(1, 33):
        f = RAW / f"issue_{n:02d}.html"
        html = f.read_text(encoding="utf-8")
        title_m = re.search(r"<title>(.*?)</title>", html, re.S)
        title = clean(title_m.group(1)).split("-中国足球协会")[0] if title_m else ""
        expect = 0
        tm = re.search(r"认定(\d+)例裁判[错漏判]+", title)
        if tm:
            expect = int(tm.group(1))
        content = extract_content(html)
        paras = split_paragraphs(content)
        # 综述 = 首个判例段之前的文本段
        summary = []
        cur = None
        orphan_vids = []
        for text, vids in paras:
            cm = re.match(r"^判例([一二三四五六七八九十百]+)[：:]", text)
            if cm:
                cur = {
                    "issue": n, "no": cn2int(cm.group(1)), "desc": text,
                    "appeal": "", "conclusion": "", "videos": [],
                }
                seq += 1
                cur["seq"] = seq
                cases.append(cur)
                continue
            if cur is None:
                if text and "扫码" not in text and "分享至" not in text:
                    summary.append(text)
                orphan_vids += vids
                continue
            if "申诉意见认为" in text or "申诉意见如下" in text:
                cur["appeal"] += (("\n" if cur["appeal"] else "") + text)
                continue
            if not text and vids:
                cur["videos"] += vids
                continue
            if re.search(r"评议组|对于此判例", text) or cur["conclusion"]:
                cur["conclusion"] += (("\n" if cur["conclusion"] else "") + text)
                continue
            # 其他正文段落并入结论区
            cur["conclusion"] += (("\n" if cur["conclusion"] else "") + text)
        # 结尾套路段剔除
        for c in cases:
            if c["issue"] != n:
                continue
            c["conclusion"] = re.sub(
                r"中国足协将继续秉持.*$", "", c["conclusion"], flags=re.S).strip()
            c["match_info"], c["comp"], c["round"], c["home"], c["away"], c["minute"] = \
                parse_case_head(c["desc"])
            c["referee_verdict"], c["var_verdict"], c["need_manual"] = classify(
                c["desc"] + "\n" + c["appeal"] + "\n" + c["conclusion"])
        wrong_n = sum(1 for c in cases if c["issue"] == n and c["referee_verdict"] == "wrong")
        issues.append({
            "no": n, "title": title, "url": ISSUE_URL[n],
            "date": re.search(r"/(\d{8})/", ISSUE_URL[n]).group(1),
            "summary": "\n".join(summary).strip(),
            "expected_wrong": expect, "parsed_wrong": wrong_n,
            "video_count": sum(len(c["videos"]) for c in cases if c["issue"] == n),
        })
    # 视频本地文件名
    for c in cases:
        for k, v in enumerate(c["videos"], 1):
            c.setdefault("video_files", []).append(f"i{c['issue']:02d}c{c['no']:02d}-{k}.mp4")
        c["video_urls"] = c.pop("videos")
    data = {"issues": issues, "cases": cases}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"共 {len(cases)} 判例")
    print(f"{'期':>3} {'判例':>4} {'视频':>4} {'标题认定':>6} {'解析错误':>6}  校验")
    for it in issues:
        nc = sum(1 for c in cases if c["issue"] == it["no"])
        ok = "OK" if it["expected_wrong"] == it["parsed_wrong"] else "<<<不一致"
        print(f"{it['no']:>3} {nc:>4} {it['video_count']:>4} {it['expected_wrong']:>8} "
              f"{it['parsed_wrong']:>8}  {ok}")
    manual = [c for c in cases if c["need_manual"]]
    print(f"\n需人工复核结论: {len(manual)} 条")
    novid = [c for c in cases if not c["video_urls"]]
    print(f"无视频判例: {len(novid)} 条 -> {[(c['issue'], c['no']) for c in novid]}")
    from collections import Counter
    print("裁判判定分布:", Counter(c["referee_verdict"] for c in cases))
    print("VAR判定分布:", Counter(c["var_verdict"] for c in cases))


if __name__ == "__main__":
    main()
