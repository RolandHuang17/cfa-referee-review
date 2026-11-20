// The "笔记" facet must use the draft being edited and keep the active editor usable.
async startPage => {
  const browser = startPage.context().browser();
  const url = new URL("season-2026.html", startPage.url()).href;
  const check = (value,message) => { if (!value) throw Error(message); };
  async function setup(mobile) {
    const ctx = await browser.newContext({viewport:mobile ? {width:390,height:844} : {width:1440,height:900},
      serviceWorkers:"block",reducedMotion:"reduce"});
    await ctx.addInitScript(() => { try { localStorage.setItem("cfa.lite","1"); } catch (_) {} });
    const page = await ctx.newPage();
    await page.goto(url + "#case-229");
    return {ctx,page};
  }
  async function expectRows(page, ids) {
    await page.waitForFunction(ids => {
      const rows = [...document.querySelectorAll(".prow")].map(row => row.dataset.seq).sort();
      return JSON.stringify(rows) === JSON.stringify(ids) && +document.querySelector("#shownCount").textContent === ids.length;
    }, ids);
  }
  const {ctx,page} = await setup(false);
  try {
    const note = page.locator("#noteBox"), facet = page.locator('[data-fav="note"]');
    await note.fill("判例229刚输入的笔记");
    await facet.click();
    await expectRows(page, ["229"]);
    check(await note.inputValue() === "判例229刚输入的笔记", "使用笔记筛选后草稿丢失");
    await page.goto(url + "#case-230");
    await page.waitForFunction(() => document.querySelector(".prow.sel")?.dataset.seq === "230");
    await note.fill("判例230的独立笔记");
    await page.goto(url + "#case-229");
    await facet.click();
    await expectRows(page, ["229","230"]);
    await note.fill("");
    await expectRows(page, ["230"]);
    check(await note.evaluate(el => el === document.activeElement) && await note.inputValue() === "",
      "自动保存时清空笔记导致输入焦点转到另一例");
    await page.keyboard.type("VAR");
    await expectRows(page, ["229", "230"]);
    check(await note.evaluate(el => el === document.activeElement && el.selectionStart === 3 && el.selectionEnd === 3),
      "重新输入后没有恢复匹配，或光标被重置");
    await note.fill("");
    await expectRows(page, ["230"]);
    await note.press("Tab");
    await page.waitForFunction(() => document.querySelector(".prow.sel")?.dataset.seq === "230");
    check(await note.inputValue() === "判例230的独立笔记", "退出已清空的编辑器后没有回到下一份笔记");
    // A just-cleared note from the unfiltered list must also be excluded immediately.
    await facet.click();
    await note.fill("");
    await facet.click();
    await expectRows(page, []);
    check(await page.locator(".plist-empty").isVisible(), "清空最后一条后的列表提示缺失");
  } finally { await ctx.close(); }

  const shared = await setup(false);
  try {
    const reader = shared.page;
    const writer = await shared.ctx.newPage();
    await writer.goto(url + "#case-230");
    async function writeInOtherTab(text) {
      await writer.bringToFront();
      const field = writer.locator("#noteBox");
      await field.click();
      await field.fill(text);
    }
    await reader.bringToFront();
    await reader.locator('[data-fav="note"]').click();
    await expectRows(reader, []);
    await writeInOtherTab("另一页的230笔记");
    await expectRows(reader, ["230"]);
    check(await reader.locator("#noteBox").inputValue() === "另一页的230笔记", "另一页新增笔记后没有定位到唯一结果");

    // Save on the writer without taking focus or moving the reader's caret.
    await writer.goto(url + "#case-229");
    await writeInOtherTab("另一页的229笔记");
    const input = reader.locator("#noteBox");
    await reader.bringToFront();
    await input.click();
    await input.fill("甲页仍在编辑");
    await input.press("Home");
    await input.press("ArrowRight");
    await writer.evaluate(() => document.getElementById("btnExport").click());
    await expectRows(reader, ["229", "230"]);
    check(await input.evaluate(el => el === document.activeElement && el.value === "甲页仍在编辑" && el.selectionStart === 1),
      "另一页新增条目时丢失本页草稿或光标");
    await reader.waitForFunction(() => document.getElementById("noteStatus").textContent === "已保存");
    await writeInOtherTab("");
    await expectRows(reader, ["230"]);
    await writer.goto(url + "#case-230");
    await writeInOtherTab("");
    await expectRows(reader, []);
    check(await input.isVisible() && await input.evaluate(el => el === document.activeElement && el.value === "甲页仍在编辑"),
      "另一页移除当前条目时挤走本页正在使用的编辑器");
    await reader.bringToFront();
    await input.click();
    await input.fill("甲页继续记录");
    await expectRows(reader, ["230"]);
    check(await input.evaluate(el => el === document.activeElement && el.value === "甲页继续记录"),
      "其他窗口删除后，本页继续输入没有保存");
  } finally { await shared.ctx.close(); }

  const mobile = await setup(true);
  try {
    const p = mobile.page, note = p.locator("#noteBox");
    await note.fill("手机上的练习笔记");
    await p.locator("#btnSb").click();
    await p.locator('[data-fav="note"]').click();
    await p.keyboard.press("Escape");
    await expectRows(p, ["229"]);
    await p.locator(".prow").click();
    await note.fill("");
    await expectRows(p, []);
    check(await note.isVisible() && await note.evaluate(el => el === document.activeElement),
      "手机空列表遮住了仍在输入的编辑器");
    await note.fill("手机继续记录");
    await expectRows(p, ["229"]);
    await p.locator("#mobileBack").click();
    check(await p.locator(".plist").isVisible() && await p.locator(".prow").getAttribute("data-seq") === "229",
      "手机返回列表时遗漏了重新填入的笔记");
  } finally { await mobile.ctx.close(); }
  return "PASS 待保存增删、已过滤时的自动保存、单项与多项、双页增删与草稿、桌面光标及手机继续编辑";
}
