# -*- coding: utf-8 -*-
"""从官方繁体PDF构建简体版竞赛规则内容 -> data/laws.json + rules.html
流程: dict模式按阅读顺序提取行(y/x排序) -> 过滤页码页脚 -> 行分类(小节标题/列表/脚注/图表页)
      -> 段落重构状态机(断行合并、一句一段、列表缩进、段距判断) -> OpenCC繁转简 -> 术语对照 -> HTML
依赖(仅构建时): pip install pymupdf opencc-python-reimplemented
"""
import json
import re
from pathlib import Path

import pymupdf
import opencc

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "data" / "laws_raw" / "lotg-202627-tc-single.pdf"
OUT = ROOT / "data" / "laws.json"
RULES_HTML = ROOT / "rules.html"
IMG_DIR = ROOT / "assets" / "rules"

CC = opencc.OpenCC("t2s")

# 足球术语对照（在OpenCC之前应用；键为繁体原文形态，值为规范简体）
GLOSSARY = {
    "足球球例": "足球竞赛规则",
    "競賽規則": "竞赛规程",
    "賽事執法人員": "比赛官员",
    "視像助理裁判員": "视频助理裁判员",
    "其他賽事執法人員": "其他比赛官员",
    "後備球員": "替补队员",
    "後備裁判員": "后备官员",
    "替換球員機會": "换人机会",
    "替換名額": "换人名额",
    "球隊職員": "球队官员",
    "球隊名單人仕": "球队名单人员",
    "驅逐離場": "罚令出场",
    "不檢行為": "不正当行为",
    "橫楣": "横梁",
    "皮球": "球",
    "入球": "进球",
    "自由球": "任意球",
    "點球區域": "罚球区",
    "點球點": "罚球点",
    "玩球": "处理球",
    "得益": "有利",
    "週年大會": "年度大会",
    "執法人員": "比赛官员",
    "換出": "换下",
    "人仕": "人员",
    "球季": "赛季",
    "箭嘴": "箭头",
    "元老": "老年",
    "球例": "规则",
    "得一": "获得一个",
    "一點球": "一个罚球点球",
    "阻延": "拖延",
    "倒數": "倒计时",
    "攝錄機": "摄像机",
    "對賽": "比赛",
    "部份": "部分",
}
# 章节标题（简体规范译名）
LAW_TITLES = {
    1: "比赛场地", 2: "球", 3: "队员", 4: "队员装备", 5: "裁判员",
    6: "其他比赛官员", 7: "比赛时间", 8: "比赛开始与重新开始比赛",
    9: "比赛进行与比赛停止", 10: "决定比赛胜负的方法", 11: "越位",
    12: "犯规与不正当行为", 13: "任意球", 14: "罚球点球", 15: "掷界外球",
    16: "球门球", 17: "角球",
}
CN_NUM = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七",
          8: "八", 9: "九", 10: "十", 11: "十一", 12: "十二", 13: "十三",
          14: "十四", 15: "十五", 16: "十六", 17: "十七"}

FRONT = [
    ("intro", "引言", 11, 16),
    ("overview", "规则概述·须知事项及修订", 17, 27),
    ("captain", "「仅限队长」指引", 28, 32),
    ("overview2", "规则概述续编与换人协定", 33, 44),
]
BACK = [
    ("var", "视频助理裁判员（VAR）协定", 155, 162),
    ("changes", "2026/27规则变更", 163, 190),
    ("revision", "规则修订与实施", 191, 210),
    ("guide", "比赛官员实用指引", 211, 236),
]

# 图形/信号页（人工核定）：球门尺寸、有利信号、红黄牌信号、助理裁判员信号、
# 进球判定、点球区违例、角球反弹、裁判位置图、词汇图等 —— 渲染为图片而非文本
DIAGRAM_PAGES = {51, 79, 80, 88, 89, 90, 104, 115, 142, 146, 201, 207, 211, 214, 215}


def convert(text: str) -> str:
    # 术语替换必须在OpenCC之前（键为繁体原文形态），替换值均为规范简体
    for k in sorted(GLOSSARY, key=len, reverse=True):
        text = text.replace(k, GLOSSARY[k])
    return CC.convert(text)


