# -*- coding: utf-8 -*-
"""生成门户首页 index.html：三入口（2024/2025评议/竞赛规则）+ 得失盘点快捷入口
纯静态单文件离线可用；数据计数从 data/*.json 读取；视觉走 data-cfa-theme 设计系统
"""
import json
from datetime import date

from lib.theme import inject_theme, icon, topbar

from lib.paths import (DATA, CONMEBOL_JSON, IFAB_JSON, INTL_JSON, LAWS_JSON, PRO_JSON, RAP_JSON,
                       RFEF_JSON, SCALE_JSON, SITE, UEFA_JSON, WEEKLY_JSON)


def load_stats():
    def season_stats(season):
        d = json.loads((DATA / f"cases-{season}.json").read_text(encoding="utf-8"))
        cases = d["cases"]
        return {
            "n": len(cases),
            "issues": len(d["issues"]),
            "wrong": sum(1 for c in cases if c["referee_verdict"] == "wrong"),
            "correct": sum(1 for c in cases if c["referee_verdict"] == "correct"),
            "videos": sum(len(c["video_files"]) for c in cases),
        }
    laws = json.loads(LAWS_JSON.read_text(encoding="utf-8"))
    secs = laws["sections"] if isinstance(laws, dict) else laws
    return {
        "2026": season_stats("2026"),
        "2025": season_stats("2025"),
        "2024": season_stats("2024"),
        "rules": {"sections": len(secs),
                  "laws": sum(1 for s in secs if isinstance(s, dict) and s.get("law"))},
    }


def load_scale_stats():
    """统一尺度页数字从 data/scale.json 计算（场景/分组/视频=例数）。"""
    p = SCALE_JSON
    scenes = groups = 0
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        for yd in d.values():
            if not isinstance(yd, dict):
                continue
            for sec in yd.get("sections", []):
                for g in sec.get("groups", []):
                    groups += 1
                    scenes += len(g.get("items", []))
    return {"scenes": scenes, "groups": groups, "videos": scenes}


def load_uefa_stats():
    """UEFA Clear Line 判例库数字从 data/uefa.json 计算。"""
    p = UEFA_JSON
    cases = groups = 0
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        for g in d.get("groups", []):
            groups += 1
            cases += len(g.get("items", []))
    return {"cases": cases, "groups": groups}


def load_rap_stats():
    """UEFA RAP 训练包数字从 data/rap.json 计算（期数/在线期数）。"""
    eds = online = 0
    if RAP_JSON.exists():
        d = json.loads(RAP_JSON.read_text(encoding="utf-8"))
        eds = len(d.get("editions", []))
        online = sum(1 for e in d.get("editions", []) if e.get("platform") == "nextaur")
    return {"editions": eds, "online": online}


def load_rfef_stats():
    """RFEF 判罚标准手册数字从 data/rfef.json 计算（专题/判例/视频）。"""
    secs = items = vids = 0
    if RFEF_JSON.exists():
        d = json.loads(RFEF_JSON.read_text(encoding="utf-8"))
        for s in d.get("sections", []):
            secs += 1
            for g in s.get("groups", []):
                for it in g.get("items", []):
                    items += 1
                    vids += len(it.get("videos", []))
    return {"secs": secs, "items": items, "vids": vids}


def load_pro_stats():
    """美国 PRO 评议索引数字从 data/pro.json 计算（篇数/MLS/NWSL）。"""
    arts = 0
    mls = nwsl = 0
    if PRO_JSON.exists():
        d = json.loads(PRO_JSON.read_text(encoding="utf-8"))
        arts = len(d.get("articles", []))
        mls = sum(1 for a in d["articles"] if a.get("league") == "MLS")
        nwsl = sum(1 for a in d["articles"] if a.get("league") == "NWSL")
    return {"arts": arts, "mls": mls, "nwsl": nwsl}


