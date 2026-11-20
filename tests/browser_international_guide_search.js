// Verify bilingual discovery, fragment placement and links without opening an external site.
async (startPage) => {
  const context = await startPage.context().browser().newContext({viewport:{width:390,height:844}});
  const base=new URL("./",startPage.url());
  if(base.protocol==="file:")await context.setOffline(true);
  const page=await context.newPage();
  try {
    for (const [query,href,expected] of [
      ["RAP Women's Euro 2017","rap.html#edition-WEURO-2017","http://bit.ly/rap-womens-euro-2017-pc"],
      ["2017 女足欧洲杯专题","rap.html#edition-WEURO-2017","http://bit.ly/rap-womens-euro-2017-pc"],
      ["Test din dommerviden","intl.html#resource-dbu","https://www.dbu.dk/turneringer-og-resultater/dommere/test-din-dommerviden/"],
      ["测测你的裁判知识","intl.html#resource-dbu","https://www.dbu.dk/turneringer-og-resultater/dommere/test-din-dommerviden/"],
    ]) {
      await page.goto(new URL("search.html",base).href);
      await page.locator("#q").fill(query);
      const result=page.locator('#sres a[href="'+href+'"]');
      await result.waitFor();
      if(await result.count()!==1)throw Error("资源应只返回一个入口："+query);
      await result.click();
      const card=page.locator(":target");
      if(!page.url().endsWith(href) || !(await card.getAttribute("tabindex")==="-1")
        || await card.locator('a[href="'+expected+'"]').count()!==1)
        throw Error("结果未定位到保留原始来源的卡片："+query);
      const y=await card.evaluate(el=>el.getBoundingClientRect().top);
      if(y<0||y>=844)throw Error("定位未进入手机可视区域："+query);
    }
    return "PASS RAP editions and curated resources by original/Chinese search";
  } finally {await context.close();}
}