def page_lines(page):
    """按阅读顺序(y,x)返回行: [{text,x0,bold,size,y0}]；过滤页码/页眉页脚/空行/大字章题"""
    d = page.get_text("dict")
    rows = []
    for block in d.get("blocks", []):
        if block.get("type") != 0:
            continue
        for ln in block.get("lines", []):
            spans = [sp for sp in ln.get("spans", []) if sp.get("text", "").strip()]
            if not spans:
                continue
            text = "".join(sp.get("text", "") for sp in spans)
            x0 = min(sp["bbox"][0] for sp in spans)
            y0 = ln["bbox"][1]
            size = max(sp.get("size", 0) for sp in spans)
            bold = any(sp.get("flags", 0) & 16 for sp in spans)
            rows.append({"text": text, "x0": x0, "y0": y0, "size": size, "bold": bold})
    rows.sort(key=lambda r: (round(r["y0"], 1), r["x0"]))
    out = []
    for r in rows:
        t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", r["text"]).strip()
        if not t:
            continue
        if re.fullmatch(r"\d{1,3}", t):  # 页码
            continue
        if "足球球例" in t and ("|" in t or r["y0"] > 540):  # 页眉/页脚
            continue
        if r["size"] >= 25:  # 章大标题（33pt）
            continue
        r["text"] = t
        out.append(r)
    return out


def classify(line):
    t = line["text"]
    if t.startswith("*"):
        return "fn"
    if t[0] in "•·▪":
        return "bullet"
    if line["bold"] and line["x0"] < 60 and re.match(r"^\d{1,2}[.、]", t):
        return "h3"
    return "plain"


class Flow:
    """段落重构状态机：断行合并、一句一段、列表缩进(x0几何判定)、段距判断"""
    CONNECTORS = "及或与和，、：；"

    def __init__(self):
        self.out, self.p = [], []
        self.in_ul = False
        self.li = None            # 开放列表项的内容片段（后续行并入）
        self.li_cls = ""
        self.li_plain = ""
        self.last_bullet_x0 = None
        self.prev_y = None
        self.new_page = True

    def close_li(self):
        if self.li is not None:
            self.out.append(f"<li{self.li_cls}>" + "".join(self.li) + "</li>")
            self.li = None
            self.li_plain = ""

    def close_ul(self):
        if self.in_ul:
            self.close_li()
            self.out.append("</ul>")
            self.in_ul = False

    def flush_p(self):
        self.close_ul()
        if self.p:
            self.out.append("<p>" + "".join(self.p) + "</p>")
            self.p = []

    def add_img(self, pno):
        self.close_ul(); self.flush_p()
        self.out.append(f'<figure class="pg"><img src="assets/rules/p{pno}.png" '
                        f'alt="图示" loading="lazy"></figure>')
        self.prev_y = None
        self.new_page = True

    def _li_text(self):
        return self.li_plain.rstrip()

    def add_line(self, cls, html, plain, x0, y0, level=1):
        gap_break = (not self.new_page and self.prev_y is not None
                     and y0 is not None and y0 - self.prev_y > 19)
        if cls == "h3":
            self.close_ul(); self.flush_p()
            self.out.append(f"<h3>{html}</h3>")
        elif cls == "fn":
            self.close_ul(); self.flush_p()
            self.out.append(f'<p class="fn">{html}</p>')
        elif cls == "bullet":
            self.flush_p()
            if not self.in_ul:
                self.out.append("<ul>")
                self.in_ul = True
            else:
                self.close_li()
            self.li = [html]      # 内容缓冲：close_li 时统一发射
            self.li_plain = html
            self.li_cls = ' class="l2"' if level >= 2 else ""
            self.last_bullet_x0 = x0
        else:  # plain
            if self.in_ul and self.li is not None:
                buf = self._li_text()
                if plain.strip() in ("及", "或", "与", "和"):
                    self.li.append(html)             # 连接词独行：属于当前列表项
                elif x0 is not None and self.last_bullet_x0 and x0 >= self.last_bullet_x0 + 4:
                    self.li.append(html)             # 缩进≥项目文字：列表项续行
                elif buf[-1:] in "。？！":
                    self.close_ul(); self.flush_p()
                    self.p.append(html)
                    if plain[-1:] in "。？！：":
                        self.flush_p()
                elif gap_break:
                    self.close_ul(); self.flush_p()  # 段距=列表结束
                    self.p.append(html)
                    if plain[-1:] in "。？！：":
                        self.flush_p()
                else:
                    self.li.append(html)             # 不完整句子：续行
            else:
                if self.p and self.p[-1].rstrip()[-1:] in "。？！：":
                    self.flush_p()
                self.p.append(html)
                if plain[-1:] in "。？！：":
                    self.flush_p()
        self.prev_y = y0
        self.new_page = False

    def finish(self):
        self.close_ul(); self.flush_p()

    def html(self):
        self.finish()
        return "\n".join(self.out)