def load_intl_stats():
    """国际评议导航数字从 data/intl.json 计算（资源数/国家机构数）。"""
    res = orgs = 0
    if INTL_JSON.exists():
        d = json.loads(INTL_JSON.read_text(encoding="utf-8"))
        for g in d.get("groups", []):
            res += len(g.get("resources", []))
            orgs += len({r.get("org") for r in g.get("resources", [])})
    return {"res": res, "orgs": orgs}


def load_conmebol_stats():
    """南美 VAR 判例数字从 data/conmebol.json 计算（案数/赛事数）。"""
    cases = 0
    comps = set()
    if CONMEBOL_JSON.exists():
        d = json.loads(CONMEBOL_JSON.read_text(encoding="utf-8"))
        cases = len(d.get("cases", []))
        comps = {c.get("comp") for c in d["cases"] if c.get("comp")}
    return {"cases": cases, "comps": len(comps)}


def load_weekly_stats():
    """周更评议节目判例库数字从 data/weekly.json 计算（期数/节目数/语言数）。"""
    eps = shows = 0
    langs = set()
    if WEEKLY_JSON.exists():
        d = json.loads(WEEKLY_JSON.read_text(encoding="utf-8"))
        eps = len(d.get("episodes", []))
        shows = len(d.get("shows", {}))
        langs = {s.get("lang") for s in d.get("shows", {}).values() if s.get("lang")}
    return {"eps": eps, "shows": shows, "langs": len(langs)}


def load_ifab_stats():
    """IFAB 材料数字从 data/ifab.json 计算（大节/FAQ/条目）。"""
    secs = faq = items = 0
    if IFAB_JSON.exists():
        d = json.loads(IFAB_JSON.read_text(encoding="utf-8"))
        secs = len(d.get("sections", []))
        faq = len(d.get("faq", []))
        items = sum(len(b.get("items", [])) for s in d.get("sections", [])
                    for b in s.get("blocks", []))
    return {"secs": secs, "faq": faq, "items": items}


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>裁判学习一站式平台 · 足协评议合集与竞赛规则</title>
<style>
/* ===== portal 页专属布局 (颜色/组件来自 data-cfa-theme 设计系统) ===== */
.hero-bg{background:
   radial-gradient(1100px 460px at 82% -8%, rgba(77,159,255,.14), transparent 60%),
   radial-gradient(900px 420px at -8% 108%, rgba(87,201,133,.08), transparent 55%)}
.wrap{max-width:1120px;margin:0 auto;padding:40px 20px 56px}
.hero{text-align:center;margin-bottom:38px}
.hero .eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:12.5px;font-weight:600;
  letter-spacing:2.5px;color:var(--brand);margin-bottom:14px}
.hero .eyebrow::before,.hero .eyebrow::after{content:"";width:28px;height:1px;background:var(--brand);opacity:.5}
.hero h1{margin:0 0 12px;font-family:var(--font-display);font-size:36px;line-height:1.45;letter-spacing:.5px;font-weight:700}
.hero h1 em{font-style:normal;color:var(--brand)}
.hero p{margin:0 auto;color:var(--muted);font-size:15.5px;max-width:660px}
.hero .sub{margin-top:12px;font-size:13px;color:var(--faint)}

/* 浏览模式分段开关（完整版/轻量版，记忆于 localStorage cfa.lite） */
.mode-pick{margin:-16px 0 30px;display:flex;flex-direction:column;align-items:center;gap:10px}
.mp-label{font-size:11.5px;font-weight:700;letter-spacing:2.5px;color:var(--muted)}
.mp-switch{display:inline-flex;gap:6px;background:var(--card);border:1px solid var(--line);border-radius:999px;padding:5px}
.mp-switch button{display:flex;flex-direction:column;align-items:center;gap:1px;padding:8px 24px;
  border-radius:999px;border:1px solid transparent;background:none;cursor:pointer;
  font-family:inherit;font-size:14px;font-weight:700;color:var(--ink2);transition:.15s}
