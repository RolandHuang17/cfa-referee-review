# AGENTS.md — AI 协作开发指南

> 本文件写给在此仓库中工作的 AI 编码助手（也适用于人类新维护者）。目标是让你在 10 分钟内理解项目全貌、数据管线与所有已知的坑，直接开始有效开发。

## 项目是什么

「裁判学习一站式平台」：抓取中国足协官网 **2024+2025+2026 三个赛季全部 81 期裁判评议**（2025：32期227判例229视频；2024：27期160判例161视频；2026：赛季进行中，已收22期225判例224视频），按新裁判统一尺度教学分类重组，生成为**完全离线的静态网页**（双击 index.html 即可用，无需任何服务），附带各队得失盘点统计页（stats-2026/2025/2024.html）与竞赛规则 2026-27 简体版（rules.html，由 IFAB 官方繁体 PDF 自动转换，支持划词高亮与章节笔记）。

核心交付物是 `site/` 下的**八个自包含 HTML 文件**（CSS/JS/数据全部内联）+ `site/videos/` 本地视频文件夹（按赛季分子目录）：
- `site/index.html` 门户首页（四张赛季/规则入口卡片）
- `site/season-2026.html` / `season-2025.html` / `season-2024.html` 各赛季判例合集
- `site/stats-2026.html` / `stats-2025.html` / `stats-2024.html` 各队得失盘点
- `site/rules.html` 竞赛规则（划词高亮/章节笔记/导出导入）

数据抓取与页面生成由 Python 脚本完成，可复用于后续赛季（管线已三赛季参数化）。

## 环境

- Python 3.8+，**零第三方依赖**（规则模块构建除外）
- Windows 优先（脚本在 Windows 上开发；`启动合集网页.bat` 仅支持 Windows，**必须存 GBK**）
- 视频不进仓库（三赛季约 30GB），clone 后运行 `python scripts/download_videos_parallel.py [赛季]` 重新下载（断点续传、可中断重跑）

## 目录结构

```
├── site/                   ← 生成站点与 GitHub Pages 发布目录（勿手改）
│   ├── index.html / season-*.html / stats-*.html / rules.html
│   └── videos/             ← 视频按赛季分目录（git忽略）
├── src/
│   ├── theme.css           ← 全站设计系统（唯一权威样式层：tokens+组件+明暗主题）
│   └── README.md
├── assets/crests/          ← 球队队徽 png（仅 verified 状态被页面使用）
├── data/
│   ├── cases-2026/2025/2024.json ← 核心：各赛季判例（issues + cases）
│   ├── impact-2026.json / impact.json(2025) / impact-2024.json ← 错漏判影响标注
│   ├── match-scores-2026.json / match_scores.json / match-scores-2024.json ← 比分（人工查证）
│   ├── teams.json          ← 队伍统一目录（generate_teams_catalog.py 产物，勿手改）
│   ├── crest_overrides.json ← 人工核验的队徽成果（重建目录时不丢失的唯一权威源）
│   ├── crests.json         ← 兼容映射（generate_teams_catalog.py 产物）
│   ├── laws.json           ← 竞赛规则章节内容（build_rules.py 产物）
│   ├── issues_raw/{2024,2025,2026}/ ← 各期官方页面原始 HTML 存档（按赛季子目录！）
│   └── review-*.txt        ← 判例纯文本汇编（可再生成）
├── scripts/                ← 全部管线脚本（见下）
├── CONTRIBUTING.md / LICENSE / NOTICE.md
└── .github/workflows/      ← GitHub Pages 自动构建发布
```

## 数据管线（按序执行）

