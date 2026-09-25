# AGENTS.md — AI 协作开发指南

> 本文件写给在此仓库中工作的 AI 编码助手（也适用于人类新维护者）。目标是让你在 10 分钟内理解项目全貌、数据管线与所有已知的坑，直接开始有效开发。

## 项目是什么

「裁判学习一站式平台」：抓取中国足协官网 **2024+2025 两个赛季全部 59 期裁判评议**（2025：32期227判例229视频；2024：27期160判例161视频），按新裁判统一尺度教学分类重组，生成为**完全离线的静态网页**（双击 index.html 即可用，无需任何服务），附带各队得失盘点统计页（stats-2025.html / stats-2024.html）与竞赛规则 2026-27 简体版（rules.html，由 IFAB 官方繁体 PDF 自动转换，支持划词高亮与章节笔记）。

核心交付物是**五个自包含的 HTML 文件**（CSS/JS/数据全部内联）+ 本地 `videos/` 视频文件夹（按赛季分子目录）：
- `index.html` 门户首页（三入口卡片）
- `season-2025.html` / `season-2024.html` 各赛季判例合集
- `stats-2025.html` / `stats-2024.html` 各队得失盘点
- `rules.html` 竞赛规则（划词高亮/章节笔记/导出导入）

数据抓取与页面生成由 Python 脚本完成，可复用于其他赛季（2026 赛季已开赛）。

## 环境

- Python 3.8+，**零第三方依赖**（全部标准库）
- Windows 优先（脚本在 Windows 上开发；`启动合集网页.bat` 仅支持 Windows）
- 视频不在仓库里（2024+2025 约 26GB，超 GitHub 限制），clone 后运行 `python scripts/download_videos_parallel.py` 重新下载（断点续传、可中断重跑）

## 目录结构

```
├── index.html              ← 门户首页（由 build_portal.py 生成，勿手改）
├── season-2025.html        ← 2025赛季合集页（由 build_page.py 生成，勿手改）
├── season-2024.html        ← 2024赛季合集页（同上）
├── stats-2025.html         ← 2025各队得失盘点页（由 build_stats.py 生成，勿手改）
├── stats-2024.html         ← 2024得失盘点页（同上）
├── rules.html              ← 竞赛规则 2026-27 简体版（由 build_rules.py 生成，勿手改）
├── videos/                 ← 视频按赛季分目录 videos/2024/ videos/2025/（git忽略）
├── assets/crests/          ← 球队队徽（fetch_crests.py 采集）
├── data/
│   ├── cases-2025.json     ← 核心：2025赛季227判例（issues + cases）
│   ├── cases-2024.json     ← 2024赛季160判例
│   ├── impact.json         ← 2025错漏判影响标注（受损队/类型/确定得失球）
│   ├── impact-2024.json    ← 2024错漏判影响标注
│   ├── match_scores.json   ← 2025赛季60场比赛最终比分（人工网络查证）
│   ├── match-scores-2024.json ← 2024赛季比分（40/45场已证，缺的页面显示"待补"）
│   ├── crests.json         ← 队名→队徽文件映射
│   ├── laws.json           ← 竞赛规则章节内容（build_rules.py 产物，内联进 rules.html）
│   ├── laws_raw/           ← IFAB 官方繁体规则PDF（git忽略，fetch_laws.py 重建）
│   ├── issues_raw/         ← 32期官方页面原始HTML存档
│   └── review.txt          ← 判例纯文本汇编（可再生成）
└── scripts/                ← 全部管线脚本（见下）
```

## 数据管线（按序执行）

```bash
cd scripts
python fetch_issues.py 2025           # 1. 抓取官方页面 → data/issues_raw/{season}/（URL清单在脚本内 ISSUES 表；2024/2025 两季）
python parse_issues.py 2025           # 2. 解析 → data/cases-{season}.json（判例/结论/视频映射/自动判定）
python fix_issue27_merge.py           # 3. 拆分第27期文章内嵌的第26期补充认定（仅2025需要；必须在 classify 前跑）
python download_videos_parallel.py    # 4. 下载视频 → videos/{season}/（断点续传，失败重跑即可）
python classify_cases.py 2025         # 5. 教学分类与结论复核（CLS_2025 内联；CLS_2024 在 classify_cls_2024.py；
                                      #    末尾含第27期判例2拆分后的#195判定校正，勿删）
python make_impact.py                 # 6. 2025错漏判影响标注（make_impact_2024.py 为2024版）
python fetch_crests.py                # 7. 队徽采集 → assets/crests/ + data/crests.json
python fetch_laws.py                  # 8. 下载 IFAB 官方 2026-27 繁体规则 PDF → data/laws_raw/
python build_rules.py                 # 9. 规则提取+繁转简+术语表 → data/laws.json + rules.html
python build_portal.py                # 10. 生成门户 index.html
python build_page.py                  # 11. 生成 season-2025.html + season-2024.html（可带赛季参数）
python build_stats.py                 # 12. 生成 stats-2025.html + stats-2024.html（可带赛季参数）
python verify_videos.py               # 辅助：视频完整性校验（大小 vs 服务器 HEAD）
python range_server.py [端口]         # 本地预览服务（支持Range，视频可拖进度条）
```

