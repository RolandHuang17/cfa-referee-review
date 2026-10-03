## 这个 PR 做了什么

<!-- 1–3 句话。说明「为什么」比「改了什么」更重要。 -->

关联议题：

## 改动类型

- [ ] 数据修正（判例解析、分类、影响标注、比分、队名归一）
- [ ] 页面/交互
- [ ] 管线脚本
- [ ] 文档
- [ ] 仓库结构 / CI

## 数据类改动必填

<!-- 官方标题认定数与合集口径存在差异是已知现象，不要「顺手修」；确有异议请开议题讨论 -->

- 官方来源 URL：
- 受影响赛季与判例编号：
- 是否改动了 `referee_verdict`：<!-- 是/否；是则说明复核依据 -->

## 自验清单

<!-- 与 AGENTS.md「AI 开发自验清单」一致，只勾你实际跑过的项 -->

- [ ] `python scripts/build_all.py` 无报错
- [ ] `python tests/test_integrity.py` 通过
- [ ] 若动了判例分类或解析：同步更新 `tests/test_integrity.py` 的 `EXPECTED`
- [ ] 浏览器实测受影响的页面（不只是看构建成功）
- [ ] 若动了队徽：图片已**人工目检**（更名前旧徽/赞助商模板/国旗/他队徽是常见误配），
      成果已登记进 `data/crest_overrides.json`（`data/teams.json` 会被脚本覆盖）
- [ ] 若新增了赛季或数据源：两 URL 表（`fetch_issues.ISSUES` 与
      `parse_issues.ISSUE_URL`）已同步；域名已加入 `lib/safe_http.ALLOWED_HOSTS`

## 硬约束自查

- [ ] 页面未引入任何外部 CDN、字体或 JS 库（构建产物必须能双击离线打开）
- [ ] 对外网络请求走 `scripts/lib/safe_http.py`，未直接用 requests/urllib
- [ ] 未把视频、下载的 PDF、凭据或临时日志加入版本库
- [ ] `site/` 下的 HTML 全部由脚本重建，没有手改
- [ ] `启动合集网页.bat` 仍是 GBK 编码（如未改动此文件请忽略）

## 截图

<!-- 涉及页面视觉变化时必填；before / after 对照最好 -->