.mp-switch button span{font-size:11.5px;font-weight:400;color:var(--muted)}
.mp-switch button:hover{border-color:var(--brand);color:var(--brand)}
.mp-switch button.on{background:var(--brand-strong);border-color:var(--brand-strong);color:var(--on-brand)}
.mp-switch button.on span{color:var(--on-brand);opacity:.82}
.mp-desc{margin:0;font-size:12.5px;color:var(--muted);max-width:720px;text-align:center;line-height:1.7}

.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
.ecard{position:relative;display:flex;flex-direction:column;text-decoration:none;
  background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:22px 22px 18px;overflow:hidden;color:var(--ink);
  transition:transform .16s ease, border-color .16s ease, box-shadow .16s ease}
.ecard:hover{transform:translateY(-4px);border-color:var(--brand);box-shadow:var(--shadow)}
.ecard .icon{width:42px;height:42px;border-radius:var(--r-md);display:flex;align-items:center;
  justify-content:center;background:var(--info-bg);color:var(--brand)}
.ecard.c-rules .icon{background:var(--amber-bg);color:var(--amber)}
.ecard.c-2024 .icon{background:var(--green-bg);color:var(--green)}
.ecard h2{margin:13px 0 4px;font-family:var(--font-display);font-size:19.5px;letter-spacing:.3px}
.ecard .desc{margin:0;color:var(--muted);font-size:13.5px;min-height:64px;line-height:1.7}
.ecard .nums{display:flex;gap:20px;margin-top:15px;padding-top:13px;border-top:1px dashed var(--line)}
.ecard .nums div b{display:block;font-family:var(--font-display);font-size:22px;font-weight:700;color:var(--brand);font-variant-numeric:tabular-nums}
.ecard.c-rules .nums div b{color:var(--amber)}
.ecard.c-2024 .nums div b{color:var(--green)}
.ecard.c-2026 .nums div b{color:var(--red)}
.ecard .nums div span{font-size:12px;color:var(--muted)}
.ecard .go{margin-top:14px;font-size:13px;color:var(--brand);font-weight:600;display:flex;align-items:center;gap:5px}
.ecard::after{content:"";position:absolute;inset:0;
  background:linear-gradient(120deg,transparent 30%,rgba(148,178,214,.08) 48%,transparent 62%);
  transform:translateX(-100%);transition:.5s}
.ecard:hover::after{transform:translateX(100%)}
/* 入场级联 (backwards 填充: 结束后释放 transform, 不锁 hover 抬升) */
.hero{animation:fadeUp .45s var(--ease) backwards}
.mode-pick{animation:fadeUp .45s var(--ease) 80ms backwards}
.ecard{animation:fadeUp .5s var(--ease) backwards;animation-delay:calc(var(--i,0)*60ms + 120ms)}
.steps{animation:fadeUp .45s var(--ease) 480ms backwards}

.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}
.steps div{display:grid;grid-template-columns:40px 1fr;column-gap:10px;align-items:center;
  padding:14px 16px;border:1px solid var(--line);border-radius:var(--r-md);background:var(--card)}
.steps b{grid-row:span 2;color:var(--brand);font-size:21px;font-variant-numeric:tabular-nums}
.steps span{font-weight:700;color:var(--ink)}
.steps small{color:var(--muted);font-size:12.5px}

.aux{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}
.aux a{display:flex;align-items:center;gap:14px;text-decoration:none;color:var(--ink);
  background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);padding:16px 20px;
  transition:border-color .15s, transform .15s}
.aux a:hover{border-color:var(--brand);transform:translateY(-2px)}
.aux .ai{width:36px;height:36px;border-radius:var(--r-sm);display:flex;align-items:center;
  justify-content:center;background:var(--info-bg);color:var(--brand);flex:none}
.aux b{display:block;font-size:15px}
.aux span{font-size:12.5px;color:var(--muted)}
.aux .arr{margin-left:auto;color:var(--faint)}

