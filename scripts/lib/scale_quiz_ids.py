"""尺度题的持久化编号与 2026-11 以前的错题本编号。

既有赛季新增同号但不同系列的场景会得到含系列的编号；新赛季从第一题起
即使用含系列的编号。同一赛季、系列与场景号重复时构建报错，须核对来源
并修正场景标识；不能通过改动已发布题号或扩大旧记录的候选范围解决。
"""

# 旧题库在这三个赛季使用 sc-年-场景号。2024/2026 只有 highlights，
# 2025 只有 reckless 的这些单义号需要沿用，其余已出过的号在下表。
_LEGACY_SERIES = {"2024": "highlights", "2025": "reckless", "2026": "highlights"}

# 冻结发布时的官方判罚，供旧错题保存的正确答案对照。以后材料的改版、
# 撤题或新同号题不能改变过去的记录归属。顺序与旧 scoreScale 输出相同。
_PUBLISHED = {
    "reckless": {
        "1": "不犯规、不出牌",
        "2": "直接任意球、黄牌",
        "3": "直接任意球、黄牌",
        "4": "直接任意球、红牌",
        "5": "不犯规、不出牌",
        "7": "罚球点球、不出牌",
        "8": "罚球点球、不出牌",
        "9": "直接任意球、黄牌",
    },
    "highlights": {
        "1": "罚球点球、不出牌",
        "2": "罚球点球、不出牌",
        "3": "罚球点球、黄牌",
        "4": "罚球点球、黄牌",
        "5": "罚球点球、红牌",
        "7": "间接任意球、黄牌",
        "8": "不犯规、不出牌",
        "9": "不犯规、不出牌",
    },
    "var": {"1": "直接任意球、黄牌", "2": "直接任意球、红牌"},
}
LEGACY_SCALE_IDS = {}
for _series, _decisions in _PUBLISHED.items():
    for _number, _answer in _decisions.items():
        LEGACY_SCALE_IDS.setdefault(f"sc-2025-{_number}", {})[
            f"sc-2025-{_series}-{_number}"
        ] = _answer


def assign_scale_quiz_ids(bank):
    """保留单义旧编号，新系列按场景锚点的年/系列/编号区分；校验全库唯一。"""
    seen = set()
    for question in bank:
        if question["t"] == "scale":
            season, series, number = question["s"], question["series"], question["id"]
            old = f"sc-{season}-{number}"
            question["k"] = (
                old
                if _LEGACY_SERIES.get(season) == series and old not in LEGACY_SCALE_IDS
                else f"sc-{season}-{series}-{number}"
            )
            question["link"] = f"scale.html#h{season}-{series}-{number}"
        key = question["k"]
        if key in seen:
            raise ValueError(
                f"题库编号重复：{key}。请核对来源中的赛季、系列和场景编号。"
            )
        seen.add(key)
