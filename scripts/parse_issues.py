# -*- coding: utf-8 -*-
"""解析评议文章HTML -> 结构化判例数据（双赛季）
用法: python parse_issues.py 2024|2025
输出: data/cases-{season}.json
视频文件命名: videos/{season}/i{期数}c{判例}-{序号}.mp4
"""

import json
import re

from lib.paths import DATA, ISSUES

CN_NUM = {
    "一": 1,
    "两": 2,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}
ISSUE_URL = {
    "2026": {
        1: "https://www.thecfa.cn/cppy/20260318/37435.html",
        2: "https://www.thecfa.cn/cppy/20260408/37528.html",
        3: "https://www.thecfa.cn/cppy/20260415/37566.html",
        4: "https://www.thecfa.cn/cppy/20260422/37586.html",
        5: "https://www.thecfa.cn/cppy/20260429/37600.html",
        6: "https://www.thecfa.cn/cppy/20260506/37623.html",
        7: "https://www.thecfa.cn/cppy/20260513/37665.html",
        8: "https://www.thecfa.cn/cppy/20260527/37734.html",
        9: "https://www.thecfa.cn/cppy/20260604/37755.html",
        10: "https://www.thecfa.cn/cppy/20260618/37791.html",
        11: "https://www.thecfa.cn/cppy/20260701/37826.html",
        12: "https://www.thecfa.cn/cppy/20260708/37857.html",
        13: "https://www.thecfa.cn/cppy/20260716/37963.html",
        14: "https://www.thecfa.cn/cppy/20260722/37975.html",
        15: "https://www.thecfa.cn/cppy/20260729/38010.html",
        16: "https://www.thecfa.cn/cppy/20260806/38045.html",
        17: "https://www.thecfa.cn/cppy/20260812/38063.html",
        18: "https://www.thecfa.cn/cppy/20260819/38072.html",
        19: "https://www.thecfa.cn/cppy/20260826/38088.html",
        20: "https://www.thecfa.cn/cppy/20260909/38123.html",
        21: "https://www.thecfa.cn/cppy/20260916/38169.html",
        22: "https://www.thecfa.cn/cppy/20260923/38210.html",
        23: "https://www.thecfa.cn/cppy/20261014/38283.html",
    },
    "2025": {
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
    },
    "2024": {
        1: "https://www.thecfa.cn/zyls1/20240311/33847.html",
        2: "https://www.thecfa.cn/zyls1/20240403/34026.html",
        3: "https://www.thecfa.cn/zyls1/20240417/34203.html",
        4: "https://www.thecfa.cn/zyls1/20240424/34242.html",
        5: "https://www.thecfa.cn/zyls1/20240430/34273.html",
        6: "https://www.thecfa.cn/zyls1/20240504/34283.html",
        7: "https://www.thecfa.cn/zyls1/20240508/34347.html",
        8: "https://www.thecfa.cn/zyls1/20240515/34422.html",
        9: "https://www.thecfa.cn/zyls1/20240529/34512.html",
        10: "https://www.thecfa.cn/zyls1/20240612/34609.html",
        11: "https://www.thecfa.cn/zyls1/20240619/34632.html",
        12: "https://www.thecfa.cn/zyls1/20240703/34717.html",
        13: "https://www.thecfa.cn/zyls1/20240710/34755.html",
        14: "https://www.thecfa.cn/zyls1/20240717/34776.html",
        15: "https://www.thecfa.cn/zyls1/20240725/34794.html",
        16: "https://www.thecfa.cn/zyls1/20240731/34836.html",
        17: "https://www.thecfa.cn/zyls1/20240807/34876.html",
        18: "https://www.thecfa.cn/zyls1/20240821/34955.html",
        19: "https://www.thecfa.cn/zyls1/20240829/34973.html",
        20: "https://www.thecfa.cn/20240904/35000.html",
        21: "https://www.thecfa.cn/zyls1/20240912/35042.html",
        22: "https://www.thecfa.cn/zyls1/20240919/35054.html",
        23: "https://www.thecfa.cn/zyls1/20240925/35077.html",
        24: "https://www.thecfa.cn/zyls1/20241009/35116.html",
        25: "https://www.thecfa.cn/zyls1/20241023/35228.html",
        26: "https://www.thecfa.cn/zyls1/20241030/35271.html",
        27: "https://www.thecfa.cn/zyls1/20241130/35387.html",
    },
}