```bash
cd scripts
python enum_issues.py                 # 0. (新赛季) 枚举 /cppy/ 列表页发现新期URL → 人工核对后写入两处URL表
python fetch_issues.py 2026           # 1. 抓取官方页面 → data/issues_raw/{season}/（URL清单在脚本内 ISSUES 表，三季）
python parse_issues.py 2026           # 2. 解析 → data/cases-{season}.json（判例/结论/视频映射/自动判定）
python fix_issue27_merge.py           # 3. 拆分第27期文章内嵌的第26期补充认定（仅2025需要；必须在 classify 前跑）
python download_videos_parallel.py 2026  # 4. 下载视频 → site/videos/{season}/（断点续传，失败重跑即可）
python classify_cases.py 2026         # 5. 教学分类与结论复核（CLS_2026/CLS_2025/CLS_2024 分别在
                                      #    classify_cls_2026.py / classify_cases.py / classify_cls_2024.py）
python make_impact_2026.py            # 6. 错漏判影响标注（make_impact.py=2025，make_impact_2024.py=2024；
                                      #    比分人工查证后填 data/match-scores-2026.json）
python generate_teams_catalog.py      # 7. 队伍目录重建（读全部 cases-*.json + crest_overrides.json）
python fetch_crests.py                # 8. 队徽目录校验（校验器，不联网）
python fetch_laws.py                  # 9. 下载 IFAB 官方 2026-27 繁体规则 PDF → data/laws_raw/
python build_rules.py                 # 10. 规则提取+繁转简+术语表 → data/laws.json + rules.html
python build_portal.py                # 11. 生成门户 index.html
python build_page.py                  # 12. 生成 season-2026/2025/2024.html（可带赛季参数）
python build_stats.py                 # 13. 生成 stats-2026/2025/2024.html（可带赛季参数）
python verify_videos.py [赛季]        # 辅助：视频完整性校验（大小 vs 服务器 HEAD）
python range_server.py [端口]         # 本地预览服务（支持Range，视频可拖进度条）
```

⚠️ 顺序要点：fix_issue27_merge 必须在 classify 之前（它拆分结构），classify 末尾含赛季特判（2025 第27期 #195 拆分校正、2026 #195 补全对阵）；漏掉任何一步都会导致统计错位。改了前面步骤后按序重跑，最后必须运行 `python scripts/build_all.py`。

规则模块构建依赖（仅 fetch/build_rules 需要，页面运行时零依赖）：
`pip install -r scripts/requirements-build.txt`（pymupdf / opencc-python-reimplemented / markdown）。
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
- 范围：仅男子中超/中甲/中乙（女超/女甲/全运会排除）

### teams.json（队伍统一目录，crest_catalog.py 消费）
- `{version, generated_from, teams: {team-NNN: {name, aliases[], slug, path, source_url, source_type, status(verified/fallback), initials, fg, bg, parent}}}`
- `status=verified` 才渲染真实队徽 `<img>`；fallback 渲染文字徽章（initials+配色）
- `parent` 表达同一俱乐部更名链（如 山西崇德荣海→西安崇德荣海）
- **由 generate_teams_catalog.py 生成，勿手改**；verified 成果登记在 crest_overrides.json（重建不丢）

### crest_overrides.json（人工队徽成果登记）
- `{标准队名: {path, source_url, source_type, status}}`；generate_teams_catalog 重建时合并

## 队徽体系（当前架构）

- **目录制**：`data/teams.json`（111 个标准队伍）+ `scripts/crest_catalog.py`（normalize_team/aliases）；页面 builder 通过 `crest()` 渲染，未登记队名显示 "?" 徽章
- **采集工具**：`fetch_crests_online.py`（中文维基词条图片，严格限本队词条防跨队误配）与 `fetch_crests_round2.py`（Commons+英文维基）；两者下载后**必须人工目检图片**再算 verified
- **校验器**：`fetch_crests.py`（build_all 里调用；verified 必须有文件+source_url+source_type）
- **人工补录路径**：下载 png 到 `assets/crests/{slug}.png` → 在 `data/crest_overrides.json` 登记（含 source_url/source_type）→ 重跑 generate_teams_catalog
- 已知坑：自动采集易采到**更名前旧徽/同名异 club**（曾采到广州富力旧徽当广州豹、永昌旧徽当沧州雄狮、省队语境采俱乐部徽），宁缺毋滥回退 fallback

## 前端架构（src/theme.css 设计系统 + 四个 builder）

