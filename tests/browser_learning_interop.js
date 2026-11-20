// Old releases wrote the entire notes map. Exercise that storage contract from a second tab.
async startPage => {
  const base = new URL("./", startPage.url()), browser = startPage.context().browser();
  function check(value, message) { if (!value) throw Error(message); }
  async function exported(page, selector) {
    return page.evaluate(async selector => {
      let blob;
      const create = URL.createObjectURL;
      URL.createObjectURL = value => { blob = value; return create.call(URL,value); };
      try {
        document.querySelector(selector).click();
        return JSON.parse(await blob.text());
      } finally { URL.createObjectURL = create; }
    },selector);
  }
  const texts = row => [row?.text,...(row?.conflicts || []).map(copy => copy.text)].filter(Boolean).sort().join(" / ");
  for (const rule of [false,true]) {
    const ctx = await browser.newContext({serviceWorkers:"block",viewport:{width:1440,height:900}});
    ctx.setDefaultTimeout(10000);
    const page = await ctx.newPage(), old = await ctx.newPage();
    const a = rule ? "law-11" : "229", b = rule ? "law-12" : "230";
    const file = rule ? "rules.html" : "season-2026.html", field = rule ? "#secNote" : "#noteBox";
    const exportButton = rule ? "#btnExportN" : "#btnExport";
    const url = id => new URL(file + "#" + (rule ? id : "case-"+id),base).href;
    async function open(id) {
      await page.goto(url(id));
      await page.waitForFunction(id=>noteEditor.id === id,id);
      if (rule && !await page.locator("#noteWrap").evaluate(el=>el.open)) await page.locator("#noteWrap summary").click();
    }
    async function originalSave(id, text) {
      await old.evaluate(({id,text}) => {
        const saved = JSON.parse(localStorage.getItem(noteStore.key) || "{}");
        if (text) saved[id] = {text,ts:Date.now()};
        else delete saved[id];
        localStorage.setItem(noteStore.key,JSON.stringify(saved));
      },{id,text});
    }
    try {
      await open(a);
      await old.goto(url(a));
      await page.locator(field).fill("新版课堂笔记");
      await exported(page,exportButton);
      await originalSave(a,"旧页补充的观察");
      const merged = (await exported(page,exportButton)).notes[a];
      check(merged.text === "旧页补充的观察" && texts(merged) === ["旧页补充的观察","新版课堂笔记"].sort().join(" / "),
        file+" 导出遗漏旧页刚写入的记录");
      const before = await page.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith(noteStore.prefix)).sort());
      await exported(page,exportButton);
      const after = await page.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith(noteStore.prefix)).sort());
      check(JSON.stringify(before) === JSON.stringify(after), file+" 重复观察旧记录新增了版本");

      await originalSave(b,"旧格式的第一段");
      await open(b); // This case has never had a versioned record.
      await originalSave(b,"另一窗口补写的第二段");
      await page.locator(field).fill("新版打开第一段后写的文字");
      const saved = (await exported(page,exportButton)).notes;
      check(texts(saved[b]) === ["新版打开第一段后写的文字","另一窗口补写的第二段"].sort().join(" / ") &&
        texts(saved[a]) === texts(merged),file+" 首次版本化或编辑其他记录时丢失旧页笔记");

      await open(a);
      const copies = page.locator("#noteCopies details");
      await copies.locator("summary").click();
      const confirm = page.waitForEvent("dialog");
      const click = copies.getByRole("button",{name:"保留编辑框文本并移除上述副本"}).click();
      await (await confirm).accept(); await click;
      check((await exported(page,exportButton)).notes[a].conflicts === undefined, file+" 明确移除的副本又出现");
      await page.locator(field).fill("");
      check(!(await exported(page,exportButton)).notes[a],file+" 主动清空后的笔记再次出现");
      await open(b);
      await originalSave(b,""); // An old whole-map snapshot can omit a versioned case.
      check(texts((await exported(page,exportButton)).notes[b]) === texts(saved[b]),file+" 旧快照缺项删除了独立版本");

      const ahead = Date.now() + 86400000;
      const future = {notes:{[a]:{text:"设备时间超前的笔记",ts:ahead}}, app:rule ? "cfa-rules-2026" : "cfa-referee-review-2026"};
      const notice = page.waitForEvent("dialog");
      await page.locator(rule ? "#importFileN" : "#importFile").setInputFiles({name:"时钟不同的备份.json",
        mimeType:"application/json",buffer:Buffer.from(JSON.stringify(future))});
      await (await notice).accept();
      await open(a);
      await page.locator(field).fill("");
      check(!(await exported(page,exportButton)).notes[a], file+" 清空后从超前时间戳的汇总复活了旧文字");
    } finally { await ctx.close(); }
  }
  return "PASS 新旧笔记并行编辑、跨记录兼容汇总、恢复副本去重、明确清空及旧快照缺项";
}
