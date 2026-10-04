# 接入新赛季

管线已三赛季参数化（2024 / 2025 / 2026），照 2026 的先例走即可。本文是**逐步操作
清单**；命令一律在仓库根执行。前置知识见 [AGENTS.md](../AGENTS.md)，目录与路径契约见
[structure.md](structure.md)。

下面以接入 **2027** 为例，把 `2027` 换成目标赛季即可。

## 1. 发现新期 URL

```bash
python scripts/enum_issues.py
```

枚举官网 `/cppy/` 列表页，输出候选期次与 URL。**必须人工核对**——thecfa.cn 没有 404，
失效 URL 一律 301 到「升级维护」页，判活只能靠 `status == 200` 且内容不含 `/upgrade/`
（`enum_issues.py` 已内置该判据）。

## 2. 同步两处 URL 表 ⚠️ 最容易漏的一步

`fetch_issues.py` 的 `ISSUES` 与 `parse_issues.py` 的 `ISSUE_URL` 是同一套官方 URL 的
**两份拷贝**（历史遗留），必须同步追加：

```python
ISSUES["2027"] = [(1, "https://www.thecfa.cn/cppy/..."), ...]   # fetch_issues.py
ISSUE_URL["2027"] = {1: "https://www.thecfa.cn/cppy/...", ...}  # parse_issues.py
```

漏一处的症状：抓取成功但解析期次为空，或解析出的 `issues[].url` 缺失导致轻量版
「打开官方评议页」链接失效。

## 3. 抓取与解析

```bash
python scripts/fetch_issues.py 2027        # → data/issues/2027/
python scripts/parse_issues.py 2027        # → data/cases-2027.json
```

解析后**逐期通读**，重点排查已知的结构坑（每季官网排版都会微调，历史上已踩过）：

| 症状 | 已知先例 | 处理位置 |
|---|---|---|
| 首判例没有「判例一:」前缀，整条丢失 | 2026 第 20 期判例一 | `parse_issues.py` 已有无前缀首判例兜底 |
| 文章是「结论摘要」式，无标准判例结构、无视频 | 2024 第 1 期 | `classify_cases.py` 内按原文补全对阵 |
| 某期文章内嵌上一期的补充认定 | 2025 第 27 期含第 26 期 | 新建 `fix_issueNN_merge.py`（照 `fix_issue27_merge.py`） |
| 判例沿用前一判例的事件，无对阵行 | 2026 第 17 期判例九 | `classify_cases.py` 内补全 |
| `comp` 为空或写法不一（「中超」/「中国足球协会超级联赛」） | 各季均有 | 兜底归一在 `parse_issues.py` 与 builder **双处**，都要加 |
| 队名带赞助冠名或横杠（「? vs ?」） | 各季均有 | 见第 5 步的 `ALIASES` |

## 4. 教学分类与结论复核

```bash
python scripts/classify_cases.py 2027
```

新建 `scripts/lib/classify_cls_2027.py` 存 `CLS_2027` 纯数据表（照
`classify_cls_2026.py`：无 I/O、无 `__main__`，因此属于 `lib/`），再在
`classify_cases.py` 加 import 与赛季分支。

**分类必须逐条通读原文后再定**，不能靠关键词自动匹配。`referee_verdict`
（wrong/correct/pending）是复核过的结论：把握度低的判 `pending` 并在数据里注释原因，
不要硬猜。2026 赛季的判定是「按同一方法论复核」而非官方逐条背书，新赛季同样处理。

## 5. 影响标注与队伍目录

```bash
python scripts/make_impact_2027.py          # 新建，照 make_impact_2026.py
python scripts/generate_teams_catalog.py    # 自动纳入新队名
python scripts/fetch_crests.py              # 队徽目录校验
```

- 比分需**人工查证**后填 `data/match-scores-2027.json`；查不到的留空，页面会显示
  「待补」，这是设计内行为，不要造假数据填充。
- 影响范围只算男子中超/中甲/中乙及足协杯（女超/女甲/全运会排除）。
- 新出现的赞助冠名、笔误变体往 `generate_teams_catalog.py` 的 `ALIASES` 加——
  **这是队名归一的唯一单点**，不要在 builder 里另建映射表。
- `impact` / `scores` 里的队名必须是**归一化后**的标准名。
- 新队徽走 [crest-guide.md](crest-guide.md)。

## 6. 页面接入

- `build_page.py` 与 `build_stats.py` 的 `SEASONS` 字典加 `"2027"` 配置
  （`cases` / `impact` / `scores` 三个文件名）。
- `build_portal.py` 的门户模板加入口卡片。
- 若同时新增统一尺度材料：`build_scale.py` 的 `PACKAGES` 与 `SCALE_SOURCE_URLS`
  **必须在同一个 commit 里增删赛季**，否则 `build_page` 会 KeyError。
- `SCALE_SOURCE_URLS` 的官方材料是 zip 发布，没有逐例链接，轻量版横幅按赛季显示
  发布页即可。

## 7. 视频下载

```bash
python scripts/download_videos_parallel.py 2027   # 断点续传，可中断重跑
python scripts/verify_videos.py 2027              # 大小 vs 服务器 HEAD
```

后台跑即可；失败重跑同一命令会续传。视频不进仓库（写进 `site/videos/2027/`，已被
`.gitignore` 的 `site/videos/` 覆盖）。

## 8. 收尾：更新回归基准并全量重建 ⚠️

`tests/test_integrity.py` 里四处必须改。注意：`SEASONS`/`EXPECTED_QUIZ` 漏加新季只是
**静默跳过该季检查**，真正会挂 CI 的是 `EXPECTED_QUIZ` 不更新导致的 quiz meta 总数不符、
以及页面内联数据与 data JSON 不同步的 stale-build 护栏——所以每处都要手动同步：

```python
PAGES = [..., "season-2027.html", "stats-2027.html"]      # 页面清单（漏加=新页不被检查）
EXPECTED = {..., "2027": (判例数, 视频数, {"wrong": N, "correct": N, "pending": N})}
SEASONS = (..., "2027")
EXPECTED_QUIZ = {..., "2027": 判例池基准}                  # 「有视频且有认定原文」的判例数
```

`EXPECTED` 是**人工复核后的基准**，不是「跑一遍把输出抄进去」——先独立数清官方认定的
错漏判数，再填进去；两者不符说明解析或分类有问题。

然后：

```bash
python scripts/build_all.py
python tests/test_integrity.py
```

## 9. 文档同步

同一 PR 内更新：`README.md`（首页段落、统计口径、目录树若变化）、`AGENTS.md`（项目
是什么、数据 schema、统计口径）、`CHANGELOG.md`（`Unreleased` 段落）、
`docs/structure.md`（若引入了新目录）。

## 提交前自查

- [ ] 两处 URL 表（`ISSUES` / `ISSUE_URL`）都已追加且条数一致
- [ ] 逐期通读过解析结果，结构坑已在对应脚本内处理并注释了先例
- [ ] `referee_verdict` 逐条复核过，把握度低的判 `pending`
- [ ] 比分缺失处显示「待补」而非编造
- [ ] 新队名归一化只改了 `ALIASES` 一处
- [ ] `tests/test_integrity.py` 的 `PAGES` / `EXPECTED` / `SEASONS` 已更新，且数字是
      独立数出来的
- [ ] `python scripts/build_all.py` 与 `python tests/test_integrity.py` 均通过
- [ ] 浏览器实测新页面的筛选、锚点、轻量版与视频播放
