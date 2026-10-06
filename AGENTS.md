# AGENTS.md — AI 协作开发指南

> 本文件写给在此仓库中工作的 AI 编码助手（也适用于人类新维护者）。目标是让你在 10 分钟内理解项目全貌、数据管线与所有已知的坑，直接开始有效开发。

## 项目是什么

「裁判学习一站式平台」：抓取中国足协官网 **2024+2025+2026 三个赛季全部 81 期裁判评议**（2025：32期227判例229视频；2024：27期160判例161视频；2026：赛季进行中，已收22期225判例224视频），按新裁判统一尺度教学分类重组，生成为**完全离线的静态网页**（双击 index.html 即可用，无需任何服务），附带各队得失盘点统计页（stats-2026/2025/2024.html）、官方《统一判罚尺度》宣讲页（scale.html，2024–2026 三季 104 例场景视频+判罚决定）、欧足联 Clear Line 判例库（uefa.html，UEFA 官方判例中文译制——中文为主、英文原文可切换，逐例官方视频链接）与竞赛规则 2026-27 简体版（rules.html，由 IFAB 官方繁体 PDF 自动转换，支持划词高亮与章节笔记）。

核心交付物是 `site/` 下的**十八个自包含 HTML 文件**（CSS/JS/数据全部内联）+ `site/videos/` 本地视频文件夹（按赛季分子目录）：
- `site/index.html` 门户首页（十四张入口卡片 + 浏览模式开关）
- `site/season-2026.html` / `season-2025.html` / `season-2024.html` 各赛季判例合集
- `site/stats-2026.html` / `stats-2025.html` / `stats-2024.html` 各队得失盘点
- `site/rules.html` 竞赛规则（划词高亮/章节笔记/导出导入）
- `site/scale.html` 官方统一判罚尺度宣讲（2024–2026 三季 104 例场景视频+判罚决定矩阵；2024 为第三代 EXE+XML 包，走 extract_season_2024 解析）
- `site/uefa.html` 欧足联 Clear Line 判例库（中文译制+英文原文开关+逐例官方视频链接；视频受 token 门禁不本地化，页面纯链接模式）
- `site/rap.html` UEFA RAP 判例训练包导航页（训练方法说明 + 23 期索引：Nextaur 在线期与历史下载包分区，纯指南页不收录判例内容）
- `site/rfef.html` 西班牙 CTA《Criterios Arbitrales》判罚标准手册（RFEF 官方手册中文译制 + 西语原文开关 + 本地化判例视频，缺失时回退官方直链）
- `site/conmebol.html` 南美 VAR 判例（CONMEBOL《Situación de Análisis VAR》60 案：比赛/日期/城市/球场/情境/分钟 + 官方 YouTube 判例视频链接；列表页+文章页双级抓取）
- `site/intl.html` 全球评议资源导航（4 组 23 项：官方周更节目/文章、YouTube 频道型、VAR 音频透明化、官方课程与测验；已在 weekly.html 建立索引的节目特别标注并互链；人工策展 intl.json）
- `site/pro.html` 美国 PRO 评议索引（MLS/NWSL 周更 VAR 评析全量 207 篇：Inside Video Review / VAR a Fondo / The Definitive Angle，纯链接索引）+ USSF 视频入口指南
- `site/weekly.html` 全球周更评议节目判例库（苏格兰/土耳其/日本/英格兰/墨西哥/阿根廷/俄罗斯七档官方节目的结构化期目索引 221 期：官方说明原文 + 中文译注层，逐期跳官方观看页）
- `site/ifab.html` IFAB《Laws of the Game》VAR 协议与统一尺度（官方全文中文译制：4 节 92 条款 + 12 条官方 FAQ 判例，中英原文开关）
- `site/quiz.html` 考题模式（三赛季判例 592 题 + 统一尺度场景 97 题随机出卷：判罚决定/纪律处分/复核结论作答判分，错题本 localStorage 记忆错选，支持练习/考试两种模式与错题重练）

全站内置**轻量版浏览模式**（门户开关或顶栏「轻量版」按钮切换，localStorage 记忆）：纯文字+官方链接、无视频窗口，专为纯在线访问（GitHub Pages、不想下载视频的裁判）设计的笔记本式界面；不开即为完整版（内嵌视频，离线学习用）。

数据抓取与页面生成由 Python 脚本完成，可复用于后续赛季（管线已三赛季参数化）。

## 环境

- Python 3.9+（`pyproject.toml` 的 `requires-python`；CI 锁 3.11），**零第三方依赖**（规则模块构建除外）
- Windows 优先（脚本在 Windows 上开发；`启动合集网页.bat` 仅支持 Windows，**必须存 GBK**）
- 视频不进仓库（三赛季约 30GB），clone 后运行 `python scripts/download_videos_parallel.py [赛季]` 重新下载（断点续传、可中断重跑）
- `site/assets/`（队徽+尺度海报）也不入库（构建中间态，与 `assets/` 重复）：clone 后先跑一次 `python scripts/build_all.py` 复原完整站点（纯标准库，几秒）

## 目录结构

