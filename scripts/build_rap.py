# -*- coding: utf-8 -*-
"""生成 site/rap.html：UEFA RAP（Refereeing Assistance Programme）判例训练包导航页
（纯指南页：训练方法说明 + 25 期索引 + 相关工具，无视频无判例内容）

数据来自 data/rap.json（人工策展并提交；fetch_rap.py 可核对索引页发现新期）。
RAP 判例内容在 Nextaur 登录墙后或已失效的下载包内，不可抓取——本页只做导航与
训练方法说明，与 uefa.html（Clear Line 判例库）互为补充。
"""
import json

from lib.theme import inject_theme, topbar, icon

from lib.paths import RAP_JSON, SITE

NEXTAUR_URL = "https://nextaur.com/uefa/"

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UEFA RAP 判例训练包 · 裁判学习平台</title>
<style>
/* ===== rap 页专属布局 (tokens/组件来自 data-cfa-theme) ===== */
.page-head{border-bottom:1px solid var(--line);background:var(--bg2)}
.page-head .wrap{max-width:920px;margin:0 auto;padding:22px 16px 18px}
.page-head h1{margin:0 0 5px;font-family:var(--font-display);font-size:23px;letter-spacing:.4px}
.page-head .sub{color:var(--muted);font-size:13px;line-height:1.7}
.src-banner{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:12px;
  padding:10px 14px;border:1px solid var(--brand);background:var(--info-bg);
  border-radius:var(--r-md);font-size:13.5px;color:var(--ink2)}
.src-banner .ic{color:var(--brand)}
.src-banner a{color:var(--brand);font-weight:600;text-decoration:none}
.src-banner a:hover{text-decoration:underline}
.wrap{max-width:920px;margin:0 auto;padding:20px 16px 60px}
.about p{font-size:14px;line-height:1.9;color:var(--ink2);margin:0 0 12px}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0 8px}
.step{background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);padding:14px 16px}
.step b{display:flex;align-items:center;gap:8px;font-family:var(--font-display);font-size:15px;margin-bottom:6px}
.step .n{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;
  border-radius:50%;background:var(--brand);color:var(--on-brand);font-size:13px;font-weight:700}
.step p{margin:0;font-size:13px;color:var(--muted);line-height:1.8}
.sect{margin-top:34px}
.sect h2{font-family:var(--font-display);font-size:19px;margin:0 0 10px;letter-spacing:.4px}
.sect .desc{font-size:13.5px;color:var(--muted);line-height:1.8;margin:0 0 14px}
.edition{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:14px 18px;margin-bottom:12px;
  transition:transform var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease)}
.edition:hover{transform:translateY(-2px);border-color:var(--brand)}
.ed-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.ed-head h3{margin:0;font-family:var(--font-display);font-size:16.5px}
.ed-size{font-size:11.5px;color:var(--muted);border:1px solid var(--line);border-radius:6px;
  padding:1px 8px;background:var(--card2);white-space:nowrap}
.ed-status{margin-left:auto}
.ed-note{font-size:13px;color:var(--muted);line-height:1.75;margin:6px 0 0}
.ed-links{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.tools{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px}
.tool{background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);padding:12px 15px;
  text-decoration:none;color:var(--ink2);transition:.12s}
.tool:hover{border-color:var(--brand);color:var(--ink)}
.tool b{display:block;font-size:13.5px;color:var(--ink);margin-bottom:4px}
.tool span{font-size:12.5px;color:var(--muted);line-height:1.7}
.related{display:flex;flex-wrap:wrap;gap:10px}
.foot{margin-top:30px;font-size:12px;color:var(--faint);line-height:1.8}
@media (max-width:760px){.steps{grid-template-columns:1fr}.ed-status{margin-left:0}}
</style>
</head>
<body class="page-rap">
<a class="skip-link" href="#content0">跳到内容</a>
__TOPBAR__
<header class="page-head">
  <div class="wrap">
    <h1>UEFA RAP 判例训练包</h1>
    <div class="sub">Refereeing Assistance Programme：欧足联每年两期的「看片段 → 自己判 → 对官方答案」视频判例训练包，与中国足协评议训练完全同构 · 本页为导航与训练方法指南（内容在注册墙/下载包内，站内不收录判例数据）</div>
    <div class="src-banner">__I_EXTERNAL__ 2025-2 起在 Nextaur 平台在线发布（免费注册）；__SOURCE_LINK__</div>
  </div>
