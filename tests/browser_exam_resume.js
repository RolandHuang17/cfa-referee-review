// Run on the generated quiz via HTTP or file://. Each scenario uses fresh browser data.
async startPage => {
  const browser = startPage.context().browser(), url = new URL("quiz.html",startPage.url()).href;
  const check = (ok,msg) => { if (!ok) throw Error(msg); };
  const same = (a,b) => JSON.stringify(a) === JSON.stringify(b);
  const errors = [];
  async function profile(setup) {
    const context = await browser.newContext({serviceWorkers:"block",reducedMotion:"reduce"});
    await context.route(/^https?:/,r=>new URL(r.request().url()).origin === new URL(url).origin ? r.continue() : r.abort());
    await context.addInitScript(()=>{ try {localStorage.setItem("cfa.lite","1");} catch (_) {} });
    if (setup) await context.addInitScript(setup);
    context.on("page",p=>{
      p.on("pageerror",e=>errors.push(e.message));
      p.on("dialog",async d => {
        if (d.type() === "confirm" && p.cancelConfirm) await d.dismiss();
        else await d.accept();
      });
    });
    const page = await context.newPage();
    await page.goto(url);
    return [context,page];
  }
  async function start(p,timer="off") {
    await p.locator('#segMode [data-v="exam"]').click();
    await p.locator('#segSrc [data-v="theory"]').click();
    await p.locator('#segCount [data-v="5"]').click();
    await p.locator('#segTimer [data-v="'+timer+'"]').click();
    await p.locator('#btnStart').click();
  }
  const history = p=>p.evaluate(()=>new QuizRecords().state.history.length);
  const snapshot = p=>p.evaluate(()=>({
    id:round.id, keys:round.qs.map(q=>q.k), order:round.qs.map(q=>q._disp || null),
    index:round.i, answers:round.answers, deadline:round.deadline,
    visible:[...document.querySelectorAll("#qForm input")].map(input=>[input.parentElement.innerText,input.checked])
  }));
  async function submit(p) {
    await p.locator("#examDots button").last().click();
    await p.locator("#btnSubmit").click();
    await p.locator("#scrResult").waitFor();
  }

  const [ctx,p] = await profile();
  try {
    await start(p,"std");
    await p.locator("#qForm input").nth(1).check();
    await p.locator("#btnSubmit").click();
    await p.locator("#qForm input").nth(2).check();
    const original = await snapshot(p);
    await p.reload();
    check(same(original,await snapshot(p)), "刷新改变了试卷、乱序、当前勾选或绝对截止时间");
    await p.reload();
    check(same(original,await snapshot(p)) && await history(p)===0, "重复刷新提前计分");
    check(!(await p.locator("#qFb").isVisible()) && !(await p.locator("#scrResult").isVisible()),
      "未交卷显示了答案或得分");
    const independent = await ctx.newPage();
    await independent.goto(url); await start(independent);
    check((await snapshot(independent)).id !== original.id, "单独新开的考试共享编号");
    const popup = ctx.waitForEvent("page");
    await p.evaluate(()=>window.open(location.href,"_blank") && true);
    const copy = await popup;
    await copy.locator("#scrQuiz").waitFor();
    check((await snapshot(copy)).id === original.id, "复制同一标签的未交试卷不一致");
    await copy.locator("#qForm input").nth(3).check();
    await submit(p);
    const firstHistory = await p.evaluate(()=>new QuizRecords().state.history[0]);
    await copy.evaluate(()=>{ if (round && !round.finished) finishExam(); });
    await copy.locator("#scrStart").waitFor();
    check(await copy.locator("#scrStart").isVisible() && await history(copy)===1 &&
      (await copy.locator("#examNotice").innerText()).includes("已经交卷"), "旧卷副本被重复计分或可覆盖首次成绩");
    await copy.reload();
    check(await copy.locator("#scrStart").isVisible() && await history(copy)===1, "关闭已交副本后又恢复");
    await submit(independent);
    const saved = await p.evaluate(()=>new QuizRecords().state.history);
    check(saved.length===2, "两场独立考试未分别记入历史");
    check(saved.some(h=>same(h,firstHistory)), "新场覆盖了另一场的成绩");
    await p.reload();
    check(await p.locator("#scrStart").isVisible() && await history(p)===2, "交卷后刷新重新开卷");

    await start(p);
    p.cancelConfirm=true; await p.locator("#btnAbandon").click(); p.cancelConfirm=false;
    check(await p.locator("#scrQuiz").isVisible(), "取消放弃仍丢失试卷");
    await p.locator("#btnAbandon").click(); await p.reload();
    check(await p.locator("#scrStart").isVisible() && await history(p)===2, "放弃后刷新又恢复或记分");
    await start(p);
    await p.evaluate(()=>{const d=JSON.parse(sessionStorage.getItem(QuizSession.key));d.bank="another-bank";
      sessionStorage.setItem(QuizSession.key,JSON.stringify(d));});
    await p.reload();
    check(await history(p)===2 && (await p.locator("#examNotice").innerText()).includes("题库已更新"),
      "题库变更仍然按新答案评分");
    await start(p);
    await p.evaluate(()=>{const d=JSON.parse(sessionStorage.getItem(QuizSession.key));d.orders[d.keys[0]]=[0,0,0,0];
      sessionStorage.setItem(QuizSession.key,JSON.stringify(d));});
    await p.reload();
    check(await history(p)===2 && await p.locator("#scrStart").isVisible() &&
      (await p.locator("#examNotice").innerText()).includes("不完整"), "损坏选项排列被恢复");
    await start(p);
    await p.evaluate(()=>{
      const d=JSON.parse(sessionStorage.getItem(QuizSession.key)); d.deadline=Date.now()-1000;
      sessionStorage.setItem(QuizSession.key,JSON.stringify(d));
    });
    await p.reload();
    check(await history(p)===2 && await p.locator("#scrStart").isVisible() &&
      (await p.locator("#examNotice").innerText()).includes("不完整"), "损坏的不限时试卷被当作到期记分");

    await p.evaluate(()=>{
      sel.mode="exam";sel.count=0;sel.timer="off";
      startRound([DATA.bank.find(q=>q.t==="case" && q.ans?.r && q.ans?.c),
        DATA.bank.find(q=>q.t==="scale" && q.dec.length>2),
        DATA.bank.find(q=>q.t==="var"),DATA.bank.find(q=>q.t==="theory")]);
    });
    for (let i=0;i<4;i++) {
      await p.locator("#examDots button").nth(i).click();
      for (const field of await p.locator("#qForm fieldset").all()) await field.locator("input").first().check();
      if (await p.locator("#qForm input[type=checkbox]").count()) await p.locator("#qForm input").nth(1).check();
      const selected = await snapshot(p); await p.reload();
      check(same(selected,await snapshot(p)), "部分作答、原始选项下标或多选未恢复");
    }
    await p.locator("#btnAbandon").click();
    await start(p,"std");
    const chosen = await p.evaluate(()=>round.qs[0]._disp.indexOf(round.qs[0].ans));
    await p.locator("#qForm input").nth(chosen).check();
    await p.evaluate(()=>{const d=JSON.parse(sessionStorage.getItem(QuizSession.key));d.deadline=Date.now()-30;
      sessionStorage.setItem(QuizSession.key,JSON.stringify(d));});
    await p.reload(); await p.locator("#scrResult").waitFor();
    const timed = await p.evaluate(()=>new QuizRecords().state.history[0]);
    check(timed.got===1 && timed.n===5 && timed.max===5, "过期重开丢失当前已答项或给空答计分");
    await p.reload(); check(await history(p)===3,"过期试卷重交");
  } finally {await ctx.close();}

  const [blocked, b] = await profile(()=>{Object.defineProperty(window,"sessionStorage",{
    get(){throw new DOMException("Storage denied","SecurityError");}});});
  try {
    await start(b);
    check((await b.locator("#examNotice").innerText()).includes("无法保存试卷"), "拒绝暂存时缺少提示");
    await submit(b);
    check(await history(b)===1, "关闭暂存妨碍正常交卷");
    await b.reload();
    check(await b.locator("#scrStart").isVisible(), "关闭暂存时误报恢复");
  } finally {await blocked.close();}

  const [retry, c] = await profile(()=>{
    const set=Storage.prototype.setItem, remove=Storage.prototype.removeItem;
    Storage.prototype.setItem=function(k,v){
      if(this===localStorage && k.startsWith("cfa.quiz.v2.event.") && sessionStorage.getItem("fixture-block"))
        throw new DOMException("Unavailable","QuotaExceededError");
      return set.call(this,k,v);
    };
    Storage.prototype.removeItem=function(k){
      if(k==="cfa.quiz.exam.v1" && sessionStorage.getItem("fixture-keep")) throw Error("Interrupted cleanup");
      return remove.call(this,k);
    };
  });
  try {
    await start(c); await c.evaluate(()=>sessionStorage.setItem("fixture-block","1"));
    await submit(c);
    const committed = await c.evaluate(()=>JSON.parse(sessionStorage.getItem(QuizSession.key)));
    check(committed.submitting && await history(c)===0, "写成绩失败时未保留待交卷答案");
    await c.evaluate(()=>{sessionStorage.removeItem("fixture-block");sessionStorage.setItem("fixture-keep","1");});
    await c.reload();await c.locator("#scrResult").waitFor();
    check(await history(c)===1 && await c.evaluate(()=>!!sessionStorage.getItem(QuizSession.key)),
      "中断后的成绩未保存或未覆盖清理故障");
    await c.evaluate(()=>sessionStorage.removeItem("fixture-keep"));await c.reload();
    check(await history(c)===1 && await c.locator("#scrStart").isVisible(),"保存后清理前中断造成重复成绩");

    const kept = await c.evaluate(()=>{
      const r = new QuizRecords(), valid = r.state.history[0];
      const before = JSON.stringify({history:r.state.history,stats:r.state.stats});
      // Another tab's durable receipt became readable after this stale copy had queued a different answer.
      const key = QuizRecords.prefix+"pending-fixture";
      r.pending.set(key,{kind:"attempt",examId:valid.id,opened:0,order:1,time:0,
        answers:[{id:"fixture-stale"}],exam:{id:valid.id,got:0,max:1,n:1}});
      const saved = r.retry();
      return saved && !r.pending.size && localStorage.getItem(key) === null &&
        before === JSON.stringify({history:r.state.history,stats:r.state.stats});
    });
    check(kept,"稍后重试的副本改变了先交的成绩");
    const retention = await c.evaluate(()=>{
      const record = new QuizRecords(), state=record.empty();
      const id=i=>i.toString(16).padStart(32,"0");
      for(let i=1;i<=130;i++) QuizRecords.apply(state,{kind:"attempt",examId:id(i),opened:i-1,
        order:i,time:i,answers:[{id:"fixture"}],exam:{got:1,max:1,n:1,id:id(i)}});
      const checkpoint=record.decodeCheckpoint(JSON.stringify({state,covered:[],checksum:QuizRecords.checksum(state,[])})).state;
      const before=checkpoint.stats.fixture.r;
      QuizRecords.apply(checkpoint,{kind:"attempt",examId:id(3),opened:2,order:133,time:133,
        answers:[{id:"fixture"}],exam:{got:1,max:1,n:1,id:id(3)}});
      return {size:checkpoint.examReceipts.length,floor:checkpoint.examFloor,status:QuizRecords.examStatus(checkpoint,id(1),0),
        recent:QuizRecords.examStatus(checkpoint,id(3),2),fresh:QuizRecords.examStatus(checkpoint,id(200),130),
        same:checkpoint.stats.fixture.r===before};
    });
    check(retention.size===128 && retention.floor===2 && retention.status==="uncertain" &&
      retention.recent==="recorded" && retention.fresh==="new" && retention.same, "压缩或淘汰后重复计分");
  } finally {await retry.close();}
  check(!errors.length,errors.join(" / "));
  return "PASS 四类试题刷新续答、限时、复制标签、独立考试、拒绝存储、提交中断与有界去重";
}
