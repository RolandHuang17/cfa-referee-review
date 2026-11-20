// Runs in a fresh browser profile under both HTTP and file://.
async startPage => {
  const base = new URL("./", startPage.url());
  const ctx = await startPage.context().browser().newContext({
    viewport:{width:390,height:844}, hasTouch:true, reducedMotion:"reduce", serviceWorkers:"block"
  });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  const check = (ok, message) => { if (!ok) throw Error(message); };
  const query = page.getByRole("searchbox", {name:"全站搜索"});
  const group = key => page.locator('#schips button[data-g="' + key + '"]');
  const hits = page.locator("#sres a.sr");
  const status = page.locator("#scount");
  const params = () => {
    const url = new URL(page.url());
    return url.hash.startsWith("#search?") ? new URLSearchParams(url.hash.slice(8)) : url.searchParams;
  };
  try {
    if (base.protocol === "file:") await ctx.setOffline(true);
    await page.goto(new URL("search.html?q=VAR&group=intl", base).href);
    check(await query.inputValue() === "VAR" && await group("intl").getAttribute("aria-pressed") === "true",
      "搜索深链未恢复输入和来源");
    const n = await page.evaluate(() => {
      const found = DOCS.filter(d => d[0] === "intl" && [d[1],d[2],d[4]].some(text => /VAR/iu.test(text)));
      return found.length;
    });
    check(await status.innerText() === "命中 " + n + " 份文档" && n > 60 && await hits.count() === 60, "当前来源命中计数或分页不符");
    const more = page.getByRole("button",{name:/继续显示/});
    await more.focus();
    await page.keyboard.press("Enter");
    check(await hits.count() === Math.min(n,120) && await hits.nth(60).evaluate(el => el === document.activeElement),
      "翻页后焦点没有落在新增内容");
    await query.fill("mLs");
    await group("intl").focus();
    await page.keyboard.press("Space");
    check(await group("intl").evaluate(el => el === document.activeElement), "切换来源后焦点丢失");
    check(await hits.count() > 0 && await page.locator("mark").evaluateAll(marks => marks.some(mark => mark.textContent === "MLS")),
      "大小写匹配时没有保留原文写法 MLS");
    check(params().get("q") === "mLs" && params().get("group") === "intl", "地址没有保留关键词与来源");
    await page.reload();
    check(await query.inputValue() === "mLs" && await group("intl").getAttribute("aria-pressed") === "true", "刷新丢失条件");
    await page.locator(".skip-link").first().focus();
    await page.keyboard.press("Enter");
    check(await page.locator("main").evaluate(el => el === document.activeElement) &&
      await query.inputValue() === "mLs" && params().get("group") === "intl", "跳到正文丢失离线搜索条件");
    await group("law").click();
    check(await hits.count() === 0 && await page.locator(".sempty").isVisible() && await group("law").innerText() === "竞赛规则 0",
      "无结果来源没有正确反馈");
    await group("all").click();
    await query.fill("[.+]");
    check(await hits.count() === 0 && await more.isHidden(), "将字面标点当作正则表达式");
    await query.fill("PRO");
    const result = hits.first();
    await result.click();
    await page.goBack();
    check(await query.inputValue() === "PRO" && await group("all").getAttribute("aria-pressed") === "true",
      "从资料返回后未恢复最后输入");
    await query.fill("");
    await group("all").click();
    check(params().get("q") === null && params().get("group") === null && (await status.innerText()).startsWith("共 "),
      "清空后仍携带旧条件");
    await page.keyboard.press("/");
    check(await query.evaluate(el => el === document.activeElement), "斜杠快捷键失效");
    await query.fill("越位");
    await page.reload();
    check(await query.inputValue() === "越位" && (await status.innerText()).startsWith("命中 "),
      "输入后立即刷新丢失查询");
    await group("intl").click();
    const clear = page.getByRole("button", {name:"清空搜索条件"});
    await clear.focus();
    await page.keyboard.press("Enter");
    check(await clear.isHidden() && await query.inputValue() === "" &&
      await group("all").getAttribute("aria-pressed") === "true" && await query.evaluate(el => el === document.activeElement) &&
      params().get("q") === null && params().get("group") === null, "一键清空未重置筛选、地址和焦点");
    check(await page.evaluate(() => document.documentElement.scrollWidth === innerWidth &&
      [...document.querySelectorAll("#schips button")].every(b => b.getBoundingClientRect().height >= 44)),
      "移动端溢出或触控目标过小");
    check(!errors.length, errors.join(" | "));
    return "PASS 可恢复查询、来源命中、原文大小写、字面标点、键盘翻页与返回";
  } finally { await ctx.close(); }
}