```
├── site/                   ← 生成站点与 GitHub Pages 发布目录（勿手改）
│   ├── index.html / season-*.html / stats-*.html / rules.html / scale.html / uefa.html
│   │   （国际板块：rap / rfef / pro / intl / conmebol / weekly / ifab.html + quiz.html）
│   ├── assets/             ← 构建时从 assets/ 复制的队徽+尺度海报（gitignored；
│   │                          clone 后跑一次 build_all.py 自动复原）
│   └── videos/             ← 视频按赛季分目录（2024/2025/2026/scale，git忽略）
├── src/
│   ├── theme.css           ← 全站设计系统（唯一权威样式层：tokens+组件+明暗主题）
│   └── README.md
├── assets/crests/          ← 球队队徽 png（仅 verified 状态被页面使用）
├── data/                   ← 入库数据（本机产物一律进 data/local/，见下）
│   ├── cases-{2024,2025,2026}.json ← 核心：各赛季判例（issues + cases）
│   ├── impact-{2024,2025,2026}.json ← 错漏判影响标注（make_impact*.py 产物，勿手改）
│   ├── match-scores-{2024,2025,2026}.json ← 比分（人工查证）
│   ├── quiz-answers.json   ← 考题答案库（gen_quiz_answers.py 产物+人工校对）
│   ├── teams.json          ← 队伍统一目录（generate_teams_catalog.py 产物，勿手改）
│   ├── crest_overrides.json ← 人工核验的队徽成果（重建目录时不丢失的唯一权威源）
│   ├── crests.json         ← 兼容映射（generate_teams_catalog.py 产物）
│   ├── scale.json          ← 官方统一尺度宣讲内容（build_scale.py 从原包解码提取）
│   ├── laws.json           ← 竞赛规则章节内容（build_rules.py 产物）
│   ├── uefa.json / uefa-zh.json ← UEFA 判例抓取产物 / 中文译文层（两者不可互相覆盖）
│   ├── rap.json            ← UEFA RAP 各期索引（人工策展提交，fetch_rap.py 核对/并入新期）
│   ├── pro.json            ← 美国 PRO 评议周报索引（fetch_pro.py 产物）
│   ├── intl.json           ← 全球评议资源导航（人工策展）
│   ├── conmebol.json       ← 南美 VAR 逐案判例（fetch_conmebol.py 产物）
│   ├── rfef.json / rfef-zh.json ← 西班牙判罚手册抓取产物 / 中文译文层（不可互相覆盖）
│   ├── weekly.json / weekly-zh.json ← 周更节目期目索引 / 中文译注层（不可互相覆盖）
│   ├── ifab.json / ifab-zh.json ← IFAB VAR 协议抓取产物 / 中文全文译制层（不可互相覆盖）
│   ├── issues/{2024,2025,2026}/ ← 各期官方页面原始 HTML 存档（按赛季子目录！）
│   └── local/              ← **整目录 gitignored**：规则 PDF、抓取缓存、截图、日志、
│                             2024 官方材料包；clone 下来不存在，脚本各自 mkdir
├── scripts/                ← 可执行入口脚本（凡直接在本层的都能 python 跑）
│   └── lib/                ← **只被 import，永不直接执行**：paths.py（路径常量唯一
│                             权威源）/ theme.py / safe_http.py / crest_catalog.py /
│                             team_names.py（队名归一唯一权威源，硬约束6）/
│                             classify_cls_{2024,2026}.py
├── tests/test_integrity.py ← 完整性断言（裸跑或 pytest 皆可，fail-collecting）
├── docs/                   ← 结构说明 / 新赛季接入 / 队徽指南
├── pyproject.toml          ← 纯元数据（py-modules=[]，不打包任何模块）
├── requirements-build.txt  ← 构建依赖唯一权威源（CI 与 pyproject build extra 共用）
├── CHANGELOG.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md / LICENSE / NOTICE.md
└── .github/                ← workflows/（Pages 自动构建发布）+ Issue/PR 模板
```

## 数据管线（按序执行）

命令一律在**仓库根**执行（脚本靠 `sys.path[0]` 解析 `lib`，两种 cwd 都可用，但文档
统一用仓库根形式）：

