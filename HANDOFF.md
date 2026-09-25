# HANDOFF — 交接给下一个 Agent

> 上一段工作在 commit `89b0a4f` 已提交并推送 GitHub（main）。
> 项目全貌、数据管线、硬约束先读 **AGENTS.md**（已更新为双赛季架构），本文件只列"还剩什么没做、怎么做"。

## 当前状态（已完成，勿重做）

- **五页架构已上线**：`index.html`（门户，build_portal.py）+ `season-2025.html`/`season-2024.html`（build_page.py，共用模板、赛季配置在脚本内 `SEASONS` 字典）+ `stats-2025.html`/`stats-2024.html`（build_stats.py，同样参数化）+ `rules.html`（划词高亮黄/绿/红 + 章节笔记 + 导出导入）。
- 所有页面顶栏导航统一（首页/24评议/25评议/得失盘点/竞赛规则）。
- 收藏/笔记 localStorage 键：`cfa2025.*`（沿用旧键保数据）、`cfa2024.*`；规则页 `cfa2026rules.hl`/`cfa2026rules.notes`。
- `data/match-scores-2024.json` 已入库影响统计涉及的45/45场比分；未纳入影响统计的场次仍可显示"待补"。
- 视频：`videos/2024/`（161个，9.92GB）+ `videos/2025/`（229个，15.9GB）均已下载完成（不进 git）。
- 生成页全部无残留占位符（已 grep 验证）；构建命令见 AGENTS.md 管线第 8-12 步。

## 剩余任务（按优先级）

### 1. 队徽补全（可见缺口最大）

已复跑采集并统一加入“广东广州豹”→“广州豹”归一化；维基无可靠队徽的球队仍保留首字占位，当前映射为34队。

`data/crests.json` 现只有 34 键。按 **build_page.py 的 NAME_VARIANTS 归一化后的规范名**，以下球队缺队徽（括号为涉及判例数）：

```
广州豹(9, cases里写"广东广州豹")  赣州瑞狮(12)  黑龙江冰城(10)  广州俱乐部(9)
无锡吴钩(9)  石家庄功夫(9)  南京城市(8)  大连鲲城(7)  广西蓝航(7)  泰安天贶(7)
廊坊荣耀之城(6)  日照宇启(6)  海门珂缔缘(6)  延边龙鼎(5)  海口名城(4)  湖南湘涛(4)
辽宁铁人(4)  重庆铜梁龙(4)  泉州亚新(3)  上海海港B队(2)  江西黑马青年(2)
沧州雄狮(2)  西安崇德荣海(2)  青岛红狮(2)  山东泰山金钢山(1)
```

做法（见 AGENTS.md「新增队徽/修正队徽」）：
- 优先编辑 `fetch_crests.py` 的 `TEAMS`/`MANUAL_FILE`（队名→维基文件标题）重跑；维基无词条的中乙新军用 `data/crest_manual.json`（队名→直接图片URL）。
- ⚠️ "广东广州豹"：把 `"广东广州豹": "广州豹"` 加进 **build_page.py 和 fetch_crests.py 两处 NAME_VARIANTS**（双处同步是硬约束），或直接在 crests.json 用原键。
- 新增误采（国旗/球衣模板）往 `NOISE`/`BLOCK_FILES` 加。
- 完成后重跑：`python fetch_crests.py && python build_portal.py && python build_page.py && python build_stats.py`，提交时 assets/crests/*.png 与 data/crests.json 一起进 git。

### 2. 2024 剩余 5 场比分（已完成）

已依据 2024 年中甲、 中乙联赛公开赛果页补齐，统计页已重建。

此前缺少的键如下（现已全部写入）：

```
中甲联赛|10|南京城市|重庆铜梁龙
中甲联赛|18|延边龙鼎|南京城市
中甲联赛|18|苏州东吴|无锡吴钩
中乙联赛|15|湖北青年星|大连鲲城
中乙联赛|28|赣州瑞狮|北京理工
```

来源记录为 `维基百科：2024年中国足球甲级联赛` / `维基百科：2024年中国足球乙级联赛`，并已重跑 `python scripts/build_stats.py 2024`。

### 3. 启动合集网页.bat 文案（小）

已完成，当前文案为“裁判学习平台”，文件保持GBK编码。

原文案已更新，无需再次修改。

### 4. README.md 更新（小）

已完成，已改为双赛季门户架构说明。

README 已更新为门户、双赛季合集、双赛季统计和规则页说明。

### 5. 浏览器回归（最后做）

按 AGENTS.md「AI 开发自验清单」逐项过：重点验证 rules.html 划词高亮（选中→浮动条→三色→刷新后仍在→点击删除）、章节笔记自动保存、season-2024 视频 `videos/2024/` 可播放、stats-2024 缺比分显示"待补"、`season-2024.html#case-19` 锚点直达。预览：`python scripts/range_server.py 8808`。

## 已踩过的坑（新 agent 必读）

1. **Mimosa 安全钩子**：本项目环境有 Mimosa hook——**不要用 Bash heredoc/echo 写源码文件**（会被拒绝），一律用 Write/Edit 工具；commit/push 时 hook 会警告"未完成完整扫描"，属兼容模式放行，继续即可，但不要对外宣称"项目已安全审计"。
2. `data/cases.json`、`data/impact.json` 等旧文件名已废——现在是 `cases-2025.json`/`cases-2024.json`/`impact.json`(2025)/`impact-2024.json`；**脚本全部赛季参数化**：`python xxx.py 2024|2025`。
3. 生成的 HTML 一律勿手改，改脚本后重建；`stats.html` 旧文件已删除，被 stats-2025.html 取代。
4. 比分键、impact 键里的队名是**归一化后**的（"浙江俱乐部绿城"不是"浙江"）；两赛季 NAME_VARIANTS 在 build_page.py 内。
5. 第20期(2024) URL 无 /zyls1/ 前缀、官方页面视频 URL 重复两次、http 混用——fetch/parse 脚本已处理，别"修复"掉。
