# 仓库结构与路径契约

本文说明**为什么目录长这样**，以及哪些路径是「契约」——被写死在数据、断言或外部
系统里，改动前必须先找到所有引用方。日常构建命令见 [README](../README.md)，数据管线
与已知坑见 [AGENTS.md](../AGENTS.md)。

## 带注释的目录树

```
├── site/                   ← GitHub Pages 发布根（pages.yml 的 path: site）。全部由
│   │                          脚本重建，**勿手改**；必须自包含才能离线双击打开
│   ├── *.html              ← 10 个页面（CSS/JS/数据全部内联）
│   ├── assets/             ← 构建时从根 assets/ 整目录 copytree 而来
│   └── videos/{2024,2025,2026,scale}/ ← 本地视频，gitignored（三赛季约 30GB）
├── src/
│   └── theme.css           ← 全站设计系统**唯一权威源**：tokens + 组件 + 明暗主题
├── assets/
│   ├── crests/             ← 队徽 png（仅 status=verified 被页面渲染成 <img>）
│   ├── rules/              ← 规则手册插图（从 IFAB PDF 区域裁剪）
│   └── scale/              ← 尺度宣讲海报（必须放这里而非 site/assets/，否则被冲掉）
├── data/                   ← **入库**数据。本机产物一律进 data/local/
│   ├── cases-{season}.json ← 核心：判例 + 期次 + 判定结论 + 视频映射
│   ├── impact-{season}.json / match-scores-{season}.json ← 影响标注 / 人工查证比分
│   ├── teams.json          ← 队伍统一目录（脚本产物，勿手改）
│   ├── crest_overrides.json← 人工核验的队徽成果（**唯一权威源**，重建目录不丢失）
│   ├── crests.json         ← 兼容映射（脚本产物）
│   ├── scale.json / laws.json ← 尺度宣讲 / 规则章节（脚本产物，但必须入库供 CI 重建）
│   ├── uefa.json           ← UEFA 抓取产物（fetch_uefa.py parse 会整体覆写）
│   ├── uefa-zh.json        ← UEFA 中文译文层（**绝不可写进 uefa.json**）
│   ├── issues/{season}/    ← 各期官方页面原始 HTML 存档
│   └── local/              ← **整目录 gitignored**，clone 下来不存在
│       ├── laws/           ← IFAB 规则 PDF
│       ├── uefa-cache/     ← 抓取缓存（断点续抓）
│       ├── shots/          ← 页面截图
│       ├── logs/           ← 下载日志、校验结果、人工复核文本
│       └── scale-2024/     ← 2024 官方统一尺度材料包（3.3GB）
├── scripts/                ← **可执行入口脚本**（25 个）：凡直接在本层的都能 python 跑
│   ├── lib/                ← **只被 import，永不直接执行**（7 个模块）
│   │   ├── __init__.py     ← 必需：否则 lib 成为 PEP 420 命名空间包，跨 sys.path 合并
│   │   ├── paths.py        ← 路径常量**唯一权威源**
│   │   ├── theme.py        ← inject_theme() / topbar()；import 时即读 src/theme.css
│   │   ├── safe_http.py    ← 所有对外请求的安全层（白名单 + 强制 https + DoH + IP 钉扎）
│   │   ├── crest_catalog.py← 队徽目录读写与校验
│   │   └── classify_cls_{2024,2026}.py ← 纯数据分类表（无 I/O、无 __main__）
│   └── build_all.py        ← 一键重建全站
├── tests/test_integrity.py ← 完整性断言（裸跑 / pytest 皆可，fail-collecting）
├── docs/                   ← 本文 + 新赛季接入 + 队徽指南
├── .github/                ← workflows/pages.yml + Issue/PR 模板
├── pyproject.toml          ← 纯元数据（py-modules=[]，不打包任何模块）
├── requirements-build.txt  ← 构建依赖**唯一权威源**
├── .gitattributes          ← EOL 与二进制策略（保护 GBK 的 .bat）
├── CHANGELOG.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md / LICENSE / NOTICE.md
├── AGENTS.md / README.md
└── 启动合集网页.bat         ← Windows 一键本地服务，**必须存 GBK**
```

## 设计原则

**1. 生成物与源分离。** `site/` 下没有一个字节是手写的。改样式改 `src/theme.css`，
改内容改 `data/*.json` 或对应 builder，然后 `python scripts/build_all.py`。

**2. 入库数据 vs 本机产物。** 判据是「CI 需不需要它」与「clone 下来该不该有它」。
CI 需要 `data/scale.json` 和 `data/laws.json`（材料包与 PDF 都被忽略，靠提交的 JSON
重建页面），所以它们入库；3.3GB 材料包、抓取缓存、截图、日志只有本机需要，全部进
`data/local/`。往 `data/local/` 写文件的脚本**必须自己 `mkdir(parents=True,
exist_ok=True)`**——新 clone 时该目录不存在。

