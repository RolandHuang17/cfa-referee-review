# 维护交接说明（bus factor 文档）

写给「如果某天我不再维护这个仓库」的那一天。目标：任何接手的人（或 AI 助手）
靠本文件 + AGENTS.md 能把项目继续跑下去。

## 数据源清单（项目的生命线）

| 内容 | 来源 | 跟更方式 |
|---|---|---|
| 裁判评议正文/视频 | thecfa.cn「裁判评议结果发布」/cppy/ 栏目 | `fetch_issues.py`（URL 表在脚本内） |
| 统一尺度宣讲包 | 官方 zip 发布（2026/2025 在仓库外 ../统一尺度宣讲原始包-*，2024 在 data/local/scale-2024/） | 日常构建读 `scale.json`，获得完整原包后运行 `build_scale.py --extract` |
| IFAB 规则 PDF | theifab.com 官方繁体版 | `fetch_laws.py`（URL 在脚本内） |
| UEFA Clear Line | uefa.com（tarpit，页间隔 35-55s） | `fetch_uefa.py all` |
| RFEF / PRO / CONMEBOL / weekly / HNS | 各官网（safe_http 白名单内） | 各 `fetch_*.py` |

## 可以自动化 vs 必须人工

- **可自动化**：抓取→解析→分类→影响→构建→测试全链（`update_season.py` 串好）；
  CI 在以 main 为目标的 PR 或手工触发时运行检查，Pages 工作流由 main 推送或手工触发。
- **必须人工**：新期 URL 写入两处表；比分查证（SofaScore 优先，流程见
  match-scores note 字段）；判定复核与 pending 改判；队徽目检；译文补译。
- **历史精修**：`case-overrides.json` 保存带原值校验的修订。使用
  `rebuild_cases.py <赛季>` 在内存中完成解析、拆分、分类与校订，验证后原子写出。
  三赛季历史快照通过归档重建回归测试保护。
- **人工答案**：默认起草保留已复核的答案、纪律对象与来源。用 `gen_quiz_answers.py --preview-all` 比较全量机器草稿，复核后再用 `--apply-review`。
- **国际快照与队徽**：UEFA、RFEF、CONMEBOL、IFAB 仅在来源完整时发布新快照，纯缓存工作沿用既有核查日期。采集到的队徽连同来源存放在 `data/local/crest-candidates/`，用户目检后登记到 `crest_overrides.json`。

## 节奏

- 赛季中：每期评议发布后 1-2 天内跟更（每周一两次）。
- 赛季收尾：跑全量核验（比分/影响覆盖）→ 打 tag 发版（release.yml 自动打包）。
- 国际板块：随各官方源更新，无固定节奏。

## 接手第一步

1. 通读 AGENTS.md（10 分钟项目全貌）。
2. `python scripts/build_all.py && python tests/test_integrity.py` 确认本机构建绿。
3. 结合 [路线图](ROADMAP.md) 与 [问题清单](BUG_TRACKER.md) 选择下一项有验收条件的工作。

## 权限与账号

- GitHub Pages 由 `.github/workflows/pages.yml` 自动发布，无需服务器/域名。
- 仓库 Collaborator / Discussions 管理权在 RolandHuang17。
- 无任何付费服务依赖（零运行成本）。
