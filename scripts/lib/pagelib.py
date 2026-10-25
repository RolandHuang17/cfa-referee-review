# -*- coding: utf-8 -*-
"""列表型页面（pro/conmebol/weekly/hns）公共骨架库：页头样式、esc、搜索框、过滤 JS、
年份分组与 main() 骨架。各 builder 只保留页面专属的卡片渲染与文案。

设计约束（与各页原内联实现一致）：
- 颜色/组件 token 一律来自 theme.py 注入的 data-cfa-theme，本模块不重定义 tokens；
- 过滤为纯展示层（style.display 切换），无状态、无 localStorage；
- 卡片通过 data-* 属性参与筛选：chips 值对比卡片的 filter 属性（等值/子串），
  搜索对比卡片的 data-search（小写子串）；年份组标题随组内可见性折叠。
"""
import json

from lib.theme import icon


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") \
        .replace('"', "&quot;").replace("'", "&#39;")


def search_blob(*parts):
    """卡片 data-search 属性值：拼接非空片段 → 转义 → 小写。"""
    return esc(" ".join(filter(None, parts))).lower()


def head_css(max_width=1040, compact_years=False):
    """页头/来源横幅/chips/年份标题/页脚的共享 CSS（卡片样式留在各页）。

    compact_years=True 用 weekly 的紧凑年份标题（16px），否则用 18px。"""
    year_h = (".year-h{font-family:var(--font-display);font-size:16px;"
              "margin:18px 0 10px;letter-spacing:.4px}" if compact_years else
              ".year-h{font-family:var(--font-display);font-size:18px;"
              "margin:26px 0 12px;letter-spacing:.4px}")
    return f""".page-head{{border-bottom:1px solid var(--line);background:var(--bg2)}}
.page-head .wrap{{max-width:{max_width}px;margin:0 auto;padding:22px 16px 18px}}
.page-head h1{{margin:0 0 5px;font-family:var(--font-display);font-size:23px;letter-spacing:.4px}}
.page-head .sub{{color:var(--muted);font-size:13px;line-height:1.7}}
.src-banner{{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:12px;
  padding:10px 14px;border:1px solid var(--brand);background:var(--info-bg);
  border-radius:var(--r-md);font-size:13.5px;color:var(--ink2)}}
.src-banner .ic{{color:var(--brand)}}
.src-banner a{{color:var(--brand);font-weight:600;text-decoration:none}}
.src-banner a:hover{{text-decoration:underline}}
.wrap{{max-width:{max_width}px;margin:0 auto;padding:18px 16px 60px}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 18px}}
{year_h}
.year-h small{{font-size:12px;color:var(--muted);font-weight:400;margin-left:8px}}
.empty{{display:none;text-align:center;color:var(--muted);padding:40px 0;font-size:14px}}
.foot{{margin-top:28px;font-size:12px;color:var(--faint);line-height:1.8}}"""


SEARCH_CSS = """.searchbar{margin-top:14px;position:relative;max-width:460px}
.searchbar .ic{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted)}
.searchbar input{width:100%;padding:9px 34px 9px 36px;border:1px solid var(--line);
  border-radius:999px;background:var(--card);color:var(--ink);font-size:13.5px;outline:none}
.searchbar input:focus{border-color:var(--brand)}"""


def searchbar(placeholder):
    """页头搜索框（weekly 同款）；配套 SEARCH_CSS 与 filter_js(search=True)。"""
    return (f'<div class="searchbar">{icon("search", 15)}<input id="q" type="search" '
            f'placeholder="{esc(placeholder)}" aria-label="搜索"></div>')