```bash
python scripts/enum_issues.py                 # 0. (新赛季) 枚举 /cppy/ 列表页发现新期URL → 人工核对后写入两处URL表
python scripts/fetch_issues.py 2026           # 1. 抓取官方页面 → data/issues/{season}/（URL清单在脚本内 ISSUES 表，三季）
python scripts/parse_issues.py 2026           # 2. 解析 → data/cases-{season}.json（判例/结论/视频映射/自动判定）
python scripts/fix_issue27_merge.py           # 3. 拆分第27期文章内嵌的第26期补充认定（仅2025需要；必须在 classify 前跑）
python scripts/download_videos_parallel.py 2026  # 4. 下载视频 → site/videos/{season}/（断点续传，失败重跑即可）
python scripts/classify_cases.py 2026         # 5. 教学分类与结论复核（CLS_2025 内联在 classify_cases.py，
                                              #    CLS_2024 / CLS_2026 是纯数据表，分别在
                                              #    scripts/lib/classify_cls_2024.py 与 _2026.py）
python scripts/make_impact_2026.py            # 6. 错漏判影响标注（make_impact.py=2025，make_impact_2024.py=2024；
                                              #    比分人工查证后填 data/match-scores-2026.json）
python scripts/generate_teams_catalog.py      # 7. 队伍目录重建（读全部 cases-*.json + crest_overrides.json）
python scripts/fetch_crests.py                # 8. 队徽目录校验（校验器，不联网）
python scripts/fetch_laws.py                  # 9. 下载 IFAB 官方 2026-27 繁体规则 PDF → data/local/laws/
python scripts/build_rules.py                 # 10. 规则提取+繁转简+术语表 → data/laws.json + rules.html
python scripts/build_scale.py                 # 11. 统一尺度宣讲页（原包在位时重新解码提取：
                                              #     2026/2025: 仓库外 ../统一尺度宣讲原始包-{2026,2025}；
                                              #     2024: data/local/scale-2024/，第三代 XML/GBK 包走
                                              #     extract_season_2024；否则用 data/scale.json 构建 → scale.html）
python scripts/fetch_uefa.py all              # 11.5 (一次性) 抓取 UEFA Clear Line 判例库 → data/uefa.json
                                              #     ⚠ uefa.com 对高频请求 tarpit：页间隔 35-55s，可断点续抓
                                              #     （缓存 data/local/uefa-cache/，gitignored）；parse 子命令纯本地重解析
python scripts/build_uefa.py                  # 12. 生成 uefa.html（从提交的 data/uefa.json + data/uefa-zh.json
                                              #     译文层合并构建：中文为主、英文原文开关，CI 安全）
python scripts/fetch_rap.py [fetch|merge]     # 12.5 (新期发布时) 抓取 dutchreferee RAP 索引核对期数；
                                              #     merge 把新期以 status=unreviewed 并入 data/rap.json 待人工补注
python scripts/fetch_rfef.py all              # 12.6 (赛季更新时) 抓取解析西班牙判罚手册 → data/rfef.json
                                              #     （缓存 data/local/rfef-cache/；parse 子命令纯本地重解析）
python scripts/download_rfef_videos.py        # 12.7 RFEF 判例视频 → site/videos/rfef/（约 14.9GB/169 段，
                                              #     断点续传；survey=HEAD 体积普查，verify=完整性比对）
python scripts/build_rfef.py                  # 12.8 生成 rfef.html（rfef.json + rfef-zh.json 译文层合并）
python scripts/build_rap.py                   # 12.9 生成 rap.html（读 data/rap.json 纯静态指南页）
python scripts/fetch_pro.py all               # 12.10 (每周可选) 抓取 PRO 两个分类列表页 → data/pro.json
                                              #     （WordPress 无 tarpit，8+7 页；只抓列表元数据，文章内视频跳官方页）
python scripts/build_pro.py                   # 12.11 生成 pro.html（PRO 索引 + USSF 指南区）
python scripts/build_intl.py                  # 12.12 生成 intl.html（读 data/intl.json 纯静态导航页）
python scripts/fetch_conmebol.py all          # 12.13 (随赛事更新) 抓取 CONMEBOL VAR 判例 → data/conmebol.json
                                              #     （列表页 5-10 页 + 逐案文章页增强；conmebol.com 属性常不带引号）
python scripts/build_conmebol.py              # 12.14 生成 conmebol.html（判例页：赛事/情境筛选 + 年份分组）
python scripts/fetch_weekly.py [all|discover] # 12.15 (新节目接入/跟更时) 抓取全球周更评议节目 → data/weekly.json
                                              #     双通道：RSS 精确日期+官方说明；播放列表/频道检索页 ytInitialData 存量回补
                                              #     discover <channel_id> [query] 辅助探明新源（ID 核验后固化进 SOURCES）
python scripts/build_weekly.py                # 12.16 生成 weekly.html（weekly.json + weekly-zh.json 译注层）
python scripts/fetch_ifab.py [all]            # 12.17 (IFAB 更新时) 抓取 VAR protocol 页 → data/ifab.json（缓存 ifab-cache/）
python scripts/build_ifab.py                  # 12.18 生成 ifab.html（ifab.json + ifab-zh.json 全文译制层）
python scripts/build_portal.py                # 13. 生成门户 index.html
python scripts/build_page.py                  # 14. 生成 season-2026/2025/2024.html（可带赛季参数）
python scripts/build_stats.py                 # 15. 生成 stats-2026/2025/2024.html（可带赛季参数）
python scripts/verify_videos.py [赛季]        # 辅助：视频完整性校验（大小 vs 服务器 HEAD）
python scripts/serve.py [端口]                # 本地预览服务（内部以绝对路径起 range_server.py，
                                              #     支持Range，视频可拖进度条）
python tests/test_integrity.py                # 收尾：完整性断言（也可 python -m pytest tests/）
```

⚠️ 顺序要点：fix_issue27_merge 必须在 classify 之前（它拆分结构），classify 末尾含赛季特判（2025 第27期 #195 拆分校正、2026 #195 补全对阵）；漏掉任何一步都会导致统计错位。改了前面步骤后按序重跑，最后必须运行 `python scripts/build_all.py`。

规则模块构建依赖（仅 fetch/build_rules 需要，页面运行时零依赖）：
`pip install -r requirements-build.txt`（pymupdf / opencc-python-reimplemented；也可
`pip install ".[build]"`，两者读同一份清单）。
⚠ 该文件第 1 行的 `# -*- coding: utf-8 -*-` 是必需的：pip 无 BOM 时会退回 locale
编码，Windows 的 GBK 遇到中文注释会以 UnicodeDecodeError 退出码 2 失败。
新赛季更新规则版本：换 fetch_laws.py 里的 PDF URL → 重跑 fetch_laws + build_rules；术语表 GLOSSARY 在 build_rules.py 内按需增补。

## 数据 schema 速查

### cases-{season}.json
- `issues[N]`: `{no, title, date, url, expected_wrong(官方标题认定数), summary, parsed_wrong}`
- `cases[]`: `{seq(赛季内全局唯一), issue, no, comp, round, home, away, minute, desc, appeal, conclusion(评议组认定原文), video_files[](含"2026/"等赛季前缀，与video_urls一一对应), video_urls[], category(教学分类id), tags[], referee_verdict(wrong/correct/pending), var_verdict(correct/wrong/none)}`
- **referee_verdict 是逐条复核过的结论**（2024/2025 为人工复核，2026 为按同一方法论复核）；官方标题认定数与合集口径的差异见 `ISSUE_NOTES`（build_page.py 内）

### impact-{season}.json（错漏判影响统计用）
- `impacts[seq]`: `{league, round, home, away, items:[{team(受损队), type, swing, note}]}`
- type ∈ denied_goal/opp_goal_should_disallow/missed_penalty/wrong_penalty_against/missed_red_opponent/wrong_red_self/missed_yellow_opponent/wrong_yellow_self/wrong_foul_called_self/wrong_offside_self
- `swing`: 仅进球判定类错误有值（denied_goal=+1, opp_goal_should_disallow=-1），点球是机会不折算进球
- 范围：男子中超/中甲/中乙及足协杯（女超/女甲/全运会排除）；各 make_impact 脚本内有
  OUT_OF_SCOPE/UNATTRIBUTABLE 排除表 + 覆盖率断言（范围内每条 wrong 必须被标注或显式排除）

### teams.json（队伍统一目录，crest_catalog.py 消费）
- `{version, generated_from, teams: {team-NNN: {name, aliases[], slug, path, source_url, source_type, status(verified/fallback), initials, fg, bg, parent}}}`
- `status=verified` 才渲染真实队徽 `<img>`；fallback 渲染文字徽章（initials+配色）
- `parent` 表达同一俱乐部更名链（如 山西崇德荣海→西安崇德荣海）
- **由 generate_teams_catalog.py 生成，勿手改**；verified 成果登记在 crest_overrides.json（重建不丢）

