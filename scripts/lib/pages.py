# -*- coding: utf-8 -*-
"""全站页面清单唯一权威源：文件名 + 标题 + 中文描述（SEO meta 用）。

消费方：tests/test_integrity.py（页面存在性/自包含断言）、build_seo.py
（sitemap.xml / robots.txt）、build_search.py（全站搜索收录范围）。
新增页面只改这里一处，测试与发现层自动跟进——不要在任何消费方再复制文件清单。

title/desc 在批次化改造中由 lib/seo.py 注入各页 <head>（meta/og/canonical）。
priority/changefreq 仅供 sitemap；season 进行中的赛季 weekly，已收尾赛季 monthly。
"""

PAGES = [
    {
        "file": "index.html",
        "title": "裁判学习一站式平台",
        "desc": "中国足协裁判评议 2024–2026 三赛季 81 期全量判例合集：视频、教学分类、"
        "各队得失盘点、统一判罚尺度与竞赛规则，完全离线可用。",
        "priority": "1.0",
        "changefreq": "weekly",
    },
    {
        "file": "season-2026.html",
        "title": "2026 赛季裁判评议合集",
        "desc": "2026 赛季中国足协裁判评议逐期判例：视频复盘、申诉意见与评议组认定原文，"
        "按统一尺度教学分类重组，支持筛选/收藏/笔记。",
        "priority": "0.9",
        "changefreq": "weekly",
    },
    {
        "file": "season-2025.html",
        "title": "2025 赛季裁判评议合集",
        "desc": "2025 赛季中国足协裁判评议 32 期 227 判例全量合集：视频复盘、认定原文与"
        "教学分类，支持筛选/收藏/笔记。",
        "priority": "0.8",
        "changefreq": "monthly",
    },
    {
        "file": "season-2024.html",
        "title": "2024 赛季裁判评议合集",
        "desc": "2024 赛季中国足协裁判评议 27 期 160 判例全量合集：视频复盘、认定原文与"
        "教学分类，支持筛选/收藏/笔记。",
        "priority": "0.8",
        "changefreq": "monthly",
    },
    {
        "file": "stats-2026.html",
        "title": "2026 各队得失盘点",
        "desc": "2026 赛季官方认定错漏判的各队得失统计：受损/获益双视角、比分修正比对与"
        "逐条明细回链。",
        "priority": "0.7",
        "changefreq": "weekly",
    },
    {
        "file": "stats-2025.html",
        "title": "2025 各队得失盘点",
        "desc": "2025 赛季官方认定错漏判的各队得失统计：受损/获益双视角、比分修正比对与"
        "逐条明细回链。",
        "priority": "0.6",
        "changefreq": "monthly",
    },
    {
        "file": "stats-2024.html",
        "title": "2024 各队得失盘点",
        "desc": "2024 赛季官方认定错漏判的各队得失统计：受损/获益双视角、比分修正比对与"
        "逐条明细回链。",
        "priority": "0.6",
        "changefreq": "monthly",
    },
    {
        "file": "rules.html",
        "title": "足球竞赛规则 2026/27 简体中文版",
        "desc": "IFAB 官方《足球竞赛规则 2026/27》简体中文版：全文搜索、划词高亮、"
        "章节笔记与阅读进度。",
        "priority": "0.9",
        "changefreq": "yearly",
    },
    {
        "file": "scale.html",
        "title": "统一判罚尺度宣讲合集",
        "desc": "中国足协官方《统一判罚尺度》宣讲 2024–2026 三季 104 例典型场景："
        "官方视频与判罚决定对照矩阵。",
        "priority": "0.9",
        "changefreq": "monthly",
    },
    {
        "file": "uefa.html",
        "title": "欧足联 Clear Line 判例库（中文译制）",
        "desc": "UEFA 官方 Clear Line 判例库中文译制：83 例真实比赛判例按场景分组，"
        "官方解释与视频页链接，可切回英文原文。",
        "priority": "0.7",
        "changefreq": "monthly",
    },
    {
        "file": "rap.html",
        "title": "UEFA RAP 判例训练包导航",
        "desc": "UEFA Referee Assistance Programme 各期训练包索引与训练方法说明，"
        "Nextaur 在线期与历史下载包分区。",
        "priority": "0.5",
        "changefreq": "monthly",
    },
    {
        "file": "rfef.html",
        "title": "西班牙 RFEF 判罚标准手册（中文译制）",
        "desc": "西班牙足协《Criterios Arbitrales》判罚手册中文译制：判例视频、"
        "认定徽章与判读总结，西语原文可切换。",
        "priority": "0.7",
        "changefreq": "monthly",
    },
    {
        "file": "pro.html",
        "title": "美国 PRO 评议索引",
        "desc": "美国职业裁判员组织 PRO 的 MLS/NWSL 周更 VAR 评析全量索引："
        "Inside Video Review / VAR a Fondo / The Definitive Angle。",
        "priority": "0.6",
        "changefreq": "weekly",
    },
    {
        "file": "intl.html",
        "title": "全球评议资源导航",
        "desc": "全球官方裁判评议资源一站式导航：周更节目、VAR 音频透明化项目、"
        "官方课程与测验等 23 项入口。",
        "priority": "0.5",
        "changefreq": "monthly",
    },
    {
        "file": "conmebol.html",
        "title": "南美 CONMEBOL VAR 判例",
        "desc": "南美足联《Situación de Análisis VAR》60 案：比赛情境、官方分析"
        "与判例视频链接，情境中文译制。",
        "priority": "0.6",
        "changefreq": "monthly",
    },
    {
        "file": "weekly.html",
        "title": "全球周更评议节目库",
        "desc": "苏格兰/土耳其/日本/英格兰/墨西哥/阿根廷/俄罗斯七档官方周更评议节目"
        "与乌克兰 UAF 文章源的结构化期目索引，附中文译注。",
        "priority": "0.6",
        "changefreq": "weekly",
    },
    {
        "file": "ifab.html",
        "title": "IFAB VAR 协议中文全译",
        "desc": "IFAB《Laws of the Game》VAR 协议与统一尺度官方全文中文译制："
        "4 节 92 条款、12 条官方 FAQ 与 8 篇配套协议，中英对照。",
        "priority": "0.8",
        "changefreq": "yearly",
    },
    {
        "file": "hns.html",
        "title": "克罗地亚 HNS 逐轮判例分析（中文全译）",
        "desc": "克罗地亚足协《Sudačka analiza》逐轮判例分析：Layec 署名逐判例认定"
        "与官方视频直链，判例级中文全译。",
        "priority": "0.6",
        "changefreq": "weekly",
    },
    {
        "file": "quiz.html",
        "title": "裁判考题模式",
        "desc": "三赛季判例 592 题 + 统一尺度场景 97 题 + IFAB VAR 协议 12 题随机出卷："
        "判罚决定/纪律处分/复核结论作答判分，错题本与间隔复习。",
        "priority": "0.8",
        "changefreq": "weekly",
    },
]

# 仅文件名序列（测试断言/sitemap 生成用）
PAGE_FILES = [p["file"] for p in PAGES]

# 季节进行中的赛季（sitemap changefreq 与 feed 取「最新期」的依据）
ACTIVE_SEASON = "2026"


def by_file(name: str) -> dict:
    for p in PAGES:
        if p["file"] == name:
            return p
    raise KeyError(name)