**3. 入口脚本 vs 共享层。** `scripts/` 平铺的是入口，`scripts/lib/` 是只被 import 的
模块。判据很硬：**有 `if __name__ == "__main__"` 或需要被人直接 `python` 调用的留在
`scripts/`，否则进 `lib/`**。唯一需要解释的是 `range_server.py`：它能独立运行，但通常
由 `serve.py` 以绝对路径 subprocess 拉起，因此留在 `scripts/`。

**4. 唯一权威源。** 同一事实只允许有一个出处，其他地方引用它：

| 事实 | 唯一权威源 |
|---|---|
| 仓库内路径常量 | `scripts/lib/paths.py` |
| 全站样式（tokens/组件/主题） | `src/theme.css` |
| 构建依赖 | `requirements-build.txt` |
| 队名归一（赞助冠名/笔误变体） | `generate_teams_catalog.py` 的 `ALIASES` |
| 人工核验的队徽成果 | `data/crest_overrides.json` |
| 判定计数回归基准 | `tests/test_integrity.py` 的 `EXPECTED` |

**5. 离线自包含。** 生成的页面运行时零外部依赖——不引 CDN、不引字体、不引 JS 库。
唯一例外是 `uefa.html` 以纯文字 + 外链收录 UEFA 判例（视频受 token 门禁与
`X-Frame-Options: DENY` 限制，无法本地化或嵌入）。

## 路径契约（改动前必读）

这些路径不是随便起的名字，它们被写死在数据文件、断言或外部系统里。

- **`site/`** — GitHub Pages 发布根，由 `.github/workflows/pages.yml` 的 `path: site`
  钉死。必须自包含：`assets/` 在构建时从根目录整目录 `copytree` 进来，所以尺度海报
  等新增图片要放**根 `assets/`**，直接放 `site/assets/` 会在下次构建被冲掉。
- **`assets/crests/`** — 这个字符串前缀写死在 `data/teams.json` 的每个 `path` 字段里，
  并被 `lib/crest_catalog.validate_catalog()` 断言。改目录名要同步重写整个 teams.json。
- **`site/videos/{season}/`** — 用户下载约 30GB 视频的约定位置，写死在
  `download_videos_parallel.py`、`verify_videos.py` 与全部页面的相对路径里。gitignored。
- **`src/theme.css`** — `lib/theme.py` 在 **import 时**就 `read_text()` 它（`THEME`
  常量被 `inject_theme()` 消费，没有惰性路径）。文件缺失或路径写错会在 import 期
  `FileNotFoundError`，一次放倒全部 7 个 builder、`build_all.py` 和 CI。
- **`scripts/`** — 三处硬编码：`build_all.py` 用 `SCRIPTS / script` 拼子进程命令，
  `serve.py` 以绝对路径拉起 `range_server.py`，`启动合集网页.bat` 第 18 行执行
  `python scripts/serve.py 8808`。重命名这个目录要同时改这三处。
- **`启动合集网页.bat`** — 必须存 **GBK**（cmd.exe 解析），用 `encoding="gbk"` 写。
  `.gitattributes` 钉了 `*.bat text eol=crlf`：cmd 的 `label`/`goto` 需要 CRLF。
  **故意不写** `working-tree-encoding=GBK`——提交的 blob 是裸 GBK 字节而非 UTF-8，
  声明工作区编码会让 git 在 add 时转码、在 checkout 时把 GBK 当 UTF-8 解码成乱码。
  同理**绝不**对它跑 `git add --renormalize`。
- **仓库外的 `../统一尺度宣讲原始包-{2025,2026}`** — 2025/2026 两季的官方材料包在
  `ROOT.parent`，**不在仓库里**，`.gitignore` 匹配不到它们（写规则也没用）。只有 2024
  包在仓库内的 `data/local/scale-2024/`。
- **`data/local/scale-2024/`** — `build_scale.py` 找 XML 的 glob 只容忍**恰好一层**
  嵌套：`pkg.glob("medias/chinese/xml")` 与 `pkg.glob("*/medias/chinese/xml")`。磁盘
  上的实际布局是双层（`scale-2024/2024-统一尺度-0220(1)/medias/...`），靠第二个 glob
  命中。移动这个目录时若目标已存在，`mv` 会把源塞进去变成 depth 2 → 两个 glob 全落空
  → 构建 `SystemExit`。
- **`requirements-build.txt`** — 第 1 行的 `# -*- coding: utf-8 -*-` 是必需的。pip 读
  requirements 文件时若无 BOM 会退回 `locale.getpreferredencoding()`，Windows 上是
  GBK，文件里的中文注释会让 pip 以 `UnicodeDecodeError` 退出码 2 失败。CI 跑在 UTF-8
  的 ubuntu 上所以从未暴露，但本机维护者会撞上。
- **两 URL 表** — `fetch_issues.py` 的 `ISSUES` 与 `parse_issues.py` 的 `ISSUE_URL`
  是同一套官方 URL 的**两份拷贝**（历史遗留），加新期必须同步改两处。