### scale.json（统一尺度宣讲内容，build_scale.py 产物）
- `{year: {sections: [{key, name, groups: [{name, items: [{id, series, title, note, decision: [{label, active}], reason, video, poster, varrule?}]}]}]}}`
- decision 矩阵 chip 顺序由 DECISION_ORDER 排序；2024 的矩阵由 XML decision/level 字段合成（语义=官方 decision_N.png 图卡），`varrule` 为 VAR 介入条件（仅 2024 有）；2024 无场景海报（本机无 ffmpeg，poster 留空，模板按需输出属性）
- CI 无原包，靠提交的 scale.json 重建 scale.html——**SCALE_SOURCE_URLS 与数据必须同 commit 增删赛季**，否则 build_page KeyError

### uefa.json（欧足联 Clear Line 判例，fetch_uefa.py 产物，提交进仓库）
- `{source, source_name, fetched, groups: [{key, name_en, name_cn, intro, criteria: [{h, items[]}], items: [{id, title, caption, url(官方视频页), date}]}]}`
- 数据源为 SSR 页面内嵌的 videoplayer `data-options` JSON；criteria 为每组页面的 ✅/❌ 官方统一尺度准则分节；视频为 Akamai token 门禁 HLS，**不下载**，每例跳官方分享页（实测 X-Frame-Options: DENY，build_uefa.py 的 EMBED=False 纯链接模式）
- uefa.com 反爬：高频请求 tarpit，fetch_uefa.py 页间隔 35-55s + 完整浏览器头（**Accept-Encoding: identity 会被 tarpit，须 gzip**）+ 120s/300s 退避；CI 不跑 fetch，靠提交的 JSON 重建

### quiz-answers.json（考题答案库，gen_quiz_answers.py 产物 + 人工校对，提交进仓库）
- `{version, rLabels, cLabels, answers: {"{season}-{seq}": {r?, c?, auto, reviewed, conf?}}}`——r=判罚决定（playon/directfk/indirectfk/penalty/retake/goal_valid/goal_invalid），c=纪律处分（none/yellow/red）
- 由脚本对认定原文按句极性起草（auto=true），**人工校对后 reviewed 才为 true**；`scripts/build_quiz.py` 只对 reviewed 条目出「判罚决定/纪律处分」两问，未复核题只出「复核结论」一问
- 校对工作流：`gen_quiz_answers.py` 生成 `data/local/quiz-review/review.tsv` 全量对照表 → 人工复核写 `approved.txt`（认可）/`overrides.tsv`（修正，r/c 为 "-" 表示删除该轴）→ `gen_quiz_answers.py --apply-review` 回写；`--recheck` 只重建未 reviewed 条目，`--approve-high` 批量认可 high 条目
- 错题本键 `cfa.quiz.wrong`（quiz 页 localStorage）：`{key: {t, s, your(上次错选), correct, star, wrong, last, done}}`

### uefa-zh.json（UEFA 判例中文译制层，与 uefa.json 并存，提交进仓库）
- `{note, translated, terms{英:中译名表}, groups: {组key: {intro, criteria: [{h, items[]}]}}, items: {判例id: {title}}}`——只存译文，不存链接等英文数据
- **绝不能把译文写进 uefa.json**（fetch_uefa.py parse 会整体覆写丢失）；build_uefa.py 构建时合并：组按 key 匹配、criteria 与英文**按块序严格对齐**（块数或条数不符该组回退英文并告警）、判例按 id 匹配；未命中/多余的译文键构建时打印 ⚠ 警告
- 页面中文为主、英文为辅：默认纯中文，页头「英文原文」开关（localStorage `cfa.uefa-en`，html[data-uefa-en] 控制所有 .en 元素显隐）
- **官方新增判例的工作流**：fetch → 新 item 无译文自动英文显示（构建警告提示 id）→ 在 uefa-zh.json 补译（术语对照 terms 表 + data/cases-*.json / scale.json 足协语料，如 DOGSO=破坏明显进球得分机会、reckless=鲁莽）→ build_uefa 重建至零警告

### rfef.json（西班牙判罚手册，fetch_rfef.py 产物，提交进仓库）
- `{source, source_name, season: "2026/27", fetched, extra_topics[], sections[]}`——extra_topics 为页内「延伸栏目」纯外链（VAR 手册/术语表等）
- `sections[]{key, name_es, name_cn, url, intro_es/complexity_es/general_es, groups[]}`——前三者为栏目级判读文本
- `groups[]{code(MD/ER/OIO…), name_es, conclusion_es, notes_es[{h,items}], items[]}`——conclusion 为表后判读总结，notes 为 h3/h4 子节（punible/no punible、加重/减轻因素）
- `items[]{id(MD.1), situation_es, decision_es, decision_norm, decision_extra_es?, videos[]{url,id,file,caption_es}}`——decision_norm 归一化认定（penalty/no_penalty/red_card/yellow_card/dfk/ifk/offside_on/offside_off…）驱动徽章配色；视频文件名前缀即判例编号（MD.1.1→MD.1）
- 解析锚点：`manual-criterion-row` 行组件 + `manual-inline-video-card` 卡片 + base64 lightbox 参数提 mp4 直链；两种判例形态（表格型/视频卡型）共用文件名前缀锚

### rfef-zh.json（rfef.json 中文译文层，并存提交，绝不可互相覆写）
- `{note, translated, terms{}, decision_labels{norm:中文}, sections{key:{name,intro,complexity,general,groups{code:{name,conclusion,notes[]}}}}, items{id:{situation,extra?,caption?}}}`
- 匹配规则：栏目按 key、分组按 code、判例/视频说明按 id（与 uefa-zh 的块序对齐不同，全 id 平铺无脆弱性）；未命中回退西语并 ⚠ 警告，译文多余键也警告
- 与情形文本重复的视频说明在 zh 层省略（构建时复用情形译文，caption_same 标记）

