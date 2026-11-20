"""首版文章缓存键碰撞的逐篇证据，供离线重解析和发行契约核对。"""

import re
from lib.pagelib import article_anchor

ARTICLE = "https://www.conmebol.com/noticias/situacion-de-analisis-var-"
QUALIFIERS = ARTICLE + "eliminatorias-sudamericanas-"
CUP = ARTICLE + "conmebol-sudamericana-"

# 95f02d4 首版使用截断的 URL 作为缓存名。右侧是旧 HTML 自报的 canonical
# 和 og:url。其余 56 篇的两种身份都与各自列表链接一致。
UNRELATED_CACHE = {
    QUALIFIERS + "bolivia-vs-brasil/": QUALIFIERS + "bolivia-vs-brasil-2/",
    CUP + "independiente-del-valle-vs-deportivo-tachira/": CUP
    + "independiente-del-valle-vs-melgar/",
    CUP + "independiente-del-valle-vs-lanus/": CUP
    + "independiente-del-valle-vs-melgar/",
    CUP + "atletico-goianiense-vs-nacional/": CUP + "atletico-goianiense-vs-sao-paulo/",
}

DETAIL_FIELDS = ("fecha", "ciudad", "estadio", "situacion_es", "minuto", "youtube")


def evidence_problems(data):
    """待核状态只适用于已查实的四个旧缓存冲突，须从该篇列表记录独立成立。"""
    problems = []
    for case in data["cases"]:
        problems.extend(check_events(case))
        url = case["url"]
        if "detail_status" not in case:
            if "unrelated_cache_url" in case:
                problems.append(f"{url} 有冲突出处但缺少待核状态")
            continue
        if (
            case["detail_status"] != "pending"
            or url not in UNRELATED_CACHE
            or case.get("unrelated_cache_url") != UNRELATED_CACHE[url]
        ):
            problems.append(f"{url} 待核状态没有对应的旧缓存身份依据")
        if (
            any(case.get(field) != "" for field in DETAIL_FIELDS)
            or case.get("situacion_norm") != "other"
        ):
            problems.append(f"{url} 待核记录含未经本篇证实的详情")
        if case["match"] != case["title"].rsplit(":", 1)[-1].strip():
            problems.append(f"{url} 待核记录的对阵与本篇列表标题不符")
    return problems


VIDEO_RE = re.compile(r"https://www\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})$")


def event_rows(case):
    if case.get("detail_status") == "pending":
        return []
    if "events" in case:
        return case["events"]
    video = case.get("youtube", "")
    return [
        {
            "situacion_es": case.get("situacion_es", ""),
            "situacion_norm": case.get("situacion_norm", "other"),
            "minuto": case.get("minuto", ""),
            "videos": [{"url": video, "title": "", "lang": ""}] if video else [],
        }
    ]


def event_anchor(url, event):
    anchor = article_anchor(url)
    videos = sorted(event["videos"], key=lambda v: v.get("lang") != "es")
    for video in videos:
        match = VIDEO_RE.fullmatch(video["url"])
        if match:
            return anchor + "-" + match[1]
    return anchor


def event_translation(url, event, zh):
    """优先精确对应本篇的原译文，亦可复用已核同一西语术语。"""
    text = event.get("situacion_es", "").casefold()
    if not text:
        return ""
    zh = zh or {}
    for local in (
        zh.get("events", {}).get(event_anchor(url, event), {}),
        zh.get("cases", {}).get(url, {}),
    ):
        if local.get("source_situation", "").casefold() == text and local.get(
            "situation"
        ):
            return local["situation"]
    return zh.get("terms", {}).get(text, "")


def translation_problems(data, zh):
    """所有原稿仍需逐篇可配对。只有明确登记的、原文未变的情境可待译。"""
    problems, used, event_used, missing = [], set(), set(), {}
    valid_terms = {}
    for row in zh.get("cases", {}).values():
        if row.get("source_situation") and row.get("situation"):
            valid_terms.setdefault(row["source_situation"].casefold(), set()).add(
                row["situation"]
            )
    for term, text in zh.get("terms", {}).items():
        if valid_terms.get(term) != {text}:
            problems.append(f"译名没有唯一既有原稿依据: {term}")
    for case in data["cases"]:
        url = case["url"]
        local = zh.get("cases", {}).get(url, {})
        for e in event_rows(case):
            text = e.get("situacion_es", "")
            eid = event_anchor(url, e)
            specific = zh.get("events", {}).get(eid, {})
            if (
                text
                and specific.get("situation")
                and text.casefold() == specific.get("source_situation", "").casefold()
            ):
                event_used.add(eid)
            if (
                text
                and text.casefold() == local.get("source_situation", "").casefold()
                and local.get("situation")
            ):
                used.add(url)
            if text and not event_translation(url, e, zh):
                missing[event_anchor(url, e)] = text
    for url in sorted(zh.get("cases", {}).keys() - used):
        problems.append(f"本篇没有译稿所针对的西语情境: {url}")
    for eid in sorted(zh.get("events", {}).keys() - event_used):
        problems.append(f"逐事件译稿与情境不符: {eid}")
    pending = zh.get("untranslated", {})
    for eid in sorted(missing.keys() | pending.keys()):
        if missing.get(eid) != pending.get(eid):
            problems.append(f"待译登记与事件原文不符: {eid}")
    return problems


def check_events(case):
    if "events" not in case:
        return []
    events = case["events"]
    url = case["url"]
    if (
        not isinstance(events, list)
        or not events
        or case.get("detail_status") == "pending"
    ):
        return [f"{url} 事件列表为空或与待核状态互斥"]
    seen = set()
    for event in events:
        for v in event["videos"]:
            if v["url"] in seen or not VIDEO_RE.fullmatch(v["url"]):
                return [f"{url} 事件视频重复或无有效 ID"]
            seen.add(v["url"])
        raw = event.get("source_fields")
        if raw is not None:
            if not (raw.get("situacion_es") and raw.get("minuto")) or any(
                event[k] for k in ("situacion_es", "minuto")
            ):
                return [f"{url} 来源字段有歧义时须保留原值并停止归类"]
        elif not (
            event.get("situacion_es")
            and re.fullmatch(r"\d+(?:\+\d+)?", event.get("minuto", ""))
        ):
            return [f"{url} 事件缺少情境或分钟"]
        if not event["videos"]:
            return [f"{url} 事件没有可配对的视频"]
    first = events[0]
    if (
        any(
            case.get(k) != first[k]
            for k in ("situacion_es", "situacion_norm", "minuto")
        )
        or case.get("youtube") != first["videos"][0]["url"]
    ):
        return [f"{url} 兼容字段与首段事实不符"]
    return []
