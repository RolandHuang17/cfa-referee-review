# 路线图

按价值/成本排序的候选方向，欢迎在 Discussions 里认领或提议新的。

## 进行中

- **2026 赛季跟更**：每期评议发布后跑 `python scripts/update_season.py 2026`
  （fetch→parse→classify→impact→build），比分查证按 AGENTS 管线注记。
- **译文层随源生长**：UEFA Clear Line / HNS / weekly 有新内容时按
  [translation-guide.md](translation-guide.md) 补译。

## 已排期（短期）

- 队徽缺口收敛：39 支 fallback 队伍等待可靠来源（见 docs/crest-guide.md）。
- `ifab-zh.json` 对照官方英文原文的社区修订（首译 2026-10，欢迎校对）。
- 考题答案库人工校对推进（`gen_quiz_answers.py` 的 reviewed 覆盖率）。

## 候选方向（未排期，认领即排）

- **判例对比模式**：选 2-3 个判例并排对照（视频内存策略需要单播放器改造，见
  AGENTS 前端架构一节的已踩坑记录）。
- **裁判员维度统计**：官方评议未系统披露裁判员姓名，需先解决数据来源。
- **离线全文搜索**：search.html 的索引压缩（当前 945KB 内联，可用前缀索引瘦身）。
- **英语版核心页面**：面向国际裁判社区的 season/scale 页英文化（译文层架构已支持）。
- **数据集 DOI**：与 schemas/ 配套的正式学术发布（Zenodo/figshare）。

## 不做

- 内嵌/下载 YouTube 与 UEFA token 门禁视频（服务条款与版权，见硬约束 1）。
- 云同步收藏/笔记（localStorage + 导出导入已是当前架构的合理终点）。
- 前端框架化（自包含单文件是产品的核心承诺）。
