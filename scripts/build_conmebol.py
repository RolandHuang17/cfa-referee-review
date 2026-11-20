# -*- coding: utf-8 -*-
"""生成 site/conmebol.html：南美足联 CONMEBOL《Situación de Análisis VAR》判例页
（评议级：逐案 比赛信息+情境+分钟+官方视频链接）

数据来自 data/conmebol.json（fetch_conmebol.py 抓取提交）+ data/conmebol-zh.json
（url 键情境译制层）。判例视频托管在 YouTube（官方），本页为纯链接模式
（不内嵌、不本地化）。页头/chips/搜索/年份分组骨架来自 lib/pagelib.py。
"""

from lib.seo import meta_tags
from lib.theme import inject_theme, topbar, icon
from lib.conmebol_evidence import (
    event_anchor,
    event_rows,
    event_translation,
    evidence_problems,
)

from lib.pagelib import (
    article_anchor,
    SEARCH_CSS,
    esc,
    filter_js,
    group_by_year,
    head_css,
    load_json_with_zh,
    search_blob,
    searchbar,
)
from lib.paths import CONMEBOL_JSON, CONMEBOL_ZH_JSON, SITE

SIT_LABEL = {
    "penalty": "点球",
    "ofr_penalty": "点球（现场回看）",
    "no_penalty": "非点球",
    "red_card": "红牌",
    "offside": "越位",
    "no_offside": "不构成越位",
    "goal": "进球",
    "no_goal": "进球无效",
    "other": "判例",
}
SIT_BADGE = {
    "penalty": "wrong",
    "ofr_penalty": "wrong",
    "red_card": "wrong",
    "no_penalty": "correct",
    "no_goal": "pending",
    "offside": "info",
    "no_offside": "info",
    "goal": "info",
    "other": "info",
}
COMP_CN = {
    "eliminatorias": "世预赛",
    "libertadores": "解放者杯",
    "sudamericana": "南美杯",
    "conmebol-recopa": "优胜者杯",
}

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>南美 VAR 判例 · 裁判学习平台</title>
<style>
/* ===== conmebol 页专属布局 (tokens/组件来自 data-cfa-theme；页头/筛选骨架来自 lib/pagelib) ===== */
__HEAD_CSS__
__SEARCH_CSS__
.ccard{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:14px 18px;margin-bottom:12px;
  transition:transform var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease)}
