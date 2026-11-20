"""PRO 节目名称按文章所属系列确定。官网的英语栏目也收录西语版。"""

SERIES_NAMES = {
    "ivr": "Inside Video Review（VAR 评析·英）",
    "vaf": "VAR a Fondo（西）",
    "angle": "The Definitive Angle（文字判例）",
    "other": "PRO 文章",
}


def series_name(article):
    return (
        SERIES_NAMES.get(article.get("kind"))
        or article.get("series_name")
        or SERIES_NAMES["other"]
    )
