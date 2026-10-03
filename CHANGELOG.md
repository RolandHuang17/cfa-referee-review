# Changelog

本项目所有值得注意的变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循
[语义化版本](https://semver.org/lang/zh-CN/)。仓库尚未打过 tag，首次切分发布时会
把 `Unreleased` 段落并入对应版本号并补上对比链接。

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
