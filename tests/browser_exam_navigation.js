// Exercise the real five-question and full-bank exams on the built site.
async startPage => {
  const url = new URL("quiz.html",startPage.url());
  const ctx = await startPage.context().browser().newContext({serviceWorkers:"block",reducedMotion:"reduce"});
  const check = (ok,message) => { if (!ok) throw Error(message); };
  await ctx.route(/^https?:/, route => new URL(route.request().url()).origin === url.origin ? route.continue() : route.abort());
  await ctx.addInitScript(()=>{ try { localStorage.setItem("cfa.lite","1"); } catch (_) {} });
  const page = await ctx.newPage(), errors = [];
  page.on("pageerror", e=>errors.push(e.message));
  page.on("dialog", d=>d.accept());
  const current = () => page.locator('#examDots [aria-current="step"]');
  const focusIndex = () => page.evaluate(()=>Number(document.activeElement.dataset.i));
  async function checkReturnTop(heading) {
    const scroller = page.locator("#scroll"), button = page.locator("#btnTop");
    await scroller.evaluate(n=>n.scrollTop=n.scrollHeight);
    if (!(await scroller.evaluate(n=>n.scrollTop > Math.min(240,n.clientHeight/2)))) return false;
    await button.waitFor();
    const fits = await button.evaluate(el=>{
      const r=el.getBoundingClientRect();
      return r.left>=0 && r.right<=innerWidth && r.top>=0 && r.bottom<=innerHeight && r.height>=44 &&
        el.contains(document.elementFromPoint(r.left+r.width/2,r.top+r.height/2));
    });
    check(fits, "return-to-top is clipped or covered");
    await button.focus(); await page.keyboard.press("Enter");
    await button.waitFor({state:"hidden"});
    check(await scroller.evaluate(n=>n.scrollTop)===0, "return action scrolled the wrong element");
    check(await page.locator(heading).evaluate(n=>n===document.activeElement), "return action lost focus");
    return true;
  }
  try {
    for (const [width,height] of [[320,640],[390,844],[768,1024],[1440,900]]) {
      await page.setViewportSize({width,height});
      for (const count of [5,0]) {
        await page.goto(url.href);
        await page.locator('#segMode [data-v="exam"]').click();
        await page.locator('#segCount [data-v="'+count+'"]').click();
        await page.locator('#segTimer [data-v="off"]').click();
        await page.locator("#btnStart").click();
        const dots = page.locator("#examDots button"), total = await dots.count();
        check(count ? total === 5 : total === await page.evaluate(()=>DATA.bank.length), "unexpected exercise size "+total);
        const nav = page.locator("#examNav"), summary = nav.locator("summary");
        const isOpen = () => nav.evaluate(n=>n.open);
        check(await isOpen() === Boolean(count), "long-exam navigation should start collapsed");
        check(await page.locator("#qCard").evaluate(e=>e.getBoundingClientRect().top) < height, "first question below first screen");
        check(!await page.locator("#btnTop").isVisible(), "top action shown at top");
        if (!count) {
          await summary.focus(); await page.keyboard.press("Enter");
          check(await isOpen(), "keyboard cannot expand numbers");
        }
        const grid = page.locator("#examDots");
        check(await grid.evaluate(n=>n.scrollWidth <= n.clientWidth && n.clientHeight <= innerHeight*.32+1), "number grid overflows");
        check(await page.locator("#scroll").evaluate(n=>n.scrollWidth <= n.clientWidth), "page overflow");
        check(await grid.locator('[tabindex="0"]').count() === 1, "many sequential number tab stops");
        await summary.focus(); await page.keyboard.press("Tab");
        check(await focusIndex()===0, "Tab should begin at current number");
        await page.keyboard.press("End");
        check(await focusIndex()===total-1 && await current().getAttribute("data-i")==="0", "End should only focus the last number");
        await page.keyboard.press("Enter");
        check(await focusIndex()===total-1 && await current().getAttribute("data-i")===String(total-1), "choosing a number lost keyboard focus");
        await page.keyboard.press("Home"); await page.keyboard.press("ArrowRight"); await page.keyboard.press("ArrowLeft");
        await page.keyboard.press("Enter");
        check(await focusIndex()===0, "cannot return to first question");
        const first = dots.first();
        check(await first.getAttribute("aria-label")==="第 1 题，未作答", "missing unanswered name");
        await page.locator("#qForm input").first().check();
        const answered = page.getByRole("button",{name:"第 1 题，已作答",exact:true});
        check(await answered.count()===1, "missing answered accessible name");
        check(await answered.evaluate(b=>getComputedStyle(b,"::after").content.includes("✓")), "answered state needs a visible shape");
        await answered.focus(); await page.keyboard.press("ArrowRight"); await page.keyboard.press("Enter");
        check(await current().getAttribute("data-i")==="1" && await answered.count()===1, "answered state lost when leaving question");
        await page.keyboard.press("Tab");
        check(!await page.evaluate(()=>document.activeElement.closest("#examDots") !== null), "Tab trapped in number grid");
        check(!(await page.locator("#qFb").isVisible()) && !(await page.locator("#scrResult").isVisible()), "navigation disclosed results");
        check(await page.evaluate(()=>new QuizRecords().state.history.length)===0, "navigation recorded a score");
        if (count===0 && width===320) {
          await grid.locator('[aria-current="step"]').focus();
          await page.keyboard.press("ArrowDown");
          const down = await focusIndex();
          check(down>2 && down<20, "vertical arrow did not follow visual columns");
          await page.keyboard.press("ArrowUp"); check(await focusIndex()===1, "vertical arrow unable to return");
          const longest = await page.evaluate(()=>round.qs.findIndex(q=>q.k==="th-t40"));
          check(longest>=0,"missing long-choice fixture");
          await dots.nth(longest).click();
          const boxes = await page.locator("#qForm .opt").evaluateAll(opts=>opts.map(el=>({
            width:el.getBoundingClientRect().width,height:el.getBoundingClientRect().height,
            inside:el.scrollWidth <= el.clientWidth+1 && el.getBoundingClientRect().right <= innerWidth
          })));
          check(boxes.length===4 && boxes.every(b=>b.inside) && boxes.some(b=>b.height>40),
            "long choice clipped instead of wrapping: "+JSON.stringify(boxes));
          check(await checkReturnTop("#qProgress"),"long exam should allow return to question heading");
        }
        await page.locator("#btnAbandon").click();
        // A desktop screen can fit the entire start form.
        const returned = await checkReturnTop(".page-h");
        if (width===320) check(returned,"mobile start form should scroll");
      }
    }
    await page.setViewportSize({width:320,height:640});
    await page.goto(url.href);
    await page.locator('#segMode [data-v="exam"]').click();
    await page.locator('#segCount [data-v="5"]').click();
    await page.locator("#btnStart").click();
    await page.locator("#examDots button").last().click();
    await page.locator("#btnSubmit").click();
    await page.locator("#scrResult").waitFor();
    check(await checkReturnTop("#rScore"),"results should return focus to the final score");
    check(!errors.length,errors.join("\n"));
    return "PASS short and full exams, keyboard question navigation, answered labels and return to top at four widths";
  } finally { await ctx.close(); }
}