# AGENTS.md — AI 协作开发指南

> 本文件写给在此仓库中工作的 AI 编码助手（也适用于人类新维护者）。目标是让你在 10 分钟内理解项目全貌、数据管线与所有已知的坑，直接开始有效开发。

## 项目是什么

「2025赛季中国足协裁判评议教学合集」：抓取中国足协官网 2025 赛季全部 **32 期裁判评议**（227 个判例、229 段视频），按新裁判统一尺度教学分类重组，生成为**完全离线的静态网页**（双击 index.html 即可用，无需任何服务），并附带各队得失盘点统计页（stats.html）。

核心交付物是**两个自包含的 HTML 文件**（CSS/JS/数据全部内联）+ 本地 `videos/` 视频文件夹。数据抓取与页面生成由 Python 脚本完成，可复用于其他赛季（2026 赛季已开赛）。

## 环境

- Python 3.8+，**零第三方依赖**（全部标准库）
- Windows 优先（脚本在 Windows 上开发；`启动合集网页.bat` 仅支持 Windows）
- 视频不在仓库里（约 16GB，超 GitHub 限制），clone 后运行 `python scripts/download_videos_parallel.py` 重新下载（断点续传、可中断重跑）

## 目录结构

```
├── index.html              ← 主合集页（由 build_page.py 生成，勿手改）
├── stats.html              ← 各队得失盘点页（由 build_stats.py 生成，勿手改）
├── videos/                 ← 229段视频（git忽略，download脚本重建）
├── assets/crests/          ← 球队队徽（fetch_crests.py 采集）
├── data/
│   ├── cases.json          ← 核心：227判例结构化数据（issues + cases）
│   ├── impact.json         ← 错漏判影响标注（受损队/类型/确定得失球）
│   ├── match_scores.json   ← 60场比赛最终比分（人工网络查证）
│   ├── crests.json         ← 队名→队徽文件映射
│   ├── issues_raw/         ← 32期官方页面原始HTML存档
│   └── review.txt          ← 判例纯文本汇编（可再生成）
└── scripts/                ← 全部管线脚本（见下）
```

## 数据管线（按序执行）

```bash
cd scripts
python fetch_issues.py               # 1. 抓取官方页面 → data/issues_raw/（URL清单在脚本内 ISSUES 表）
python parse_issues.py               # 2. 解析 → data/cases.json（判例/结论/视频映射/自动判定）
python download_videos_parallel.py   # 3. 下载视频 → videos/（断点续传，失败重跑即可）
python classify_cases.py             # 4. 教学分类与结论复核（分类表 CLS 在脚本内，人工维护）
python make_impact.py                # 5. 错漏判影响标注（受损队/损失类型表 CLS 在脚本内）
python fetch_crests.py               # 6. 队徽采集 → assets/crests/ + data/crests.json
python build_page.py                 # 7. 生成 index.html
python build_stats.py                # 8. 生成 stats.html
python verify_videos.py              # 辅助：视频完整性校验（大小 vs 服务器 HEAD）
python range_server.py [端口]        # 本地预览服务（支持Range，视频可拖进度条）
```

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

## 前端架构（index.html）

- 布局：单行顶栏 + 三栏 grid（侧栏 240px / 播放列表 336px / 详情自适应），每列独立滚动，`body.sb-off` 收起侧栏
- 数据以 `const DATA = {...}` 内联注入；`bySeq` 为判例索引
- 状态对象 `state = {cat, v(判定), issue, q(搜索), sel(选中seq), vIdx(多视频序号), fav(收藏筛选)}`
- 筛选统一走 `visibleCases()` → `renderList()` → `applyFilter()`（选中项被筛掉时自动跳到第一条）
- **视频内存策略**：详情区只有一个 `<video>`，`select()` 时替换 src。**绝不要**恢复为列表内联 video 元素——229 个播放器会让浏览器内存膨胀到 4-5GB（这是已经踩过并修复的坑）
- 收藏/笔记存 localStorage：键 `cfa2025.fav` / `cfa2025.notes`（按 origin 隔离，file:// 与 http:// 不同源，故有导出/导入 JSON 功能）
- 锚点：`index.html#case-<seq>` 打开时自动选中对应判例（stats.html 的明细链接依赖此；初始化代码必须在 applyFilter **之前**捕获 hash，否则会被自动选中的 replaceState 覆盖——已踩过）
- 搜索框同时监听 `input` 和 `search` 事件（后者是 type=search 输入框 ✕ 清空按钮触发的）

## 硬约束（违反会直接出错）

1. **离线单文件**：两个页面禁止引入任何外部 CDN/字体/JS 库；视频/队徽一律相对路径
2. **safe_http.py 安全模块**：所有对公网的请求必须走它——域名白名单（`ALLOWED_HOSTS`，新数据源需显式添加）、强制 https、DoH 解析校验公网 IP（本机 TUN 代理会返回 fake-ip）、IP 钉扎连接。**不要**绕过它直接用 requests/urllib
3. **thecfa.cn 没有 404**：失效 URL 一律 301 到"升级维护"页，判活必须用 `status==200` 且 URL 不含 /upgrade/
4. **编码**：全部 UTF-8；但 `启动合集网页.bat` 必须存为 **GBK**（cmd 解析），改它时用 `encoding="gbk"` 写入，且路径分隔符不要用 `\r` 开头的转义组合
5. **期数结构坑**：第27期文章内嵌了对第26期判例2/判例7的补充认定（`fix_issue27_merge.py` 处理过）；约19条判例 comp 为空（其中10条是"中超第28轮"式写法，已归中超；其余为全运会）
6. **球队名变体**：河南俱乐部/河南酒祖杜康、陕西联合/陕西联合月亮泊、广西平果/广西平果国晶、浙江俱乐部/浙江俱乐部绿城、大连英博/大连英博海发、温州俱乐部/温州俱乐部中胤——统一映射在 `NAME_VARIANTS`（fetch_crests.py），新增统计维度时必须先归一化

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
- [ ] `python build_page.py && python build_stats.py` 无报错
- [ ] 浏览器打开 index.html：227行列表、详情视频可播放可拖进度、筛选（分类/判定/期数/搜索/收藏视图）相互叠加、↑↓键盘切换、统计与说明弹层、`#case-183` 锚点直达、收藏+笔记刷新后仍在
- [ ] stats.html：双视角切换、联赛筛选、36+队徽显示
- [ ] `python verify_videos.py`（如动过视频/数据）
- [ ] 统计口径：合计错漏判82例、支持原判138例、不予认定7例（与 cases.json 一致）

## 已知不足（欢迎改进）

- 16支中乙新军队徽维基无词条，页面显示首字占位（名单见 fetch_crests.py 运行输出）
- 第9期标题认定6例 vs 合集5例裁判错漏判（第6例为VAR划线错误，计入VAR统计）
- 收藏/笔记仅存浏览器本地，无云同步（导出/导入 JSON 作为迁移方案）
