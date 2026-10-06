# Changelog

本项目所有值得注意的变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循
[语义化版本](https://semver.org/lang/zh-CN/)。仓库尚未打过 tag，首次切分发布时会
把 `Unreleased` 段落并入对应版本号并补上对比链接。

## 2026-10-05

### 新增（第四批：CONMEBOL 深度整合 + RFEF 视频齐备）
- **南美 VAR 判例 conmebol.html**（新页面 + `scripts/fetch_conmebol.py` + 数据 `data/conmebol.json`）：CONMEBOL《Situación de Análisis VAR》**60 案判例页**（世预赛 36 / 南美杯 20 / 优胜者杯 4）——双级抓取（Elementor 列表页 5 页 + 逐案文章页增强），每案含对阵/日期/城市/球场/情境（点球 14 / 红牌 6 / 越位 9 / 进球无效 4 等，官方西语原文保留）/分钟 + 官方 YouTube 判例视频链接（60/60，纯链接模式）。页面提供赛事与情境筛选 chips + 年份分组。解析要点：conmebol.com 属性常不带引号、正文字段各自独立成 <p>、页面头部有无关嵌入组件（取「最后一组」完整字段规避）。
- **RFEF 判例视频 169/169 全部下载完成**（约 14.9GB，verify 通过），rfef.html 全量本地播放就绪。
- 门户第十二张卡片「南美 VAR 判例」；`safe_http` 白名单新增 `hns.family`（调研用）、`www.conmebol.com`；`paths.py` 新增 `CONMEBOL_JSON`/`CONMEBOL_CACHE`；`build_all.py` 挂入 build_conmebol；测试 `PAGES` 扩至 16 页全绿。
- 深度整合结论：9 国资源中 CONMEBOL 是唯一具备逐案公开数据的（HNS 的逐镜头认定在 YouTube 视频内、苏格兰为视频节目、其余为频道型）——HNS/苏格兰/频道型保持 intl.html 导航级。

### 新增（第三批：全球导航）
- **国际评议导航 intl.html**（新页面 + `scripts/build_intl.py` + 数据 `data/intl.json`）：美国之外的 9 项官方评议资源一页导航——苏格兰 SFA《The VAR Review》（Collum 主裁-VAR 通话音频复盘）、克罗地亚 HNS《Sudačka analiza》（Layec 逐镜头认定）、乌克兰 UAF（Rizzoli 复盘）、南美 CONMEBOL《Situación de Análisis VAR》、英格兰《Match Officials: Mic'd Up》（Webb，内容最深）、墨西哥 FMF《VAR Review》（注意 VAR 音频 2025 底暂停）、土耳其 TFF《VAR Kayıtları》（休息室音频公开）、日本 J联赛《シンレポ》（VAR 室原声）、俄罗斯 RFS《Судейский разбор》。按「官方周更节目/文章」与「官方 YouTube 频道型」两组组织，每项标注语言/更新频率/内容形态与注意事项；纯导航页（rap.html 模式），不抓取条目。
- 顶栏新增第 13 个导航项「国际评议」（≤1560px 媒体查询微调字号/间距防溢出）；门户第十一张卡片；`paths.py` 新增 `INTL_JSON`；`build_all.py` 挂入 build_intl；测试 `PAGES` 扩至 15 页全绿。

### 新增（第二批：美国资源）
- **美国评议 pro.html**（新页面 + `scripts/fetch_pro.py` / `scripts/build_pro.py` + 数据 `data/pro.json`）：美国 PRO（MLS/NWSL 职业裁判机构）周更 VAR 评析**全量索引 207 篇**（Inside Video Review 英文版 75 / VAR a Fondo 西语版 41 / The Definitive Angle 文字判例 91，2025–2026 两个赛季），WordPress 分类列表页直抓（无反爬），系列/联赛/轮次从标题解析，页面提供系列与联赛筛选 chips + 年份分组，逐篇跳官方页（文章内视频受官方播放器约束，纯链接索引模式）。USSF（美国足协）视频页为 JS 渲染且完整内容在 Learning Center 免费注册墙内、无公开 YouTube 播放列表 → 页内作入口指南区（视频页/Learning Center/裁判项目）。
- 全站导航新增「美国评议」入口（门户十张卡片）；为容纳第 12 个导航项，顶栏「欧足联判例」「考题模式」缩写为「UEFA」「考题」；`safe_http` 白名单新增 `proreferees.com`；`paths.py` 新增 `PRO_JSON`/`PRO_CACHE`；`build_all.py` 挂入 build_pro；`tests/test_integrity.py` 的 `PAGES` 扩至 14 页并全绿。
- 小屏回归修复：≤1560px 隐藏顶栏导航图标的规则曾使 ≤760px（图标模式）导航变空盒，已在 760px 断点内恢复图标显示。

### 新增
- **西班牙判罚标准手册 rfef.html**（新页面 + `scripts/fetch_rfef.py` / `scripts/download_rfef_videos.py` / `scripts/build_rfef.py` + 数据 `data/rfef.json` / `data/rfef-zh.json`）：RFEF/CTA《Criterios Arbitrales》2026/27 官方手册全量整合——8 个判罚专题 / 39 个代码分组 / 134 条判罚尺度（情形+认定+判读总结+加重/减轻因素）+ 169 段官方判例视频（约 14.9GB，下载至 gitignored 的 `site/videos/rfef/`，缺失时运行时回退官方直链）。页面中文译制为主（译文层全 id 平铺匹配，构建时零缺口/零漂移告警）、页头「西语原文」开关（localStorage `cfa.rfef-es`）、判例过滤框（编号/中文/西语）、轻量版隐藏视频+官方手册横幅。解析锚定手册站自定义组件（`manual-criterion-row`/`manual-inline-video-card`）与 base64 lightbox 参数，视频文件名前缀即判例编号（MD.1.1→MD.1），表格型与视频卡型（越位正反例）两种形态共用同一锚。
- **UEFA RAP 训练包导航页 rap.html**（新页面 + `scripts/build_rap.py` / `scripts/fetch_rap.py` + 数据 `data/rap.json`）：RAP 判例内容在 Nextaur 注册墙后、旧版下载包链接多已失效，故做纯指南页——训练三步法（看片段→自己判→对官方答案，含 borderline 含义）、23 期索引按 Nextaur 在线期/下载包时期分组（含体积、状态标注、PC/MAC 多链接）、Mulppy/第三方查看器等工具区，与 uefa.html 互为导流。
- 全站导航与门户新增「RAP 训练」「RFEF 标准」入口（门户九张卡片）；`scripts/lib/safe_http.py` 白名单新增 `www.card.rfef.es`、`www.dutchreferee.com`；`scripts/lib/paths.py` 新增 `RAP_JSON`/`RFEF_JSON`/`RFEF_ZH_JSON`/`RFEF_CACHE`/`DUTCHREF_CACHE`；`build_all.py` 管线挂入 build_rap/build_rfef；`tests/test_integrity.py` 的 `PAGES` 扩至 13 页并全绿。

## 2026-10-04

### 新增
- **考题模式 quiz.html**（新页面 + `scripts/build_quiz.py` builder）：三赛季 592 道判例题 + 97 道统一尺度场景题随机出卷；练习（即时反馈）/考试（统一出分）两种模式；判例题三问制（复核结论/判罚决定/纪律处分，有答案库才出②③问），尺度场景官方 decision 矩阵多选；错题本 localStorage `cfa.quiz.wrong` 自动记入未满分题并记忆上次错选，支持收藏星标、错题重练与导出/导入 JSON。
- **考题答案库 `data/quiz-answers.json`**（新数据 + `scripts/gen_quiz_answers.py`）：从评议认定原文按句极性起草判罚决定/纪律处分答案，575 条全部人工校对（reviewed），校对工作流与回写机制见 AGENTS.md。
- **隐藏答案模式**（三赛季评议页顶栏新开关 `#btnHideAns`，localStorage `cfa.hideans`）：开启后详情只显示事件与申诉，评议认定/判定徽章/分类要点/标签隐藏，列表判定圆点隐去；「显示本题答案」逐题揭示，切题自动重隐。
- 全站导航与门户新增「考题模式」入口；`tests/test_integrity.py` 新增考题池回归基准（2024:141 / 2025:227 / 2026:224 + 尺度场景 97）。

### 修复（全面维护审计）
- **stats 三页丢失全部设计 token**：`build_stats.py` 页面模板 `<style>` 缺闭合标签，页面 CSS 把主题 `<style data-cfa-theme>` 吞进同一 raw-text 块，`:root` 规则被整条丢弃（暗色塌白、圆角/字体/顶栏高度失效）。补 `</style>`，并新增 11 页面 `<style>`/`<script>` 配平护栏防复发。
- **重跑 2025 管线会静默写坏视频路径**：`fix_issue27_merge.py` 写入的 `video_files` 缺 `2025/` 赛季前缀且断言因前缀恒真。改为从既有数据推导前缀、断言按去前缀比较；#195 的归类/判定校正只保留在 `classify_cases.py`（消除双份漂移源）。
- **impact/scores 数据泄漏未归一化队名**：`河南俱乐部彩陶坊`/`辽宁铁人楠波湾`/`延边龙鼎可喜安`/`广东广州豹` 共 6 处数据 + 3 个比分键，导致 stats 页这些队查不到队徽、与 season 页队名不一致。已修复数据并收口队名归一单点（见下）。
- **quiz 三处交互 bug**：赛季多选 chips 高亮只亮最后点击的一个；错题本 `correct` 恒为空（无法对照正确答案复盘）；「上一题」不暂存当前作答（考试模式来回查看会静默清答案记 0 分）。
- **统一尺度页深链失效**：scale.html 无任何 hash 初始化，quiz 错题本/结果页的 `scale.html#h2025-…` 链接落在 `display:none` 的赛季块上无法定位。新增 `#s2025` 页签恢复与 `#h*` 场景滚动定位，页签同步 `aria-selected`。
- **season 页切到无视频判例不停止播放**：上一判例的 `<video>` 被隐藏后继续出声，补 `stopVideo()`。
- **stats 页 fallback 球队徽章透明不可见**：内联只设 `--badge-fg/--badge-bg` 而 `.team-dot` 无背景/边框规则，改为直接设 `background/border`（与评议页一致），并删除该页对共享组件 `.team-badge` 的重定义。
- **safe_http 下载器 416 分支必抛错**：`os.replace` 之后才 `tmp.stat()`，必发 FileNotFoundError 被当失败重试、整文件重下；charset 解析遇 `charset=utf-8;` 形式报头会 LookupError（safe_http 与 fetch_uefa 两处）；移除无人使用的 `expected_size` 死参数。
- **fetch_issues.py 判活违反「thecfa.cn 没有 404」约束**：失效 URL 301 到升级维护页仍按 200 存档；对齐 enum_issues 的内容判活，缓存跳过也复检历史坏档。
- 其余：2024 足协杯半决赛轮次不再静默回退 `round=0`（保留"半决赛"原文，排序/渲染兼容）；verify_videos 重复输出、range_server 非法 `Range: bytes=-` 500、fetch_crests_online 退避注释漂移、make_impact 死代码与重复键等清理。

### 变更
- **队名归一收口单点**：新增 `scripts/lib/team_names.py`（`ALIASES`/`normalize_name`/`PARENT`），generate_teams_catalog 与三个 make_impact 脚本统一 import（各脚本私有映射删除）；build_stats 构建时兜底归一；generate_teams_catalog 加 `main()` 守卫（原 import 即重写 teams.json）。
- **影响统计口径对齐**：2025 补入足协杯（seq44 广州豹守门员红牌错误）+ 2024 补录 seq117（漏判点球+VAR未介入），2024 影响标注 53→54 例、2025 67→68 例；各 make_impact 脚本新增 OUT_OF_SCOPE 排除表与**覆盖率断言**（范围内每条 wrong 必须被标注或显式排除）；2024 第1期判例三（seq3）因原文未载明防守方无法归因，显式登记 UNATTRIBUTABLE。
- **`site/assets/` 取消 git 跟踪**：它是构建中间态（build_all 每次 rmtree+copytree 从 `assets/` 重新生成，docs/structure.md 早已说明"会被冲掉"），误跟踪让仓库 pack 体积翻倍。克隆后跑一次 `python scripts/build_all.py` 复原；CI 不受影响。
- 门户入口卡片类名 `.card`→`.ecard`（不再重定义主题共享组件）；主题注入 `<style data-cfa-theme>` 后页面数据 JSON 的 `</` 统一转义为 `<\/`（防 `</script>` 提前闭合）；topbar 默认赛季/盘点链接更新为 2026；quiz 视频两级回退补直链失败提示与 lite 切换重渲染。

### 护栏
- `tests/test_integrity.py` 新增：11 页面 `<style>`/`<script>` 标签配平；impact/scores 一致性（键⊆wrong 判例、items 属对阵双方、队名已归一化、比分键无孤儿）；stale-build 护栏（season 页 `DATA.meta` 与 stats 页 `overview.cases` 内联计数必须与 data JSON 一致）；官方页面存档按期完整性；内部链接检查跳过 query/根绝对路径。


## Unreleased

### Changed

仓库结构重组，**对生成的站点与所有构建命令零行为变化**（重组后重建 `site/` 与
`data/` 与基线逐字节一致）：

- 新增 `scripts/lib/` 共享层。路径常量收拢到 `lib/paths.py`——此前 25 个脚本各自
  复制一份 `ROOT = Path(__file__).resolve().parent.parent`。`theme.py`、
  `safe_http.py`、`crest_catalog.py`、`classify_cls_2024.py`、`classify_cls_2026.py`
  这五个「只被 import、从不直接执行」的模块搬进 `lib/`，由此确立不变量：**凡直接
  位于 `scripts/` 下的都是可执行入口脚本**。顺带删除 5 处无效的 `sys.path.insert`
  （CPython 已把脚本自身所在目录放进 `sys.path[0]`）。
- `data/` 分成「入库数据」与「本机产物」两层。`data/issues_raw/` →
  `data/issues/{2024,2025,2026}/`；新增整目录被 git 忽略的 `data/local/`，收纳规则
  PDF、抓取缓存、页面截图、日志与 3.3GB 官方统一尺度材料包。2025 赛季补齐文件名
  后缀：`impact.json` → `impact-2025.json`，`match_scores.json` →
  `match-scores-2025.json`。
- `scripts/verify_project.py` → `tests/test_integrity.py`，并由 fail-fast 改为
  fail-collecting：一次运行报告全部问题而非只报第一个，退出码仍非零以拦截 CI。
  支持 `python tests/test_integrity.py` 与 `python -m pytest tests/` 两种跑法，检查
  项完全一致。重复的队徽校验逻辑抽到 `lib/crest_catalog.validate_catalog()`，由
  构建步骤 `fetch_crests.py` 与完整性测试共用。
- `scripts/requirements-build.txt` → 仓库根 `requirements-build.txt`，删除从未被
  import 的死依赖 `markdown>=3.5`。新增 `pyproject.toml`：纯元数据、显式声明零模块
  （这是脚本集合而非可安装的库），`build` extra 动态读取 `requirements-build.txt`，
  因此 `pip install ".[build]"` 与 CI 装的是同一份清单，版本不会漂移。
- 新增 `.gitattributes`，把 EOL 与二进制处理策略显式钉死（此前依赖每台机器的
  `core.autocrlf`；同时修掉 Linux/macOS 检出拿到纯 LF `.bat` 导致 cmd.exe 处理
  `goto`/`label` 出错的隐患）。`.gitignore` 从 25 行收敛到 18 行，删除 5 条永不
  匹配的死规则，新增 `*.egg-info/` 与 `.pytest_cache/`。

### Removed

- `scripts/download_videos.py`：全库零引用，功能已被 `download_videos_parallel.py`
  （断点续传）完全取代。
- `data/review-2024.txt` 取消跟踪：本机人工复核用的判例纯文本汇编，不是构建输入。

## 1.0.0 — 2026-10-03

首个归档版本，覆盖中国足协 2024–2026 三个赛季全部 81 期裁判评议（612 条判例、
614 个官方视频）。

### Added

- **门户** `site/index.html`：六张入口卡片 + 完整版/轻量版浏览模式开关。
- **赛季判例合集** `site/season-{2024,2025,2026}.html`：三栏工作台（侧栏筛选 /
  播放列表 / 详情），按教学分类、判定结论、赛事、球队、期数、关键词叠加筛选，
  ↑↓ 键盘切换，收藏与笔记存 localStorage，`#case-<seq>` 锚点直达。
  2024：27 期 160 判例 161 视频；2025：32 期 227 判例 229 视频；2026：22 期
  225 判例 224 视频。
- **得失盘点** `site/stats-{2024,2025,2026}.html`：各队错漏判影响统计（进球/点球/
  红黄牌），双视角切换，明细链接回跳对应赛季页锚点。
- **竞赛规则** `site/rules.html`：IFAB 官方 2026-27 繁体 PDF 自动转简体（OpenCC +
  足球术语表），章节树、全文搜索、划词高亮（三色）、章节笔记、导出导入。
- **统一判罚尺度** `site/scale.html`：官方宣讲材料 2024–2026 三季 104 例场景视频 +
  判罚决定矩阵，赛季页签切换。
- **欧足联 Clear Line 判例库** `site/uefa.html`：UEFA 官方 83 例判例中文译制
  （中文为主、英文原文可切换），逐例官方视频链接；译文层独立存于
  `data/uefa-zh.json`，不污染抓取产物。
- **轻量版浏览模式**：纯文字 + 官方链接的笔记本式界面，无视频窗口，适合在线访问；
  完整版遇本地视频缺失自动回退官方直链。
- **数据管线**：`enum_issues` → `fetch_issues` → `parse_issues` → `classify_cases` →
  `make_impact_*` → `generate_teams_catalog` → 各 builder，三赛季参数化；
  `download_videos_parallel.py` 多线程断点续传下载视频。
- **队徽体系**：`data/teams.json` 111 支标准队伍目录 + 别名归一 + verified/fallback
  两级状态，人工核验成果登记在 `data/crest_overrides.json`（目录重建不丢失）。
- **安全网络层** `scripts/lib/safe_http.py`：域名白名单、强制 https、DoH 解析校验
  公网 IP、IP 钉扎；所有对外抓取统一走它。
- **离线单文件交付**：生成的页面 CSS/JS/数据全部内联，双击即用，运行时零外部
  CDN/字体/JS 依赖；GitHub Actions 自动构建并发布到 GitHub Pages。
- 设计系统 `src/theme.css`：全站唯一权威样式层（tokens + 组件 + 明暗主题），
  暖纸色编辑排版风格。
- 文档与法务：`AGENTS.md`（AI 协作开发指南）、`README.md`、`CONTRIBUTING.md`、
  `LICENSE`（MIT）、`NOTICE.md`（数据来源与版权声明）、`启动合集网页.bat`
  （Windows 一键本地服务）。