### pro.json（美国 PRO 评议索引，fetch_pro.py 产物，提交进仓库）
- `{source, source_name, fetched, ussf{videos,learning,refereeing}, articles[]}`——ussf 为页内指南区三个入口
- `articles[]{title, url, date, series(ivr/vaf/angle), series_name, kind, league(MLS/NWSL/USL), round, lang(en/es)}`——从两个 WordPress 分类列表页解析（inside-video-review 含西语 VAR a Fondo；the-definitive-angle）；系列/联赛/轮次从标题正则提取
- v1 只抓列表元数据；文章内嵌视频跳官方页。新周报发布后重跑 fetch_pro.py 即增量（按日期去重）

### intl.json（全球评议资源导航，人工策展，提交进仓库）
- `{checked, intro_cn[], groups[{key, name_cn, desc_cn, resources[]}], related[]}`
- `resources[]{id, org, name, lang, update, form, status_cn, note_cn, links[{label,url}]}`——官方之外 9 国评议节目的人工核验入口；新节目直接补 JSON 后重跑 build_intl.py

### conmebol.json（南美 VAR 判例，fetch_conmebol.py 产物，提交进仓库）
- `{source, source_name, fetched, cases[]}`；`cases[]{title, url, date, excerpt_es, comp, comp_cn, match, fecha, ciudad, estadio, situacion_es, situacion_norm, minuto, youtube}`
- 双级抓取：Elementor 列表页（分页 /2/…/10/，data-max-page 指示）+ 每案文章页增强（字段各自独立成 <p>，全页剥标签后取最后一组完整字段；YouTube 取字段区之后首个 embed）
- situacion_norm 归一：penalty/no_penalty/red_card/offside/no_goal/ofr_penalty/other（官方西语原文保留在 situacion_es）

### weekly.json（全球周更评议节目期目索引，fetch_weekly.py 产物，提交进仓库）
- `{source, source_name, fetched, shows: {key: {name, org, lang, update, url}}, episodes[]}`
- `episodes[]{id(videoId), show(=shows 键), title, url(官方观看页), date(ISO), date_src(exact/approx), duration, views, desc(官方说明原文，≤3500 字符)}`——exact 来自 RSS，approx 由页面相对时间按抓取日近似（页面显示 ≈ 前缀）
- 双通道抓取：RSS（精确，≤15 条/源）+ 播放列表/频道检索页 ytInitialData 存量回补（新版 lockupViewModel 与旧版 renderer 双兼容；紧凑相对时间 `1mo ago` 已处理）；按 videoId 字段级增量合并，重跑只增不减
- ⚠ SOURCES 注册表的频道/播放列表 ID 已人工核验（2026-10）；`@TFF`、`@ScottishFA` 等 handle 存在撞车/空壳陷阱，**一律用频道 ID 直访**（属主以 `ytInitialPlayerResponse.videoDetails.channelId` 为准）
- ⚠ RSS 属不可信输入：parse_rss 拒绝 DTD/实体并限输入大小（防 XML 实体扩展）

### weekly-zh.json（weekly 中文译注层，并存提交，绝不可互相覆写）
- `{note, translated, shows{key:{intro}}, items{videoId:{note}}}`——id 键平铺（rfef-zh 同构，无块序脆弱性）；未译期页面回退官方原文，构建时对不上键打 ⚠
- 补译工作流：直接在 items 补 `{videoId: {note}}` → 重跑 build_weekly.py 至零警告

### ifab.json（IFAB VAR 协议，fetch_ifab.py 产物，提交进仓库）
- `{source, source_name, fetched, sections[{id(s1…), num, h, blocks[{h(英文子节标题；节首为空), items[{k(p/li), t}]}]}], faq[{id(q1…), q, a}], links[]}`
- 解析锚点：accordion h2（button+span 编号）/ h3 子节 / p+li（li 内嵌 p 整体吞并防重复）/ FAQ 的 `QuestionAndAnswer__StyledQuestion/Answer` 容器；clean() 处理块尾未闭合标签

### ifab-zh.json（ifab 中文全文译制层，并存提交，绝不可互相覆写）
- `{note, translated, terms{}, sections{id:{h, blocks{_head|[英文子节标题]: {h, items[]}}}}, faq{id:{q,a}}}`——`_head` 为裸 items 列表，命名子节为 dict；条目按块内序号 1:1 配对（数量不齐整块回退英文并 ⚠）
- 页面中文为主：默认中文，页头「英文原文」开关（localStorage `cfa.ifab-en`，html[data-ifab-en] 控制所有 .en/.zhv 显隐互换）

### rap.json（UEFA RAP 各期索引，人工策展，提交进仓库）
- `{source, checked, nextaur_url, about_cn[], howto_cn[3步], eras[], tools[], editions[]}`
- `editions[]{id, title, year, era(nextaur/download), platform, size, status_cn, links[{label,url}], note_cn}`——下载包链接时效性强，status_cn 按人工核对填写
- 新期工作流：`fetch_rap.py merge` 自动并入 status=unreviewed 的新期 → 人工核对链接/大小后改注 → `build_rap.py` 重建

### crest_overrides.json（人工队徽成果登记）
- `{标准队名: {path, source_url, source_type, status}}`；generate_teams_catalog 重建时合并

## 队徽体系（当前架构）

操作流程与目检清单见 [docs/crest-guide.md](docs/crest-guide.md)，此处只留架构要点：

