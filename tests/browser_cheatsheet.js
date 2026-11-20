// Exercise actual Chromium disclosure semantics, text flow, fragments and print output.
async startPage => {
  const base = new URL("cheatsheet.html", startPage.url());
  const browser = startPage.context().browser();
  const ids = ["handball","force","dogso","var","cards","penalty","offside","restart","laws-2627"];
  function check(value, message) { if (!value) throw Error(message); }
  for (const mobile of [true,false]) {
    const context = await browser.newContext({
      viewport:mobile ? {width:390,height:844} : {width:1440,height:900},
      colorScheme:mobile ? "dark" : "light", reducedMotion:mobile ? "reduce" : "no-preference",
      serviceWorkers:"block",
    });
    context.setDefaultTimeout(10000);
    try {
      const page = await context.newPage();
      const cdp = await context.newCDPSession(page);
      async function disclosureTree() {
        const tree = await cdp.send("Accessibility.getFullAXTree");
        return tree.nodes.filter(node => node.role?.value === "DisclosureTriangle");
      }
      for (const id of ids) {
        await page.goto(base.href + "#card-" + id);
        const card = page.locator("article:target"), summary = card.locator("summary");
        check(await card.getAttribute("id") === "card-"+id && await card.evaluate(el => {
          const rect = el.getBoundingClientRect(); return rect.top >= 0 && rect.top < innerHeight;
        }), "碎片链接未定位 "+id);
        await page.keyboard.press("Tab");
        check(await summary.evaluate(el=>el === document.activeElement), "从链接按 Tab 未到翻卡控件 "+id);
        const title = await card.locator("h2").evaluate(h=>h.lastChild.textContent);
        await page.keyboard.press("Enter");
        const open = (await disclosureTree()).find(node=>node.name?.value === "翻回速记 "+title);
        check(open?.properties.some(p=>p.name === "expanded" && p.value.value === true), "无障碍树缺少展开状态 "+id);
        check(!await card.locator(".card-front").isVisible() && await card.locator(".card-back").evaluate(back =>
          back.clientHeight >= back.scrollHeight-1 && back.clientWidth >= back.scrollWidth-1), "细则存在嵌套滚动或溢出 "+id);
        check(await card.locator("h3").last().isVisible(), "细则末段不可见 "+id);
        if (mobile) check(await card.locator(".card-back").evaluate(e => getComputedStyle(e).animationName === "none"), "减少动态失效");
        await page.keyboard.press("Space");
        check(await summary.evaluate(el=>el === document.activeElement && !el.parentElement.open), "空格未翻回或焦点丢失 "+id);
        const closed = (await disclosureTree()).find(node=>node.name?.value === "查看细则 "+title);
        check(closed?.properties.some(p=>p.name === "expanded" && p.value.value === false), "无障碍树缺少收起状态 "+id);
      }
      check(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth), "速查卡撑开页面");
      const last = page.locator("article:target");
      await last.locator(".card-front li").first().click();
      const example = await last.locator("h3").first().innerText();
      check(await last.evaluate(el=>el.querySelector("details").open), "点卡片正文无法翻面");
      let tree = await cdp.send("Accessibility.getFullAXTree");
      check(tree.nodes.some(n=>n.role?.value === "heading" && n.name?.value === example), "展开细则未出现在朗读顺序中");
      await last.locator(".card-back h3").first().click();
      tree = await cdp.send("Accessibility.getFullAXTree");
      check(!tree.nodes.some(n=>n.role?.value === "heading" && n.name?.value === example), "已收起细则仍出现在朗读顺序中");

      if (!mobile) {
        await last.locator("summary").click();
        // Replace only the platform print dialog. page.pdf drives real beforeprint/afterprint and paged layout.
        await page.evaluate(()=>{window.print = () => {};});
        for (const mode of ["front","full"]) {
          await page.locator('[data-print="'+mode+'"]').click();
          const pdf = await page.pdf({preferCSSPageSize:true});
          const pages = (pdf.toString("latin1").match(/\/Type\s*\/Page\b/g) || []).length;
          check(mode === "front" ? pages === 1 : pages > 1, "打印页数异常 "+mode+" "+pages);
          check(await page.evaluate(()=>!document.documentElement.hasAttribute("data-print-front") &&
            document.querySelectorAll(".study-card details[open]").length === 1), "打印改变阅读状态 "+mode);
        }
      }
      await cdp.detach();
    } finally { await context.close(); }
  }
  return "PASS 九卡独立深链、移动/桌面键盘与原生读屏状态、长细则无内部滚动、减少动态及两种 A4 打印";
}
