// Run through the same public controls on file:// or a served deployment.
async startPage => {
  const base = new URL("./", startPage.url());
  const browser = startPage.context().browser();
  const ctx = await browser.newContext({viewport:{width:1440, height:900}});
  const privateTag = "周四内部复盘";
  const privateNote = "周六个人训练笔记";
  await ctx.addInitScript(() => {
    localStorage.setItem("cfa.lite", "1");
    Object.defineProperty(navigator, "clipboard", {configurable:true, value:{
      writeText:async text => {
        if (window.manualFilterCopy) throw new Error("clipboard unavailable");
        window.copiedFilters = text;
      },
    }});
  });
  const check = (ok, reason) => { if (!ok) throw new Error(reason); };
  const ids = page => page.locator(".prow").evaluateAll(rows => rows.map(row => row.dataset.seq).join(","));
  const page = await ctx.newPage();
  const other = await ctx.newPage();
  async function clickFacet(key, value) {
    const target = page.locator("#sidebar [data-" + key + "]").filter({visible:true});
    const index = await target.evaluateAll((buttons, [key, value]) =>
      buttons.findIndex(button => button.dataset[key] === value), [key, String(value)]);
    check(index >= 0, "找不到筛选项 " + key + " " + value);
    await target.nth(index).click();
  }
  async function copy() {
    await page.locator("#copyFilters").click();
    await page.waitForFunction(() => document.querySelector("#filterCopyStatus").textContent.includes("已复制"));
    return page.evaluate(() => window.copiedFilters);
  }
  try {
    for (const season of [2024, 2025, 2026]) {
      const file = "season-" + season + ".html";
      const url = new URL(file, base);
      await page.goto(url.href);
      const f = await page.evaluate(() => {
        const path = DATA.paths.find(p => p.seqs.some(seq => bySeq[seq].comp && bySeq[seq].home));
        const item = bySeq[path.seqs.find(seq => bySeq[seq].comp && bySeq[seq].home)];
        return {path:path.id, seq:item.seq, cat:item.category, v:item.v, comp:item.comp, team:item.home, issue:item.issue,
          total:DATA.cases.length, categoryCount:DATA.cases.filter(c => c.category === item.category).length};
      });
      await page.goto(url.href + "#cat-" + f.cat);
      await page.waitForFunction(() => document.querySelector("[data-remove=cat]"));
      const categoryIds = await ids(page);
      await page.reload();
      check(categoryIds.split(",").length === f.categoryCount && categoryIds === await ids(page) &&
        await page.locator("[data-cat][aria-pressed=true]").getAttribute("data-cat") === f.cat,
        season + " 分类入口刷新后结果或侧栏错误");

      const emptyCat = await page.evaluate(() => CATS.find(cat => !DATA.cases.some(c => c.category === cat.id))?.id);
      if (emptyCat) {
        await page.goto(url.href + "#cat-" + emptyCat);
        await page.waitForFunction(() => document.querySelector(".plist-empty"));
        check(await page.locator("[data-cat][aria-pressed=true]").getAttribute("data-cat") === emptyCat,
          "旧规则入口指向本季无判例分类时应保留该条件");
        await page.reload();
        check(await page.locator(".prow").count() === 0, "空分类刷新变成全部判例");
        await page.goto(url.href + "#cat-" + f.cat);
        await page.waitForFunction(() => !!document.querySelector(".prow"));
      }
      // Foreign links may carry stale facets. Match the UI's cross-competition team view.
      const imported = new URLSearchParams({comp:f.comp, team:f.team, path:"unknown", fav:"all"});
      await other.goto(url.href + "#filters?" + imported);
      await other.waitForFunction(team => document.querySelector("[data-remove=team]")?.textContent.includes(team), f.team);
      check(await other.locator("#activeFilters button").count() === 1 && await other.locator("#localFilterHint").isHidden(),
        "外来链接覆盖了球队跨赛事规则或恢复了个人筛选");

      await clickFacet("path", f.path);
      await clickFacet("cat", f.cat);
      check(await page.locator("[data-path][aria-pressed=true]").getAttribute("data-path") === f.path,
        season + " 选择分类使学习路径失去选中状态");
      await clickFacet("v", f.v);
      await clickFacet("issue", f.issue);
      await clickFacet("comp", f.comp);
      check(await page.locator("[data-remove=comp]").count() === 1, "缺少赛事条件");
      await clickFacet("team", f.team);
      check(await page.locator("[data-remove=comp]").count() === 0, "球队没有恢复跨赛事范围");
      await page.locator("#fSearch").fill(f.team);
      const expected = await ids(page);
      check(expected.split(",").includes(String(f.seq)), "筛选移除了已知符合条件的判例");
      check(await page.locator("#activeFilters button").count() === 6, "活动条件缺项");
      const share = await copy();
      const link = new URL(share, base);
      check(!share.startsWith("file:") && !link.search && link.hash.startsWith("#filters?"), "分享暴露文件路径或带入历史参数");
      const localBase = base.protocol === "file:" || ["localhost", "127.0.0.1", "[::1]"].includes(base.hostname);
      const canonical = await page.locator('link[rel="canonical"]').getAttribute("href");
      check(localBase ? link.origin + link.pathname === canonical : link.pathname === url.pathname,
        "本地分享未使用公开地址，或线上分享丢失部署子目录");
      check(await page.evaluate(() => seasonSharePage("https://school.example/study/season-2026.html?case=1",
        "https://other.example/season-2026.html", "2026") === "https://school.example/study/season-2026.html"),
        "独立部署分享未保留自己的域名与目录");
      await other.goto(url.href + link.hash);
      check(await ids(other) === expected, season + " 异页打开公开链接结果不同");
      await page.reload();
      check(await ids(page) === expected && await page.locator("#fSearch").inputValue() === f.team,
        season + " 刷新丢失组合条件");
      await page.locator('.prow[data-seq="' + f.seq + '"]').click();
      await page.reload();
      check(await ids(page) === expected && await page.locator(".prow.sel").getAttribute("data-seq") === String(f.seq),
        season + " 选中具体判例后刷新丢失组合");
      await page.locator("#fSearch").fill("赛季实测 + & #");
      check(await page.locator(".prow").count() === 0 && await page.locator(".plist-empty").isVisible(), "没有可读的空结果");
      const emptyLink = new URL(await copy(), base);
      await other.goto(url.href + emptyLink.hash);
      await other.waitForFunction(() => document.querySelector("#fSearch").value === "赛季实测 + & #");
      check(await other.locator(".prow").count() === 0, "带特殊字符的零结果链接没有还原");
      await page.locator("[data-remove=q]").click();
      check(await page.locator(".prow").count() > 0 && !(await page.locator("#fSearch").inputValue()), "单独清除搜索失败");
      await page.locator("#clearFilters").click();
      check(await page.locator(".prow").count() === f.total && await page.locator("#filterSummary").isHidden(), "清空没有恢复赛季全部判例");
    }

    const file = new URL("season-2026.html", base);
    await page.goto(file.href + "#case-229");
    await page.waitForFunction(() => document.querySelector(".prow.sel")?.dataset.seq === "229");
    await page.locator("#noteBox").fill(privateNote);
    await page.locator("#favBtn").click();
    await page.locator("#customTag").fill(privateTag);
    await page.locator("#addTag").click();
    await clickFacet("fav", "tag:" + privateTag);
    check(await page.locator("#copyFilters").isHidden() && await page.locator("#localFilterHint").isVisible(), "仅本机筛选不应可分享");
    const cat = await page.evaluate(() => bySeq[229].category);
    await clickFacet("cat", cat);
    const share = await copy();
    check(!decodeURIComponent(share).includes(privateTag) && !decodeURIComponent(share).includes(privateNote) &&
      new URL(share, base).hash === "#cat-" + cat, "链接包含私人内容或已收藏判例身份");
    await page.evaluate(() => { window.manualFilterCopy = true; });
    await page.locator("#copyFilters").click();
    check(await page.locator("#filterCopyText").inputValue() === share && await page.locator("#filterCopyText").isVisible(),
      "无剪贴板权限时手动复制的链接不同");
    await page.locator("#clearFilters").click();
    await clickFacet("fav", "note");
    check(await ids(page) === "229" && await page.locator("#noteBox").inputValue() === privateNote, "清空筛选删除或改变了笔记");
    await clickFacet("fav", "tag:" + privateTag);
    check(await ids(page) === "229" && await page.locator("#favBtn").getAttribute("aria-pressed") === "true",
      "清空筛选删除或改变了收藏和标签");

    await page.goto(file.href + "?case=229&hideans=1");
    check(await page.locator(".prow.sel").getAttribute("data-seq") === "229" && await page.locator("#ansGate").isVisible(),
      "旧挑战链接没有定位或显示了答案");
    await page.setViewportSize({width:390, height:844});
    await page.goto(file.href + "#cat-" + cat);
    await page.waitForFunction(() => !document.body.classList.contains("detail-open"));
    check(await page.locator(".plist").isVisible() && await page.locator("#clearFilters").isVisible(), "手机打开筛选链接没有显示结果列表");
    await page.locator("#fSearch").fill("零结果实测");
    await page.locator("#clearFilters").focus();
    await page.keyboard.press("Enter");
    check(await page.locator(".prow").count() === 240 && await page.evaluate(() => document.activeElement.matches(".prow")),
      "手机键盘清空没有恢复结果和焦点");
    return "PASS · 三季公开筛选、旧深链、零结果、个人数据边界、手动复制、手机键盘";
  } finally {
    await ctx.close();
  }
}