def filter_js(card_sel, filter_attr="data-kinds", match="substr", search=False,
              sections=None, group="ybody"):
    """生成 chips(+可选搜索) 过滤脚本。

    - card_sel: 卡片选择器（如 ".ccard"）；卡片以 style.display 显隐
    - filter_attr/match: chips 值与卡片属性的比对方式（"substr"=子串，"eq"=等值）；
      sections 模式下改为与 section 的 data-show 等值比对（filter_attr 不用）
    - search: True 时接线 #q 输入框，对卡片 data-search 做小写子串匹配
    - sections: 传 section 选择器（如 "section.show"）时按 weekly 的两级折叠：
      chips 过滤整个 section（data-show），年份标题用相邻元素折叠
    - group: 年份组定位方式，"ybody"=#ybody-<年份>（全局扁平列表），"sibling"=年份
      标题的 nextElementSibling（section 内多组年份，id 会冲突）
    页面需有 #emptyTip 空态元素。"""
    # JS 花括号密集，模板用纯字符串 + 占位符拼接，避免 f-string 转义错漏
    card = card_sel
    if match == "eq":
        match_expr = 'c.getAttribute("' + filter_attr + '")===cur'
    else:
        match_expr = '(c.getAttribute("' + filter_attr + '")||"").indexOf(cur)>=0'
    if search:
        search_expr = '&&(!q||(c.getAttribute("data-search")||"").indexOf(q)>=0)'
        wire = ('  var si=document.getElementById("q");\n'
                '  if(si)["input","search"].forEach(function(ev){\n'
                '    si.addEventListener(ev,function(){q=(si.value||"").trim().toLowerCase();apply();});\n'
                '  });\n')
        var_decl = 'var cur="all", q=""'
    else:
        search_expr = ""
        wire = ""
        var_decl = 'var cur="all"'
    if group == "sibling":
        grp_lookup = "y.nextElementSibling"
    else:
        grp_lookup = 'document.getElementById("ybody-"+y.getAttribute("data-year"))'
    if sections:
        loop = "".join([
            '    var secs=document.querySelectorAll("' + sections + '");\n',
            '    secs.forEach(function(sec){\n',
            '      var hitShow=cur==="all"||sec.getAttribute("data-show")===cur;\n',
            '      var anyS=false;\n',
            '      sec.querySelectorAll("' + card + '").forEach(function(c){\n',
            '        var hit=hitShow' + search_expr + ';\n',
            '        c.style.display=hit?"":"none";\n',
            '        if(hit)anyS=true;\n',
            '      });\n',
            '      sec.querySelectorAll(".year-h").forEach(function(y){\n',
            '        var body=y.nextElementSibling,anyY=false;\n',
            '        if(body)body.querySelectorAll("' + card + '")'
            '.forEach(function(c){if(c.style.display!=="none")anyY=true;});\n',
            '        y.style.display=anyY?"":"none";\n',
            '        if(body)body.style.display=anyY?"":"none";\n',
            '      });\n',
            '      sec.style.display=anyS?"":"none";\n',
            '      if(anyS)any=true;\n',
            '    });',
        ])
    else:
        loop = "".join([
            '    var cards=document.querySelectorAll("' + card + '");\n',
            '    var years=document.querySelectorAll(".year-h[data-year]");\n',
            '    cards.forEach(function(c){\n',
            '      var hit=(cur==="all"||' + match_expr + ')' + search_expr + ';\n',
            '      c.style.display=hit?"":"none";\n',
            '      if(hit)any=true;\n',
            '    });\n',
            '    years.forEach(function(y){\n',
            '      var grp=' + grp_lookup + ',anyY=false;\n',
            '      if(grp)grp.querySelectorAll("' + card + '")'
            '.forEach(function(c){if(c.style.display!=="none")anyY=true;});\n',
            '      y.style.display=anyY?"":"none";\n',
            '      if(grp)grp.style.display=anyY?"":"none";\n',
            '    });',
        ])
    return "".join([
        '(function(){\n',
        '  ' + var_decl + ';\n',
        '  var chips=document.querySelectorAll("[data-chips] .chip");\n',
        '  var emptyTip=document.getElementById("emptyTip");\n',
        '  function apply(){\n',
        '    var any=false;\n',
        loop + '\n',
        '    if(emptyTip)emptyTip.style.display=any?"none":"block";\n',
        '  }\n',
        '  chips.forEach(function(c){\n',
        '    c.addEventListener("click",function(){\n',
        '      chips.forEach(function(x){x.classList.remove("on");});\n',
        '      c.classList.add("on");\n',
        '      cur=c.getAttribute("data-f")||"all";\n',
        '      apply();\n',
        '    });\n',
        '  });\n',
        wire + '})();\n',
    ])


def group_by_year(items, date_of=None, fallback="待定"):
    """按年份分组：date_of 取日期字符串（默认 e["date"]），前 4 位为年份；
    年份降序，无日期者以 fallback 标签垫底。返回 [(年份, [条目]), ...]。"""
    if date_of is None:
        def date_of(e):
            return e.get("date") or ""
    groups = {}
    for e in items:
        y = (date_of(e) or "")[:4]
        groups.setdefault(y if y.isdigit() else fallback, []).append(e)
    ordered = sorted((y for y in groups if y != fallback), reverse=True)
    if fallback in groups:
        ordered.append(fallback)
    return [(y, groups[y]) for y in ordered]


def load_json_with_zh(src_path, zh_path=None):
    """列表页 main() 骨架：读源 json + 可选译文层（缺失时打 ⚠ 并返回空 dict）。"""
    data = json.loads(src_path.read_text(encoding="utf-8"))
    zh = {}
    if zh_path is not None and not zh_path.exists():
        print(f"⚠ 缺少 {zh_path.name}，页面将回退原文呈现")
    elif zh_path is not None:
        zh = json.loads(zh_path.read_text(encoding="utf-8"))
    return data, zh