COMP_KEYWORDS = [
    "中超联赛",
    "中甲联赛",
    "中乙联赛",
    "中国足协杯",
    "足协杯",
    "全国运动会",
    "全运会",
    "女超联赛",
    "女甲联赛",
    "女乙联赛",
    "中冠联赛",
    "U21联赛",
    "U19联赛",
    "U17联赛",
    "锦标赛",
    "青少年联赛",
    "超级杯",
]


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
    a = html.find('<div class="news_right_list">')
    if a < 0:
        return ""
    b = html.find('<div class="news_sidebar"', a)
    return html[a + len('<div class="news_right_list">') : b] if b > a else ""


def split_paragraphs(content_html: str):
    paras = []
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", content_html, re.S):
        inner = m.group(1)
        vids = re.findall(
            r'(?:<video|<source)[^>]+src="(https?://videooss\.thecfa\.cn[^"]+)"', inner
        )
        vids = list(dict.fromkeys(vids))
        text = clean(inner)
        paras.append((text, vids))
    return paras


def parse_case_head(text: str):
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
        # 剥离黏在队名前的赛事前缀（2024早期文章"中超第5轮山东泰山VS河南"无逗号）
        home = re.sub(
            r"^(?:中超|中甲|中乙|女超|女甲)(?:联赛)?第[0-9一二三四五六七八九十百]+轮",
            "",
            home,
        )
        away = re.sub(
            r"^(?:中超|中甲|中乙|女超|女甲)(?:联赛)?第[0-9一二三四五六七八九十百]+轮",
            "",
            away,
        )
    else:
        seg = head.split("，")[-1].strip()
        if seg.count("-") == 1:
            m2 = re.match(r"^([^\-，。]{2,20})-([^\-，。]{2,20})$", seg)
            if m2:
                home, away = m2.group(1), m2.group(2)
    minute = ""
    m = re.search(r"比赛第\s*(\d+)\s*分钟", text)
    if m:
        minute = m.group(1)
    return head, comp, rnd, home, away, minute


def strip_var_parts(text: str) -> str:
    text = re.sub(r"(?:VAR|视频助理裁判)[^。；;]*", "", text)
    text = re.sub(r"(?:未|不)?介入[^。；;]*", "", text)
    return text


def classify(conc: str):
    var = "none"
    if re.search(r"VAR|视频助理裁判", conc):
        if re.search(r"(?:介入|未介入|不介入)(?:错误)", conc):
            var = "wrong"
        elif re.search(r"(?:介入|不介入)(?:正确|恰当|无误)", conc):
            var = "correct"
        else:
            var = "unknown"
    if re.search(r"不予认定|无法判断|无法认定", conc):
        return "pending", var, var == "unknown"
    body = strip_var_parts(conc)
    wrong = re.search(
        r"决定错误|判罚错误|错判|漏判|误判|认定.{0,6}为犯规|应为|属于犯规", body
    )
    correct = re.search(
        r"支持|正确|并无不当|不构成犯规|不属犯规|并无犯规|并无明显犯规", body
    )
    if wrong and not correct:
        return "wrong", var, False
    if correct and not wrong:
        return "correct", var, False
    if wrong and correct:
        return "wrong", var, True
    return "unclear", var, True


# 标题语义存在歧义时的人工口径（键已去空白；只在精确命中时生效）
TITLE_EXPECT_OVERRIDES = {
    "认定裁判判罚正确但有一起VAR介入错误": 0,
    "认定8个判例正确但漏判两张黄牌": 2,
    "认定北京国安上海申花两起关键越位判罚正确": 0,
    "认定3例裁判判罚均正确": 0,
}


