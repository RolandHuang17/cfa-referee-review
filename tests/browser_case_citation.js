// Run from either the local preview or a double-clicked HTML page.
async (startPage) => {
  const base = new URL("./", startPage.url());
  const context = await startPage.context().browser().newContext({viewport:{width:390,height:844}});
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", err => errors.push(err.message));
  const check = (ok, message) => { if (!ok) throw Error(message); };
  const button = page.locator("#citationCopy");
  const field = page.locator("#citationText");
  const status = page.locator("#citationStatus");
  const goto = path => page.goto(new URL(path, base).href);
  const deny = () => page.evaluate(() => {
    Object.defineProperty(navigator, "clipboard", {configurable:true, value:{
      writeText() { return Promise.reject(new Error("permission denied")); }
    }});
  });
  async function manualCopy() {
    await button.click();
    await field.waitFor({state:"visible"});
    check(await field.evaluate(el => el === document.activeElement &&
      el.selectionStart === 0 && el.selectionEnd === el.value.length), "手动复制未完整选中文字");
    return field.inputValue();
  }
  try {
    await goto("season-2025.html#case-183");
    await page.locator("#noteBox").fill("私人备课笔记 C183");
    const evidence = await page.evaluate(() => {
      const c = DATA.cases.find(row => row.seq === 183);
      return {official:c.conclusion, source:DATA.issues[c.issue].url,
        supplement:DATA.issues[c.supplementIssue].url, edition:DATA.rulebookEdition};
    });
    await deny();
    const text = await manualCopy();
    check(await page.locator("#dFoot a").nth(1).getAttribute("href") === evidence.supplement, "详情未链接补充认定原期");
    check(text.includes(evidence.official) && text.includes(evidence.source) && text.includes(evidence.supplement),
      "引用缺少完整的足协认定、来源或补充期");
    check(text.includes("现行规则参考 · " + evidence.edition) && text.includes("rules.html#law-"), "引用缺少现行版本与规则链接");
    check(text.includes("season-2025.html#case-183") && !text.includes("私人备课笔记") &&
      !text.includes("file:") && !text.includes("127.0.0.1"), "引用包含本机信息或无法定位");
    await goto("season-2025.html?case=188&hideans=1#case-188");
    await deny();
    check(await button.innerText() === "复制判例出处", "隐藏时按钮未说明只复制出处");
    const blind = await manualCopy();
    check(blind.includes("?case=188&hideans=1#case-188") && blind.includes("第 27 期补充认定") &&
      !blind.includes("足协评议组认定") && !blind.includes("现行规则参考"), "盲判引用泄露认定或缺少来源");
    await page.locator("#ansRevealBtn").click();
    check(await field.isHidden() && (await field.inputValue()) === "", "揭晓后仍保留旧的复制区");
    check((await manualCopy()).includes("足协评议组认定"), "已揭示的认定未能复制");
    // A pending clipboard operation can settle after the reader has switched cases.
    await page.evaluate(() => {
      navigator.clipboard.writeText = () => new Promise((resolve, reject) => { window.rejectCopy = reject; });
    });
    await button.click();
    await page.evaluate(() => { select(189); window.rejectCopy(new Error("denied")); });
    check(await field.isHidden() && !(await status.innerText()), "上一条认定覆盖下一题的隐藏状态");
    await goto("season-2024.html#case-112");
    await deny();
    check((await manualCopy()).includes("未单列评议认定"), "无单独认定的案例被当作有结论");
    await page.locator("#btnLite").click();
    check((await manualCopy()).includes("season-2024.html#case-112"), "轻量版未能复制当前判例");
    if (base.protocol !== "file:") {
      await context.grantPermissions(["clipboard-read","clipboard-write"], {origin:base.origin});
      await goto("season-2026.html#case-1");
      await page.bringToFront();
      await button.click();
      await page.waitForFunction(() => document.getElementById("citationStatus").textContent === "已复制");
      const copied = await page.evaluate(() => navigator.clipboard.readText());
      check(copied.includes("season-2026.html#case-1") && copied.includes("期足协原文"), "剪贴板没有当前引用");
    }
    check(!errors.length, errors.join("\n"));
    return "PASS 三季判例出处、足协原文与补充期、盲判链接、离线手动复制、异步切题";
  } finally { await context.close(); }
}