.ccard:hover{transform:translateY(-2px);border-color:var(--brand)}
.chead{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.chead .badge{margin-left:auto}
.cmatch{font-family:var(--font-display);font-size:16.5px}
.cinfo{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.cinfo .chip{cursor:default;padding:3px 10px;font-size:11.5px}
.clinks{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.ccard .go{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:999px;
  border:1px solid var(--brand);background:var(--info-bg);color:var(--brand);
  font-size:12px;font-weight:600;text-decoration:none;white-space:nowrap}
.case-event{margin-top:12px;padding-block:10px;border-top:1px solid var(--line);scroll-margin-block-start:calc(var(--top-h) + 12px)}.case-event:target{outline:2px solid var(--brand);outline-offset:3px}.event-copy{color:var(--ink2);line-height:1.6}.event-copy strong{margin-inline-end:.4em}.article-title{color:var(--muted);font-size:13px}.ccard .go{max-width:100%;white-space:normal;overflow-wrap:anywhere}.ccard .go:hover{background:var(--brand-strong);color:var(--on-brand)}
@media (max-width:760px){.chead .badge{margin-left:0}}
</style>
</head>
<body class="page-conmebol">
<a class="skip-link" href="#content0">跳到内容</a>
__TOPBAR__
<header class="page-head">
  <div class="wrap">
    <h1>南美足联 VAR 判例</h1>
    <div class="sub">CONMEBOL《Situación de Análisis VAR》：世预赛（南美区）/ 解放者杯 / 南美杯 / 优胜者杯逐案 VAR 判例分析（比赛 · 情境 · 分钟）· 官方视频为 YouTube 链接 · 版权归 CONMEBOL 所有</div>
    <div class="src-banner">__I_EXTERNAL__ 每案可查官方分析文章，已核实的录像另附视频链接。__SOURCE_LINK__</div>
    __SEARCHBAR__
  </div>
</header>
<div class="wrap" id="content0">
  <div class="chips" data-chips>
    <button class="chip on" data-f="all">全部 <b>__N_ALL__</b></button>
    __COMP_CHIPS__
    __SIT_CHIPS__
  </div>
  __SECTIONS__
  <p class="empty" id="emptyTip">没有匹配的判例——换个关键词或筛选试试。</p>
  <p class="foot">判例内容版权归 CONMEBOL 所有；本页收录结构化元数据与官方链接（来源 conmebol.com，全索引核对日期 __CHECKED__）。情境保留官方西语；已有可核译名时并列显示中文。</p>
</div>
<script>
__FILTER_JS__
</script>
</body>
</html>
"""


def render_event(url, event, zh):
    eid = event_anchor(url, event)
    raw = event.get("source_fields")
    if raw:
        heading = "官方字段标注不一致"
        detail = f'<span lang="es">Situación: {esc(raw["situacion_es"])} · Minuto: {esc(raw["minuto"])}</span>'
    else:
        translated = event_translation(url, event, zh)
        heading = " · ".join(
            filter(None, [event["minuto"] + "′" if event["minuto"] else "", translated])
        )
        detail = (
            f'<span lang="es">{esc(event["situacion_es"])}</span>'
            if event["situacion_es"]
            else ""
        )
    links = []
    for video in event["videos"]:
        lang = {"es": " · 西语", "pt": " · 葡语"}.get(video["lang"], "")
        title = video["title"] or "判例视频"
        # 来源字段交叉时展示录像原题，观众可独立核对。
        link_text = title if raw else f"判例视频{lang}"
        accessible_name = (
            f"{link_text} · {title}" if video["title"] and not raw else link_text
        )
        links.append(
            f'<a class="go" href="{esc(video["url"])}" target="_blank" rel="noopener noreferrer" '
            f'title="{esc(title)}" aria-label="{esc(accessible_name)}">{icon("play", 11)} {esc(link_text)}</a>'
        )
    target = f' id="{esc(eid)}" tabindex="-1"' if eid != article_anchor(url) else ""
    return (
        f'<div class="case-event"{target}><div class="event-copy"><strong>{esc(heading)}</strong> '
        f'{detail}</div><div class="clinks">{"".join(links)}</div></div>'
    )


def build_page(data, zh=None):
    problems = evidence_problems(data)
    if problems:
        raise ValueError(problems[0])
    cases = data.get("cases", [])
    zh = zh or {}
    comps = sorted({c["comp"] for c in cases if c.get("comp")})
    kinds_by_url = {
        c["url"]: set(e["situacion_norm"] for e in event_rows(c)) for c in cases
    }

    # Delimit tokens on both sides so "penalty" cannot match "no_penalty".
    def chips(values, label, count):
        return "".join(
            f'<button class="chip" data-f="|{esc(key)}|">{esc(label.get(key, key))} '
            f"<b>{count(key)}</b></button>"
            for key in values
        )

    comp_chips = chips(comps, COMP_CN, lambda k: sum(c.get("comp") == k for c in cases))
    sits = sorted({key for values in kinds_by_url.values() for key in values})
    sit_chips = chips(
        sits, SIT_LABEL, lambda k: sum(k in values for values in kinds_by_url.values())
    )
    secs = ""
    for y, ycases in group_by_year(
        cases,
        date_of=lambda c: (c.get("fecha") or c.get("date") or "")[-4:],
        fallback="其他",
    ):
        rows = ""
        for c in ycases:
            url = c["url"]
            pending = c.get("detail_status") == "pending"
            events = event_rows(c)
            kinds = (
                "|"
                + "|".join(filter(None, [c.get("comp"), *sorted(kinds_by_url[url])]))
                + "|"
            )
            norm = c.get("situacion_norm", "other")
            badge = (
                "pending"
                if pending
                else SIT_BADGE.get(norm, "info")
                if len(events) == 1
                else "info"
            )
            label = (
                "文章详情待核"
                if pending
                else f"{len(events)} 个情境"
                if len(events) > 1
                else SIT_LABEL.get(norm, "判例")
            )
            title_match = c["title"].rsplit(":", 1)[-1].strip()
            source_title = (
                f'<p class="article-title">官方文章标题 · <span lang="es">{esc(c["title"])}</span></p>'
                if pending or title_match.casefold() != c["match"].casefold()
                else ""
            )
            meta = "".join(
                f'<span class="chip">{esc(v)}</span>'
                for v in (
                    f"文章发布 {c['date']}" if pending else "",
                    c.get("fecha"),
                    c.get("ciudad"),
                    c.get("estadio"),
                    COMP_CN.get(c.get("comp")),
                )
                if v
            )
            details = "".join(render_event(url, e, zh) for e in events)
            words = []
            for e in events:
                words.extend(
                    [e["minuto"], e["situacion_es"], event_translation(url, e, zh)]
                )
                words.extend(e.get("source_fields", {}).values())
                words.extend(v["title"] for v in e["videos"])
            blob = search_blob(
                c.get("match"),
                c["title"],
                c.get("date"),
                c.get("fecha"),
                c.get("ciudad"),
                c.get("estadio"),
                COMP_CN.get(c.get("comp")),
                label,
                *words,
            )
            rows += f"""<article class="ccard" id="{article_anchor(url)}" tabindex="-1" data-kinds="{esc(kinds)}" data-search="{blob}">
  <div class="chead"><span class="cmatch">{esc(c.get("match") or c["title"])}</span>
    <span class="badge {badge}">{esc(label)}</span></div>
  {source_title}<div class="cinfo">{meta}</div>{details}
  <div class="clinks"><a class="go" href="{esc(url)}" target="_blank" rel="noopener noreferrer">{icon("note", 11)} 官方分析</a></div>
</article>"""

        secs += (
            f'<h3 class="year-h" data-year="{esc(y)}">{esc(y)} <small>'
            f'{len(ycases)} 案</small></h3><div id="ybody-{esc(y)}">{rows}</div>'
        )
    tb = topbar(
        active="conmebol.html",
        stats="stats-2026.html",
        brand_sub="南美 VAR 判例",
        seasons=("2026", "2025", "2024"),
    )
    src_link = (
        f'<a href="{esc(data.get("source", ""))}" target="_blank" '
        f'rel="noopener noreferrer">conmebol.com VAR 分析专栏</a>'
    )
    html = inject_theme(
        HTML.replace("__TOPBAR__", tb)
        .replace("__SOURCE_LINK__", src_link)
        .replace("__I_EXTERNAL__", icon("external", 14))
        .replace("__SEARCHBAR__", searchbar("搜索判例：对阵 / 球场 / 情境…"))
        .replace("__HEAD_CSS__", head_css(max_width=1000))
        .replace("__SEARCH_CSS__", SEARCH_CSS)
        .replace(
            "__FILTER_JS__",
            filter_js(
                ".ccard",
                filter_attr="data-kinds",
                match="substr",
                search=True,
                group="ybody",
            ),
        )
        .replace("__N_ALL__", str(len(cases)))
        .replace("__COMP_CHIPS__", comp_chips)
        .replace("__SIT_CHIPS__", sit_chips)
        .replace("__CHECKED__", esc(data.get("fetched", "")))
        .replace("__SECTIONS__", secs),
        meta=meta_tags("conmebol.html"),
    )
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "conmebol.html").write_text(html, encoding="utf-8")
    print(
        f"生成 {SITE / 'conmebol.html'}（{len(cases)} 案 / "
        f"{len({y for y, _ in group_by_year(cases, date_of=lambda c: (c.get('fecha') or c.get('date') or '')[-4:], fallback='其他')})} 个年份）"
    )


def main():
    if not CONMEBOL_JSON.exists():
        raise SystemExit(f"缺少 {CONMEBOL_JSON}；请先运行 fetch_conmebol.py")
    data, zh = load_json_with_zh(CONMEBOL_JSON, CONMEBOL_ZH_JSON)
    build_page(data, zh)


if __name__ == "__main__":
    main()