def _title_num(text: str) -> int:
    return int(text) if text.isdigit() else cn2int(text)


def parse_expected_wrong(title: str) -> int:
    """从官方标题提取“错漏判”认定数（不是判例总数）。

    2024 标题写法远比 2025/2026 分散：有四起/7次/8个判例中有3起/漏判两张黄牌/
    判罚均正确/无错漏判。旧正则只认“认定N例…错漏判”，且把“判罚”的“判”误当
    “错漏判”，导致 2024 大量为 0 甚至方向相反。
    """
    text = re.sub(r"\s+", "", title or "")
    if not text:
        return 0
    for key, value in TITLE_EXPECT_OVERRIDES.items():
        if key in text:
            return value
    if "无错漏判" in text:
        return 0
    # “漏判N张黄牌”按官方口径计 N 例（2024 第6期：8例正确但漏判2黄）
    m = re.search(r"漏判([一二三四五六七八九十百两\d]+)张黄牌", text)
    if m:
        return _title_num(m.group(1))
    # “X个/起/例判例中有Y起错漏判”取 Y
    m = re.search(
        r"[一二三四五六七八九十百两\d]+(?:个|起|例).{0,8}?中有"
        r"([一二三四五六七八九十百两\d]+)(?:起|例|次).{0,3}?错漏判",
        text,
    )
    if m:
        return _title_num(m.group(1))
    # “评定X起…错判”（2024 第3期标题用“评定一起中超错判”）
    m = re.search(
        r"评定[^，。]{0,12}?([一二三四五六七八九十百两\d]+)(?:起|例|次)"
        r"[^，。]{0,8}?错判",
        text,
    )
    if m:
        return _title_num(m.group(1))
    # “认定（本轮/共/有）X起/例/次（裁判）错漏判/漏判”
    m = re.search(
        r"认定(?:本轮|本期|第[一二三四五六七八九十百两\d]+期)?(?:共|有)?"
        r"([一二三四五六七八九十百两\d]+)(?:起|例|次|个)?(?:裁判)?(?:错漏判|漏判)",
        text,
    )
    if m:
        return _title_num(m.group(1))
    # “判罚正确/均正确/关键…正确”且没有错漏判字样 → 0
    if "正确" in text and not re.search(r"错漏判|漏判", text):
        return 0
    return 0


def parse_issue(html: str, n: int, url: str, seq: int):
    """解析单期官方评议页 HTML（纯函数，golden 测试直接消费 data/issues/ 归档）。

    seq 传入该期首判例之前的赛季判例计数；返回 (期摘要, 本期判例列表, 更新后的 seq)。
    视频去重与本地命名是赛季级状态，留在 parse_season。
    """
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = clean(title_m.group(1)).split("-中国足球协会")[0] if title_m else ""
    expect = parse_expected_wrong(title)
    content = extract_content(html)
    paras = split_paragraphs(content)
    summary, cur, prev_text, issue_cases = [], None, "", []
    for text, vids in paras:
        cm = re.match(r"^判例([一二三四五六七八九十百]+)[：:]", text)
        if cm:
            cur = {
                "issue": n,
                "no": cn2int(cm.group(1)),
                "desc": text,
                "appeal": "",
                "conclusion": "",
                "videos": [],
            }
            seq += 1
            cur["seq"] = seq
            issue_cases.append(cur)
            continue
        if cur is None:
            # 兜底：个别文章首个判例没有"判例N:"前缀（如2026第20期判例一），
            # 以"俱乐部申诉意见认为"行识别，前一非空段落即对阵描述
            if "申诉意见认为" in text:
                cur = {
                    "issue": n,
                    "no": 1,
                    "desc": prev_text or text,
                    "appeal": text,
                    "conclusion": "",
                    "videos": [],
                }
                seq += 1
                cur["seq"] = seq
                issue_cases.append(cur)
                continue
            if text and "扫码" not in text and "分享至" not in text:
                summary.append(text)
                prev_text = text
            continue
        if "申诉意见认为" in text or "申诉意见如下" in text:
            cur["appeal"] += ("\n" if cur["appeal"] else "") + text
            continue
        if not text and vids:
            cur["videos"] += vids
            continue
        if re.search(r"评议组|对于此判例", text) or cur["conclusion"]:
            cur["conclusion"] += ("\n" if cur["conclusion"] else "") + text
    for c in issue_cases:
        c["conclusion"] = re.sub(
            r"中国足协将继续秉持.*$", "", c["conclusion"], flags=re.S
        ).strip()
        head, comp, rnd, home, away, minute = parse_case_head(c["desc"])
        c.update(
            match_info=head, comp=comp, round=rnd, home=home, away=away, minute=minute
        )
        c["referee_verdict"], c["var_verdict"], c["need_manual"] = classify(
            c["desc"] + "\n" + c["appeal"] + "\n" + c["conclusion"]
        )
    issue = {
        "no": n,
        "title": title,
        "url": url,
        "date": re.search(r"/(\d{8})/", url).group(1),
        "summary": "\n".join(summary).strip(),
        "expected_wrong": expect,
        "parsed_wrong": sum(1 for c in issue_cases if c["referee_verdict"] == "wrong"),
        "video_count": sum(len(c["videos"]) for c in issue_cases),
    }
    return issue, issue_cases, seq


