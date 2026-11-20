// Run with playwright-cli run-code --filename tests/browser_quiz_records.js on the generated site.
async (startPage) => {
  const browser = startPage.context().browser();
  const context = await browser.newContext();
  const url = new URL("quiz.html",startPage.url()).href;
  const a = await context.newPage(), b = await context.newPage(), errors = [];
  for (const tab of [a,b]) {
    tab.on("pageerror",e=>errors.push(e.message));
    tab.on("dialog",d=>d.accept());
  }
  const check = (ok,msg) => { if (!ok) throw Error(msg); };
  async function roundFor(tab, id, mode) {
    await tab.evaluate(({id,mode}) => {
      sel.mode = mode; sel.timer = "off"; startRound([BANK[id]]);
    },{id,mode});
  }
  async function answer(tab,id,mode,correct) {
    await roundFor(tab,id,mode);
    if (correct) {
      const index = await tab.evaluate(()=>BANK[round.qs[0].k].ans);
      await tab.locator("#qForm .opt").nth(index).click();
    }
    await tab.locator("#btnSubmit").click();
  }
  async function importFile(tab, contents) {
    const notice = tab.waitForEvent("dialog");
    await tab.locator("#importFile").setInputFiles({name:"错题本.json",mimeType:"application/json",
      buffer:Buffer.from(JSON.stringify(contents))});
    return (await notice).message();
  }
  try {
    await Promise.all([a.goto(url),b.goto(url)]);
    const ids = await a.evaluate(()=>DATA.bank.filter(q=>q.t==="var").slice(0,3).map(q=>q.k));
    const [first,second,third] = ids;
    await Promise.all([answer(a,first,"exam",false),answer(b,second,"exam",false)]);
    await Promise.all([answer(a,first,"exam",false),answer(b,first,"exam",false)]);
    await a.reload();
    await a.locator("#btnWb").click();
    check(await a.locator("#wbList .wbitem").count()===2,"不同题的错题本记录被覆盖");
    check(await a.locator("#histList .histrow").count()===4,"并行交卷的历史缺失或重复");
    await a.locator('#wbList [data-star="'+first+'"]').click();
    await Promise.all([answer(a,first,"practice",true),answer(b,first,"practice",true)]);
    const state = await b.evaluate(id=>{
      const state = new QuizRecords().state;
      return {wrong:state.wrong[id],stat:state.stats[id]};
    },first);
    check(state.stat.w===3 && state.stat.r===2 && state.wrong.wrong===3 &&
      state.wrong.star && state.wrong.stage===2,"同题并发的次数、收藏或复习档位丢失");

    await a.reload();
    const baseline = await a.evaluate(()=>JSON.stringify({...localStorage}));
    const bad = {app:"cfa-referee-quiz",wrong:{[first]:{t:"var",last:Date.now()+1000},[third]:null}};
    check((await importFile(a,bad)).includes("导入失败"),"混合损坏备份未被拒绝");
    check(await a.evaluate(()=>JSON.stringify({...localStorage}))===baseline,"导入失败后有部分写入");
    const old = {wrong:{[third]:{t:"var",star:true,your:"0",wrong:1,correct:["旧版答案"]}}};
    check((await importFile(a,old)).includes("合并了 1 条"),"旧版备份未导入");
    check((await importFile(a,old)).includes("合并了 0 条"),"重复导入重复记账");

    await a.reload();
    await a.locator("#btnWb").click();
    const exported = await a.evaluate(async()=>{
      const original = URL.createObjectURL;
      let blob;
      URL.createObjectURL = value => {blob=value;return original.call(URL,value);};
      try {
        document.getElementById("btnExport").click();
        return JSON.parse(await blob.text());
      } finally { URL.createObjectURL = original; }
    });
    check(exported.app==="cfa-referee-quiz" && Object.keys(exported.wrong).length===3 &&
      exported.wrong[third].correct==="旧版答案","标准错题备份未包括已合并记录");

    if (new URL(url).protocol !== "file:") {
      const portal = await context.newPage();
      await portal.goto(new URL("index.html",url).href);
      check(await portal.locator("#msDue b").textContent() === "2", "门户到期数与错题本不一致");
      await answer(b,second,"practice",true);
      await portal.waitForFunction(()=>document.querySelector("#msDue b").textContent === "1");
      await portal.close();
    }

    // A separate legacy profile includes a bad record written by a previous release.
    const legacy = await browser.newContext();
    try {
      const page = await legacy.newPage();
      page.on("pageerror",e=>errors.push(e.message));
      await page.goto(url);
      const raw = JSON.stringify({[first]:{t:"var",wrong:1},[third]:null});
      await page.evaluate(raw=>localStorage.setItem("cfa.quiz.wrong",raw),raw);
      await page.reload();
      check((await page.locator("#recordStatus").innerText()).includes("跳过 1"),"旧损坏记录缺少提示");
      check((await page.locator("#poolTip").innerText()).includes("题"),"旧损坏记录阻断题库");
      await page.locator("#btnWb").click();
      check(await page.locator("#wbList .wbitem").count()===1,"有效旧记录未保留");
      check(await page.evaluate(()=>localStorage.getItem("cfa.quiz.wrong"))===raw,"恢复时覆盖了旧记录");
    } finally {await legacy.close();}
    check(!errors.length,errors.join("\n"));
    return "PASS 跨标签异题与同题计数、并发交卷历史、星标、Leitner、旧数据恢复、整份导入与导出";
  } finally {await context.close();}
}
