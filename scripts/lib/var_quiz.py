"""人工核对的 VAR 考题。6ad8574 首次收录了这里的 12 组中英文问答、选项和评分键。

详情译文与当前官方来源配对后，还需单独核对四选项和正确下标，才可更新对应的 review 指纹。
"""

import json
from collections import defaultdict

from lib.translation_versions import fingerprint


# VAR 协议题干扰项映射（人工指定：每题 4 选项、ans=正确项下标；正确项全部为官方答案）
VAR_OPTS = {
    "q1": {
        "review": "52ae573d52bad037264d",
        "ans": 0,
        "opts": [
            "可以——该黄牌（非第二张黄牌）可回看确认犯规球员身份，黄牌取消并改判 B 队直接任意球",
            "不可以——黄牌判罚一律不可回看，维持原判",
            "可以，但 VAR 只能提示裁判员注意，原判不可更改",
            "可以——直接取消黄牌并判给 A 队点球",
        ],
    },
    "q2": {
        "review": "b3ad3e9344ac1923fd67",
        "ans": 1,
        "opts": [
            "不可以——由第二张黄牌引发的红牌不可回看",
            "可以——明显错误的第二张黄牌可由 VAR 协助：红牌取消，假摔球员被警告，进攻方获间接任意球",
            "可以——直接改判进攻方点球",
            "可以——红牌维持，另补判进攻方间接任意球",
        ],
    },
    "q3": {
        "review": "2e8213b8bb6180707e24",
        "ans": 0,
        "opts": [
            "不可以——VAR 只能纠正「明显错误的第二张黄牌」，不能补漏判第二张黄牌",
            "可以——这属于严重漏判事件，VAR 应建议回看",
            "可以——VAR 直接出示第二张黄牌并罚令出场",
            "不可以——除非裁判员已经出示了红牌",
        ],
    },
    "q4": {
        "review": "ba93e77ead074c74e751",
        "ans": 2,
        "opts": [
            "维持点球——回看后非清晰错误不得更改",
            "取消点球，改判防守方球门球",
            "取消点球，改判防守方间接任意球，假摔球员因非体育行为被警告（黄牌）",
            "取消点球，坠球恢复比赛",
        ],
    },
    "q5": {
        "review": "9b8184959d839f133092",
        "ans": 1,
        "opts": [
            "可以——任何改变比赛进程的判罚都可回看",
            "不可以——仅错罚对象，或与暴力行为、吐口水、咬人、极其攻击性/侮辱性言行相关的罚令出场事件例外",
            "可以——但只能更改纪律处分，不能更改重新开始方式",
            "不可以——比赛重新开始后一律不可回看",
        ],
    },
    "q6": {
        "review": "2d7a938bf8f83fe71c87",
        "ans": 3,
        "opts": [
            "必须维持红牌——回看是为红牌发起的，不能降级",
            "由 VAR 决定最终出示红牌还是黄牌",
            "取消处罚但不补牌，比赛照常恢复",
            "以回看所见为准——若裁判员认为该犯规只值警告而非罚令出场，就必须出示黄牌",
        ],
    },
    "q7": {
        "review": "137c5cbf3e4cda158069",
        "ans": 0,
        "opts": [
            "适用「仅 VAR 回看」——VAR 告知回放内容，裁判员做出电视信号手势后取消点球、改判防守方任意球",
            "必须进行场上回看（OFR）",
            "维持点球——罚球区内外的判断属于裁判员主观裁量",
            "取消点球，坠球恢复比赛",
        ],
    },
    "q8": {
        "review": "6d0d7fd116a8765a2b9e",
        "ans": 3,
        "opts": [
            "VAR 直接判罚点球并通知裁判员",
            "比赛继续——VAR 无权提示这类情形",
            "立即停止比赛并以坠球恢复",
            "裁判员在球下次进入中立区域/局面时停止比赛、做出电视信号手势，经场上回看（OFR）后再作最终决定",
        ],
    },
    "q9": {
        "review": "83463e19b85331b563e2",
        "ans": 0,
        "opts": [
            "不可以——VAR 只能在裁判员已作出第一决定（包括允许比赛继续）之后使用",
            "可以——这属于「延迟吹罚」的正常执法形态",
            "可以——但仅限进球类判定",
            "不可以——VAR 只能应由队长申请使用",
        ],
    },
    "q10": {
        "review": "78fd15b67b26e9aec778",
        "ans": 1,
        "opts": [
            "不允许——点球执行阶段的犯规不可回看",
            "允许——罚球点球时守门员和/或主罚队员犯规，裁判员可以获得 VAR 协助",
            "允许——但仅限主罚队员的犯规",
            "允许——且该进球必须判定有效",
        ],
    },
    "q11": {
        "review": "e0d985316bc07eec3e0e",
        "ans": 2,
        "opts": [
            "维持点球，并向防守队员出示黄牌",
            "取消点球，坠球恢复比赛",
            "取消点球，改判防守方间接任意球，假摔球员因非体育行为被警告（黄牌）",
            "取消点球，改判防守方球门球",
        ],
    },
    "q12": {
        "review": "8c35f627beea842bd46d",
        "ans": 1,
        "opts": [
            "黄牌维持——已出示的牌不可通过回看取消",
            "取消黄牌并改判点球；犯规的防守队员视情况被警告或罚令出场",
            "取消黄牌并改判点球，但不得再处罚防守队员",
            "维持比赛原样，赛后报告处理",
        ],
    },
}