def parse_season(season: str):
    raw = ISSUES / season
    urls = ISSUE_URL[season]
    issues, cases, seq = [], [], 0
    for n in sorted(urls):
        f = raw / f"issue_{n:02d}.html"
        html = f.read_text(encoding="utf-8")
        issue, issue_cases, seq = parse_issue(html, n, urls[n], seq)
        issues.append(issue)
        cases.extend(issue_cases)
    # 视频URL去重（官方HTML重复2次）+ https归一 + 本地命名。
    # 去重必须在归一化之后按归一化 URL 做：issue 内同一段视频常以 http/https
    # 各嵌一次，段落内 dict.fromkeys 挡不住跨协议重复（2025 第22期实测：
    # 不去重会把 2 段视频数成 4，撑破 EXPECTED 的 229 基准）
    seen = {}
    for c in cases:
        c["video_urls"] = list(
            dict.fromkeys(u.replace("http://", "https://") for u in c["videos"])
        )
        c["video_files"] = []
        for k, u in enumerate(c["video_urls"], 1):
            if u not in seen:
                seen[u] = f"{season}/i{c['issue']:02d}c{c['no']:02d}-{k}.mp4"
            c["video_files"].append(seen[u])
        del c["videos"]
    # video_count 以去重后的 video_urls 为准（parse_issue 里按原始 videos
    # 计的只是中间值，跨协议重复会虚增）
    for i in issues:
        i["video_count"] = sum(
            len(c["video_urls"]) for c in cases if c["issue"] == i["no"]
        )
    return {"season": season, "issues": issues, "cases": cases}


def main():
    import sys

    season = sys.argv[1] if len(sys.argv) > 1 else "2025"
    data = parse_season(season)
    out = DATA / f"cases-{season}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    cases = data["cases"]
    print(f"共 {len(cases)} 判例")
    print(f"{'期':>3} {'判例':>4} {'视频':>4} {'标题认定':>6} {'解析错误':>6}  校验")
    for it in data["issues"]:
        nc = sum(1 for c in cases if c["issue"] == it["no"])
        nv = sum(len(c["video_urls"]) for c in cases if c["issue"] == it["no"])
        ok = "OK" if it["expected_wrong"] == it["parsed_wrong"] else "<<<不一致"
        print(
            f"{it['no']:>3} {nc:>4} {nv:>4} {it['expected_wrong']:>8} {it['parsed_wrong']:>8}  {ok}"
        )
    manual = [c["seq"] for c in cases if c.get("need_manual")]
    novid = [c["seq"] for c in cases if not c["video_urls"]]
    print(f"需人工复核: {len(manual)} | 无视频判例: {novid or '无'}")


if __name__ == "__main__":
    main()