.feats{display:flex;flex-wrap:wrap;gap:9px;justify-content:center;margin:38px 0 0}
.feat{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;color:var(--ink2);
  background:var(--card);border:1px solid var(--line);border-radius:999px;padding:6px 15px}
.feat .ic{color:var(--brand)}
.foot{margin-top:40px;text-align:center;color:var(--faint);font-size:12.5px;line-height:2}
.foot a{color:var(--brand);text-decoration:none}
@media (max-width:960px){ .grid{grid-template-columns:1fr} .aux{grid-template-columns:1fr}
  .steps{grid-template-columns:1fr} .hero h1{font-size:25px} .wrap{padding-top:26px} }
</style>
</head>
<body class="page-portal hero-bg">
__TOPBAR__

<div class="wrap">
  <section class="hero">
    <div class="eyebrow">中国足协裁判评议 · 教学整理</div>
    <h1>判例合集 <em>统一尺度</em> 与最新竞赛规则</h1>
    <p>按新裁判统一尺度教学重组的官方评议判例全集，配判罚视频、影响统计与最新版竞赛规则，全部内容可离线使用。</p>
    <div class="sub">数据来源：中国足球协会官网「裁判评议」栏目 · IFAB《足球竞赛规则》2026-27</div>  </section>

  <section class="mode-pick">
    <div class="mp-label">浏览模式</div>
    <div class="mp-switch" role="group" aria-label="浏览模式切换">
      <button type="button" id="modeFull" aria-pressed="false">完整版<span>含视频 · 适合本地离线</span></button>
      <button type="button" id="modeLite" aria-pressed="false">轻量版<span>纯文字+官方链接 · 适合在线浏览</span></button>
    </div>
    <p class="mp-desc" id="modeDesc"></p>
  </section>

  <section class="grid">
    <a class="ecard c-2026" style="--i:0" href="season-2026.html">
      <div class="icon">__I_FILM__</div>
      <h2>2026赛季评议</h2>
      <p class="desc">进行中的最新赛季，已收录 __N26_ISSUES__ 期评议，随官方发布持续更新。</p>
      <div class="nums">
        <div><b>__N26__</b><span>判例</span></div>
        <div><b>__W26__</b><span>错漏判</span></div>
        <div><b>__V26__</b><span>视频</span></div>
      </div>
      <div class="go">进入学习 __I_RIGHT__</div>
    </a>
    <a class="ecard c-2025" style="--i:1" href="season-2025.html">
      <div class="icon">__I_FILM__</div>
      <h2>2025赛季评议</h2>
      <p class="desc">最新赛季全部 __N25_ISSUES__ 期评议，含第27期对第26期的补充认定合并，分类与判定均经人工复核。</p>
      <div class="nums">
        <div><b>__N25__</b><span>判例</span></div>
        <div><b>__W25__</b><span>错漏判</span></div>
        <div><b>__V25__</b><span>视频</span></div>
      </div>
      <div class="go">进入学习 __I_RIGHT__</div>
    </a>
    <a class="ecard c-2024" style="--i:2" href="season-2024.html">
      <div class="icon">__I_FILM__</div>
      <h2>2024赛季评议</h2>
      <p class="desc">上赛季全部 __N24_ISSUES__ 期评议（含三大球运动会判例），同样的教学分类与收藏笔记体系。</p>
      <div class="nums">
        <div><b>__N24__</b><span>判例</span></div>
        <div><b>__W24__</b><span>错漏判</span></div>
        <div><b>__V24__</b><span>视频</span></div>
      </div>
      <div class="go">进入学习 __I_RIGHT__</div>
    </a>
    <a class="ecard c-rules" style="--i:3" href="rules.html">
      <div class="icon">__I_BOOK__</div>
      <h2>足球竞赛规则 2026-27</h2>
      <p class="desc">IFAB 官方最新版全文（简体中文），支持划词高亮、章节笔记、全文搜索——备赛案头工具。</p>
      <div class="nums">
        <div><b>__NRL__</b><span>章节</span></div>
        <div><b>__NLAW__</b><span>规则正文</span></div>
        <div><b>__I_NOTE__</b><span>可标注</span></div>
      </div>
      <div class="go">打开规则 __I_RIGHT__</div>
    </a>
    <a class="ecard c-scale" style="--i:4" href="scale.html">
      <div class="icon">__I_SHIELD__</div>
      <h2>统一判罚尺度宣讲</h2>
      <p class="desc">中国足协官方《统一判罚尺度》2024–2026 三季：__S_SCENES__ 例典型场景视频、官方说明与判罚决定对照。</p>
      <div class="nums">
        <div><b>__S_SCENES__</b><span>场景</span></div>
        <div><b>__S_GROUPS__</b><span>分组</span></div>
        <div><b>__S_VIDEOS__</b><span>视频</span></div>
      </div>
      <div class="go">进入学习 __I_RIGHT__</div>
    </a>
    <a class="ecard c-uefa" style="--i:5" href="uefa.html">
      <div class="icon">__I_PLAY__</div>
      <h2>欧足联判例库</h2>
      <p class="desc">UEFA 官方 Clear Line：__U_CASES__ 例真实比赛场景与官方解释（英文原文），逐例跳转官方视频页。</p>
      <div class="nums">
        <div><b>__U_CASES__</b><span>判例</span></div>
        <div><b>__U_GROUPS__</b><span>分组</span></div>
        <div><b>__I_EXT_S__</b><span>官方视频</span></div>
      </div>
      <div class="go">进入学习 __I_RIGHT__</div>
    </a>
    <a class="ecard c-rap" style="--i:6" href="rap.html">
      <div class="icon">__I_TARGET__</div>
      <h2>UEFA RAP 训练包</h2>
      <p class="desc">欧足联每年两期的「看片段→自己判→对官方答案」判例训练包：__RA_EDS__ 期索引（__RA_ONLINE__ 期 Nextaur 在线）与训练方法指南。</p>
      <div class="nums">
        <div><b>__RA_EDS__</b><span>期索引</span></div>
        <div><b>__RA_ONLINE__</b><span>在线期</span></div>
        <div><b>__I_EXT_S__</b><span>免费注册</span></div>
      </div>
      <div class="go">查看指南 __I_RIGHT__</div>
    </a>
    <a class="ecard c-rfef" style="--i:7" href="rfef.html">
      <div class="icon">__I_GLOBE__</div>
      <h2>西班牙判罚标准</h2>
      <p class="desc">RFEF/CTA《Criterios Arbitrales》2026/27：__RF_ITEMS__ 条判罚尺度配官方判例视频，中文译制、可切西语原文。</p>
      <div class="nums">
        <div><b>__RF_SECS__</b><span>专题</span></div>
        <div><b>__RF_ITEMS__</b><span>判例</span></div>
        <div><b>__RF_VIDS__</b><span>视频</span></div>
      </div>
      <div class="go">进入学习 __I_RIGHT__</div>
    </a>
    <a class="ecard c-pro" style="--i:8" href="pro.html">
      <div class="icon">__I_FLAG__</div>
      <h2>美国评议</h2>
      <p class="desc">美国 PRO（MLS/NWSL）周更 VAR 评析全量索引：Inside Video Review / VAR a Fondo / The Definitive Angle，附 USSF 视频入口指南。</p>
      <div class="nums">
        <div><b>__P_ARTS__</b><span>篇索引</span></div>
        <div><b>__P_MLS__</b><span>MLS</span></div>
        <div><b>__P_NWSL__</b><span>NWSL</span></div>
      </div>
      <div class="go">进入索引 __I_RIGHT__</div>
    </a>
    <a class="ecard c-intl" style="--i:9" href="intl.html">
      <div class="icon">__I_COMPASS__</div>
      <h2>国际评议导航</h2>
      <p class="desc">全球官方评议节目、VAR 音频与课程测验导航（4 组 __I_RES__ 项）：语言、频率、形态与注意事项一页掌握。</p>
      <div class="nums">
        <div><b>__I_RES__</b><span>资源</span></div>
        <div><b>__I_ORGS__</b><span>机构</span></div>
        <div><b>__I_LANG__</b><span>语言</span></div>
      </div>
      <div class="go">查看导航 __I_RIGHT__</div>
    </a>
    <a class="ecard c-cmem" style="--i:10" href="conmebol.html">
      <div class="icon">__I_PLAY2__</div>
      <h2>南美 VAR 判例</h2>
      <p class="desc">CONMEBOL《Situación de Análisis VAR》：世预赛/解放者杯/南美杯逐案 VAR 判例（比赛 · 情境 · 分钟），附官方分析与视频链接。</p>
      <div class="nums">
        <div><b>__C_CASES__</b><span>判例</span></div>
        <div><b>__C_COMPS__</b><span>赛事</span></div>
        <div><b>__I_EXT_S__</b><span>官方视频</span></div>
      </div>
      <div class="go">进入判例 __I_RIGHT__</div>
    </a>
    <a class="ecard c-weekly" style="--i:11" href="weekly.html">
      <div class="icon">__I_TV__</div>
      <h2>周更评议节目</h2>
      <p class="desc">全球七档官方评议节目的结构化期目索引（苏格兰/土耳其/日本/英格兰/墨西哥/阿根廷/俄罗斯）：官方说明原文 + 中文译注，逐期跳官方观看。</p>
      <div class="nums">
        <div><b>__W_SHOWS__</b><span>节目</span></div>
        <div><b>__W_EPS__</b><span>期目</span></div>
        <div><b>__W_LANGS__</b><span>语言</span></div>
      </div>
      <div class="go">进入索引 __I_RIGHT__</div>
    </a>
    <a class="ecard c-ifab" style="--i:12" href="ifab.html">
      <div class="icon">__I_FILE__</div>
      <h2>IFAB 统一尺度</h2>
      <p class="desc">IFAB《Laws of the Game》VAR 协议官方全文中文译制：原则 / 可回看判定 / 实务 / 程序四节 + 官方 FAQ 判例，可切英文原文。</p>
      <div class="nums">
        <div><b>__IF_SECS__</b><span>章节</span></div>
        <div><b>__IF_ITEMS__</b><span>条款</span></div>
        <div><b>__IF_FAQ__</b><span>FAQ 判例</span></div>
      </div>
      <div class="go">进入阅读 __I_RIGHT__</div>
    </a>
    <a class="ecard c-quiz" style="--i:13" href="quiz.html">
      <div class="icon">__I_QUIZ__</div>
      <h2>考题模式</h2>
      <p class="desc">__Q_TOTAL__ 道题随机出卷（判例 __Q_CASES__ + 尺度场景 __Q_SCALE__）：先看视频自己做判罚，再对照评议组认定算分，错题自动进错题本。</p>
      <div class="nums">
        <div><b>__Q_TOTAL__</b><span>题库</span></div>
        <div><b>__Q_CASES__</b><span>判例</span></div>
        <div><b>__Q_SCALE__</b><span>尺度场景</span></div>
      </div>
      <div class="go">开始答题 __I_RIGHT__</div>
    </a>
  </section>

  <section class="steps">
    <div><b>01</b><span>选择赛季</span><small>打开 2026 / 2025 / 2024 评议合集</small></div>
    <div><b>02</b><span>筛选判例</span><small>按赛事、球队、期数、分类和判定查找</small></div>
    <div><b>03</b><span>复盘记录</span><small>观看视频、收藏并记录学习笔记</small></div>
  </section>

  <section class="aux">
    <a href="stats-2026.html">
      <div class="ai">__I_CHART__</div>
      <div><b>2026 各队得失盘点</b><span>错漏判影响统计（赛季进行中，比分逐步补齐）</span></div>
      <div class="arr">__I_RIGHT__</div>
    </a>
    <a href="stats-2025.html">
      <div class="ai">__I_CHART__</div>
      <div><b>2025 各队得失盘点</b><span>错漏判影响统计：哪队受损、损失了什么</span></div>
      <div class="arr">__I_RIGHT__</div>
    </a>
    <a href="stats-2024.html">
      <div class="ai">__I_CHART__</div>
      <div><b>2024 各队得失盘点</b><span>错漏判影响统计：中超 / 中甲 / 中乙 / 足协杯</span></div>
      <div class="arr">__I_RIGHT__</div>
    </a>
  </section>

  <div class="feats">
    <span class="feat">__I_PLAY__ __VTOTAL__段官方判罚视频</span>
    <span class="feat">__I_SHIELD__ 教学分类 + 统一尺度要点</span>
    <span class="feat">__I_STAR__ 收藏多标签</span>
    <span class="feat">__I_NOTE__ 判例笔记</span>
    <span class="feat">__I_SEARCH__ 全文搜索</span>
    <span class="feat">__I_DOWN__ 完全离线可用</span>
  </div>

  <div class="foot">
    <p>本站为裁判员教学研究用途 · 判罚认定权属于中国足协裁判委员会评议组 · 规则文本版权归 IFAB，译文使用须遵守 <a href="NOTICE.md">版权声明</a></p>
    <p>构建于 __BUILT__ · 打开本目录即可离线使用，视频请放在 videos/ 文件夹 · 纯在线访问（如 GitHub Pages）无需下载视频，选上方「轻量版」即可</p>
  </div>
