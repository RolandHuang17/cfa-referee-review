# -*- coding: utf-8 -*-
"""共享视觉系统:设计 tokens/组件 CSS + 统一顶栏 + 明暗主题切换,注入全部生成页。
页面专属布局写在各 builder 的 <style>;颜色/顶栏/按钮等一律走本模块。"""
from lib.paths import THEME_CSS

THEME = THEME_CSS.read_text(encoding="utf-8")

# feather 风格描边图标 (stroke=currentColor, 24 viewBox)
_E = {
    "home": '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "film": '<rect x="2" y="2" width="20" height="20" rx="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/>',
    "chart": '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    "book": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    "shield": '<path d="M12 2l8 3.5V12c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10V5.5z"/><path d="M9 12l2 2 4-4"/>',
    "sun": '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
    "moon": '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    "search": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "star-f": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "menu": '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
    "x": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "chev-d": '<polyline points="6 9 12 15 18 9"/>',
    "up": '<line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>',
    "down": '<line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>',
    "left": '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    "right": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    "note": '<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>',
    "help": '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    "filter": '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
    "play": '<polygon points="6 3 20 12 6 21 6 3"/>',
    "external": '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>',
    "sliders": '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
    "eye-off": '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>',
    "quiz": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
}
_FILLED = {"star-f"}


def icon(name, size=15):
    filled = name in _FILLED
    fill = ' fill="currentColor" stroke="none"' if filled else ' fill="none" stroke="currentColor"'
    return (f'<svg class="ic{" f" if filled else ""}" width="{size}" height="{size}" '
            f'viewBox="0 0 24 24"{fill} stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_E[name]}</svg>')


def js_icons():
    """给页面 JS 渲染函数用的图标常量 (const IC = {...})。"""
    import json
    return json.dumps({k: icon(k, 13) for k in ("star", "star-f", "note", "up", "down", "search",
                                                "help", "x", "left", "right", "play", "upload",
                                                "download", "chev-d", "menu", "external",
                                                "eye-off", "quiz", "check")},
                      ensure_ascii=False, separators=(",", ":"))


def topbar(active="", right="", stats="stats-2026.html", brand_sub="", seasons=("2026", "2025", "2024"),
           sb_btn=False, help_btn=False, lite_btn=False):
    """统一顶栏。active=当前页 href;right=页面临有控件(搜索框等)HTML;
    sb_btn=侧栏开关(#btnSb, season 页用);help_btn=说明按钮(#btnHelp, season 页用);
    lite_btn=轻量版开关(#btnLite, season/scale 页用;门户用自带的分段控件)。"""
    items = [("index.html", "首页", "home")]
    for s in seasons:
        items.append((f"season-{s}.html", f"{s}评议", "film"))
    items += [(stats, "得失盘点", "chart"), ("rules.html", "竞赛规则", "book"),
              ("scale.html", "统一尺度", "sliders"), ("uefa.html", "欧足联判例", "play"),
              ("quiz.html", "考题模式", "quiz")]
    nav = ""
    for href, label, ic in items:
        cur = ' class="tbtn cur" aria-current="page"' if href == active else ' class="tbtn"'
        nav += f'<a{cur} href="{href}">{icon(ic)}<span>{label}</span></a>'
    sb = (f'<button class="tbtn" id="btnSb" title="收起/展开筛选侧栏" aria-label="切换筛选侧栏">'
          f'{icon("menu")}</button>') if sb_btn else ""
    lite_b = ('<button class="tbtn" id="btnLite" title="切换轻量版：纯文字+官方链接（无视频窗口），适合在线浏览" '
              'aria-pressed="false">' + icon("book") + '<span>轻量版</span></button>') if lite_btn else ""
    help_b = (f'<button class="tbtn" id="btnHelp" title="使用说明与统计口径">'
              f'{icon("help")}<span>说明</span></button>') if help_btn else ""
    theme_btn = ('<button class="tbtn" id="btnTheme" title="切换明暗主题" aria-label="切换明暗主题">'
                 '<span class="when-dark">' + icon("sun") + '</span>'
                 '<span class="when-light">' + icon("moon") + '</span></button>')
    sub = f'<span class="brand-sub">{brand_sub}</span>' if brand_sub else ""
    return (f'<header class="topbar">{sb}'
            f'<a class="brand" href="index.html">{icon("shield", 19)}<b>裁判学习平台</b>{sub}</a>'
            f'<nav class="nav" aria-label="站点导航">{nav}</nav>'
            f'<div class="top-right">{right}{lite_b}{help_b}{theme_btn}</div></header>')


# 首帧前设置主题与轻量版/隐藏答案标记,避免明暗闪跳/布局闪跳
_EARLY_JS = ("<script>try{var t=localStorage.getItem('cfa.theme');"
             "if(t!=='light'&&t!=='dark')t=matchMedia('(prefers-color-scheme: light)').matches?'light':'dark';"
             "document.documentElement.dataset.theme=t;"
             "if(localStorage.getItem('cfa.lite')==='1')document.documentElement.dataset.lite='1';"
             "if(localStorage.getItem('cfa.hideans')==='1')document.documentElement.dataset.hideans='1'"
             "}catch(e){}</script>")
# 主题/轻量版切换按钮的全局点击处理(所有页面通用;#btnLite 切换后派发 cfa:lite 事件供页面重渲染)
_TOGGLE_JS = ("<script>document.addEventListener('click',function(e){"
              "var b=e.target.closest&&e.target.closest('#btnTheme');if(!b)return;"
              "var r=document.documentElement,t=r.dataset.theme==='light'?'dark':'light';"
              "r.dataset.theme=t;try{localStorage.setItem('cfa.theme',t)}catch(_){}});"
              "document.addEventListener('click',function(e){"
              "var b=e.target.closest&&e.target.closest('#btnLite');if(!b)return;"
              "var r=document.documentElement,on=r.dataset.lite!=='1';"
              "if(on)r.dataset.lite='1';else r.removeAttribute('data-lite');"
              "b.setAttribute('aria-pressed',on?'true':'false');"
              "try{localStorage.setItem('cfa.lite',on?'1':'0')}catch(_){}"
              "try{document.dispatchEvent(new CustomEvent('cfa:lite',{detail:{on:on}}))}catch(_){}});"
              "(function(){var bl=document.getElementById('btnLite');if(bl)bl.setAttribute('aria-pressed',"
              "document.documentElement.dataset.lite==='1'?'true':'false');})();</script>")


def inject_theme(html):
    html = html.replace("</head>", f"<style data-cfa-theme>\n{THEME}\n</style>{_EARLY_JS}</head>", 1)
    return html.replace("</body>", f"{_TOGGLE_JS}</body>", 1)
