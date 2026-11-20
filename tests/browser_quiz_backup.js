// Complete a standard wrong-book export/import round trip across two independent browser profiles.
async startPage => {
  const browser = startPage.context().browser(), url = new URL("quiz.html",startPage.url()).href;
  const contexts = [await browser.newContext({serviceWorkers:"block"}),await browser.newContext({serviceWorkers:"block"})];
  const errors = [];
  const check = (ok,msg) => {if (!ok) throw Error(msg);};
  async function transfer(page,backup) {
    const shown = page.waitForEvent("dialog");
    await page.locator("#importFile").setInputFiles({name:"考题错题本.json",mimeType:"application/json",
      buffer:Buffer.from(JSON.stringify(backup))});
    const dialog=await shown, message=dialog.message();
    await dialog.accept();
    return message;
  }
  async function backup(page) {
    return page.evaluate(async()=>{
      const original=URL.createObjectURL;
      let file;
      URL.createObjectURL = blob=>{file=blob;return original.call(URL,blob);};
      try { document.getElementById("btnExport").click(); return JSON.parse(await file.text()); }
      finally {URL.createObjectURL=original;}
    });
  }
  async function star(page) {
    if (!await page.locator("#wbList").isVisible()) await page.locator("#btnWb").click();
    await page.locator('#wbList [data-star="var-q1"]').click();
  }
  async function practice(page,correct) {
    await page.evaluate(()=>{sel.count=1;startRound([BANK["var-q1"]],"practice");});
    const idx=await page.evaluate(ok=>{const q=BANK["var-q1"]; return ok?q.ans:(q.ans+1)%q.opts.length;},correct);
    await page.locator("#qForm input").nth(idx).check();
    await page.locator("#btnSubmit").click(); await page.locator("#btnSubmit").click();
    await page.locator("#btnBack").click();
  }
  try {
    for (const context of contexts) {
      await context.route(/^https?:/,r=>new URL(r.request().url()).origin === new URL(url).origin ? r.continue() : r.abort());
      await context.addInitScript(()=>{try{localStorage.setItem("cfa.lite","1");}catch(_){}});
      context.on("page",p=>p.on("pageerror",e=>errors.push(e.message)));
    }
    const [a,b]=await Promise.all(contexts.map(c=>c.newPage()));
    await Promise.all([a.goto(url),b.goto(url)]);
    const seed={wrong:{"var-q1":{t:"var",s:"ifab",star:false,stage:0,due:100,done:false,last:100,wrong:2,correct:"旧答案"}}};
    check((await transfer(a,seed)).includes("合并了 1") && (await transfer(b,seed)).includes("合并了 1"),"旧备份未还原");
    await star(b);await practice(a,true);
    const bStar=await backup(b), aReview=await backup(a);
    check(bStar.wrong["var-q1"].last===100 && aReview.wrong["var-q1"].last===100,"星标或正确复习篡改了最后错答时间");
    check((await transfer(a,bStar)).includes("合并了 1") && (await transfer(b,aReview)).includes("合并了 1"),"不同设备的独立修改未合并");
    for (const p of [a,b]) {
      await p.reload();
      const row=(await backup(p)).wrong["var-q1"];
      check(row.star && row.stage===1 && row.due===aReview.wrong["var-q1"].due && row.wrong===2,
        "星标、复习档位、到期时间或错次不一致");
    }
    await star(b);
    const unstar=await backup(b);
    check(!unstar.wrong["var-q1"].star && (await transfer(a,unstar)).includes("合并了 1"),"明确取消收藏未同步");
    const raw=await a.evaluate(()=>JSON.stringify({...localStorage}));
    check((await transfer(a,unstar)).includes("合并了 0") && (await transfer(a,bStar)).includes("合并了 0") &&
      await a.evaluate(v=>JSON.stringify({...localStorage})===v,raw),"重导或旧文件覆盖了较新的取消收藏");
    await practice(a,false);
    const again=await backup(a);
    check((await transfer(b,again)).includes("合并了 1"),"较新的错答没有重置复习进度");
    const latest=(await backup(b)).wrong["var-q1"];
    check(!latest.star && latest.stage===0 && latest.wrong===3 && latest.last>100,"错后重置、次数或星标不正确");
    check((await transfer(b,aReview)).includes("合并了 0"),"旧备份令错后重置失效");
    const state=await b.evaluate(()=>JSON.stringify({...localStorage}));
    const malformed={wrong:{"var-q2":{t:"var",star:true},"var-q1":{...latest,starVersion:["invalid","clock"]}}};
    check((await transfer(b,malformed)).includes("导入失败") &&
      await b.evaluate(saved=>JSON.stringify({...localStorage})===saved,state),"混合损坏版本的备份部分写入");
    check(!errors.length,errors.join(" / "));
    return "PASS 两台设备独立更新、星标/取消、复习与重置、旧备份、重复导入和整份验证";
  } finally {await Promise.all(contexts.map(c=>c.close()));}
}
