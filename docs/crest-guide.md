# 队徽补录与核验指南

本项目**故意不做自动猜图**。历史上自动匹配曾把错队徽放上站（跨页面混选让北京国安/
上海申花的队徽错配到佛山南狮/湖北青年星/温州/嘉定汇龙），此后改成「自动采集只作候选，
必须人工目检，宁缺毋滥回退文字徽章」。这条红线优先于覆盖率。

当前状态：111 支标准队伍中 72 支有已核验的真实队徽，39 支显示文字徽章（历史队、
女足与全运会省队为主）。**人工补录已于 2026-10 止步，39 是设计内终态，不是待修的
bug。**

## 体系构成

| 部件 | 作用 |
|---|---|
| `data/teams.json` | 队伍统一目录：标准名、别名、slug、队徽路径、来源、状态。**脚本产物，勿手改** |
| `data/crest_overrides.json` | 人工核验成果登记。**唯一权威源**——`generate_teams_catalog.py` 重建时会合并它，所以手改 teams.json 会丢，改这里不会 |
| `data/crests.json` | 兼容映射（脚本产物） |
| `scripts/lib/crest_catalog.py` | `normalize_team()` / `load_catalog()` / `validate_catalog()` |
| `scripts/generate_teams_catalog.py` | 读全部 `cases-*.json` + `crest_overrides.json` 重建 teams.json |
| `scripts/fetch_crests.py` | **校验器，不联网**（名字有误导）：检查 verified 项的文件、路径前缀与来源元数据是否齐全 |
| `scripts/fetch_crests_online.py` | 采集候选：中文维基本队词条图片，严格限本队词条防跨队误配 |
| `scripts/fetch_crests_round2.py` | 采集候选第二轮：Wikimedia Commons + 英文维基 |
| `assets/crests/{slug}.png` | 图片落地位置 |

## 路径 A：自动采集 + 人工目检

```bash
python scripts/fetch_crests_online.py     # 中文维基
python scripts/fetch_crests_round2.py     # Commons + 英文维基
```

两个脚本都走 `lib/safe_http.py`（域名白名单 + 强制 https + DoH 校验公网 IP + IP
钉扎），下载后写入 `assets/crests/`。**采完必须逐张看图**，确认后才算 verified。

采集时的已知环境坑：

- **要查两个 host**：队徽文件可能在 Wikimedia **Commons** 而不在 zh.wikipedia，只查
  zh 会返回空 pages，容易被误判成「该队无队徽」。
- **本机网络抖动**：`safe_http` 的 IP 钉扎连接在 TUN 代理下常报
  `SSL: UNEXPECTED_EOF_WHILE_READING`。当前脚本的 `retries=1`，抖动严重时抓不全属
  正常现象，重跑即可；若要提高成功率，调大 `retries`（注意 `retries=0` 等于从不发
  请求，曾是 `fetch_crests_online.api()` 的 bug）。
- **重定向的 File 标题**：文章 images 列表里的 File 标题可能本身是重定向，查
  imageinfo 时不带 `redirects=1` 会返回 missing。
- 懂球帝等非维基源已被穷尽：DoH 解析失败会被 `safe_http` 拦截，不要试图绕过。

## 路径 B：纯人工补录

1. 找到可靠的官方或维基来源图片，下载为 png 存到 `assets/crests/{slug}.png`
   （slug 取 teams.json 里该队的 `slug` 字段，保持唯一）。
2. 在 `data/crest_overrides.json` 登记：
   ```json
   "标准队名": {
     "path": "assets/crests/{slug}.png",
     "source_url": "https://…",
     "source_type": "wikipedia | commons | official",
     "status": "verified"
   }
   ```
   `path` 必须以 `assets/crests/` 开头——这个前缀被写死在 `teams.json` 与
   `validate_catalog()` 的断言里。`source_url` 与 `source_type` 缺一个就校验失败。
   用户人工投图而无公开来源页时，`source_type` 记 `manual`、`source_url` 记
   `manual:user-provided-<日期>`，不要编造 URL。
3. **B 队不单独找图**：直接复用母队 `path`，并在 `source_url` 注明「B队复用母队徽」
   （先例：山东泰山B队、成都蓉城B队、大连英博B队、成都蓉城希拉谷、山东泰山金钢山）。
4. 重建并校验：
   ```bash
   python scripts/generate_teams_catalog.py
   python scripts/fetch_crests.py
   python scripts/build_all.py
   python tests/test_integrity.py
   ```

## 目检清单（每张图都要过）

- [ ] 是**本俱乐部**的队徽，不是同名异地或同省他队
- [ ] 是**当前**队徽，不是更名前/前身球队的旧徽（曾把广州富力旧徽当广州豹、
      石家庄永昌旧徽当沧州雄狮）
- [ ] 不是赞助商广告模板图、不是国旗、不是联赛标志、不是队旗照片
- [ ] 不是省队/协会徽被误当俱乐部徽
- [ ] 图片清晰、主体居中、背景透明或干净（文字徽章旁并排显示时不违和）
- [ ] `source_url` 打开后确实指向这张图的来源页

**任何一项存疑 → 不标 verified，保持 fallback 文字徽章。** 文字徽章由
`teams.json` 的 `initials` / `fg` / `bg` 渲染，是完整的设计内行为，不是降级。

## 队名归一

新队名（赞助冠名、笔误变体、更名）只改**一处**：`generate_teams_catalog.py` 的
`ALIASES`。旧的 `build_page.py` / `fetch_crests.py` 双处 `NAME_VARIANTS` 已废弃，
不要重新引入第二张映射表。

更名链用 `teams.json` 的 `parent` 字段表达（如 山西崇德荣海 → 西安崇德荣海），让统计
页能把前后身球队的记录串起来。

## 常见问题

**队徽显示成「?」徽章** — 该队名没登记进 teams.json。检查 `cases-*.json` 里的原始
队名是否需要加进 `ALIASES`，然后重跑 `generate_teams_catalog.py`。

**改了 teams.json 但下次构建被冲掉** — 预期行为，它是脚本产物。改
`crest_overrides.json`。

**`fetch_crests.py` 报「队徽文件不存在」** — `crest_overrides.json` 里登记的 `path`
与 `assets/crests/` 下的实际文件名不一致，或 png 没提交。

**图片显示了但明显是别的队** — 立刻改回 `status: fallback` 并从 `assets/crests/`
删掉该 png，然后重跑 `generate_teams_catalog.py` + `build_all.py`。
