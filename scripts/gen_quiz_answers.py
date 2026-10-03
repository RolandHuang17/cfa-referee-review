# -*- coding: utf-8 -*-
"""起草考题模式答案库 data/quiz-answers.json（判例的结构化正确答案）。

官方数据只有「评议组认定」自由文本，没有结构化的正确判罚决定/红黄牌字段。
本脚本按句子极性从结论提取草稿（漏判X→X为正确判罚；判罚X…错误/不应判X→X被否定），
并用 desc（临场判罚，referee_verdict=correct 时即正确答案）与否定语境交叉验证：

  r ∈ playon 不犯规(比赛继续) / directfk 直接任意球 / indirectfk 间接任意球 /
      penalty 罚球点球 / goal_valid 进球有效 / goal_invalid 进球无效
  c ∈ none 不出牌 / yellow 黄牌 / red 红牌

置信度：high=支持原判且 desc 可识别临场判罚；medium=错漏判且结论肯定语境明确；
low=靠兜底默认值。产出条目 reviewed=false —— **未校对的轴不出题**；校对流程：

  1. 本脚本生成 data/local/quiz-review/review.tsv 全量对照表（gitignored）
  2. 人工逐条复核后写 approved.txt（认可行：每行一个 key）与 overrides.tsv
     （修正行：key\tr\tc，r/c 为 "-" 表示删除该轴）
  3. python scripts/gen_quiz_answers.py --apply-review   → 回写 reviewed/修正值
     （--approve-high 同时把全部 high 条目置 reviewed，须先抽样复核认可）

--recheck 只重建 reviewed!=true 的条目，人工成果不丢。
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

from lib.paths import DATA

SEASONS = ("2024", "2025", "2026")
OUT = DATA / "quiz-answers.json"
REVIEW_DIR = DATA / "local" / "quiz-review"

R_LABELS = {"playon": "不犯规（比赛继续）", "directfk": "直接任意球", "indirectfk": "间接任意球",
            "penalty": "罚球点球", "retake": "重罚球点球", "goal_valid": "进球有效", "goal_invalid": "进球无效"}
C_LABELS = {"none": "不出牌", "yellow": "黄牌", "red": "红牌"}

# 候选优先级：进球判定 > 点球 > 任意球 > 比赛继续（同一叙述多命中时取语义重心）
R_PRIORITY = ["goal_invalid", "goal_valid", "retake", "penalty", "directfk", "indirectfk", "playon"]

# 恢复方式关键词（长词优先 + 已命中区间遮蔽，避免「点球」吃掉「罚球点球」）
_KW = [("罚球点球", "penalty"), ("直接任意球", "directfk"), ("间接任意球", "indirectfk"),
       ("越位犯规", "indirectfk"), ("进球有效", "goal_valid"), ("进球无效", "goal_invalid"),
       ("点球", "penalty")]
NEG_PREFIX = ("不应", "不宜", "不能", "不予", "并非", "不是", "不判", "未判", "没有判", "错判",
              "未出示", "取消", "撤销", "推翻", "不存在", "不构成")
# 否定后缀必须紧随关键词且不跨句号：「X的决定错误 / X不成立」成立，
# 「X。裁判员决定错误」（裁判整体决定错误）与「X，VAR未介入错误」不算
NEG_SUFFIX = re.compile(r"[^。；]{0,5}决定错误|[^。；]{0,3}均为错误|不成立")
RETAKE_RE = re.compile(r"重新(踢|罚)罚?球点球|重罚球点球")
GOAL_SCORED_RE = re.compile(r"已进球|漏判进球")
GOAL_VALID_LOOSE = re.compile(r"进球[，,]?应[^。；]{0,4}有效")
GOAL_INVALID_LOOSE = re.compile(r"进球[，,]?应[^。；]{0,4}无效")

# 注意语义反转：「判罚犯规…错误 / 不应视为犯规 / 不构成犯规」都指向 playon 成立；
# playon 的否定形式是「漏判犯规 / 应判犯规」，但那类句子必然另有恢复方式词，无需单独禁用。
PLAYON_RE = re.compile(r"(不构成|未构成|不应|并非|没有|不视为|不属于|不是)[^。；]{0,6}(?<!严重)(?<!暴力)犯规"
                       r"|(判罚|判)[^。；]{0,14}(?<!越位)犯规[^。；]{0,10}?错误"
                       r"|(?:均)?[不未](?<!严重)(?<!暴力)犯规"
                       r"|掌握有利|有利条款")


def _banned(text):
    """文本中被否定掉的判罚决定（不应判X / X的决定错误 / X不成立 / 取消X）。"""
    out, spans = set(), []
    for kw, rid in _KW:
        for m in re.finditer(re.escape(kw), text):
            if any(s <= m.start() and m.end() <= e for s, e in spans):
                continue
            spans.append((m.start(), m.end()))
            pre = text[max(0, m.start() - 8):m.start()]
            post = text[m.end():m.end() + 10]
            if any(p in pre for p in NEG_PREFIX) or NEG_SUFFIX.match(post):
                out.add(rid)
    return out


def _affirmative(text):
    """未被否定语境排除的恢复方式候选（裸出现即计入，极性由调用方结合 _banned 判断）。"""
    out = set()
    for kw, rid in _KW:
        if kw in text:
            out.add(rid)
    if RETAKE_RE.search(text):
        out.add("retake")
    if GOAL_SCORED_RE.search(text) or GOAL_VALID_LOOSE.search(text):
        out.add("goal_valid")
    if GOAL_INVALID_LOOSE.search(text):
        out.add("goal_invalid")
    if PLAYON_RE.search(text):
        out.add("playon")
    return out

# desc 中的临场判罚（referee_verdict=correct 时按优先级取非被否定项即为正确答案）
# 「未判罚X/没有判罚X」是对临场动作的否定描述，lookbehind 排除
DESC_R = [("goal_invalid", re.compile(r"(?<!未)(?<!没有)判[^。；]{0,6}进球无效")),
          ("goal_valid", re.compile(r"(?<!未)(?<!没有)判[^。；]{0,6}进球有效")),
          ("penalty", re.compile(r"(?<!未)(?<!没有)(?:判罚|改判)[^。；]{0,14}(罚球点球|点球)")),
          ("directfk", re.compile(r"(?<!未)(?<!没有)(?:判罚|改判)[^。；]{0,14}直接任意球")),
          ("indirectfk", re.compile(r"(?<!未)(?<!没有)(?:判罚|改判)[^。；]{0,14}间接任意球|判[^。；]{0,6}越位犯规")),
          ("playon", re.compile(r"未判(罚)?[^。；]{0,6}犯规|不构成犯规|没有判罚犯规"))]
DESC_C = [("red", re.compile(r"出示[^。；]{0,3}红牌|红牌罚令出场|罚令出场")),
          ("yellow", re.compile(r"出示[^。；]{0,3}黄牌|黄牌警告")),
          ("none", re.compile(r"未出示[^。；]{0,4}牌|不出示[^。；]{0,4}牌"))]

C_AFF = [("red", re.compile(r"(?<!不)(?<!未)应(?:(?!无需|不应|不宜|未出示|取消|撤销)[^。；]){0,16}(出示)?红牌|漏判[^。；]{0,10}红牌|出示红牌[^。；]{0,4}正确|红牌[^。；]{0,4}正确")),
         ("yellow", re.compile(r"(?<!不)(?<!未)应(?:(?!无需|不应|不宜|未出示|取消|撤销)[^。；]){0,16}(出示)?黄牌|漏判[^。；]{0,10}黄牌|出示黄牌[^。；]{0,4}正确|黄牌[^。；]{0,4}正确"))]
# 牌的否定与「不予认定」（红黄牌取决于细节无法确定时该轴不出题）
C_NEG_R = re.compile(r"红牌[^。；]{0,8}?(?:决定?错误|不成立)|不应[^。；]{0,6}红牌|取消[^。；]{0,3}红牌|撤销[^。；]{0,3}红牌|无需[^。；]{0,8}(?:红黄牌|红牌)")
C_NEG_Y = re.compile(r"黄牌[^。；]{0,8}?(?:决定?错误|不成立)|不应[^。；]{0,6}黄牌|多余[^。；]{0,3}黄牌|撤销[^。；]{0,3}黄牌|无需[^。；]{0,8}(?:红黄牌|黄牌)")
C_UNSET = re.compile(r"(?:红牌|黄牌)[^。；]{0,14}不予认定|不予认定[^。；]{0,14}(?:红牌|黄牌)"
                     r"|(?:红牌或是?黄牌|红牌还是黄牌)[^。；]{0,6}不予认定")


def derive(conclusion, desc, verdict):
    """返回 (r, c, conf, why)。r/c 可为 None 表示该轴不出题。"""
    why = []
    if verdict == "pending":
        return None, None, "skip", "不予认定，两轴都不出题"

    banned_c = _banned(conclusion)
    aff_c = _affirmative(conclusion) - banned_c
    cr = next((rid for rid in R_PRIORITY if rid in aff_c), None)

    if verdict == "correct":
        # 临场判罚被评议组支持 → 正确答案=临场判罚（按优先级取 desc 中未被否定项）
        banned_d = _banned(desc)
        r = next((rid for rid, pat in DESC_R if pat.search(desc) and rid not in banned_d), None)
        src = f"desc命中{r}" if r else "desc未识别恢复方式"
        if r is None and cr:
            r, src = cr, src + f"，结论补{cr}"
        elif r is not None and cr and r != cr:
            # desc 初始状态与结论表述不一致 → 取 R_PRIORITY 中更具体者并降级待复核
            pick = min((r, cr), key=lambda x: R_PRIORITY.index(x))
            src += f"，与结论{cr}冲突→取{pick}"
            r = pick
        # 牌按「最后一次提及」取最终决定（VAR 回看降级/取消以最后一次为准）
        hits = [max((m.start(), cid) for m in pat.finditer(desc))
                for cid, pat in DESC_C if pat.search(desc)]
        c = max(hits)[1] if hits else "none"
        if c in banned_d or (c == "red" and C_NEG_R.search(conclusion))                 or (c == "yellow" and C_NEG_Y.search(conclusion)):
            c = "none"
        # desc 未提牌但结论明确要求出牌（如 DOGSO 点球+黄牌）→ 以结论为准
        if c == "none" and not C_UNSET.search(conclusion):
            for cid, pat in C_AFF:
                if pat.search(conclusion):
                    c = cid
                    why.append(f"结论牌{cid}")
                    break
        if C_UNSET.search(conclusion):
            c = None
        conf = "low" if "冲突" in src else ("high" if r and src.startswith("desc命中") else "medium")
        why.append(src)
        why.append(f"desc牌{c}")
        return r, c, conf, "；".join(why)

    # verdict == wrong：结论描述的「应然的判罚」即为正确答案（未被否定语境排除）
    r = cr
    why.append(f"结论肯定{r}" if r else "结论未识别恢复方式")

    # 纪律处分：不予认定 > 结论明确的牌（剔除被否定者）> 无提及按不出牌
    c = None
    if C_UNSET.search(conclusion):
        why.append("牌不予认定→不出题")
    else:
        for cid, pat in C_AFF:
            if pat.search(conclusion) and not (C_NEG_R if cid == "red" else C_NEG_Y).search(conclusion):
                c = cid
                why.append(f"结论牌{cid}")
                break
        if c is None and (C_NEG_R.search(conclusion) or C_NEG_Y.search(conclusion)):
            c = "yellow" if (C_NEG_R.search(conclusion) and re.search(r"(?<!不)应[^。；]{0,10}(出示)?黄牌", conclusion)
                             and not C_NEG_Y.search(conclusion)) else "none"
            why.append(f"牌被否定→{c}")
        elif c is None:
            c = "none"
            why.append("结论未提及牌→none")
    # 越位+进球场景：漏判越位且进球→进球无效；错判越位且有进球→进球有效；错判越位无进球→继续比赛
    if r == "indirectfk" and "越位犯规" in conclusion:
        missed = bool(re.search(r"漏判[^。；]{0,6}越位", conclusion))
        wrongly = bool(re.search(r"越位犯规[^。；]{0,12}决定?错误|判[^。；]{0,6}越位犯规[^。；]{0,10}错误", conclusion))
        if re.search(r"进球有效|进球无效", conclusion + desc):
            r = "goal_invalid" if missed else "goal_valid"
            why.append(f"越位+进球→{r}")
        elif wrongly:
            r = "playon"
            why.append("越位误判无进球→playon")
    # 越位误判特判：判了越位但评议组认为不越位 → 进球有效；因提前鸣哨无法认定进球则不犯规继续
    if r is None and "越位犯规" in conclusion and "indirectfk" in banned_c             and re.search(r"判[^。；]{0,12}越位犯规", desc):
        if re.search(r"鸣哨|无法认定", conclusion):
            r = "playon"
            why.append("越位误判+提前鸣哨→playon")
        else:
            r = "goal_valid"
            why.append("越位误判→goal_valid")
    # 漏判犯规（未提恢复方式）→ 通常为直接任意球
    if r is None and re.search(r"漏判[^。；]{0,6}犯规", conclusion) and "playon" not in aff_c:
        r = "directfk"
        why.append("漏判犯规→directfk")
    # 恢复方式未识别、且错误仅在纪律层面（结论无「漏判犯规/进球」类表述）时，
    # desc 的临场恢复方式即为正确答案（如漏判红牌：犯规已吹，任意球维持）
    if r is None and c is not None and not re.search(
            r"漏判[^。；]{0,6}(犯规|手球|越位|点球|球点球|任意球|进球)|应判[^。；]{0,6}(犯规|进球)", conclusion):
        if "坠球" in desc:
            why.append("坠球恢复→该轴不出题")
        else:
            d = next((rid for rid, pat in DESC_R if pat.search(desc) and rid not in banned_c), None)
            if d == "playon" and re.search(r"(?<!未)(?<!没有)判(罚)?[^。；]{0,14}犯规", desc):
                d = "directfk"  # VAR 回看后已改判犯规，恢复方式按改判后计
            if d is None and re.search(r"(?<!未)(?<!没有)判(罚)?[^。；]{0,14}犯规", desc):
                d = "directfk"
            if d:
                r = d
                why.append(f"仅纪律错误→desc{d}")
    return r, c, ("medium" if r else "low"), "；".join(why)


def collect():
    """考题池：有视频且结论非空的判例。"""
    pool = []
    for season in SEASONS:
        d = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        for c in d["cases"]:
            if c.get("video_files") and (c.get("conclusion") or "").strip():
                pool.append((season, c))
    return pool


def draft_all(recheck=False):
    old = {}
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8")).get("answers", {})
    pool = collect()
    answers, rows = {}, []
    for season, c in pool:
        key = f"{season}-{c['seq']}"
        if recheck and old.get(key, {}).get("reviewed"):
            answers[key] = old[key]
            continue
        r, cc, conf, why = derive(c["conclusion"], c["desc"], c.get("referee_verdict", ""))
        if r is None and cc is None:
            continue
        answers[key] = {"r": r, "c": cc, "auto": True, "reviewed": False, "conf": conf}
        rows.append((key, c.get("referee_verdict", ""), r or "-", cc or "-", conf,
                     (c.get("conclusion") or "").replace("\n", " ")[:170],
                     (c.get("desc") or "").replace("\n", " ")[:110],
                     "；".join(why)))
    return answers, rows, pool


def write_out(answers):
    payload = {"version": 1, "generated": date.today().isoformat(),
               "note": "考题答案库（判例轴）：r=判罚决定 c=纪律处分，取值见 rLabels/cLabels；"
                       "auto=脚本起草，reviewed=人工已校对（quiz 页只对 reviewed 条目出②③问）",
               "rLabels": R_LABELS, "cLabels": C_LABELS, "answers": answers}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def write_review_tsv(rows):
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    tsv = REVIEW_DIR / "review.tsv"
    with tsv.open("w", encoding="utf-8") as f:
        f.write("key\tverdict\tr\tc\tconf\tconclusion\tdesc\twhy\n")
        for row in rows:
            f.write("\t".join(row) + "\n")
    return tsv


def apply_review():
    """把 data/local/quiz-review/ 的人工校对成果回写进 quiz-answers.json。

    approved.txt: 每行一个 key，表示「核对无误，置 reviewed=true」
    rejected.txt: 每行一个 key，从 approved 中剔除（保持 reviewed=false，待后续修数据）
    overrides.tsv: key\tr\tc 三列，r/c ∈ rLabels/cLabels 或 "-"（删除该轴）；同时置 reviewed
    --approve-high: 把全部 conf=high 的条目批量置 reviewed（应先抽样认可）
    """
    data = json.loads(OUT.read_text(encoding="utf-8"))
    answers = data["answers"]
    n_app = n_rej = n_ov = 0
    if "--approve-high" in sys.argv:
        for v in answers.values():
            if v.get("conf") == "high" and not v.get("reviewed"):
                v["reviewed"] = True
                n_app += 1
    ap = REVIEW_DIR / "approved.txt"
    if ap.exists():
        keys = {x.strip() for x in ap.read_text(encoding="utf-8").splitlines()
                if x.strip() and not x.startswith("#")}
        for k in keys:
            if k in answers and not answers[k].get("reviewed"):
                answers[k]["reviewed"] = True
                n_app += 1
    rj = REVIEW_DIR / "rejected.txt"
    if rj.exists():
        keys = {x.strip() for x in rj.read_text(encoding="utf-8").splitlines()
                if x.strip() and not x.startswith("#")}
        for k in keys:
            if k in answers and answers[k].get("reviewed"):
                answers[k]["reviewed"] = False
                n_rej += 1
    ov = REVIEW_DIR / "overrides.tsv"
    if ov.exists():
        for line in ov.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("key\t"):
                continue
            parts = line.split("\t")
            k, r, c = parts[0].strip(), parts[1].strip(), parts[2].strip()
            if k not in answers:
                print(f"⚠ overrides 指向不存在的 key: {k}")
                continue
            if r in ("", "-"):
                answers[k].pop("r", None)
            elif r in R_LABELS:
                answers[k]["r"] = r
            if c in ("", "-"):
                answers[k].pop("c", None)
            elif c in C_LABELS:
                answers[k]["c"] = c
            answers[k]["reviewed"] = True
            answers[k].pop("conf", None)
            n_ov += 1
    write_out(answers)
    n_rev = sum(1 for v in answers.values() if v.get("reviewed"))
    print(f"回写完成：置 reviewed {n_app} 条，剔除 {n_rej} 条，修正 {n_ov} 条；"
          f"总计 reviewed {n_rev}/{len(answers)}")


def main():
    if "--apply-review" in sys.argv:
        apply_review()
        return
    answers, rows, pool = draft_all(recheck="--recheck" in sys.argv)
    write_out(answers)
    tsv = write_review_tsv(rows)
    print(f"生成 {OUT}: {len(answers)} 条（high {sum(1 for r_ in rows if r_[4]=='high')} / "
          f"medium {sum(1 for r_ in rows if r_[4]=='medium')} / low {sum(1 for r_ in rows if r_[4]=='low')}）")
    print(f"对照表: {tsv}（共 {len(rows)} 行）")
    print(f"题库 {len(pool)} 条，其中无结构化答案条目 {len(pool)-len(answers)} 条（pending 等）")


if __name__ == "__main__":
    main()