⚠️ 顺序要点：fix_issue27_merge 必须在 classify 之前（它拆分结构），classify 末尾会恢复 #195 的拆分后判定；漏掉任何一步都会导致统计错位。

规则模块构建依赖（仅 fetch/build_rules 需要，页面运行时零依赖）：
`pip install -r scripts/requirements-build.txt`（pymupdf / opencc-python-reimplemented / markdown）。
新赛季更新流程：换 fetch_laws.py 里的 PDF URL → 重跑 fetch_laws + build_rules；术语表 GLOSSARY 在 build_rules.py 内按需增补。

`parse/classify/make_impact` 会重新覆盖 `cases.json` 中的对应字段——改了前面步骤后按序重跑，最后必须重跑 build_page/build_stats。

## 数据 schema 速查

### cases.json
- `issues[N]`: `{no, title, date, url, expected_wrong(官方标题认定数), summary, parsed_wrong}`
- `cases[]`: `{seq(1-227全局唯一), issue(1-32), no(期内判例号), comp, round, home, away, minute, desc, appeal, conclusion(评议组认定原文), video_files[](本地文件名), video_urls[](原始URL，与video_files一一对应), category(教学分类id), tags[], referee_verdict(wrong/correct/pending), var_verdict(correct/wrong/none)}`
- **referee_verdict 是人工复核过的结论**，官方口径差异见 `ISSUE_NOTES`（build_page.py 内）

### impact.json（错漏判影响统计用）
- `impacts[seq]`: `{league, round, home, away, items:[{team(受损队), type, swing, note}]}`
- type ∈ denied_goal/opp_goal_should_disallow/missed_penalty/wrong_penalty_against/missed_red_opponent/wrong_red_self/missed_yellow_opponent/wrong_yellow_self/wrong_foul_called_self/wrong_offside_self
- `swing`: 仅进球判定类错误有值（denied_goal=+1, opp_goal_should_disallow=-1），点球是机会不折算进球

### crests.json
- `{球队标准名: "assets/crests/<slug>.png"}`；B队字段映射母俱乐部；**无队徽的球队不出现在映射中**（页面自动降级为首字占位）

## 前端架构（season-2025.html / season-2024.html，由 build_page.py 生成）

- 双赛季共用一套模板；赛季差异（标题/期数/存储键/统计页链接）经 `DATA.cfg` 注入，配置在 `SEASONS` 字典
- 布局：单行顶栏（含 首页/24评议/25评议/得失盘点/竞赛规则 导航）+ 三栏 grid（侧栏 240px / 播放列表 336px / 详情自适应），每列独立滚动，`body.sb-off` 收起侧栏
- 数据以 `const DATA = {...}` 内联注入；`bySeq` 为判例索引
- 状态对象 `state = {cat, v(判定), issue, q(搜索), sel(选中seq), vIdx(多视频序号), fav(收藏筛选), comp(赛事), team(球队)}`
- 筛选统一走 `visibleCases()` → `renderList()` → `applyFilter()`（选中项被筛掉时自动跳到第一条）
- **视频内存策略**：详情区只有一个 `<video>`，`select()` 时替换 src（视频路径已含 `2025/`、`2024/` 前缀）。**绝不要**恢复为列表内联 video 元素——几百个播放器会让浏览器内存膨胀到 4-5GB（这是已经踩过并修复的坑）
- 收藏/笔记存 localStorage：键 `cfa2025.fav` / `cfa2025.notes`、`cfa2024.fav` / `cfa2024.notes`（按赛季隔离，且按 origin 隔离，file:// 与 http:// 不同源，故有导出/导入 JSON 功能）
- 锚点：`season-2025.html#case-<seq>` 打开时自动选中对应判例（stats-*.html 的明细链接依赖此；初始化代码必须在 applyFilter **之前**捕获 hash，否则会被自动选中的 replaceState 覆盖——已踩过）
- 搜索框同时监听 `input` 和 `search` 事件（后者是 type=search 输入框 ✕ 清空按钮触发的）

## 竞赛规则页（rules.html）

- 划词高亮：选中正文 → 浮动工具条选色（黄=重要/绿=已掌握/红=易错）→ 以 `{sec, quote, color, ts}` 存 localStorage `cfa2026rules.hl`；切章/刷新时按引文文本匹配重新应用（`applyHl`）；点击高亮可删除
- 章节笔记：每节一个自动保存的笔记框，存 `cfa2026rules.notes`；支持导出/导入 JSON（高亮+笔记合并去重）
- 搜索高亮用的 `mark[data-h]` 与用户高亮 `mark.hl` 是两套互不干扰的标记

