// Run on the built site using playwright-cli run-code --filename.
async (startPage) => {
  const base = new URL("./", startPage.url());
  const browser = startPage.context().browser();
  const check = (ok, message) => { if (!ok) throw new Error(message); };

  for (const width of [390, 1280]) {
    const context = await browser.newContext({
      viewport: {width, height: width === 390 ? 844 : 900},
      serviceWorkers: "block", reducedMotion: "reduce"
    });
    if (base.protocol === "file:") await context.setOffline(true);
    await context.route(/^https?:/, route => {
      const origin = new URL(route.request().url()).origin;
      return origin === base.origin ? route.continue() : route.abort();
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));

    async function visibleHeading(href) {
      await page.waitForURL(url => url.href === new URL(href,base).href);
      const id = href.split("#")[1];
      await page.waitForFunction(id => {
        const target = document.getElementById(id);
        const heading = target?.querySelector(target.matches("article") ? ".hhead" : "h2");
        if (!heading) return false;
        const box = heading.getBoundingClientRect();
        const bar = document.querySelector(".topbar").getBoundingClientRect();
        const hit = document.elementFromPoint(box.left+box.width/2, box.top+box.height/2);
        return document.scrollingElement.scrollTop > 0 && box.height > 0 &&
          box.top >= bar.bottom - 1 && box.bottom <= innerHeight + 1 && heading.contains(hit);
      }, id, {timeout:5000});
    }

    async function searchThenOpen(href) {
      await page.goto(new URL("search.html",base).href);
      const title = await page.evaluate(url => DOCS.find(r => r[3] === url)[2],href);
      await page.getByRole("searchbox",{name:"全站搜索"}).fill(title);
      await page.locator('#sres a[href="'+href+'"]').click();
      await visibleHeading(href);
    }

    async function bookmark(href) {
      await page.goto(new URL(href,base).href);
      await visibleHeading(href);
    }

    try {
      for (const series of ["reckless", "highlights", "var"]) {
        await searchThenOpen("scale.html#h2025-"+series+"-1");
        check(await page.getByRole("tab",{selected:true}).getAttribute("data-season") === "2025",
          "旧尺度书签未恢复相应赛季");
      }
      await page.locator('.season-tab[data-season="2024"]').click();
      const group = await page.locator('.gnavcol[data-season="2024"] a.gnav').first().getAttribute("href");
      await page.locator('.gnavcol[data-season="2024"] a.gnav').first().click();
      await visibleHeading("scale.html"+group);
      const lastScale = await page.locator('.gcontent [data-season="2024"] .hcard').last().getAttribute("id");
      await bookmark("scale.html#"+lastScale);

      await searchThenOpen("rfef.html#r-ESP.2");
      const disclosure = page.locator("details.sx").first();
      await disclosure.locator("summary").click();
      check(await disclosure.evaluate(el => el.open),"RFEF 说明未能手动展开");
      const groupLink = page.locator(".gnavs a.gnav[href^='#']").first();
      const rfefGroup = await groupLink.getAttribute("href");
      await groupLink.click();
      await visibleHeading("rfef.html"+rfefGroup);
      check(await disclosure.evaluate(el => el.open),"组书签改变了已展开的说明");
      await disclosure.locator("summary").click();
      check(!await disclosure.evaluate(el => el.open),"RFEF 说明未能手动收起");
      const lastRfef = await page.locator(".gcontent .hcard").last().getAttribute("id");
      await bookmark("rfef.html#"+lastRfef);
      check(errors.length === 0, errors.join("\n"));
    } finally { await context.close(); }
  }
  return "PASS 尺度与 RFEF 搜索、分组和文末书签在手机及桌面均可读取";
}
