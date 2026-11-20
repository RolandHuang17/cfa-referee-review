# 译文层贡献指南

本项目的国际板块采用「源数据 + 中文译文层」双文件架构：抓取脚本产出/覆写源 JSON
（如 `data/uefa.json`），人工翻译写进对应的 `-zh.json`（如 `data/uefa-zh.json`）。
**两层永不互相覆写**——这是全仓库最重要的一条红线，把译文写进源文件会在下次抓取时
全部丢失。

## 各层的结构与匹配键

| 译文层 | 源文件 | 匹配方式 | 必译对象 |
|---|---|---|---|
| `uefa-zh.json` | `uefa.json` | 组按 key，判例按视频 ID，准则按整块现行原文与历史译块配对 | 判例标题、组名、导语和准则 |
| `rfef-zh.json` | `rfef.json` | 栏目按 key、分组按 code、判例按 id | 判例情形（situation） |
| `conmebol-zh.json` | `conmebol.json` | 匹配文章和情境原词，或复用该词唯一的已核译名 | 有可核西语标签的时刻，逐项登记缺译 |
| `weekly-zh.json` | `weekly.json` | 期目按 videoId、节目按 show key | 各期 note 译注 |
| `ifab-zh.json` | `ifab.json` | 主协议与配套资料按 id，条款块按英文小节标题（节首为 `_head`），FAQ 按本节内 id | 文档标题、小节标题、正文条款和问答 |
| `hns-zh.json` | `hns.json` | 轮次按 id、判例按 no | 判例 paras（与原文 1:1 条数对齐） |

运行 `python scripts/translation_status.py` 查看各类对象的覆盖数，加 `-v` 可按当前资料顺序列出每项缺口。「缺译」表示该项缺少可用中文。「待复核」表示存在历史译文，当前来源版本、结构或身份需要核对。若官网新增或改写了一个无稳定 ID 的准则块，应从所在组核对它与旧译的关系。

UEFA、IFAB 和 CONMEBOL 的覆盖数使用详情页实际能配对的译文。CONMEBOL 的 `untranslated` 用时刻锚点登记尚无已核译名的西语原词，`pending_cases` 留存有来源归属问题的历史稿。RFEF、weekly 和 HNS 按上表所列文字字段统计；这些来源变更时仍需逐项对照。HNS 的段落条数另有完整性测试。[数据结构与约束](../AGENTS.md)

## 补译工作流

1. 在仓库根目录运行 `python scripts/translation_status.py -v`。用输出的键打开上表对应的源 JSON。以本次收录的官方原文为底本，若需核对背景，可从该条的官方链接阅读上下文。
2. 在对应 `-zh.json` 中逐项校译。术语优先使用文件中的 `terms` 表和既有译法，例如 DOGSO「破坏明显进球得分机会」、reckless「鲁莽」。UEFA 分类组名另有既有来源，见下表。
3. 对 UEFA、IFAB 完成下节的单项版本登记。原文含义尚未确认时保留旧译和已登记版本，页面会展示可核对的现行英文。
4. 再运行 `python scripts/translation_status.py -v`，确认本次处理的缺口已消失。运行该板块的构建脚本，检查网页中的英文与中文，然后运行 `python tests/test_integrity.py`。
5. 在贡献说明中注明本次核对的板块、原文键和条数，便于后续维护者定位。

## 登记单项原文版本

`--source-version` 可离线打印一个键对应的完整原文和指纹。它只读取仓库内的数据。以下三条命令分别查看一个 UEFA 标题、一块 UEFA 准则和一个 IFAB 标题。

```text
python scripts/translation_status.py --source-version uefa items/02a7-21381fdca64f-3a2d59a205aa-1000
python scripts/translation_status.py --source-version uefa dogso/criteria/1
python scripts/translation_status.py --source-version ifab s1/title
```

从 `-v` 输出取键时，使用「 · 」之前的部分。键内包含空格时，在命令中给整个键加双引号。逐字对照命令打印的原文和已编辑的中文，确认该项的全部内容后，再把同一次输出的指纹登记到下表位置。

| 核对对象 | 原文键 | 译层中的登记位置 |
|---|---|---|
| UEFA 判例标题 | `items/<视频ID>` | `source_versions.items[视频ID]`。中文在 `items[视频ID].title`。 |
| UEFA 组名、导语 | `<组key>/name_en` 或 `<组key>/intro` | `source_versions.groups[组key].name_en` 或 `.intro`。导语中文在 `groups[组key].intro`。组名中文来自抓取器 `GROUP_CN` 的策展标签，原文改名时先人工核实标签；需要改名时同步维护该来源及其正常采集输出。 |
| UEFA 准则块 | `<组key>/criteria/<现行第几块>`，从 1 开始 | 核对英文标题和块内每条准则，找到 `groups[组key].criteria` 中对应的中文块，把指纹填入 `source_versions.groups[组key].criteria` 的**同一译文下标**。官网重排后现行块序可能不同。新增译块与指纹应写在译层两份数组的相同位置。 |
| IFAB 文档标题 | `<文档id>/title` | 在 `ifab-zh.json` 的 `source_versions[原文键]` 更新该项。主协议正文在 `sections`，配套正文在 `extras`。 |
| IFAB 正文条款块 | `<文档id>/block/<英文小节标题或_head>` | 在 `source_versions[原文键]` 登记整块。保持英文小节键、段落顺序和每一项的 `p` / `li` 类型对应；同块逐条校对完毕再登记。 |
| IFAB 问答 | 主协议 `faq/<问题id>`，配套 `<文档id>/faq/<问题id>` | 在 `source_versions[原文键]` 登记。问题与答案一起复核。 |

指纹仅表示译文所针对的官方文本版本。只登记本次实际核对的项，其余项保留原值。相同原文键命中多项时，命令会列出匹配数并停止；先查清来源身份。

## 注意事项

- 译文以官方原文为准，不增删语义；官方原文本身的强调（加粗/引号）可转为中文引号。
- 译文层处理文字。各板块的视频来源与播放方式见 [随站声明](../NOTICE.md)。
- `weekly-zh` 的 note 是「译注」性质：可以是概述+要点，不必逐句直译；
  `ifab-zh`/`hns-zh` 是全文翻译，须逐条对应。