- **目录制**：`data/teams.json`（111 个标准队伍，当前 verified 72 / fallback 39）+ `scripts/lib/crest_catalog.py`（normalize_team/aliases）；页面 builder 通过 `crest()` 渲染，未登记队名显示 "?" 徽章
- **两级状态**：`status=verified` 才渲染真实队徽 `<img>`；`fallback` 渲染文字徽章（initials+配色），是**设计内行为而非降级**
- **采集工具**：`fetch_crests_online.py`（中文维基词条图片，严格限本队词条防跨队误配）与 `fetch_crests_round2.py`（Commons+英文维基）；两者下载后**必须人工目检图片**再算 verified
- **校验器**：`fetch_crests.py`（build_all 里调用；verified 必须有文件+`assets/crests/` 路径前缀+source_url+source_type，校验逻辑在 `lib/crest_catalog.validate_catalog()`，与 `tests/test_integrity.py` 共用）
- **人工成果唯一权威源**：`data/crest_overrides.json`——`generate_teams_catalog.py` 重建 teams.json 时会合并它，所以手改 teams.json 会丢
- 已知坑：自动采集易采到**更名前旧徽/同名异 club**（曾采到广州富力旧徽当广州豹、永昌旧徽当沧州雄狮、省队语境采俱乐部徽），宁缺毋滥回退 fallback

## 前端架构（src/theme.css 设计系统 + 各页面 builder）

- **设计系统**：`src/theme.css` 是全站唯一权威样式层——视觉风格为暖纸色编辑排版（浅色=米白纸面，深色=暖炭色；陶土色为品牌点缀色，红/绿/黄为判定语义色；标题用衬线字栈 `--font-display`，正文用无衬线 `--font`）、共享组件（topbar/btn/chip/badge/dot/card/modal/team-badge）、SVG 图标与明暗切换。`scripts/lib/theme.py` 提供 `inject_theme()`（注入 CSS + 首帧主题脚本 + 切换脚本，localStorage 键 `cfa.theme`，默认跟随系统）与 `topbar()`（统一顶栏生成器：brand/nav/搜索槽/主题切换，season 页另有 sb_btn/help_btn）
- **builder 职责**：各页面 builder 的 `<style>` 只写页面专属布局，禁止重定义 tokens/顶栏/组件；颜色一律用 var(--token)
- **season 页布局**：顶栏 + `.workspace` 三栏 grid（侧栏筛选 276px / 播放列表 356px / 详情自适应），每列独立滚动；**全部筛选收进侧栏**（判定 chips / 我的收藏 chips / 赛事 chips / 球队列表(带徽) / 期数 6 列数字网格 / 教学分类行），`body.sb-off` 收起侧栏
- **数据以 `const DATA = {...}` 内联注入**；`bySeq` 为判例索引
- **状态对象** `state = {cat, v(判定), issue, q(搜索), sel(选中seq), vIdx(多视频序号), fav(收藏筛选), comp(赛事), team(球队)}`
- 筛选统一走 `visibleCases()` → `renderList()` → `applyFilter()`（选中项被筛掉时自动跳到第一条）
- **JS 分层契约**：逻辑层（state/baseMatch/存储/锚点/键盘/单播放器）与渲染层（render* 函数 + innerHTML 模板）分离；事件委托挂在容器 ID 上，**重写渲染层时保持容器 ID 与 `data-*` 属性契约**（data-seq/data-cat/data-v/data-comp/data-team/data-issue/data-fav/data-tag/data-i）
- **视频内存策略**：详情区只有一个 `<video>`，`select()` 时替换 src（视频路径已含赛季前缀）。**绝不要**恢复为列表内联 video 元素——几百个播放器会让浏览器内存膨胀到 4-5GB（已经踩过并修复的坑）
- **响应式断点**：season 页唯一一套 1280 / 1080 / 640。≤1080px：侧栏变抽屉（`body.sb-open`，顶栏 btnSb 切换）、列表/详情二选一（`body.detail-open`，select() 自动加）。其余页面另有自己的断点（topbar 压缩 760px、rules/scale/uefa 抽屉 900px、portal 960px），不与 season 页共用
- 收藏/笔记存 localStorage：键 `cfa2026.fav/notes`、`cfa2025.fav/notes`、`cfa2024.fav/notes`（按赛季隔离，且按 origin 隔离，file:// 与 http:// 不同源，故有导出/导入 JSON 功能）
- **quiz 页（build_quiz.py）**：客户端渲染三屏（开始/答题/结果）；题库 DATA 内联（判例+尺度场景两种题型）；判分「复核结论 1 分 + 判罚决定 1 分 + 纪律处分 1 分」（无答案库轴不出题）、尺度矩阵多选满分 2 分；错题本键 `cfa.quiz.wrong`；season 页隐藏答案模式开关 `#btnHideAns`（`cfa.hideans`，`html[data-hideans]` CSS 门控 + `.d-card.revealed` 逐题揭示，切题自动重隐）
- **轻量版模式（cfa.lite）**：全局浏览模式开关——门户分段控件（`#modeFull/#modeLite`）+ season/scale 顶栏 `#btnLite`（theme.py `_TOGGLE_JS` 统一处理：写 `cfa.lite`、切 `html[data-lite]`、派发 `cfa:lite` 事件；`_EARLY_JS` 首帧前设置防闪烁）。开启后（build_page.py）：`select()` 走 LITE 分支，无任何视频逻辑，`#srcActions` 渲染「打开官方评议页」（`issues[].url`，按期跳转）+ 每条 `video_urls` 官方直链（新标签页在线播放）；scale 页 CSS 隐藏全部场景视频 `.hvideo` 并显示官方发布页横幅（`SCALE_SOURCE_URLS` 按赛季随页签切换，官方材料为 zip 发布无逐例链接）。筛选/收藏/笔记/锚点两模式共用同一套（同一 localStorage 键，笔记本用法核心）。完整版遇本地视频 404 自动改用官方直链（`vidsMissing` 会话级直连，`ossTried` 防循环），彻底失败且未开轻量时弹 `#vfailTip` 一次性提示条（sessionStorage `cfa.vfail` 记忆关闭）
- **锚点**：`season-*.html#case-<seq>` 打开时自动选中对应判例（stats-*.html 明细链接依赖此；初始化代码必须在 applyFilter **之前**捕获 hash——`initialHashSeq`，否则会被自动选中的 replaceState 覆盖——已踩过）
- 搜索框监听 `input` 和 `search` 事件（后者是 type=search ✕ 清空按钮触发）；`esc()` 必须转义引号（用于 data-* 属性）