## 硬约束（违反会直接出错）

1. **离线单文件**：所有页面禁止引入任何外部 CDN/字体/JS 库；视频/队徽一律相对路径
2. **safe_http.py 安全模块**：所有对公网的请求必须走它——域名白名单（`ALLOWED_HOSTS`，新数据源需显式添加）、强制 https、DoH 解析校验公网 IP（本机 TUN 代理会返回 fake-ip）、IP 钉扎连接。**不要**绕过它直接用 requests/urllib
3. **thecfa.cn 没有 404**：失效 URL 一律 301 到"升级维护"页，判活必须用 `status==200` 且 URL 不含 /upgrade/
4. **编码**：全部 UTF-8；但 `启动合集网页.bat` 必须存为 **GBK**（cmd 解析），改它时用 `encoding="gbk"` 写入，且路径分隔符不要用 `\r` 开头的转义组合
5. **期数结构坑**：第27期文章内嵌了对第26期判例2/判例7的补充认定（`fix_issue27_merge.py` 处理过）；comp 曾有19条为空（"中超第28轮"式写法与"第十五届运动会"式），已在 parse_issues.py 用兜底关键词+COMP_ALIAS 归一修复，修复后分布：中超75/中甲71/中乙51/女超13/全运会12/女甲4/足协杯1；seq=11（南京城市-大连鲲城）两队用"-"分隔，parse_case_head 有横杠兜底解析
6. **球队名变体**：河南俱乐部/河南酒祖杜康、陕西联合/陕西联合月亮泊、广西平果/广西平果国晶、浙江俱乐部/浙江俱乐部绿城、大连英博/大连英博海发、温州俱乐部/温州俱乐部中胤——统一映射在 `NAME_VARIANTS`（fetch_crests.py 与 build_page.py **双处存在，修改须同步**），新增统计维度时必须先归一化
7. **侧栏筛选体系**：赛事→球队→期数三维 + 犯规分类/判定/收藏；分面计数走 `baseMatch(c, skip)`（skip 为要排除的维度名或数组）；球队筛选跨赛事聚合（选中球队会清空赛事筛选，广州豹=中甲8例+足协杯1例）

## 扩展任务指南

### 接入 2026 赛季
1. 在 `fetch_issues.py` 的 `ISSUES` 表追加新期 URL（来源：官方列表页或 rest.thecfa.cn 搜索接口 `?keyword=裁判评议&page=N`）
2. 视情况把 `parse_issues.py`/`classify_cases.py` 的赛季假设参数化
3. 重跑管线 1→8

### 新增队徽/修正队徽
- 编辑 `fetch_crests.py` 的 `MANUAL_FILE`（队名→维基文件标题）或 `data/crest_manual.json`（队名→直接图片URL），删除对应错误 png 重跑
- `NOISE`/`BLOCK_FILES` 正则用于排除误采（国旗、球衣模板、赞助商logo、他队徽）；新增误采样例时往这里加

### 新增统计维度
- 在 `build_stats.py` 的 `team_stats()`/`build_matches()` 扩展；数据源缺失时页面必须优雅降级（显示"待补"），参考比分缺失的处理

## AI 开发自验清单

改动后依次验证：
- [ ] `python build_portal.py && python build_page.py && python build_stats.py && python build_rules.py` 无报错
- [ ] 浏览器打开 index.html：门户三卡片数字正确
- [ ] season-2025.html：227行列表、详情视频可播放可拖进度、筛选（分类/判定/期数/搜索/收藏视图）相互叠加、↑↓键盘切换、统计与说明弹层、`#case-183` 锚点直达、收藏+笔记刷新后仍在
- [ ] season-2024.html：160行列表、27期筛选、视频路径 videos/2024/ 可播放
- [ ] stats-2025.html / stats-2024.html：双视角切换、联赛筛选（含足协杯）、缺失比分显示"待补"、明细链接跳对应赛季页
- [ ] rules.html：划词出现高亮工具条、三种颜色可标可删、章节笔记自动保存、导出导入
- [ ] `python verify_videos.py`（如动过视频/数据）
- [ ] 统计口径：2025合计错漏判82例、支持原判138例、不予认定7例（与 cases-2025.json 一致）；2024错漏判60例、支持99例、不予认定1例

## 已知不足（欢迎改进）

- 16支中乙新军队徽维基无词条，页面显示首字占位（名单见 fetch_crests.py 运行输出）；2024 部分球队（赣州瑞狮、廊坊荣耀之城、日照宇启等）队徽待补
- 2024 比分尚有 5 场待查证（stats-2024.html 显示"待补"）
- 第9期标题认定6例 vs 合集5例裁判错漏判（第6例为VAR划线错误，计入VAR统计）
- 收藏/笔记仅存浏览器本地，无云同步（导出/导入 JSON 作为迁移方案）