</div>
<script>
(function(){
  var lite = false;
  try { lite = localStorage.getItem("cfa.lite") === "1"; } catch(_) {}
  var full = document.getElementById("modeFull"), lit = document.getElementById("modeLite"),
      desc = document.getElementById("modeDesc");
  var DESC_ON = "已选轻量版：评议与统一尺度各页无视频窗口，判例详情为纯文字阅读 + 笔记区，并提供官方评议页与官方视频直链链接（新标签页在线播放）。",
      DESC_OFF = "已选完整版：判例详情内嵌视频播放器（本地需有 videos/ 视频文件夹；在线访问时本地视频缺失会自动改用官方直链在线播放）。";
  function sync(){
    full.classList.toggle("on", !lite);
    lit.classList.toggle("on", lite);
    full.setAttribute("aria-pressed", lite ? "false" : "true");
    lit.setAttribute("aria-pressed", lite ? "true" : "false");
    desc.textContent = lite ? DESC_ON : DESC_OFF;
  }
  function set(v){
    lite = v;
    try { localStorage.setItem("cfa.lite", v ? "1" : "0"); } catch(_) {}
    if (v) document.documentElement.dataset.lite = "1";
    else document.documentElement.removeAttribute("data-lite");
    sync();
  }
  full.addEventListener("click", function(){ set(false); });
  lit.addEventListener("click", function(){ set(true); });
  sync();
})();
</script>
</body>
</html>
"""


def main():
    s = load_stats()
    sc = load_scale_stats()
    u = load_uefa_stats()
    ra = load_rap_stats()
    rf = load_rfef_stats()
    pro = load_pro_stats()
    intl = load_intl_stats()
    cm = load_conmebol_stats()
    wk = load_weekly_stats()
    ifab = load_ifab_stats()
    from build_quiz import build_bank  # 与 quiz 页同一题库口径
    bank, _, _ = build_bank()
    q_case = sum(1 for b in bank if b["t"] == "case")
    q_scale = sum(1 for b in bank if b["t"] == "scale")
    tb = topbar(active="index.html", stats="stats-2026.html", brand_sub="评议 · 规则 · 尺度统一",
                seasons=("2024", "2025", "2026"))
    subs = {"__I_FILM__": icon("film", 20), "__I_BOOK__": icon("book", 20),
            "__I_CHART__": icon("chart", 17), "__I_RIGHT__": icon("right", 13),
            "__I_NOTE__": icon("note", 15), "__I_STAR__": icon("star", 13),
            "__I_SEARCH__": icon("search", 13), "__I_DOWN__": icon("download", 13),
            "__I_PLAY__": icon("play", 12), "__I_SHIELD__": icon("shield", 13),
            "__I_QUIZ__": icon("quiz", 20), "__I_EXT_S__": icon("external", 15),
            "__I_TARGET__": icon("target", 20), "__I_GLOBE__": icon("globe", 20),
            "__I_FLAG__": icon("flag", 20), "__I_COMPASS__": icon("compass", 20),
            "__I_PLAY2__": icon("play", 20), "__I_TV__": icon("tv", 20),
            "__I_FILE__": icon("file-text", 20)}
    html = inject_theme(HTML
            .replace("__TOPBAR__", tb)
            .replace("__N26__", str(s["2026"]["n"]))
            .replace("__W26__", str(s["2026"]["wrong"]))
            .replace("__V26__", str(s["2026"]["videos"]))
            .replace("__N26_ISSUES__", str(s["2026"]["issues"]))
            .replace("__VTOTAL__", str(s["2026"]["videos"] + s["2025"]["videos"] + s["2024"]["videos"]))
            .replace("__N25__", str(s["2025"]["n"]))
            .replace("__W25__", str(s["2025"]["wrong"]))
            .replace("__V25__", str(s["2025"]["videos"]))
            .replace("__N25_ISSUES__", str(s["2025"]["issues"]))
            .replace("__N24__", str(s["2024"]["n"]))
            .replace("__W24__", str(s["2024"]["wrong"]))
            .replace("__V24__", str(s["2024"]["videos"]))
            .replace("__N24_ISSUES__", str(s["2024"]["issues"]))
            .replace("__NRL__", str(s["rules"]["sections"]))
            .replace("__NLAW__", str(s["rules"]["laws"]))
            .replace("__S_SCENES__", str(sc["scenes"]))
            .replace("__S_GROUPS__", str(sc["groups"]))
            .replace("__S_VIDEOS__", str(sc["videos"]))
            .replace("__U_CASES__", str(u["cases"]))
            .replace("__U_GROUPS__", str(u["groups"]))
            .replace("__RA_EDS__", str(ra["editions"]))
            .replace("__RA_ONLINE__", str(ra["online"]))
            .replace("__RF_SECS__", str(rf["secs"]))
            .replace("__RF_ITEMS__", str(rf["items"]))
            .replace("__RF_VIDS__", str(rf["vids"]))
            .replace("__P_ARTS__", str(pro["arts"]))
            .replace("__P_MLS__", str(pro["mls"]))
            .replace("__P_NWSL__", str(pro["nwsl"]))
            .replace("__I_RES__", str(intl["res"]))
            .replace("__I_ORGS__", str(intl["orgs"]))
            .replace("__I_LANG__", "7")
            .replace("__C_CASES__", str(cm["cases"]))
            .replace("__C_COMPS__", str(cm["comps"]))
            .replace("__W_SHOWS__", str(wk["shows"]))
            .replace("__W_EPS__", str(wk["eps"]))
            .replace("__W_LANGS__", str(wk["langs"]))
            .replace("__IF_SECS__", str(ifab["secs"]))
            .replace("__IF_ITEMS__", str(ifab["items"]))
            .replace("__IF_FAQ__", str(ifab["faq"]))
            .replace("__Q_TOTAL__", str(q_case + q_scale))
            .replace("__Q_CASES__", str(q_case))
            .replace("__Q_SCALE__", str(q_scale))
            .replace("__BUILT__", date.today().isoformat()))
    for k, v in subs.items():
        html = html.replace(k, v)
    SITE.mkdir(parents=True, exist_ok=True)
    out = SITE / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"生成 {out}  ({len(html.encode('utf-8'))/1024:.0f} KB)")


if __name__ == "__main__":
    main()
