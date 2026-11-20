"""首版文章缓存键碰撞的逐篇证据，供离线重解析和发行契约核对。"""

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
