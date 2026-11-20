async (startPage) => {
  const base = new URL("./", startPage.url());
  const context = await startPage.context().browser().newContext({viewport:{width:390,height:844},reducedMotion:"reduce"});
  const page = await context.newPage();
  function check(value, message) { if (!value) throw Error(message); }
  try {
    for (const [name, label] of [["pro","PRO"],["conmebol","CONMEBOL"]]) {
      await page.goto(new URL("search.html",base).href);
      const [title, href] = await page.evaluate(label => {
        const docs = DOCS.filter(d => d[1] === label);
        const doc = docs[Math.floor(docs.length/2)];
        return [doc[2],doc[3]];
      }, label);
      await page.getByRole("searchbox",{name:"全站搜索"}).fill(title);
      const hit = page.locator('.sr[href="'+href+'"]');
      check(await hit.count() === 1 && !(await hit.getAttribute("target")), label+" 搜索仍跳到外站");
      await hit.click();
      await page.waitForURL(url => url.href.endsWith(href));
      const target = page.locator("article:target");
      check(await target.count() === 1 && await target.isVisible(), label+" 没有定位到相应资料");
      check(await target.evaluate(el => el.getBoundingClientRect().top >= document.querySelector(".topbar").getBoundingClientRect().bottom-1),
        label+" 命中条目被顶栏遮挡");
      const source = target.getByRole("link",{name:name === "pro" ? "官方页" : "官方分析", exact:true});
      check(/^https?:/.test(await source.getAttribute("href")), label+" 原有官方链接不可达");
    }
    return "PASS PRO 与 CONMEBOL 搜索在本地打开确切条目，保留官方出处";
  } finally { await context.close(); }
}
