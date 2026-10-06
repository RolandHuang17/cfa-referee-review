# -*- coding: utf-8 -*-
"""生成 site/intl.html：全球裁判评议资源导航（美国/欧洲已整合资源之外的部分）

数据来自 data/intl.json（人工核验策展并提交）。这些资源形态各异（YouTube 频道、
新闻文章、播放列表，覆盖 6+ 语言），公开层面无可抓取的统一判例数据，故本页为
导航 + 方法说明（rap.html 同款指南模式），不抓取条目、不做外链视频内嵌。
"""
import json

from lib.theme import inject_theme, topbar, icon

from lib.paths import INTL_JSON, SITE

LANG_BADGE = {
    "英语": "info", "西语 / 葡语": "pending", "克罗地亚语": "pending",
    "乌克兰语": "pending", "土耳其语": "pending", "日语": "pending", "俄语": "pending",
}

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>全球裁判评议资源导航 · 裁判学习平台</title>
<style>
/* ===== intl 页专属布局 (tokens/组件来自 data-cfa-theme, 骨架同 rap 页) ===== */
.page-head{border-bottom:1px solid var(--line);background:var(--bg2)}
.page-head .wrap{max-width:920px;margin:0 auto;padding:22px 16px 18px}
.page-head h1{margin:0 0 5px;font-family:var(--font-display);font-size:23px;letter-spacing:.4px}
.page-head .sub{color:var(--muted);font-size:13px;line-height:1.7}
.src-banner{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:12px;
  padding:10px 14px;border:1px solid var(--brand);background:var(--info-bg);
  border-radius:var(--r-md);font-size:13.5px;color:var(--ink2)}
.src-banner .ic{color:var(--brand)}
.wrap{max-width:920px;margin:0 auto;padding:20px 16px 60px}
.about p{font-size:14px;line-height:1.9;color:var(--ink2);margin:0 0 12px}
.sect{margin-top:30px}
.sect h2{font-family:var(--font-display);font-size:19px;margin:0 0 6px;letter-spacing:.4px}
.sect .desc{font-size:13px;color:var(--muted);line-height:1.8;margin:0 0 14px}
.res{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:14px 18px;margin-bottom:12px;
  transition:transform var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease)}
.res:hover{transform:translateY(-2px);border-color:var(--brand)}
.res-head{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.res-head h3{margin:0;font-family:var(--font-display);font-size:16px}
.res-org{font-size:12px;color:var(--brand);font-weight:600;white-space:nowrap}
.res-head .badge{margin-left:auto;white-space:nowrap}
.res-meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.res-meta .chip{cursor:default;padding:3px 10px;font-size:11.5px}
.res-note{font-size:13px;color:var(--muted);line-height:1.8;margin:8px 0 0}
.res-links{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.related{display:flex;flex-wrap:wrap;gap:10px}
.foot{margin-top:28px;font-size:12px;color:var(--faint);line-height:1.8}
@media (max-width:760px){.res-head .badge{margin-left:0}}
</style>
</head>
<body class="page-intl">
<a class="skip-link" href="#content0">跳到内容</a>
__TOPBAR__
<header class="page-head">
  <div class="wrap">
    <h1>全球裁判评议资源导航</h1>
    <div class="sub">苏格兰 · 克罗地亚 · 乌克兰 · 南美 · 英格兰 · 墨西哥 · 土耳其 · 日本 · 俄罗斯的官方评议节目与周更解析 · 人工核验入口 + 语言/频率/注意事项 · __CHECKED__ 核对</div>
    <div class="src-banner">__I_GLOBE__ 这些渠道以官方语言发布；文字型周更建议配合机器翻译跟读，YouTube 型直接订阅。</div>
  </div>
</header>
<div class="wrap" id="content0">
  <section class="about">__ABOUT__</section>
  __GROUPS__
  <section class="sect">
    <h2>__I_PLAY__ 站内已整合资源</h2>
    <div class="related">__RELATED__</div>
  </section>
  <p class="foot">各资源版权归其发布机构所有；本页仅收录入口链接与使用说明（人工核对日期 __CHECKED__）。链接失效或新节目上线可直接改 data/intl.json 后重跑 build_intl.py。</p>
</div>
</body>
</html>
"""


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") \
        .replace('"', "&quot;").replace("'", "&#39;")


def build_page(data):
    about = "".join(f"<p>{esc(p)}</p>" for p in data.get("intro_cn", []))
    groups_html = ""
    for g in data.get("groups", []):
        cards = ""
        for r in g.get("resources", []):
            lang_badge = LANG_BADGE.get(r.get("lang", ""), "info")
            meta = "".join(
                f'<span class="chip">{icon("film", 11) if k == "form" else icon("note", 11)} {esc(v)}</span>'
                for k, v in (("lang", r.get("lang", "")), ("update", r.get("update", "")),
                             ("form", r.get("form", ""))) if v)
            links = "".join(
                f'<a class="btn" href="{esc(l["url"])}" target="_blank" rel="noopener noreferrer">'
                f'{icon("external", 11)} {esc(l["label"])}</a>'
                for l in r.get("links", []))
            cards += f"""<div class="res">
  <div class="res-head"><span class="res-org">{esc(r["org"])}</span>
    <h3>{esc(r["name"])}</h3>
    <span class="badge {lang_badge}">{esc(r.get("status_cn", ""))}</span></div>
  <div class="res-meta">{meta}</div>
  <p class="res-note">{esc(r.get("note_cn", ""))}</p>
  <div class="res-links">{links}</div>
</div>"""
        groups_html += (f'<section class="sect"><h2>{icon("flag", 17)} {esc(g["name_cn"])}</h2>'
                        f'<p class="desc">{esc(g.get("desc_cn", ""))}</p>{cards}</section>')
    related = "".join(
        f'<a class="btn" href="{esc(l["url"])}">{icon("right", 11)} {esc(l["label"])}</a>'
        for l in data.get("related", []))
    tb = topbar(active="intl.html", stats="stats-2026.html", brand_sub="国际评议导航",
                seasons=("2026", "2025", "2024"))
    html = inject_theme(HTML
                        .replace("__TOPBAR__", tb)
                        .replace("__I_GLOBE__", icon("globe", 14))
                        .replace("__I_FLAG__", icon("flag", 17))
                        .replace("__I_PLAY__", icon("play", 17))
                        .replace("__ABOUT__", about)
                        .replace("__GROUPS__", groups_html)
                        .replace("__RELATED__", related)
                        .replace("__CHECKED__", esc(data.get("checked", ""))))
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "intl.html").write_text(html, encoding="utf-8")
    n = sum(len(g.get("resources", [])) for g in data.get("groups", []))
    print(f"生成 {SITE / 'intl.html'}（{len(data.get('groups', []))} 组 / {n} 个资源）")


def main():
    if not INTL_JSON.exists():
        raise SystemExit(f"缺少 {INTL_JSON}；请先人工策展")
    data = json.loads(INTL_JSON.read_text(encoding="utf-8"))
    build_page(data)


if __name__ == "__main__":
    main()