def build_section_html(doc, page_nums, diagrams):
    flow = Flow()
    prev_page = None
    for pno in page_nums:
        if pno in diagrams:
            flow.add_img(pno)
            prev_page = pno
            continue
        lines = page_lines(doc[pno - 1])
        # 页内bullet按x0分级（每+10pt约一层）
        bullet_x = sorted({round(l["x0"], 1) for l in lines if classify(l) == "bullet"})
        for line in lines:
            line["page"] = pno
            cls = classify(line)
            flow.new_page = (prev_page is not None and pno != prev_page)
            if cls == "h3":
                flow.add_line("h3", convert(line["text"]), "", line["x0"], line["y0"], 1)
            elif cls == "fn":
                flow.add_line("fn", convert(line["text"]), "", line["x0"], line["y0"], 1)
            elif cls == "bullet":
                t = convert(re.sub(r"^[•·▪]\s*", "", line["text"]))
                lvl = next((k for k, x in enumerate(bullet_x, 1)
                            if abs(line["x0"] - x) < 3), 1)
                flow.add_line("bullet", t, "", line["x0"], line["y0"], lvl)
            else:
                flow.add_line("plain", convert(line["text"]), line["text"],
                              line["x0"], line["y0"], 1)
            prev_page = pno
    return flow.html()


def find_law_starts(doc):
    """各章起始页（1-based）: 优先'球例N'分隔页（首行）, 兜底页眉'第X章'"""
    starts = {}
    for i in range(len(doc)):
        lines = doc[i].get_text("text").strip().split("\n")
        if not lines:
            continue
        m = re.fullmatch(r"球例\s*(\d{1,2})", lines[0].strip())
        if m:
            n = int(m.group(1))
            if n in LAW_TITLES and n not in starts:
                starts[n] = i + 1
    cn = {v: k for k, v in CN_NUM.items()}
    for i in range(len(doc)):
        if len(starts) == len(LAW_TITLES):
            break
        for line in doc[i].get_text("text").split("\n")[:6]:
            m = re.search(r"第\s*([一二三四五六七八九十]+)\s*章", line)
            if m and "足球球例" in line:
                n = cn.get(m.group(1))
                if n in LAW_TITLES and n not in starts:
                    starts[n] = i + 1
                break
    return starts


RULES_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>足球竞赛规则 2026/27 · 简体中文</title>
<style>
:root{--bg:#f4f6f9;--card:#fff;--ink:#1c2733;--muted:#5c6b7a;--line:#e3e9f0;
  --brand:#0b4c8c;--brand2:#1266b5;--bluebg:#eef4fb;--mark:#ffe9a8;--fs:16px}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-size:var(--fs);line-height:1.85;
  font-family:"Microsoft YaHei","PingFang SC","Segoe UI",system-ui,sans-serif}
