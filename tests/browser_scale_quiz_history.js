// playwright-cli run-code --filename tests/browser_scale_quiz_history.js
async (startPage) => {
  const url = new URL("quiz.html",startPage.url()).href;
  const browser = startPage.context().browser();
  const contexts = [], errors = [];
  const check = (value, message) => { if (!value) throw Error(message); };
  async function open() {
    const ctx = await browser.newContext({viewport:{width:390,height:844}});
    contexts.push(ctx);
    const page = await ctx.newPage();
    await page.addInitScript(()=>{ Math.random=()=>0.9999; localStorage.setItem("cfa.lite","1"); });
    page.on("dialog",dialog=>dialog.accept());
    page.on("pageerror",e=>errors.push(e.message));
    await page.goto(url);
    return page;
  }
  async function download(page, button) {
    return page.evaluate(async id=>{
      const create = URL.createObjectURL;
      let body;
      URL.createObjectURL = blob => {body=blob;return create.call(URL,blob);};
      try {document.getElementById(id).click();return await body.text();}
      finally {URL.createObjectURL=create;}
    },button);
  }
  async function upload(page, backup) {
    const notice = page.waitForEvent("dialog");
    await page.locator("#importFile").setInputFiles({name:"错题本.json",mimeType:"application/json",
      buffer:Buffer.from(JSON.stringify(backup))});
    return (await notice).message();
  }
  try {
    const first = await open();
    await first.locator('#segSrc [data-v="scale"]').click();
    await first.locator('#seasonChips [data-s="2025"]').click();
    await first.locator("#btnStart").click();
    const exact = "scale.html#h2025-reckless-1", firstKey = "sc-2025-reckless-1";
    check(await first.locator("#qCard a.srcbtn").getAttribute("href")===exact,"初始题面的来源不对应争抢 1");
    await first.locator("#btnSkip").click();
    await first.reload();
    await first.locator("#btnWb").click();
    check(await first.locator("#wbList a").getAttribute("href")===exact,"重开后的错题来源串题");
    await first.locator('#segRange [data-v="wrong"]').click();
    check(await first.locator("#poolTip").innerText()==="当前范围 1 题","一次错答产生了多道复练题");
    const old = await open();
    await old.evaluate(()=>{
      const wrong = {
        "sc-2025-1":{t:"scale",s:"2025",correct:["不犯规","不出牌","漏选 不犯规","不出牌"],your:[],wrong:5,star:true,stage:2},
        "sc-2025-2":{t:"scale",s:"2025",your:["红牌"],wrong:3,last:3},
      };
      const stats = {"sc-2025-1":{r:2,w:5},"sc-2025-7":{r:6,w:1}};
      localStorage.setItem("cfa.quiz.wrong",JSON.stringify(wrong));
      localStorage.setItem("cfa.quiz.stats",JSON.stringify(stats));
    });
    await old.reload();
    await old.locator("#btnWb").click();
    const group = id=>old.locator('[data-legacy-id="sc-2025-'+id+'"]');
    check(await old.locator("#legacyScaleList article").count()===3,"漏掉了只有成绩或只有错题的旧编号");
    check((await group(1).innerText()).includes("旧编号合计：答对 2 次，答错 5 次。"),"合计未按旧编号展示");
    check((await group(1).innerText()).includes("已收藏") && (await group(1).innerText()).includes("复习档位 2"),"旧收藏/复习档位遗失");
    check(await group(1).locator("button").count()===1 && await group(2).locator("button").count()===0 &&
      await group(7).locator("button").count()===0,"给不明旧记录猜测了题目");
    check(await group(2).locator("a").count()===3 && await group(7).locator("a").count()===2,"缺少来源候选");
    check(await old.locator("#nWrong").innerText()==="0" && await old.locator("#nStar").innerText()==="0","旧合计误入新题或收藏池");
    check(await old.evaluate(()=>{
      const key="sc-2025-1",q=BANK["sc-2025-var-1"];
      return scaleHistory.lastQuestion(key,{link:q.link})===q &&
        scaleHistory.lastQuestion(key,{series:q.series})===q &&
        !scaleHistory.lastQuestion(key,{series:q.series,correct:"不犯规、不出牌"}) &&
        !scaleHistory.lastQuestion(key,{your:["不犯规","不出牌"]});
    }),"历史线索冲突时仍自动归属");
    const tsv = await download(old,"btnAnki");
    check(tsv.includes(exact) && tsv.includes("上次场景待核对") &&
      tsv.includes("scale.html#h2025-var-2") && tsv.includes("scale.html#h2025-highlights-2"),"Anki 漏记旧错题或误指唯一来源");
    await group(1).locator("button").focus();
    await old.keyboard.press("Enter");
    check(await old.locator("#qCard a.srcbtn").getAttribute("href")===exact,"旧错题的复练场景错误");
    await old.locator("#btnSkip").click();
    const backup = JSON.parse(await download(old,"btnExport"));
    check(backup.wrong[firstKey].wrong===1 && !backup.wrong[firstKey].star &&
      backup.wrong["sc-2025-1"].wrong===5 && backup.legacyScaleStats["sc-2025-1"].w===5,"新练习继承了共享的旧计数");
    if (new URL(url).protocol !== "file:") {
      const portal = await old.context().newPage();
      await portal.goto(new URL("index.html",url).href);
      check(await portal.locator("#msDue b").innerText()==="1","门户把旧记录计为可复练的新题");
    }
    const fresh = await open();
    check((await upload(fresh,backup)).includes("补回 2 组"),"标准备份未恢复旧统计");
    check((await upload(fresh,backup)).includes("合并了 0 条"),"同一份备份重复导入产生了新记录");
    const conflict = {...backup,legacyScaleStats:{"sc-2025-1":{r:200,w:500}}};
    check((await upload(fresh,conflict)).includes("保留本机数值"),"不同设备的合计没有说明保留规则");
    const bad = {wrong:{"sc-2025-9":{t:"scale",s:"2025"}},legacyScaleStats:{"sc-2025-1":{r:-1,w:2}}};
    check((await upload(fresh,bad)).includes("导入失败"),"错误的旧统计造成部分导入");
    await fresh.reload();
    const again = JSON.parse(await download(fresh,"btnExport"));
    check(JSON.stringify(again.wrong)===JSON.stringify(backup.wrong) &&
      JSON.stringify(again.legacyScaleStats)===JSON.stringify(backup.legacyScaleStats),"重复导入、刷新后备份的记录改变");
    check((await upload(fresh,{wrong:{"sc-2025-3":{t:"scale",s:"2025",last:4}}})).includes("合并了 1 条"),"旧格式 JSON 备份失效");
    await fresh.evaluate(()=>{
      const state = new QuizRecords().state;
      const covered = Object.keys(localStorage).filter(key=>key.startsWith(QuizRecords.prefix));
      localStorage.setItem(QuizRecords.recovery,JSON.stringify({state,covered,checksum:QuizRecords.checksum(state,covered)}));
      localStorage.setItem(QuizRecords.checkpoint,"{");
      for (const key of covered) localStorage.removeItem(key);
    });
    await fresh.reload();
    await fresh.locator("#btnWb").click();
    check(await fresh.locator("#legacyScaleList article").count()===4 &&
      await fresh.locator("#wbList .wbitem").count()===1,"v2 备用快照中恢复的记录未呈现");
    check(errors.length===0,errors.join("\n"));
    return "PASS scale identities, old answers, source links, JSON/Anki and checkpoint recovery";
  } finally {
    for (const ctx of contexts) await ctx.close();
  }
}
