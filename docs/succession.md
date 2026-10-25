# 维护交接说明（bus factor 文档）

写给「如果某天我不再维护这个仓库」的那一天。目标：任何接手的人（或 AI 助手）
靠本文件 + AGENTS.md 能把项目继续跑下去。

## 数据源清单（项目的生命线）

| 内容 | 来源 | 跟更方式 |
|---|---|---|
| 裁判评议正文/视频 | thecfa.cn「裁判评议结果发布」/cppy/ 栏目 | `fetch_issues.py`（URL 表在脚本内） |
| 统一尺度宣讲包 | 官方 zip 发布（2026/2025 在仓库外 ../统一尺度宣讲原始包-*，2024 在 data/local/scale-2024/） | 官方发布后替换原包重跑 `build_scale.py` |
| IFAB 规则 PDF | theifab.com 官方繁体版 | `fetch_laws.py`（URL 在脚本内） |
| UEFA Clear Line | uefa.com（tarpit，页间隔 35-55s） | `fetch_uefa.py all` |
| RFEF / PRO / CONMEBOL / weekly / HNS | 各官网（safe_http 白名单内） | 各 `fetch_*.py` |

## 可以自动化 vs 必须人工

- **可自动化**：抓取→解析→分类→影响→构建→测试全链（`update_season.py` 串好）；
  CI 每次 push 自动构建发布 Pages。
- **必须人工**：新期 URL 写入两处表；比分查证（SofaScore 优先，流程见
  match-scores note 字段）；判定复核与 pending 改判；队徽目检；译文补译。
- **红线**：`data/cases-2025.json` 含管线外人工数据（对阵/赛事/结论引语/seq215
  改判），**不要对 2025 重跑 parse**——golden 测试看护，覆盖即红。

## 节奏

- 赛季中：每期评议发布后 1-2 天内跟更（每周一两次）。
- 赛季收尾：跑全量核验（比分/影响覆盖）→ 打 tag 发版（release.yml 自动打包）。
- 国际板块：随各官方源更新，无固定节奏。

## 接手第一步

1. 通读 AGENTS.md（10 分钟项目全貌）。
2. `python scripts/build_all.py && python tests/test_integrity.py` 确认本机构建绿。
3. 从 docs/ROADMAP.md 的「进行中」挑一件事做。

## 权限与账号

- GitHub Pages 由 `.github/workflows/pages.yml` 自动发布，无需服务器/域名。
- 仓库 Collaborator / Discussions 管理权在 RolandHuang17。
- 无任何付费服务依赖（零运行成本）。