- **设计系统**：`src/theme.css` 是全站唯一权威样式层——design tokens（深色默认，`[data-theme="light"]` 浅色翻转；品牌蓝 + 红/绿/黄判定语义色）、共享组件（topbar/btn/chip/badge/dot/card/modal/team-badge）、SVG 图标与明暗切换。`scripts/theme.py` 提供 `inject_theme()`（注入 CSS + 首帧主题脚本 + 切换脚本，localStorage 键 `cfa.theme`，默认跟随系统）与 `topbar()`（统一顶栏生成器：brand/nav/搜索槽/主题切换，season 页另有 sb_btn/help_btn）
- **builder 职责**：四个 builder 的 `<style>` 只写页面专属布局，禁止重定义 tokens/顶栏/组件；颜色一律用 var(--token)
- **season 页布局**：顶栏 + `.workspace` 三栏 grid（侧栏筛选 276px / 播放列表 356px / 详情自适应），每列独立滚动；**全部筛选收进侧栏**（判定 chips / 我的收藏 chips / 赛事 chips / 球队列表(带徽) / 期数 6 列数字网格 / 教学分类行），`body.sb-off` 收起侧栏
- **数据以 `const DATA = {...}` 内联注入**；`bySeq` 为判例索引
- **状态对象** `state = {cat, v(判定), issue, q(搜索), sel(选中seq), vIdx(多视频序号), fav(收藏筛选), comp(赛事), team(球队)}`
- 筛选统一走 `visibleCases()` → `renderList()` → `applyFilter()`（选中项被筛掉时自动跳到第一条）
- **JS 分层契约**：逻辑层（state/baseMatch/存储/锚点/键盘/单播放器）与渲染层（render* 函数 + innerHTML 模板）分离；事件委托挂在容器 ID 上，**重写渲染层时保持容器 ID 与 `data-*` 属性契约**（data-seq/data-cat/data-v/data-comp/data-team/data-issue/data-fav/data-tag/data-i）
- **视频内存策略**：详情区只有一个 `<video>`，`select()` 时替换 src（视频路径已含赛季前缀）。**绝不要**恢复为列表内联 video 元素——几百个播放器会让浏览器内存膨胀到 4-5GB（已经踩过并修复的坑）
- **响应式断点（唯一一套）**：1280 / 1080 / 640。≤1080px：侧栏变抽屉（`body.sb-open`，顶栏 btnSb 切换）、列表/详情二选一（`body.detail-open`，select() 自动加）
- 收藏/笔记存 localStorage：键 `cfa2026.fav/notes`、`cfa2025.fav/notes`、`cfa2024.fav/notes`（按赛季隔离，且按 origin 隔离，file:// 与 http:// 不同源，故有导出/导入 JSON 功能）
- **锚点**：`season-*.html#case-<seq>` 打开时自动选中对应判例（stats-*.html 明细链接依赖此；初始化代码必须在 applyFilter **之前**捕获 hash——`initialHashSeq`，否则会被自动选中的 replaceState 覆盖——已踩过）
- 搜索框监听 `input` 和 `search` 事件（后者是 type=search ✕ 清空按钮触发）；`esc()` 必须转义引号（用于 data-* 属性）

## 竞赛规则页（rules.html）

- 划词高亮：选中正文 → 浮动工具条选色（黄=重要/绿=已掌握/红=易错）→ 以 `{sec, quote, color, ts}` 存 localStorage `cfa2026rules.hl`；切章/刷新时按引文文本匹配重新应用（`applyHl`）；点击高亮可删除
- 章节笔记：每节一个自动保存的笔记框，存 `cfa2026rules.notes`；支持导出/导入 JSON（高亮+笔记合并去重）
- 搜索高亮用的 `mark[data-h]` 与用户高亮 `mark.hl` 是两套互不干扰的标记
- ≤900px 章节树变抽屉（`body.toc-open`，顶栏按钮切换），搜索下拉 fixed 定位（不绑侧栏宽度）

## 硬约束（违反会直接出错）

1. **离线单文件**：所有页面禁止引入任何外部 CDN/字体/JS 库；视频/队徽一律相对路径；图标用 theme.py 内联 SVG
2. **safe_http.py 安全模块**：所有对公网的请求必须走它——域名白名单（`ALLOWED_HOSTS`，新数据源需显式添加）、强制 https、DoH 解析校验公网 IP（本机 TUN 代理会返回 fake-ip）、IP 钉扎连接。**不要**绕过它直接用 requests/urllib
3. **thecfa.cn 没有 404**：失效 URL 一律 301 到"升级维护"页，判活必须用 `status==200` 且内容不含 /upgrade/
4. **编码**：全部 UTF-8；但 `启动合集网页.bat` 必须存为 **GBK**（cmd 解析），改它时用 `encoding="gbk"` 写入
5. **期数结构坑**：2025 第27期内嵌第26期补充认定（fix_issue27_merge.py）；2026 第20期判例一无"判例N:"前缀（parse_issues.py 已有无前缀首判例兜底）；2026 第17期判例九沿判例八事件无对阵行（classify_cases.py 内补全）；comp 兜底归一在 parse/builder 双处
6. **球队名归一是单点**：`generate_teams_catalog.py` 的 `ALIASES`（赞助冠名/笔误变体 → 标准名，如 河南俱乐部彩陶坊→河南俱乐部、杭州临江吴越→杭州临平吴越）；impact/scores 里的队名必须是归一化后名字；**新增 alias 只改这一处**（旧的 build_page/fetch_crests 双处 NAME_VARIANTS 已废弃）
7. **两 URL 表同步**：fetch_issues.py 的 `ISSUES` 与 parse_issues.py 的 `ISSUE_URL` 是同一套 URL 的两份拷贝，加新期必须同步
8. **expectation 断言**：verify_project.py 的 `EXPECTED` 是三赛季判例数/视频数/判定分布的回归护栏，改了分类或解析必须同步；`generate_teams_catalog.py` 重建会**覆盖手改**，verified 成果只能走 crest_overrides.json