.topbar{height:54px;display:flex;align-items:center;gap:10px;padding:0 14px;
  background:linear-gradient(90deg,#0b3d73,#0b4c8c 60%,#1266b5);color:#fff;
  position:sticky;top:0;z-index:40}
.topbar .brand{font-size:17px;font-weight:700;white-space:nowrap}
.topbar .brand span{font-size:12.5px;color:#cfe2f5;font-weight:400;margin-left:6px}
.topbar input[type=search]{flex:1;max-width:430px;padding:7px 12px;border:1px solid #3a6ea8;
  border-radius:8px;background:rgba(255,255,255,.94);font-size:14px;color:var(--ink)}
.tbtn{padding:7px 14px;border-radius:8px;border:1px solid #3a6ea8;cursor:pointer;
  background:rgba(255,255,255,.12);color:#e8f1fa;font-size:13.5px;text-decoration:none;white-space:nowrap}
.tbtn:hover{background:rgba(255,255,255,.22)}
.layout{display:grid;grid-template-columns:290px 1fr;height:calc(100vh - 54px)}
.sidebar{overflow-y:auto;background:#f8fafc;border-right:1px solid var(--line);padding:10px 8px}
.toc-item{display:block;width:100%;text-align:left;padding:7px 10px;border:none;background:none;
  border-radius:8px;cursor:pointer;font-size:13.8px;color:var(--ink);font-family:inherit}
.toc-item:hover{background:#eef3f9}
.toc-item.on{background:var(--brand);color:#fff}
.toc-item .lawno{display:inline-block;min-width:52px;color:var(--brand2);font-weight:600;font-size:12.5px}
.toc-item.on .lawno{color:#cfe2f5}
.toc-group{font-size:11.5px;color:var(--muted);letter-spacing:1px;margin:12px 6px 4px}
main{overflow-y:auto;padding:22px 28px 60px}
.content{max-width:900px;background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:26px 32px;box-shadow:0 1px 3px rgba(15,40,80,.05)}
.content h2{margin:0 0 4px;font-size:23px;color:var(--brand)}
.content .pages{font-size:12.5px;color:var(--muted);margin-bottom:14px}
.content h3{font-size:17.5px;color:var(--brand);margin:22px 0 6px}
.content p{margin:9px 0}
.content ul{margin:8px 0;padding-left:26px}
.content li{margin:5px 0}
.content li.l2{margin-left:24px;list-style-type:"–"}
.content .fn{font-size:12.5px;color:var(--muted);margin:4px 0}
.content .pg{margin:16px 0;text-align:center}
.content .pg img{max-width:100%;border:1px solid var(--line);border-radius:8px}
.content mark{background:var(--mark);padding:0 2px;border-radius:3px}
.dnav{display:flex;gap:10px;margin-top:20px}
.dnav button{flex:1;padding:10px;border-radius:9px;border:1px solid #cbd5e1;background:#fff;
  cursor:pointer;font-size:14.5px;color:var(--ink)}
.dnav button:hover{border-color:var(--brand2);color:var(--brand2)}
.empty{padding:60px;text-align:center;color:var(--muted)}
.searchbox{position:absolute;top:56px;left:300px;right:24px;z-index:30;display:none;
  background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.14);
  max-height:55vh;overflow-y:auto;padding:8px}
.searchbox.open{display:block}
.sr{display:block;width:100%;text-align:left;padding:8px 12px;border:none;background:none;
  cursor:pointer;border-bottom:1px solid #f1f5f9;font-size:13.5px;font-family:inherit;color:var(--ink)}
.sr:hover{background:#f6f9fc}
.sr .t{color:var(--brand2);font-weight:600}
.sr .s{color:var(--muted);font-size:12.5px}
.sr mark{background:var(--mark)}
footer{margin-top:18px;font-size:12.5px;color:var(--muted);max-width:900px}
@media (max-width:900px){.layout{grid-template-columns:1fr}.sidebar{display:none}
  .searchbox{left:12px;right:12px}}
</style>
</head>
<body>
<header class="topbar">
  <div class="brand">📖 足球竞赛规则 <span>2026/27 · 简体中文</span></div>
  <input id="fSearch" type="search" placeholder="搜索规则全文…（如：越位 罚球区 手球）">
  <button class="tbtn" id="fsMinus">A－</button>
  <button class="tbtn" id="fsPlus">A＋</button>
  <a class="tbtn" href="index.html">← 判例合集</a>
  <a class="tbtn" href="stats.html">得失盘点</a>
</header>
<div class="layout">
  <nav class="sidebar" id="toc"></nav>
  <main id="main">
    <div class="content" id="content">
      <div class="empty" id="emptyBox">← 从左侧目录选择章节开始学习</div>
      <div id="secBody" style="display:none">
        <h2 id="secTitle"></h2>
        <div class="pages" id="secPages"></div>
        <div id="secHtml"></div>
      </div>
      <div class="dnav">
        <button id="prevBtn">◀ 上一节</button>
        <button id="nextBtn">下一节 ▶</button>
      </div>
      <footer>
        内容版权归国际足球协会理事会（The IFAB）所有。本页面为官方繁体中文版（2026/27单页版）的
        自动简体转换，并按大陆裁判术语做了词表替换，<b>非官方译本</b>，仅供学习参考；
        如有歧义请以 IFAB 英文原版及中国足协官方简体版本为准。
        来源：theifab.com/downloads（2026/27）。
      </footer>
    </div>
  </main>
</div>
<div class="searchbox" id="searchBox"></div>
<script>
const DATA = __DATA__;
const byId = {};
DATA.sections.forEach((s,i)=>{ byId[s.id]=s; s.idx=i; });
let cur = null;

function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}

// ---------- 目录 ----------
const groups = [["前言与总纲", s=>!s.id.startsWith("law-") && !["var","changes","revision","guide"].includes(s.id)],
  ["规则正文（第1—17章）", s=>!!s.law],
  ["附录与指引", s=>["var","changes","revision","guide"].includes(s.id)]];
document.getElementById("toc").innerHTML = groups.map(([g, pred])=>{
  const items = DATA.sections.filter(pred).map(s=>
    `<button class="toc-item" data-id="${s.id}"><span class="lawno">${s.law?("第"+s.law+"章"):"•"}</span> ${esc(s.title.replace(/^第.+章\s*/,""))}</button>`).join("");
  return `<div class="toc-group">${g}</div>`+items;
}).join("");

function select(id, scroll=true){
  const s = byId[id]; if(!s) return;
  cur = id;
  document.getElementById("emptyBox").style.display = "none";
  document.getElementById("secBody").style.display = "block";
  document.getElementById("secTitle").textContent = s.title;
  document.getElementById("secPages").textContent = "官方PDF页码: " + s.pages;
  document.getElementById("secHtml").innerHTML = s.html;
  document.getElementById("main").scrollTop = 0;
  document.querySelectorAll(".toc-item").forEach(x=>x.classList.toggle("on", x.dataset.id===id));
  history.replaceState(null, "", "#"+id);
  clearMarks();
}
function step(dir){
  if(!cur) return;
  const i = byId[cur].idx + dir;
  if(i>=0 && i<DATA.sections.length) select(DATA.sections[i].id);
}
document.getElementById("toc").addEventListener("click", e=>{
  const b = e.target.closest(".toc-item"); if(b) select(b.dataset.id);
});
document.getElementById("prevBtn").onclick = ()=>step(-1);
document.getElementById("nextBtn").onclick = ()=>step(1);

// ---------- 字号 ----------
let fs = 16;
document.getElementById("fsPlus").onclick = ()=>{ fs=Math.min(22,fs+1); document.documentElement.style.setProperty("--fs",fs+"px"); };
document.getElementById("fsMinus").onclick = ()=>{ fs=Math.max(13,fs-1); document.documentElement.style.setProperty("--fs",fs+"px"); };

// ---------- 搜索 ----------
const sb = document.getElementById("searchBox");
const fSearch = document.getElementById("fSearch");
fSearch.addEventListener("input", ()=>{
  const q = fSearch.value.trim();
  if(q.length < 2){ sb.classList.remove("open"); clearMarks(); return; }
  const hits = [];
  for (const s of DATA.sections){
    const plain = s.html.replace(/<[^>]+>/g,"");
    let i = plain.indexOf(q);
    while(i >= 0 && hits.length < 60){
      hits.push({id: s.id, title: s.title, snippet:
        (i>40?"…":"") + esc(plain.slice(Math.max(0,i-40), i+q.length+60)) + "…"});
      i = plain.indexOf(q, i+q.length);
    }
  }
  sb.innerHTML = hits.length
    ? hits.map(h=>`<button class="sr" data-id="${h.id}" data-q="${esc(q)}">
        <span class="t">${esc(h.title)}</span><br><span class="s">${h.snippet.replace(new RegExp(esc(q).replace(/[.*+?^${}()|[\]\\]/g,"\\$&"),"g"), m=>`<mark>${m}</mark>`)}</span></button>`).join("")
    : `<div style="padding:12px;color:var(--muted)">未找到「${esc(q)}」</div>`;
  sb.classList.add("open");
});
sb.addEventListener("click", e=>{
  const b = e.target.closest(".sr"); if(!b) return;
  select(b.dataset.id);
  sb.classList.remove("open");
  highlight(b.dataset.q);
});
function clearMarks(){
  document.querySelectorAll("#secHtml mark[data-h]").forEach(m=>{
    const p = m.parentNode; p.replaceChild(document.createTextNode(m.textContent), m); p.normalize();
  });
}
function highlight(q){
  clearMarks();
  if(!q) return;
  const walker = document.createTreeWalker(document.getElementById("secHtml"), NodeFilter.SHOW_TEXT);
  const nodes = [];
  while(walker.nextNode()){
    if(walker.currentNode.textContent.toLowerCase().includes(q.toLowerCase())) nodes.push(walker.currentNode);
  }
  for (const node of nodes){
    const frag = document.createDocumentFragment();
    let text = node.textContent, lower = text.toLowerCase(), ql = q.toLowerCase();
    let pos = lower.indexOf(ql);
    while(pos >= 0){
      frag.appendChild(document.createTextNode(text.slice(0, pos)));
      const mk = document.createElement("mark"); mk.dataset.h = "1";
      mk.textContent = text.slice(pos, pos+q.length);
      frag.appendChild(mk);
      text = text.slice(pos+q.length); lower = lower.slice(pos+q.length);
      pos = lower.indexOf(ql);
    }
    frag.appendChild(document.createTextNode(text));
    node.parentNode.replaceChild(frag, node);
  }
}
document.addEventListener("keydown", e=>{
  if(e.key==="Escape") sb.classList.remove("open");
});
document.addEventListener("click", e=>{
  if(!e.target.closest("#searchBox") && !e.target.closest("#fSearch")) sb.classList.remove("open");
});

// ---------- 初始化 ----------
{ const m = location.hash.match(/^#([\w-]+)$/);
  if(m && byId[m[1]]) select(m[1]);
  else select(DATA.sections[0].id, false); }
</script>
</body>
</html>
"""


def build_html_page(sections):
    data = {"season": "2026/27", "sections": sections}
    html = RULES_TEMPLATE.replace("__DATA__",
        json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    RULES_HTML.write_text(html, encoding="utf-8")
    print(f"生成 {RULES_HTML}  ({len(html.encode('utf-8'))/1024:.0f} KB)")


def main():
    doc = pymupdf.open(str(PDF))
    starts = find_law_starts(doc)
    print("章起始页:", dict(sorted(starts.items())))
    missing = [n for n in LAW_TITLES if n not in starts]
    assert not missing, f"章节起始页缺失: {missing}"

    # 图表页（人工核定的图形/信号页：文字提取必然破碎，渲染为图片才可读）
    diagrams = set(DIAGRAM_PAGES)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    for pno in sorted(diagrams):
        png = IMG_DIR / f"p{pno}.png"
        if not png.exists():
            pix = doc[pno - 1].get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6))
            pix.save(str(png))
    print(f"图表页: {sorted(diagrams)}")

    sections = []
    for sid, title, a, b in FRONT:
        nums = list(range(a, b + 1))
        sections.append({"id": sid, "title": title, "pages": f"{a}-{b}",
                         "html": build_section_html(doc, nums, diagrams)})
    order = sorted(starts.items())
    for idx, (n, start) in enumerate(order):
        end = (order[idx + 1][1] - 1) if idx + 1 < len(order) else BACK[0][2] - 1
        nums = list(range(start, end + 1))  # 图表页包含在内（以图片形式呈现）
        sections.append({"id": f"law-{n}", "title": f"第{CN_NUM[n]}章 {LAW_TITLES[n]}",
                         "law": n, "pages": f"{start}-{end}",
                         "html": build_section_html(doc, nums, diagrams)})
    for sid, title, a, b in BACK:
        nums = list(range(a, b + 1))
        sections.append({"id": sid, "title": title, "pages": f"{a}-{b}",
                         "html": build_section_html(doc, nums, diagrams)})

    OUT.write_text(json.dumps({"season": "2026/27", "sections": sections},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(s["html"]) for s in sections)
    print(f"共 {len(sections)} 节, 正文 {total/1000:.0f}K 字符 -> {OUT}")
    build_html_page(sections)


if __name__ == "__main__":
    main()
