# -*- coding: utf-8 -*-
"""生成门户首页 index.html：三入口（24评议/25评议/竞赛规则）+ 得失盘点快捷入口
纯静态单文件离线可用；数据计数从 data/*.json 读取
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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
        "2025": season_stats("2025"),
        "2024": season_stats("2024"),
        "rules": {"sections": len(secs),
                  "laws": sum(1 for s in secs if isinstance(s, dict) and s.get("law"))},
    }


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>裁判学习一站式平台 · 足协评议合集与竞赛规则</title>
<style>
:root{
  --bg:#0d1b2a; --ink:#e8f0f8; --muted:#8fa6bc; --line:#1e3a56;
  --brand:#1266b5; --brand2:#2f8be6;
  --red:#ff7b6b; --green:#5ad18a; --amber:#ffc94d;
}
*{box-sizing:border-box}
body{margin:0;background:
   radial-gradient(1200px 500px at 85% -10%, rgba(47,139,230,.22), transparent 60%),
   radial-gradient(900px 420px at -10% 110%, rgba(90,209,138,.10), transparent 55%),
   var(--bg);
  color:var(--ink);min-height:100vh;
  font-family:"Microsoft YaHei","PingFang SC","Segoe UI",system-ui,sans-serif;
  font-size:15.5px;line-height:1.75}
a{color:inherit}

.topbar{height:54px;display:flex;align-items:center;gap:10px;padding:0 22px;
  background:rgba(9,20,34,.85);border-bottom:1px solid var(--line);color:#fff;
  position:sticky;top:0;z-index:10;backdrop-filter:blur(6px)}
.topbar .brand b{font-size:17px;letter-spacing:.5px}
.topbar .brand span{font-size:12.5px;color:#9db8d2;margin-left:8px}
.topbar nav{margin-left:auto;display:flex;gap:8px}
.topbar a.tbtn{padding:7px 14px;border-radius:8px;border:1px solid #2c5075;
  color:#dceafa;text-decoration:none;font-size:13.5px;white-space:nowrap}
.topbar a.tbtn:hover{background:rgba(255,255,255,.10)}

.wrap{max-width:1120px;margin:0 auto;padding:44px 20px 60px}
.hero{text-align:center;margin-bottom:40px}
.hero h1{margin:0 0 10px;font-size:34px;line-height:1.35;letter-spacing:1px}
.hero h1 em{font-style:normal;background:linear-gradient(90deg,#5ad1f0,#2f8be6 45%,#7ea8ff);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.hero p{margin:0;color:var(--muted);font-size:16px;max-width:640px;margin:0 auto}
.hero .sub{margin-top:12px;font-size:13.5px;color:#6f8aa3}

.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.card{position:relative;display:flex;flex-direction:column;gap:0;text-decoration:none;
  background:linear-gradient(180deg,#12263c,#0f2136);border:1px solid var(--line);
  border-radius:16px;padding:24px 24px 20px;overflow:hidden;
  transition:transform .16s ease, border-color .16s ease, box-shadow .16s ease}
.card:hover{transform:translateY(-4px);border-color:#2f8be6;
  box-shadow:0 14px 34px rgba(0,0,0,.45)}
.card .icon{font-size:34px;line-height:1}
.card h2{margin:14px 0 4px;font-size:21px}
.card .desc{margin:0;color:var(--muted);font-size:13.8px;min-height:66px}
.card .nums{display:flex;gap:18px;margin-top:16px;padding-top:14px;
  border-top:1px dashed #234160}
.card .nums div b{display:block;font-size:22px;font-weight:700;color:#fff}
.card .nums div span{font-size:12px;color:#7e97ad}
.card .go{margin-top:16px;font-size:13.5px;color:var(--brand2);font-weight:600}
.card::after{content:"";position:absolute;inset:0;
  background:linear-gradient(120deg,transparent 30%,rgba(255,255,255,.05) 48%,transparent 62%);
  transform:translateX(-100%);transition:.5s}
.card:hover::after{transform:translateX(100%)}
.card.c-rules .nums div b{color:var(--amber)}
.card.c-2024 .nums div b{color:var(--green)}
.card.c-2025 .nums div b{color:var(--brand2)}

.aux{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}
.aux a{display:flex;align-items:center;gap:16px;text-decoration:none;
  background:#0f2136;border:1px solid var(--line);border-radius:14px;padding:18px 22px;
  transition:border-color .15s, transform .15s}
.aux a:hover{border-color:#2f8be6;transform:translateY(-2px)}
.aux .ai{font-size:26px}
.aux b{display:block;font-size:16px}
.aux span{font-size:13px;color:var(--muted)}
.aux .arr{margin-left:auto;color:#5f7c96}

.feats{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin:42px 0 0}
.feat{font-size:13px;color:#a9c2d8;background:#10233a;border:1px solid #1e3a56;
  border-radius:20px;padding:6px 16px}
.foot{margin-top:46px;text-align:center;color:#5f7891;font-size:12.8px;line-height:2}
.foot a{color:#7fa3c4}

@media (max-width:960px){ .grid{grid-template-columns:1fr} .aux{grid-template-columns:1fr}
  .hero h1{font-size:26px} .wrap{padding-top:28px} }
</style>
</head>
<body>
<header class="topbar">
  <div class="brand"><b>⚽ 裁判学习平台</b><span>评议合集 · 竞赛规则 · 尺度统一</span></div>
  <nav>
    <a class="tbtn" href="season-2024.html">24评议</a>
    <a class="tbtn" href="season-2025.html">25评议</a>
    <a class="tbtn" href="rules.html">📖 竞赛规则</a>
  </nav>
</header>

<div class="wrap">
  <section class="hero">
    <h1>中国足协裁判评议 <em>教学合集</em> 与最新竞赛规则</h1>
    <p>按新裁判统一尺度教学重组的官方评议判例全集，配判罚视频、影响统计与最新版竞赛规则，全部内容可离线使用。</p>
    <div class="sub">数据来源：中国足球协会官网「裁判评议」栏目 · IFAB《足球竞赛规则》2026-27</div>
  </section>

  <section class="grid">
    <a class="card c-2025" href="season-2025.html">
      <div class="icon">🟦</div>
      <h2>2025赛季评议</h2>
      <p class="desc">最新赛季全部 __N25_ISSUES__ 期评议，含第27期对第26期的补充认定合并，分类与判定均经人工复核。</p>
      <div class="nums">
        <div><b>__N25__</b><span>判例</span></div>
        <div><b>__W25__</b><span>错漏判</span></div>
        <div><b>__V25__</b><span>视频</span></div>
      </div>
      <div class="go">进入学习 →</div>
    </a>
    <a class="card c-2024" href="season-2024.html">
      <div class="icon">🟩</div>
      <h2>2024赛季评议</h2>
      <p class="desc">上赛季全部 __N24_ISSUES__ 期评议（含三大球运动会判例），同样的教学分类与收藏笔记体系。</p>
      <div class="nums">
        <div><b>__N24__</b><span>判例</span></div>
        <div><b>__W24__</b><span>错漏判</span></div>
        <div><b>__V24__</b><span>视频</span></div>
      </div>
      <div class="go">进入学习 →</div>
    </a>
    <a class="card c-rules" href="rules.html">
      <div class="icon">📖</div>
      <h2>足球竞赛规则 2026-27</h2>
      <p class="desc">IFAB 官方最新版全文（简体中文），支持划词高亮、章节笔记、全文搜索——备赛案头工具。</p>
      <div class="nums">
        <div><b>__NRL__</b><span>章节</span></div>
        <div><b>__NLAW__</b><span>规则正文</span></div>
        <div><b>✎</b><span>可标注</span></div>
      </div>
      <div class="go">打开规则 →</div>
    </a>
  </section>

  <section class="aux">
    <a href="stats-2025.html">
      <div class="ai">📊</div>
      <div><b>2025 各队得失盘点</b><span>错漏判影响统计：哪队受损、损失了什么</span></div>
      <div class="arr">→</div>
    </a>
    <a href="stats-2024.html">
      <div class="ai">📊</div>
      <div><b>2024 各队得失盘点</b><span>错漏判影响统计：中超 / 中甲 / 中乙 / 足协杯</span></div>
      <div class="arr">→</div>
    </a>
  </section>

  <div class="feats">
    <span class="feat">🎥 390段官方判罚视频</span>
    <span class="feat">🗂 教学分类 + 统一尺度要点</span>
    <span class="feat">⭐ 收藏多标签</span>
    <span class="feat">✏️ 判例笔记</span>
    <span class="feat">🔍 全文搜索</span>
    <span class="feat">📶 完全离线可用</span>
  </div>

  <div class="foot">
    <p>本站为裁判员教学研究用途 · 判罚认定权属于中国足协裁判委员会评议组 · 规则文本版权归 IFAB，译文使用须遵守 <a href="declaration.md">版权声明</a></p>
    <p>构建于 __BUILT__ · 双击本文件即可离线使用，视频请放在同目录 videos/ 文件夹</p>
  </div>
</div>
</body>
</html>
"""


def main():
    s = load_stats()
    html = (HTML
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
            .replace("__BUILT__", date.today().isoformat()))
    out = ROOT / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"生成 {out}  ({len(html.encode('utf-8'))/1024:.0f} KB)")


if __name__ == "__main__":
    main()
