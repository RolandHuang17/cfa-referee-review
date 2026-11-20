// Run on the built site over file:// or HTTP. The optional local fixture is made
// from test_ifab_content.source_and_translation() with the two clauses reversed.
async (startPage) => {
  const base = new URL("./",startPage.url());
  const fixture = new URL(startPage.url()).searchParams.has("ifabFixture");
  const ctx = await startPage.context().browser().newContext({viewport:{width:390,height:844}});
  if (base.protocol==="file:") await ctx.setOffline(true);
  const page = await ctx.newPage(), errors = [];
  page.on("pageerror",e=>errors.push(e.message));
  function check(ok, message) {if (!ok) throw Error(message);}
  async function search(term) {
    await page.goto(new URL("search.html",base).href);
    await page.locator("#q").fill(term);
    const hits = page.locator('#sres a[href^="ifab.html#"]');
    check(await hits.count()===1,"IFAB 检索没有唯一到达目标：" + term);
    const href = await hits.getAttribute("href");
    await hits.click();
    check(new URL(page.url()).hash === new URL(href,base).hash,"点击结果丢失段落标识");
    return page.locator(":target");
  }
  try {
    const para = await search("被换下队员须在 10 秒内离场");
    check((await para.innerText()).includes("本协议对应第 3 章"),"没有打开限时换人的完整条款");
    const y = await para.evaluate(el=>el.getBoundingClientRect().top);
    check(y>=0 && y<844,"定位落在可见范围之外");
    await page.getByRole("button",{name:/英文原文/}).click();
    check((await para.innerText()).includes("within ten seconds"),"切换英文后的同一条款消失");
    const anchored = page.url();
    const fromEnglish = await search("substituted player to leave the field of play within ten seconds");
    check(page.url()===anchored && (await fromEnglish.innerText()).includes("within ten seconds"),"中英文搜索没有落在同一段");
    const question = await search("one corner flag is missing");
    const extra = question.locator("..");
    check(await extra.evaluate(el=>el.tagName==="DETAILS" && el.open),"配套 FAQ 跳转没有展开答案");
    check((await extra.innerText()).includes("lower levels of football"),"未显示匹配问题的官方答案");
    await page.locator("#btnEn").click();
    check((await extra.innerText()).includes("向有关当局提交报告"),"切换中文后配套 FAQ 的答案不可见");
    await page.goto(new URL("ifab.html#faq-q1",base).href);
    check(await page.locator("#faq-q1").evaluate(el=>el.open),"旧题库的主协议问答链接未展开");
    await page.goto(new URL("ifab.html#s1",base).href);
    check((await page.locator(":target h2").innerText()).includes("原则"),"旧主节书签失效");
    const printed = await page.evaluate(()=>{
      const items = [...document.querySelectorAll(".faq > details,details.xfaq")];
      const open = items.map(el=>el.open);
      dispatchEvent(new Event("beforeprint"));
      dispatchEvent(new Event("beforeprint"));
      const all = items.every(el=>el.open);
      dispatchEvent(new Event("afterprint"));
      return all && items.every((el,i)=>el.open===open[i]);
    });
    check(printed,"打印时遗漏答案或退出打印后展开状态变化");
    if (fixture) {
      await page.goto(new URL("ifab-source-change.html#s1",base).href);
      const body = page.locator("#s1 .panel");
      check((await body.innerText()).includes("Start again.") &&
        !(await body.innerText()).includes("重新开始。"),"错位版本的旧译误当成现行原文的译文");
      const old = body.locator("details.previous");
      await old.locator("summary").click();
      check((await old.innerText()).includes("旧版译文（待核对）") && (await old.innerText()).includes("甲与乙"),"未保留明确标识的旧译");
      await page.locator("#btnEn").click();
      check((await body.innerText()).includes("A & B"),"原文切换后出现 HTML 实体或整段隐藏");
    }
    check(!errors.length,errors.join("\n"));
    return "PASS IFAB bilingual paragraph and FAQ links, language modes, print and source version safeguards";
  } finally {await ctx.close();}
}
