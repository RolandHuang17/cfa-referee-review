// Run against the built site in a fresh Chromium profile, over HTTP or file://.
async (startPage) => {
  const base = new URL("./", startPage.url());
  const browser = startPage.context().browser();
  function check(value, message) { if (!value) throw Error(message); }
  async function download(tab, selector) {
    return tab.evaluate(async css => {
      let file;
      const original = URL.createObjectURL;
      URL.createObjectURL = blob => { file = blob; return original.call(URL, blob); };
      try {
        document.querySelector(css).click();
        return JSON.parse(await file.text());
      } finally { URL.createObjectURL = original; }
    }, selector);
  }
  for (const rule of [false,true]) {
    const context = await browser.newContext({serviceWorkers:"block", viewport:{width:1440,height:900}});
    const page = await context.newPage();
    const input = page.locator(rule ? "#secNote" : "#noteBox");
    const output = rule ? "#btnExportN" : "#btnExport";
    const ids = rule ? ["law-11","law-12"] : ["229","230"];
    const file = rule ? "rules.html" : "season-2026.html";
    async function open(id, reload = false) {
      if (reload) await page.reload();
      else await page.goto(new URL(file + "#" + (rule ? id : "case-" + id), base).href);
      await page.waitForFunction(k => typeof noteEditor !== "undefined" && noteEditor.id === k, id);
      const box = page.locator("#noteWrap");
      if (rule && !await box.evaluate(e => e.open)) await box.locator("summary").click();
    }
    async function importFile(data) {
      const alert = page.waitForEvent("dialog");
      await page.locator(rule ? "#importFileN" : "#importFile").setInputFiles({
        name:"另一设备的笔记备份.json",mimeType:"application/json",buffer:Buffer.from(JSON.stringify(data))
      });
      const dialog = await alert, message = dialog.message();
      await dialog.accept();
      return message;
    }
    try {
      const independent = rule ? "law-10" : "228";
      await open(independent);
      await input.fill("设备甲记录");
      const abroad = await download(page, output);
      const stamp = abroad.notes[independent].ts;
      abroad.notes[independent] = {text:"设备乙记录", ts:stamp+100, conflicts:[{text:"乙的副本",ts:stamp-1}]};
      check((await importFile(abroad)).includes("合并了 1 条"), file + " 新备份没有合并");
      const afterImport = (await download(page, output)).notes[independent];
      check(afterImport.text === "设备乙记录" && afterImport.conflicts.map(v=>v.text).sort().join("/") ===
        ["设备甲记录","乙的副本"].sort().join("/"), file + " 跨设备导入丢失不同文本");
      const versions = await page.evaluate(id=>noteStore.base(id, true), independent);
      check((await importFile(abroad)).includes("合并了 0 条") && await page.evaluate(
        ({id,versions}) => JSON.stringify(noteStore.base(id,true)) === JSON.stringify(versions), {id:independent,versions}),
        file + " 重复导入同一备份还在写版本");
      abroad.notes[independent] = {text:"旧设备另一份记录", ts:stamp-100};
      await importFile(abroad);
      const final = (await download(page, output)).notes[independent];
      check(final.text === "设备乙记录" && final.conflicts.some(v=>v.text === "旧设备另一份记录"),
        file + " 旧备份的不同文字未保留为可恢复副本");
      await open(ids[0]);
      await input.fill("第一次编辑");
      await open(ids[1]);
      await input.fill("第二条健康笔记");
      let saved = await download(page, output);
      check(saved.notes[ids[0]].text === "第一次编辑" && saved.notes[ids[1]].text === "第二条健康笔记",
        file + " 快速切换记录丢失输入");
      // Fail before the ordinary 800 ms debounce and request an actual navigation.
      await input.click();
      await page.evaluate(() => {
        const original = Storage.prototype.setItem;
        window.restoreNoteStorage = () => Storage.prototype.setItem = original;
        Storage.prototype.setItem = function(key, value) {
          if (key.includes(".notes")) throw new DOMException("配额不足","QuotaExceededError");
          return original.call(this, key, value);
        };
      });
      await input.fill("离开前的最后一句");
      const prompt = page.waitForEvent("dialog", {timeout:5000});
      await page.evaluate(() => { setTimeout(() => location.reload(), 0); });
      const dialog = await prompt;
      check(dialog.type() === "beforeunload", file + " 离开前没有保留草稿的机会");
      await dialog.dismiss();
      check(await page.locator("#retryWrite").isVisible() &&
        (await download(page, output)).notes[ids[1]].text === "离开前的最后一句", file + " 留在页面后无法备份草稿");
      await page.evaluate(() => restoreNoteStorage());
      await page.locator("#retryWrite").click();
      await open(ids[1], true);
      check(await input.inputValue() === "离开前的最后一句", file + " 草稿重试后未落盘");

      // A damaged version must not hide the healthy aggregate or a sibling revision.
      const broken = await page.evaluate(id => {
        const key = noteStore.base(id)[0];
        localStorage.setItem(key, "{截断");
        return key;
      }, ids[0]);
      await open(ids[1], true);
      saved = await download(page, output);
      check(saved.notes[ids[0]].text === "第一次编辑" && saved.notes[ids[1]].text === "离开前的最后一句",
        file + " 一个坏版本遮蔽了可读的笔记");
      const recovery = page.getByRole("button",{name:"导出异常记录原件"});
      check(await recovery.isVisible(), file + " 缺少异常记录导出入口");
      const original = await download(page, "#retryWrite + button");
      check(original.entries[broken] === "{截断", file + " 恢复资料缺少原始字节");
      await page.evaluate(() => localStorage.setItem(noteStore.key, "[坏汇总"));
      await open(ids[1], true);
      check(await input.inputValue() === "离开前的最后一句", file + " 损坏旧汇总后丢失健康独立版本");
      await input.fill("修复期间继续写笔记");
      await download(page, output);
      await open(ids[1], true);
      check(await input.inputValue() === "修复期间继续写笔记" && await page.evaluate(
        key => localStorage.getItem(noteStore.key) === "[坏汇总" && localStorage.getItem(key) === "{截断", broken),
        file + " 继续写入后覆盖了异常原件或新笔记");
    } finally { await context.close(); }
  }
  // Save two separate occurrences of a common word, then a selection spanning blocks.
  const context = await browser.newContext({serviceWorkers:"block"});
  context.setDefaultTimeout(10000);
  const rules = await context.newPage();
  const file = id => new URL("rules.html#" + id, base).href;
  async function selectText(test, color) {
    const quote = await rules.evaluate(test => {
      const body = document.getElementById("secHtml");
      const walk = document.createTreeWalker(body, NodeFilter.SHOW_TEXT), nodes = [];
      while (walk.nextNode()) nodes.push(walk.currentNode);
      const range = document.createRange();
      if (test === "cross") {
        const i = nodes.findIndex((n,i) => n.length > 100 && nodes.slice(i+1).some(v => v.length > 5));
        const first = nodes[i], last = nodes.slice(i+1).find(n => n.length > 5 && n.parentElement.closest("[id]") !== first.parentElement.closest("[id]"));
        range.setStart(first, 2);
        range.setEnd(last, 4);
      } else {
        const hits = [];
        for (const node of nodes) {
          let offset = node.data.indexOf("队员");
          while (offset >= 0) { hits.push([node,offset]); offset = node.data.indexOf("队员", offset+2); }
        }
        const [node, offset] = hits[test];
        range.setStart(node,offset); range.setEnd(node,offset+2);
      }
      range.startContainer.parentElement.scrollIntoView({block:"center"});
      const selection = getSelection();
      selection.removeAllRanges(); selection.addRange(range);
      body.dispatchEvent(new MouseEvent("mouseup", {bubbles:true}));
      return range.toString();
    }, test);
    await rules.locator('#hlBar button[data-c="' + color + '"]').click();
    return quote;
  }
  async function marks(tab) {
    return tab.locator("#secHtml mark.hl").evaluateAll(items => items.map(mark => {
      const prefix = document.createRange();
      prefix.selectNodeContents(document.querySelector("#secHtml"));
      prefix.setEndBefore(mark);
      return [prefix.toString().length,mark.className,mark.textContent];
    }));
  }
  async function importRules(tab, data) {
    const notified = tab.waitForEvent("dialog");
    await tab.locator("#importFileN").setInputFiles({name:"规则备份.json",mimeType:"application/json",buffer:Buffer.from(JSON.stringify(data))});
    const dialog = await notified, message = dialog.message();
    await dialog.accept();
    return message;
  }
  try {
    await rules.goto(file("law-12"));
    await selectText(3,"y"); await selectText(8,"g");
    const selected = await marks(rules);
    check(selected.length === 2 && selected[0][0] !== selected[1][0], "新高亮展开为全章匹配");
    await rules.reload();
    check(JSON.stringify(await marks(rules)) === JSON.stringify(selected), "重复词的选中位置或颜色在刷新后改变");
    const backed = await download(rules,"#btnExportN");
    const other = await browser.newContext({serviceWorkers:"block"});
    try {
      other.setDefaultTimeout(10000);
      const second = await other.newPage();
      await second.goto(file("law-12"));
      check((await importRules(second,backed)).includes("合并了 2 条") &&
        JSON.stringify(await marks(second)) === JSON.stringify(selected), "导入时合并了本来位于不同位置的高亮");
      check((await importRules(second,backed)).includes("合并了 0 条"), "重复导入高亮未正确去重");
      const shifted = structuredClone(backed); shifted.highlights = [{...backed.highlights[0],
        anchor:{block:"已经修订的段落",offset:0}}];
      await importRules(second,shifted);
      check(await second.locator("#hlMissing").isVisible() && (await marks(second)).length === 2,
        "正文变动后精确高亮被错误地套到其他段落");
      // Legacy records have no positions. Keep their historical whole-chapter display.
      await importRules(second,{app:"cfa-rules-2026",highlights:[{sec:"law-12",quote:"队员",color:"r",ts:10}]});
      check((await marks(second)).filter(m=>m[1].includes("hr")).length > 2, "旧备份失去历史全章匹配方式");
      const deletion = second.waitForEvent("dialog");
      const click = second.locator("mark.hl.hy").first().click();
      await (await deletion).accept();
      await click;
      const kept = (await download(second,"#btnExportN")).highlights;
      check(kept.length === 3 && kept.some(h=>h.color === "g"), "删除单处精确高亮影响了另一处");
    } finally { await other.close(); }

    // Use a clean section for the long sample to avoid overlap with the two selections above.
    await rules.goto(file("law-1"));
    const quote = await selectText("cross","r");
    const before = await marks(rules);
    check(quote.length > 80 && before.length > 1 && before.map(m=>m[2]).join("") === quote,
      "跨段长选区未完整上色");
    await rules.reload();
    check(JSON.stringify(await marks(rules)) === JSON.stringify(before), "长选区刷新后被截断或跨段消失");
  } finally { await context.close(); }
  return "PASS 赛季和规则笔记快速切换、离开前写失败保留草稿、异常隔离及原件恢复、多设备备份合并、跨段完整高亮和旧备份匹配";
}
