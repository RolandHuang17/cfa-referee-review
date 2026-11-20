// A later mark can cover an earlier one at the very same text and offset.
async startPage => {
  const browser = startPage.context().browser();
  const url = new URL("rules.html#law-12", startPage.url()).href;
  const check = (ok, message) => { if (!ok) throw new Error(message); };
  async function open() {
    const context = await browser.newContext({viewport:{width:1440,height:900}, serviceWorkers:"block"});
    const page = await context.newPage();
    await page.goto(url);
    await page.locator("#noteWrap > summary").click();
    return {context, page};
  }
  async function exported(page) {
    const [download] = await Promise.all([page.waitForEvent("download"), page.locator("#btnExportN").click()]);
    const stream = await download.createReadStream();
    const chunks = [];
    for await (const chunk of stream) chunks.push(chunk);
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  }
  async function importMarks(page, highlights) {
    const text = JSON.stringify({app:"cfa-rules-2026", notes:{}, highlights});
    const notified = page.waitForEvent("dialog");
    await page.locator("#importFileN").setInputFiles({
      name:"规则备份.json", mimeType:"application/json", buffer:Buffer.from(text),
    });
    const dialog = await notified;
    const message = dialog.message();
    await dialog.accept();
    return message;
  }
  async function markSameWord(page, colour) {
    const rect = await page.evaluate(() => {
      const walker = document.createTreeWalker(document.querySelector("#secHtml"), NodeFilter.SHOW_TEXT);
      let count = 0;
      while (walker.nextNode()) {
        const node = walker.currentNode;
        for (let i = node.data.indexOf("队员"); i >= 0; i = node.data.indexOf("队员", i+2)) {
          if (++count !== 4) continue;
          node.parentElement.scrollIntoView({block:"center"});
          const range = document.createRange();
          range.setStart(node, i); range.setEnd(node, i+2);
          const box = range.getBoundingClientRect();
          return {left:box.left+1.5, right:box.right-1.5, y:box.top+box.height/2};
        }
      }
    });
    await page.mouse.move(rect.left, rect.y);
    await page.mouse.down();
    await page.mouse.move(rect.right, rect.y, {steps:8});
    await page.mouse.up();
    check(await page.evaluate(() => getSelection().toString()) === "队员", "未选中相同词组");
    await page.locator('#hlBar [data-c="' + colour + '"]').click();
  }
  const sorted = items => JSON.stringify([...items].sort((a,b) => a.ts - b.ts));
  const source = await open();
  try {
    await markSameWord(source.page, "y");
    // The original mark's own click handler may offer to delete it after dragging.
    source.page.on("dialog", dialog => dialog.dismiss());
    await markSameWord(source.page, "g");
    const records = (await exported(source.page)).highlights.sort((a,b) => a.ts - b.ts);
    check(records.length === 2 && records[0].color === "y" && records[1].color === "g" &&
      JSON.stringify(records[0].anchor) === JSON.stringify(records[1].anchor), "没有生成原位叠加的两个标注");
    for (const mode of ["original", "reverse", "partial"]) {
      const {page, context} = await open();
      try {
        if (mode === "partial") await importMarks(page, [records[0]]);
        const order = mode === "original" ? records : [...records].reverse();
        check((await importMarks(page, order)).includes(mode === "partial" ? "1 条" : "2 条"), "未按记录合并叠层");
        check((await importMarks(page, records)).includes("0 条"), "重复备份生成了额外标注");
        await page.reload();
        await page.locator("#noteWrap > summary").click();
        check(sorted((await exported(page)).highlights) === sorted(records), "还原后原始颜色、时间或锚点丢失");
        check(await page.locator("#secHtml mark.hl").count() === 1 &&
          await page.locator("#secHtml mark.hg").textContent() === "队员", "重新载入后上层颜色错误");
        const top = page.locator("#secHtml mark.hg");
        page.once("dialog", dialog => dialog.accept());
        await top.click();
        check(await page.locator("#secHtml mark.hy").textContent() === "队员" &&
          sorted((await exported(page)).highlights) === sorted([records[0]]), "移除上层后没有恢复原来的黄标");
        const old = {sec:"law-12", quote:"队员", color:"r", ts:12345};
        check((await importMarks(page,[old])).includes("1 条") && (await importMarks(page,[old])).includes("0 条"),
          "旧摘录备份没有保持导入幂等");
        check(await page.locator("#secHtml mark.hr").count() > 1 && await page.locator("#secHtml mark.hy").count() === 1,
          "无锚点旧摘录和精确锚点不能共存");
        check(sorted((await exported(page)).highlights) === sorted([old,records[0]]), "旧摘录字段改变");
      } finally { await context.close(); }
    }
    return "PASS 规则标注叠层真实下载与导入、反序及分次合并、重复导入、逐层删除和无锚点旧备份";
  } finally { await source.context.close(); }
}