## 竞赛规则页（rules.html）

- 划词高亮：选中正文 → 浮动工具条选色（黄=重要/绿=已掌握/红=易错）→ 以 `{sec, quote, color, ts}` 存 localStorage `cfa2026rules.hl`；切章/刷新时按引文文本匹配重新应用（`applyHl`）；点击高亮可删除
- 章节笔记：每节一个自动保存的笔记框，存 `cfa2026rules.notes`；支持导出/导入 JSON（高亮+笔记合并去重）
- 搜索高亮用的 `mark[data-h]` 与用户高亮 `mark.hl` 是两套互不干扰的标记
- ≤900px 章节树变抽屉（`body.toc-open`，顶栏按钮切换），搜索下拉 fixed 定位（不绑侧栏宽度）

## 硬约束（违反会直接出错）

1. **离线单文件**：所有页面禁止引入任何外部 CDN/字体/JS 库；视频/队徽一律相对路径；图标用 theme.py 内联 SVG。唯一例外（用户批准）：uefa.html 无内嵌第三方资源，仅以文字+外链方式收录 UEFA 判例（视频受官方 token 门禁与 X-Frame-Options: DENY 限制，无法本地化/嵌入）；weekly.html 同为纯链接模式——七档 YouTube 官方节目受 YouTube 服务条款约束不可下载/内嵌，仅收录元数据并跳官方观看页。rfef.html 的判例视频为官方同域直链的本地化副本（site/videos/rfef/，git 忽略，约 14.9GB），仅本地学习用途、与各赛季评议视频同策略；视频缺失时运行时回退官方直链（vfb）。
2. **safe_http.py 安全模块**（`scripts/lib/safe_http.py`）：所有对公网的请求必须走它——域名白名单（`ALLOWED_HOSTS`，新数据源需显式添加）、强制 https、DoH 解析校验公网 IP（本机 TUN 代理会返回 fake-ip）、IP 钉扎连接。**不要**绕过它直接用 requests/urllib。⚠ 扩白名单只能写 `from lib import safe_http as S` + `S.ALLOWED_HOSTS |= {...}`；写成 `from lib.safe_http import ALLOWED_HOSTS` 会让 `_validate_url` 看到的仍是原集合，**白名单静默失效**
3. **thecfa.cn 没有 404**：失效 URL 一律 301 到"升级维护"页，判活必须用 `status==200` 且内容不含 /upgrade/
4. **编码**：全部 UTF-8；但 `启动合集网页.bat` 必须存为 **GBK**（cmd 解析），改它时用 `encoding="gbk"` 写入
5. **期数结构坑**：2024 第1期为"结论摘要"式文章（无标准判例结构/无视频，阵容仅在导语中，classify_cases.py 内按原文补全，判例二/三属中甲第1轮）；2025 第27期内嵌第26期补充认定（fix_issue27_merge.py）；2026 第20期判例一无"判例N:"前缀（parse_issues.py 已有无前缀首判例兜底）；2026 第17期判例九沿判例八事件无对阵行（classify_cases.py 内补全）；comp 兜底归一在 parse/builder 双处
6. **球队名归一是单点**：`scripts/lib/team_names.py` 的 `ALIASES`/`normalize_name`（赞助冠名/笔误变体 → 标准名，如 河南俱乐部彩陶坊→河南俱乐部、杭州临江吴越→杭州临平吴越）；generate_teams_catalog 与 make_impact* 都从这里取，build_stats 构建时兜底再归一一次；impact/scores 里的队名必须是归一化后名字（test_integrity 强制）；**新增 alias 只改这一处**（旧的 build_page/fetch_crests 双处 NAME_VARIANTS 已废弃）
7. **两 URL 表同步**：fetch_issues.py 的 `ISSUES` 与 parse_issues.py 的 `ISSUE_URL` 是同一套 URL 的两份拷贝，加新期必须同步
8. **expectation 断言**：`tests/test_integrity.py` 的 `EXPECTED` 是三赛季判例数/视频数/判定分布的回归护栏，改了分类或解析必须同步；`generate_teams_catalog.py` 重建会**覆盖手改**，verified 成果只能走 crest_overrides.json
9. **videooss CDN 拒绝带 Referer 的请求（403）**：`videooss.thecfa.cn` 只接受无 Referer 的请求（实测：无 Referer → 206 且支持 Range 拖进度；带任何 Referer → 403）。凡指向它的 `<video>` 或 `<a>` 必须带 `referrerpolicy="no-referrer"`（直链再加 `rel="noreferrer"`），否则轻量版直链与完整版在线回退全部失效

## 扩展任务指南

三份任务指南已拆到 `docs/`，此处只留最易踩的坑，细节以 docs 为准（避免两处漂移）：

- **接入新赛季** → [docs/add-new-season.md](docs/add-new-season.md)。管线已三赛季参数化，照 2026 先例即可。最容易漏的两处：`fetch_issues.ISSUES` 与 `parse_issues.ISSUE_URL` 是同一套 URL 的**两份拷贝**，必须同步；收尾要更新 `tests/test_integrity.py` 的 `PAGES` 与 `EXPECTED`。
- **新增/修正队徽** → [docs/crest-guide.md](docs/crest-guide.md)。核心红线：自动采集到的图**必须人工目检**（更名前旧徽、赞助商模板、国旗、他队徽是反复踩过的坑），宁缺毋滥回退 fallback 文字徽章；成果只登记进 `crest_overrides.json`（`teams.json` 会被脚本覆盖）。
- **仓库结构与路径契约** → [docs/structure.md](docs/structure.md)。哪些目录被写死在数据或断言里、为什么 `site/` 必须自包含、`data/local/` 里放什么。

### 新增统计维度
- 在 `build_stats.py` 的 `team_stats()`/`build_matches()` 扩展；数据源缺失时页面必须优雅降级（显示"待补"），参考比分缺失的处理

