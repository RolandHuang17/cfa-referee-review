# -*- coding: utf-8 -*-
"""生成门户首页 index.html：三入口（2024/2025评议/竞赛规则）+ 得失盘点快捷入口
纯静态单文件离线可用；数据计数从 data/*.json 读取；视觉走 data-cfa-theme 设计系统
"""
import json
from datetime import date
from pathlib import Path
from theme import inject_theme, icon, topbar

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"


def load_stats():
    def season_stats(season):
        d = json.loads((ROOT / "data" / f"cases-{season}.json").read_text(encoding="utf-8"))
        cases = d["cases"]
        return {
            "n": len(cases),
            "issues": len(d["issues"]),
            "wrong": sum(1 for c in cases if c["referee_verdict"] == "wrong"),
            "correct": sum(1 for c in cases if c["referee_verdict"] == "correct"),
            "videos": sum(len(c["video_files"]) for c in cases),
        }
    laws = json.loads((ROOT / "data" / "laws.json").read_text(encoding="utf-8"))
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
    p = ROOT / "data" / "scale.json"
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
.card{position:relative;display:flex;flex-direction:column;text-decoration:none;
  background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:22px 22px 18px;overflow:hidden;color:var(--ink);
  transition:transform .16s ease, border-color .16s ease, box-shadow .16s ease}
.card:hover{transform:translateY(-4px);border-color:var(--brand);box-shadow:var(--shadow)}
.card .icon{width:42px;height:42px;border-radius:var(--r-md);display:flex;align-items:center;
  justify-content:center;background:var(--info-bg);color:var(--brand)}
.card.c-rules .icon{background:var(--amber-bg);color:var(--amber)}
.card.c-2024 .icon{background:var(--green-bg);color:var(--green)}
.card h2{margin:13px 0 4px;font-family:var(--font-display);font-size:19.5px;letter-spacing:.3px}
.card .desc{margin:0;color:var(--muted);font-size:13.5px;min-height:64px;line-height:1.7}
.card .nums{display:flex;gap:20px;margin-top:15px;padding-top:13px;border-top:1px dashed var(--line)}
.card .nums div b{display:block;font-family:var(--font-display);font-size:22px;font-weight:700;color:var(--brand);font-variant-numeric:tabular-nums}
.card.c-rules .nums div b{color:var(--amber)}
.card.c-2024 .nums div b{color:var(--green)}
.card.c-2026 .nums div b{color:var(--red)}
.card .nums div span{font-size:12px;color:var(--muted)}
.card .go{margin-top:14px;font-size:13px;color:var(--brand);font-weight:600;display:flex;align-items:center;gap:5px}
.card::after{content:"";position:absolute;inset:0;
  background:linear-gradient(120deg,transparent 30%,rgba(148,178,214,.08) 48%,transparent 62%);
  transform:translateX(-100%);transition:.5s}
.card:hover::after{transform:translateX(100%)}

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
    <a class="card c-2026" href="season-2026.html">
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
    <a class="card c-2025" href="season-2025.html">
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
    <a class="card c-2024" href="season-2024.html">
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
    <a class="card c-rules" href="rules.html">
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
    <a class="card c-scale" href="scale.html">
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
    tb = topbar(active="index.html", stats="stats-2025.html", brand_sub="评议 · 规则 · 尺度统一",
                seasons=("2024", "2025", "2026"))
    subs = {"__I_FILM__": icon("film", 20), "__I_BOOK__": icon("book", 20),
            "__I_CHART__": icon("chart", 17), "__I_RIGHT__": icon("right", 13),
            "__I_NOTE__": icon("note", 15), "__I_STAR__": icon("star", 13),
            "__I_SEARCH__": icon("search", 13), "__I_DOWN__": icon("download", 13),
            "__I_PLAY__": icon("play", 12), "__I_SHIELD__": icon("shield", 13)}
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
            .replace("__BUILT__", date.today().isoformat()))
    for k, v in subs.items():
        html = html.replace(k, v)
    SITE.mkdir(parents=True, exist_ok=True)
    out = SITE / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"生成 {out}  ({len(html.encode('utf-8'))/1024:.0f} KB)")


if __name__ == "__main__":
    main()
