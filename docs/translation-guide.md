# 译文层贡献指南

本项目的国际板块采用「源数据 + 中文译文层」双文件架构：抓取脚本产出/覆写源 JSON
（如 `data/uefa.json`），人工翻译写进对应的 `-zh.json`（如 `data/uefa-zh.json`）。
**两层永不互相覆写**——这是全仓库最重要的一条红线，把译文写进源文件会在下次抓取时
全部丢失。

## 各层的结构与匹配键

| 译文层 | 源文件 | 匹配方式 | 必译对象 |
|---|---|---|---|
| `uefa-zh.json` | `uefa.json` | 组按 key、准则按块序、判例按 id | 判例标题 + 组 intro/criteria |
| `rfef-zh.json` | `rfef.json` | 栏目按 key、分组按 code、判例按 id | 判例情形（situation） |
| `conmebol-zh.json` | `conmebol.json` | 案例按文章 url | 官方情境（situacion_es 非空的案子） |
| `weekly-zh.json` | `weekly.json` | 期目按 videoId、节目按 show key | 各期 note 译注 |
| `ifab-zh.json` | `ifab.json` | 大节按 id、子节按英文标题（裸 items 为 `_head`）、FAQ 按 id | 全文（条款 + FAQ） |
| `hns-zh.json` | `hns.json` | 轮次按 id、判例按 no | 判例 paras（与原文 1:1 条数对齐） |

匹配规则细节见 AGENTS.md 的数据 schema 速查一节；对齐情况由
`tests/test_integrity.py` 硬断言把守（缺口会拦 CI），`scripts/translation_status.py`
打印各层覆盖率（`-v` 列出逐条缺失）。

## 补译工作流

1. 跑 `python scripts/translation_status.py -v` 找缺口（当前全绿；新抓取的期次/
   判例会先以原文回退显示并打构建警告，那就是缺口）。
2. 在对应 `-zh.json` 里按上表的键补译文——只改 `-zh` 文件，不动源文件。
3. 术语对照优先用文件内 `terms` 表与既有译法（DOGSО=破坏明显进球得分机会、
   reckless=鲁莽、SPA=停止有希望的进攻……），保持全站一致。
4. `python scripts/build_<板块>.py` 重建对应页面至零警告，再跑
   `python tests/test_integrity.py`。
5. PR 说明里注明翻译的来源板块与条数。

## 注意事项

- 译文以官方原文为准，不增删语义；官方原文本身的强调（加粗/引号）可转为中文引号。
- 视频不做本地化/内嵌（版权原因，见 NOTICE.md），译文只处理文字。
- `weekly-zh` 的 note 是「译注」性质：可以是概述+要点，不必逐句直译；
  `ifab-zh`/`hns-zh` 是全文翻译，须逐条对应。