</header>
<div class="wrap" id="content0">
  <section class="about">
    __ABOUT__
    <div class="steps">__STEPS__</div>
  </section>
  <section class="sect">
    <h2>__I_FILM__ 各期索引</h2>
    <p class="desc">按发布时期分组。下载包时期的 WeTransfer 链接通常在数周后失效，「链接可能已失效」为常态——在线期请直接使用 Nextaur。介意第三方工具的请只用 Nextaur。</p>
    __EDITIONS__
  </section>
  <section class="sect">
    <h2>__I_TOOL__ 相关工具与链接</h2>
    <div class="tools">__TOOLS__</div>
  </section>
  <section class="sect">
    <h2>__I_PLAY__ 站内关联</h2>
    <div class="related">
      <a class="tool" href="uefa.html"><b>欧足联 Clear Line 判例库</b><span>判例+官方解释直接可见的公开库，与 RAP 的「先判后看」互补；本站已全量中文译制</span></a>
      <a class="tool" href="quiz.html"><b>考题模式</b><span>用足协评议判例自测判罚决定与纪律处分，RAP 式训练的离线练习场</span></a>
    </div>
  </section>
  <p class="foot">RAP 各期内容版权归 UEFA 所有；dutchreferee.com 为各期下载链接的社区索引来源。本页仅提供导航与训练方法说明。数据核对日期：__CHECKED__。</p>
</div>
</body>
</html>
"""


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") \
        .replace('"', "&quot;").replace("'", "&#39;")


def build_page(data):
    about = "".join(f"<p>{esc(p)}</p>" for p in data.get("about_cn", []))
    steps = "".join(
        f'<div class="step"><b><span class="n">{esc(h["step"])}</span>{esc(h["title"])}</b>'
        f'<p>{esc(h["text"])}</p></div>'
        for h in data.get("howto_cn", []))
    eras = {e["key"]: e for e in data.get("eras", [])}
    editions_html = ""
    for era in data.get("eras", []):
        eds = [e for e in data.get("editions", []) if e.get("era") == era["key"]]
        if not eds:
            continue
        editions_html += (f'<h3 style="font-family:var(--font-display);font-size:15.5px;'
                          f'margin:18px 0 10px">{esc(era["name_cn"])}</h3>'
                          f'<p class="desc" style="margin:-6px 0 12px">{esc(era["desc_cn"])}</p>')
        for e in eds:
            online = e.get("platform") == "nextaur"
            size = f'<span class="ed-size">{esc(e["size"])}</span>' if e.get("size") else ""
            status = (f'<span class="ed-status badge {"correct" if online else "info"}">'
                      f'{esc(e.get("status_cn", ""))}</span>')
            links = "".join(
                f'<a class="btn" href="{esc(l["url"])}" target="_blank" rel="noopener noreferrer">'
                f'{icon("external", 12)} {esc(l["label"])}</a>'
                for l in e.get("links", []))
            editions_html += f"""<div class="edition">
  <div class="ed-head"><h3>{esc(e["title"])}</h3>{size}{status}</div>
  <p class="ed-note">{esc(e.get("note_cn", ""))}</p>
  <div class="ed-links">{links}</div>
</div>"""
    tools = "".join(
        f'<a class="tool" href="{esc(t["url"])}" target="_blank" rel="noopener noreferrer">'
        f'<b>{esc(t["name"])}</b><span>{esc(t.get("note_cn", ""))}</span></a>'
        for t in data.get("tools", []))
    tb = topbar(active="rap.html", stats="stats-2026.html", brand_sub="UEFA RAP 训练包",
                seasons=("2026", "2025", "2024"))
    src_link = (f'<a href="{esc(data.get("source", ""))}" target="_blank" '
                f'rel="noopener noreferrer">dutchreferee.com 各期索引</a>')
    html = inject_theme(HTML
                        .replace("__TOPBAR__", tb)
                        .replace("__SOURCE_LINK__", src_link)
                        .replace("__I_EXTERNAL__", icon("external", 14))
                        .replace("__I_FILM__", icon("film", 17))
                        .replace("__I_TOOL__", icon("sliders", 17))
                        .replace("__I_PLAY__", icon("play", 17))
                        .replace("__ABOUT__", about)
                        .replace("__STEPS__", steps)
                        .replace("__EDITIONS__", editions_html)
                        .replace("__TOOLS__", tools)
                        .replace("__CHECKED__", esc(data.get("checked", ""))))
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "rap.html").write_text(html, encoding="utf-8")
    n = len(data.get("editions", []))
    print(f"生成 {SITE / 'rap.html'}（{n} 期索引 / {len(data.get('tools', []))} 个工具链接）")


def main():
    if not RAP_JSON.exists():
        raise SystemExit(f"缺少 {RAP_JSON}；请先人工策展或运行 fetch_rap.py merge")
    data = json.loads(RAP_JSON.read_text(encoding="utf-8"))
    build_page(data)


if __name__ == "__main__":
    main()
