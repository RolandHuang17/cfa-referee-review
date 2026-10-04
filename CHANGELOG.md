# Changelog

本项目所有值得注意的变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循
[语义化版本](https://semver.org/lang/zh-CN/)。仓库尚未打过 tag，首次切分发布时会
把 `Unreleased` 段落并入对应版本号并补上对比链接。

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
