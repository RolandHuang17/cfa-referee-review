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
    // This official Lanús article contains two separate decisions and clips.
    for (const [video, minute, other] of [["ONE6TOLhbIY","60","Kq9pP_NKwe4"],["Kq9pP_NKwe4","85","ONE6TOLhbIY"]]) {
      await page.goto(new URL("search.html",base).href);
      const href = "conmebol.html#article-52d5a488bd8a85c3-" + video;
      const query = await page.evaluate(href => DOCS.find(d => d[3] === href)?.[2], href);
      check(query?.includes(minute + "′"), "南美判例各自的时间未进索引");
      await page.getByRole("searchbox",{name:"全站搜索"}).fill(query);
      await page.locator('.sr[href="'+href+'"]').click();
      await page.waitForURL(url => url.href.endsWith(href));
      const target = page.locator(":target");
      const info = await target.evaluate(el => ({
        links:Array.from(el.querySelectorAll("a[href]"),a=>a.href),
        top:el.getBoundingClientRect().top, bar:document.querySelector(".topbar").getBoundingClientRect().bottom,
        source:el.closest("article")?.querySelector('a[href*="valle-vs-lanus/"]')?.href,
      }));
      check(info.links.some(url=>url.endsWith(video)) && !info.links.some(url=>url.endsWith(other)) &&
        info.source && info.top >= info.bar-1 && info.top < 844, "搜索落点未展示对应时间和影片");
    }
    return "PASS PRO 与 CONMEBOL 离线检索定位文章及独立判例时刻，保留各自的影片和官方出处";
  } finally { await context.close(); }
}