## AI 开发自验清单

改动后依次验证（命令一律在仓库根执行）：
- [ ] `python scripts/build_portal.py && python scripts/build_page.py && python scripts/build_stats.py && python scripts/build_rules.py` 无报错
- [ ] `python tests/test_integrity.py` 通过（18页面/三赛季数据/impact一致性/页面-数据同步/考题池基准/weekly+ifab 数据层/离线资源/内部链接/队徽目录）；或 `python -m pytest tests/ -q`
- [ ] season 页隐藏答案模式：开关持久化、详情答案区隐藏、逐题揭示后切题重隐、列表圆点不泄底、与轻量版叠加正常
- [ ] quiz.html：开始屏筛选叠加、练习即时反馈、考试交卷出分、判例三问与尺度多选两种题型、错题本记忆/收藏/重练/导出导入、`#case-N` 锚点回跳、明暗主题
- [ ] 浏览器打开 index.html：门户十四张卡片数字正确、浏览模式分段开关与说明文字正确
- [ ] season-2026.html：225 行列表、详情视频可播放可拖进度、筛选（分类/判定/期数/搜索/收藏视图）相互叠加、↑↓键盘切换、统计与说明弹层、`#case-183` 锚点直达、收藏+笔记刷新后仍在、明暗切换
- [ ] season-2024.html：160 行列表、视频路径 videos/2024/ 可播放
- [ ] 轻量版回归：门户选轻量 → season 详情无视频窗口且有「官方评议页/官方视频」链接、`#case-194`（无视频判例）只显示评议页链接、笔记两模式共用、scale 页视频隐藏+官方发布页横幅、uefa 页 lite 下隐藏 iframe（如有）只留链接、顶栏「轻量版」随时切回完整版、刷新记忆保持
- [ ] 完整版在线回退：临时改名 site/videos 后刷新 → 自动改用官方直链播放并出提示条；恢复原名后 → 本地播放
- [ ] stats-2026/2025/2024.html：双视角切换、联赛筛选（含足协杯）、缺失比分显示"待补"、明细链接跳对应赛季页
- [ ] rules.html：划词出现高亮工具条、三种颜色可标可删、章节笔记自动保存、导出导入
- [ ] rfef.html：栏目导航/判例卡片/认定徽章渲染正确、西语原文开关持久化、过滤框（编号/中文/西语）可用、本地视频可播、临时删一个视频文件刷新 → 该视频回退官方直链、lite 模式视频隐藏+官方手册横幅、明暗主题
- [ ] rap.html：各期索引与外链、训练三步说明、era 分组、明暗主题
- [ ] pro.html：筛选 chips（系列/联赛）过滤正常、年份分组与 207 篇索引、官方页外链、USSF 指南区、明暗主题
- [ ] conmebol.html：赛事/情境筛选 chips、年份分组 60 案、官方分析+判例视频双链接、明暗主题
- [ ] weekly.html：节目筛选 chips、搜索（标题/译注/原文说明）、年份分组、≈ 近似日期标记、译注与原文折叠、官方观看直链 rel 属性、明暗主题
- [ ] ifab.html：章节导航跳转、中英原文开关（刷新持久化）、FAQ 折叠、配套材料区内外链、明暗主题
- [ ] intl.html：四组 23 资源卡（语言/频率/形态 + 注意事项 + 官方外链）、站内关联区、明暗主题
- [ ] `python scripts/verify_videos.py [赛季]`（如动过视频/数据）
- [ ] 统计口径：2026 错漏判 95、支持原判 121、不予认定 9；2025 错漏判 82、支持 138、不予 7；2024 错漏判 60、支持 99、不予 1（与 cases-*.json 一致）

## 已知不足（欢迎改进）

- 2026 赛季进行中：持续跑 fetch→parse→classify→impact 增量更新；影响统计的 79 场比分已核 19 场（确定得失球场次优先），其余"待补"；2024 第1期判例三（seq3）因原文未载明对阵与防守方无法归因受损队，未纳入影响统计（make_impact_2024.py UNATTRIBUTABLE 有注）
- weekly.html 的中文译注层目前覆盖节目简介与各节目近期期目，其余回退官方原文说明（按 weekly-zh 增量补译）；英格兰《Mic'd Up》因官方发布形态分散（Sky 频道内短片、无完整播放列表）仅收录 3 期；YouTube 存量回补依赖页面 ytInitialData 结构，若其变更则仅影响回补通道（RSS 主通道不受影响）；ifab-zh.json 为 2026-10 首译，欢迎对照官方英文原文修订
- 111 支标准队伍中 39 支无可靠来源队徽（历史队/女足/全运会省队为主），显示文字徽章；人工补录已于 2026-10 止步（2026 在册男足仅余山西崇德荣海一支），维基体系与懂球帝（DoH 解析失败被 safe_http 拦截）之外的自动源已穷尽
- 官方标题认定数与合集口径存在差异（漏判黄牌/低级别联赛/本轮中超口径），已在页面"说明"弹层按期注释（ISSUE_NOTES）
- 2026 判例的判定与影响标注为按同一方法论复核（非官方逐条人工背书），把握度低的判 pending 并注释
- 收藏/笔记仅存浏览器本地，无云同步（导出/导入 JSON 作为迁移方案）
- 轻量版直链与完整版在线回退依赖官方 videooss CDN 现行策略（无 Referer 即可播，见硬约束 9）；若官方收紧防盗链，在线直播路径失效，页面会降级为提示条引导切换轻量版/官方文章页观看
- rfef.html 的 RFEF 判例视频约 14.9GB（169 段官方直链副本，download_rfef_videos.py 断点续传）；译文层 rfef-zh.json 为 2026-10 首译，欢迎对照西语原文修订
- rap.json 的下载包时期链接时效性强（WeTransfer 数周即过期，「链接可能已失效」为常态）；UEFA 发布新 RAP 后跑 fetch_rap.py merge 并人工补注