def review_version(qid, source, translated, choices):
    return fingerprint(
        [
            qid,
            source["q"],
            source["a"],
            translated["q"],
            translated["a"],
            choices["opts"],
            choices["ans"],
        ]
    )


def _pending_reason(qid, occurrences, translated, source_version, choices):
    if choices is None:
        return "尚无已复核的四选项和评分键"
    if len(occurrences) != 1:
        return "官方编号重复"
    source = occurrences[0]
    if not all(
        isinstance(source.get(k), str) and source[k].strip() for k in ("q", "a")
    ):
        return "官方问答不完整"
    if not isinstance(translated, dict) or not all(
        isinstance(translated.get(k), str) and translated[k].strip() for k in ("q", "a")
    ):
        return "中文问答不完整"
    if source_version != fingerprint([source["q"], source["a"]]):
        return "中文译文对应的官方版本不符"
    options = choices.get("opts")
    if (
        not isinstance(options, list)
        or len(options) != 4
        or not all(isinstance(v, str) and v.strip() for v in options)
        or len(set(options)) != 4
        or type(choices.get("ans")) is not int
        or not 0 <= choices["ans"] < 4
    ):
        return "四选项或正确下标不完整"
    if review_version(qid, source, translated, choices) != choices.get("review"):
        return "问答、四选项或评分键已变更"
    return None


def reviewed_var_questions(data, zh, warn=None):
    """Portal totals and paper generation share this list; rejected rows never reach the quiz."""
    groups = defaultdict(list)
    for row in data.get("faq", []):
        qid = row.get("id") if isinstance(row, dict) else None
        groups[qid if isinstance(qid, str) else ""].append(row)
    translations = zh.get("faq", {})
    versions = zh.get("source_versions", {})
    result = []
    for qid, rows in groups.items():
        choices = VAR_OPTS.get(qid)
        pair = translations.get(qid) if isinstance(translations, dict) else None
        version = versions.get("faq/" + qid) if isinstance(versions, dict) else None
        pending = _pending_reason(qid, rows, pair, version, choices)
        if pending:
            if warn:
                warn(
                    f"VAR 协议题 {qid or '（未编号）'} 待复核（{pending}），本次不出题"
                )
            continue
        source = rows[0]
        result.append(
            {
                "k": "var-" + qid,
                "t": "var",
                "s": "ifab",
                "qid": qid,
                "q": pair["q"],
                "q_en": source["q"],
                "a": pair["a"],
                "a_en": source["a"],
                "opts": list(choices["opts"]),
                "ans": choices["ans"],
                "link": "ifab.html#faq-" + qid,
            }
        )
    if warn:
        for qid in VAR_OPTS:
            if qid not in groups:
                warn(f"VAR 协议题 {qid} 待复核（当前官方 FAQ 缺失该编号），本次不出题")
    return result


def read_var_questions(source_path, translation_path, warn=None):
    source = (
        json.loads(source_path.read_text(encoding="utf-8"))
        if source_path.exists()
        else {}
    )
    translation = (
        json.loads(translation_path.read_text(encoding="utf-8"))
        if translation_path.exists()
        else {}
    )
    return reviewed_var_questions(source, translation, warn)