## 扩展任务指南

### 接入 2027 赛季（管线已参数化，照 2026 的先例）
1. `python scripts/enum_issues.py` 枚举新期 URL → 人工核对
2. fetch_issues.py `ISSUES["2027"]` 与 parse_issues.py `ISSUE_URL["2027"]` 同步追加
3. 抓取→解析→检查 comp/无前缀首判例等结构坑 → 逐条通读新建 `CLS_2027`（新文件 classify_cls_2027.py，classify_cases.py 加 import+分支）
4. 新建 make_impact_2027.py（照 make_impact_2026.py），比分人工查证填 match-scores-2027.json
5. generate_teams_catalog 自动纳入新队名（赞助冠名往 ALIASES 加）→ build_page/build_stats 的 SEASONS 加配置 → 门户模板加卡片 → verify_project 的 PAGES/EXPECTED 更新
6. 视频后台下载 + verify_videos 校验

### 新增队徽/修正队徽
- 自动：`fetch_crests_online.py`（维基）→ **人工目检**每张图 → 确认后自动写 teams.json → 重播种 crest_overrides.json
- 人工：下载 png 到 `assets/crests/{slug}.png` → crest_overrides.json 登记来源 → 重跑 generate_teams_catalog
- 目检重点：更名前旧徽、赞助商模板、国旗、他队徽；宁缺毋滥（fallback 文字徽章是设计内行为）

### 新增统计维度
- 在 `build_stats.py` 的 `team_stats()`/`build_matches()` 扩展；数据源缺失时页面必须优雅降级（显示"待补"），参考比分缺失的处理

## AI 开发自验清单

改动后依次验证：
- [ ] `python build_portal.py && python build_page.py && python build_stats.py && python build_rules.py` 无报错
- [ ] `python scripts/verify_project.py` 通过（8页面/三赛季数据/离线资源/队徽目录）
- [ ] 浏览器打开 index.html：门户四卡片数字正确
- [ ] season-2026.html：225 行列表、详情视频可播放可拖进度、筛选（分类/判定/期数/搜索/收藏视图）相互叠加、↑↓键盘切换、统计与说明弹层、`#case-183` 锚点直达、收藏+笔记刷新后仍在、明暗切换
- [ ] season-2024.html：160 行列表、视频路径 videos/2024/ 可播放
- [ ] stats-2026/2025/2024.html：双视角切换、联赛筛选（含足协杯）、缺失比分显示"待补"、明细链接跳对应赛季页
- [ ] rules.html：划词出现高亮工具条、三种颜色可标可删、章节笔记自动保存、导出导入
- [ ] `python verify_videos.py [赛季]`（如动过视频/数据）
- [ ] 统计口径：2026 错漏判 95、支持原判 121、不予认定 9；2025 错漏判 82、支持 138、不予 7；2024 错漏判 60、支持 99、不予 1（与 cases-*.json 一致）

## 已知不足（欢迎改进）

- 2026 赛季进行中：持续跑 fetch→parse→classify→impact 增量更新；影响统计的 79 场比分已核 19 场（确定得失球场次优先），其余"待补"
- 111 支标准队伍中 72 支无可靠来源队徽（女足/中乙新军为主），显示文字徽章；维基体系与懂球帝（DoH 解析失败被 safe_http 拦截）之外的自动源已穷尽，需人工补录
- 官方标题认定数与合集口径存在差异（漏判黄牌/低级别联赛/本轮中超口径），已在页面"说明"弹层按期注释（ISSUE_NOTES）
- 2026 判例的判定与影响标注为按同一方法论复核（非官方逐条人工背书），把握度低的判 pending 并注释
- 收藏/笔记仅存浏览器本地，无云同步（导出/导入 JSON 作为迁移方案）
