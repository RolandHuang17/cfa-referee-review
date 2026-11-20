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
  return "PASS 赛季和规则笔记快速切换、离开前写失败保留草稿、异常隔离及原件恢复、多设备备份合并与去重";
}
