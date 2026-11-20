// Run with playwright-cli run-code --filename tests/browser_coach.js against the built site.
async (startPage) => {
  const browser = startPage.context().browser();
  const classroom = new URL("compare.html", startPage.url());
  const context = await browser.newContext({viewport:{width:390,height:844},acceptDownloads:true});
  const page = await context.newPage();
  const errors = [];
  function check(ok, message) { if (!ok) throw Error(message); }
  function watch(tab) {
    tab.on("pageerror", e => errors.push(e.message));
    tab.on("dialog", dialog => dialog.accept());
  }
  async function open(tab, hash = "coach") {
    await tab.goto(new URL("#"+hash,classroom).href,{waitUntil:"domcontentloaded"});
    await tab.locator("#workspace").waitFor();
  }
  const row = (tab,id) => tab.locator('li[data-coach-case="'+id+'"]');
  const field = (tab,id,key) => row(tab,id).locator('[data-field="'+key+'"]');
  async function closePanel(tab) {
    const modal = tab.locator("dialog:modal");
    if (await modal.count()) {
      await tab.keyboard.press("Escape");
      await modal.waitFor({state:"hidden"});
    }
  }
  async function arrange(tab) {
    await closePanel(tab);
    await tab.locator("#coach-arrange").click();
  }
  async function panel(tab,kind) {
    const outline = kind === "outline";
    const dialog = tab.locator(outline ? "#coach-outline-dialog" : "#coach-tools-dialog");
    if (!await dialog.isVisible()) {
      await arrange(tab);
      await tab.locator(outline ? "#coach-edit-items" : "#coach-tools-open").click();
      await dialog.waitFor();
    }
  }
  async function edit(locator,text) {
    if (await locator.getAttribute("data-field")) await panel(locator.page(),"outline");
    const disclosure = locator.locator("xpath=ancestor::details[1]");
    if (await disclosure.count() && !await disclosure.evaluate(el => el.open)) await disclosure.locator(":scope > summary").click();
    await locator.fill(text); await locator.blur();
  }
  async function order(tab) {
    return tab.locator("li[data-coach-case]").evaluateAll(rows => rows.map(r => r.dataset.coachCase));
  }
  async function add(tab,id,category,team) {
    await closePanel(tab);
    await tab.locator("#coach-category").selectOption(category);
    await tab.locator("#coach-year").selectOption(id.split("-")[0]);
    await tab.locator("#coach-filter").fill(team || "");
    await tab.locator("#coach-pick").selectOption(id);
    await tab.locator("#coach-add").click();
    await row(tab,id).waitFor({state:"attached"});
  }
  async function download(tab,selector) {
    await panel(tab,"tools");
    await tab.evaluate(() => {
      const create = URL.createObjectURL;
      window.latestCoachBlob = null;
      URL.createObjectURL = function(blob) {
        window.latestCoachBlob = blob;
        URL.createObjectURL = create;
        return create.call(URL,blob);
      };
    });
    const [file] = await Promise.all([tab.waitForEvent("download"),tab.locator(selector).click()]);
    const text = await tab.evaluate(async () => await window.latestCoachBlob.text());
    return {file,text};
  }
  async function sharedUrl(tab) {
    await tab.evaluate(() => Object.defineProperty(navigator,"clipboard",{configurable:true,
      value:{writeText:async () => {throw new DOMException("clipboard disabled","NotAllowedError");}}}));
    await tab.locator("#coach-link").click();
    const input = tab.locator("#coach-share-text");
    await input.waitFor();
    const result = new URL(await input.inputValue());
    const canonical = new URL(await tab.locator('link[rel="canonical"]').getAttribute("href"));
    check(result.origin === canonical.origin && result.pathname === canonical.pathname && result.hash.startsWith("#handout-"),
      "分享链接缺少公开部署地址或讲义内容");
    return result;
  }
  async function selectLesson(tab,id) {
    await arrange(tab);
    await tab.locator("#coach-choose").selectOption(id);
    await tab.locator("#coach-title").waitFor();
  }
  const name = "U17 双案例课堂", question = "谁先触球，哪一次接触需要观察？";
  const scenario = "公开课堂观察：两名队员在禁区内争抢一个落点。";
  const secret = "教练私有标记：第二组需多留讨论时间";
  const official = "评议组一致认为";
  const expected = ["2026-1","2024-1"];
  watch(page);
  try {
    await open(page);
    await arrange(page);
    await page.locator("#coach-new").click();
    await edit(page.locator("#coach-title"),name);
    const first = await page.locator("#coach-choose").inputValue();
    check(!await page.locator("#coach-present").isEnabled(), "空课单允许投屏");
    await add(page,"2024-1","penalty_area","浙江");
    await add(page,"2026-1","handball","山东泰山");
    if (await page.locator('#coach-pick option[value="2026-1"]').count()) {
      await page.locator("#coach-pick").selectOption("2026-1");
      if (await page.locator("#coach-add").isEnabled()) await page.locator("#coach-add").click();
    }
    check((await order(page)).length === 2, "相同案例被重复加入");
    await panel(page,"outline");
    await row(page,"2026-1").locator('[data-action="up"]').click();
    check(JSON.stringify(await order(page)) === JSON.stringify(expected), "上移后顺序错误");
    await row(page,"2026-1").locator('[data-action="down"]').click();
    await row(page,"2024-1").locator('[data-action="down"]').click();
    await edit(field(page,"2026-1","question"),question);
    await edit(field(page,"2026-1","scenario"),scenario);
    await edit(field(page,"2026-1","note"),secret);
    await closePanel(page);
    check(await page.locator("#coach-edit-items").evaluate(el=>el===document.activeElement), "Esc 关闭编排后焦点未返回入口");
    await page.reload();
    check(await page.locator("#coach-title").inputValue() === name &&
      await field(page,"2026-1","note").inputValue() === secret &&
      JSON.stringify(await order(page)) === JSON.stringify(expected), "刷新后课单、顺序或备注丢失");

    const backup = await download(page,"#coach-backup");
    check(backup.file.suggestedFilename().endsWith(".json") && backup.text.includes(secret) &&
      backup.text.includes(question) && backup.text.includes(scenario), "私人备份不完整");
    await arrange(page);
    await page.locator("#coach-new").click();
    await edit(page.locator("#coach-title"),"晚场练习");
    const second = await page.locator("#coach-choose").inputValue();
    check(first !== second, "新课覆盖旧课");
    await add(page,"2026-14","offside","深圳新鹏城");
    await panel(page,"outline");
    await row(page,"2026-14").locator('[data-action="remove"]').click();
    check(!(await order(page)).length, "删除没有作用");
    await selectLesson(page,first);

    await page.locator("#coach-present").click();
    await page.waitForURL(u => u.hash.startsWith("#present-"));
    const stage = page.locator("#workspace");
    // The hash changes before the hashchange handler mounts the presentation.
    const heading = stage.locator(".coach-stage .coach-content h2");
    await heading.waitFor({state:"visible"});
    const initial = await stage.evaluate(el => ({
      question: el.querySelector(".coach-stage .coach-content h2").innerText,
      content: el.textContent,
      answerPanel: !!el.querySelector(".coach-answer"),
      revealState: el.querySelector("#stage-reveal")?.getAttribute("aria-pressed")
    }));
    check(initial.question === question, "投屏首题问题不符，实际为 " + JSON.stringify(initial.question));
    check(!initial.content.includes(secret), "投屏初始 DOM 包含私人笔记");
    check(!initial.content.includes(official), "投屏初始 DOM 包含足协认定原文");
    check(!initial.answerPanel && initial.revealState === "false", "投屏初始认定面板或揭晓开关状态异常");
    check(!await page.locator("#stage-prev").isEnabled() &&
      !(await stage.innerText()).includes("浙江队"), "首案混入第二案或可越界回退");
    if (!await page.evaluate(() => !!document.fullscreenElement)) await page.locator("#stage-fullscreen").click();
    await page.waitForFunction(() => !!document.fullscreenElement);
    await page.evaluate(() => document.exitFullscreen());
    await page.evaluate(() => Object.defineProperty(Element.prototype,"requestFullscreen",{
      configurable:true, value:async () => { throw new DOMException("fullscreen denied","NotAllowedError"); }
    }));
    await page.locator("#stage-fullscreen").click();
    check(await page.locator("#stage-next").isVisible(), "未授权全屏后不能继续投屏");
    await page.locator("#stage-reveal").click();
    check((await stage.innerText()).includes(official), "手动揭晓没有出现足协原文");
    await page.keyboard.press("ArrowRight");
    const nextCase = await stage.innerText();
    check(!await page.locator("#stage-next").isEnabled() && nextCase.includes("浙江") && !nextCase.includes(question) &&
      !nextCase.includes(official) && !nextCase.includes("临场的最终判罚正确"),
      "下一案例混入上一案或泄露了原始描述中的判定");
    await page.keyboard.press("ArrowLeft");
    check((await stage.innerText()).includes(question) && !(await stage.innerText()).includes(official), "返回上一案例没有恢复讨论状态");
    await page.keyboard.press("r");
    check((await stage.innerText()).includes(official), "R 键未揭晓当前认定");
    await page.locator("#stage-exit").click();
    check(await page.locator("#coach-choose").inputValue() === first, "退出投屏没有回到原课单");

    await arrange(page);
    await page.locator("#coach-present").click();
    await page.locator("#stage-reveal").waitFor();
    check(!(await stage.innerText()).includes(official), "重新投屏沿用了上一次已揭晓状态");
    await page.locator("#stage-exit").click();
    await panel(page,"tools");
    check(!await page.locator("#coach-review").isChecked(), "默认学员讲义包含复盘答案");
    for (const review of [false,true]) {
      await panel(page,"tools");
      await page.locator("#coach-review").setChecked(review);
      const share = await sharedUrl(page);
      const payload = Buffer.from(share.hash.slice("#handout-".length),"base64url").toString("utf8");
      check(payload.includes(question) && payload.includes(scenario) && !payload.includes(secret) && !payload.includes(first),
        "公开链接含私人记录或缺少公开情境");
      const output = await download(page,"#coach-download");
      check(output.file.suggestedFilename().endsWith(".html") && !output.text.includes(secret), "导出的学员讲义泄露私人备注");
      const plain = await browser.newContext({acceptDownloads:true});
      try {
        const student = await plain.newPage(); watch(student);
        // Exercise the published token against this candidate without contacting the public deployment.
        await open(student,share.hash.slice(1));
        const body = await student.locator("#coach-sheet").innerText();
        check(body.includes(question) && body.includes(scenario) && !body.includes(secret) &&
          body.includes(official) === review && !body.includes("临场的最终判罚正确"), "新浏览器学员视图的讨论、复盘口径错误");
        if (review) check((await student.locator('#coach-sheet a[href="https://www.thecfa.cn/zyls1/20240311/33847.html"]').count()) === 1 &&
          body.includes("未单列评议结论"), "无单独结论的案例缺少原期引用或被补判");
        if (!review) {
          const unknown = Buffer.from(payload.replace("2026-1","2099-999999"),"utf8").toString("base64url");
          await open(student,"handout-"+unknown);
          await student.getByRole("alert").filter({hasText:/无法识别|未知|不存在/}).waitFor();
          check(await student.locator("#coach-sheet").count() === 0, "失效分享链接仍生成了不完整的讲义");
        }
        const target = (await output.file.path()) + ".html";
        await output.file.saveAs(target);
        const fileUrl = new URL("file:///");
        fileUrl.pathname = target.replace(/\\/g,"/");
        const requested = [];
        student.on("request", req => {if (/^https?:/.test(req.url())) requested.push(req.url());});
        await plain.setOffline(true);
        await student.goto(fileUrl.href);
        const offlineText = await student.locator("body").innerText();
        check(!await student.evaluate(() => navigator.onLine) && offlineText.includes(question) &&
          offlineText.includes(scenario) && !offlineText.includes(secret) && offlineText.includes(official) === review,
          "断网时独立讲义不完整或显示了未选择的内容");
        const pdf = await student.pdf({format:"A4"});
        check(pdf.byteLength > 1000 && requested.length === 0, "讲义打印失败或读取了网络资源");
      } finally { await plain.close(); }
    }
    await page.locator("#coach-review").uncheck();
    await page.locator("#coach-preview").click();
    await page.locator("#coach-sheet").waitFor();
    check(!(await page.locator("#coach-sheet").innerText()).includes(secret), "讲义预览泄露教师笔记");
    await open(page);

    const fromPair = await browser.newContext();
    try {
      const pair = await fromPair.newPage(); watch(pair);
      await open(pair,"pair-2026-1~2026-28");
      await pair.locator("#coach-from-pair").click();
      await row(pair,"2026-28").waitFor({state:"attached"});
      check(JSON.stringify(await order(pair)) === JSON.stringify(["2026-1","2026-28"]), "自由配对没有按 A/B 顺序创建备课单");
    } finally { await fromPair.close(); }

    const restore = await browser.newContext();
    try {
      const imported = await restore.newPage(); watch(imported); await open(imported);
      await panel(imported,"tools");
      await imported.locator("#coach-import").setInputFiles({name:"课单备份.json",mimeType:"application/json",buffer:Buffer.from(backup.text)});
      await row(imported,"2026-1").waitFor({state:"attached"});
      check(await field(imported,"2026-1","note").inputValue() === secret &&
        await field(imported,"2026-1","scenario").inputValue() === scenario &&
        JSON.stringify(await order(imported)) === JSON.stringify(expected), "从私人备份恢复错误");
      const unknown = backup.text.replace(/"caseId"\s*:\s*"2026-1"/,'"caseId":"2099-999999"');
      check(unknown !== backup.text, "缺少用于未知案例验收的原始记录");
      const before = await imported.locator("#coach-choose option").count();
      await panel(imported,"tools");
      await imported.locator("#coach-import").setInputFiles({name:"未知案例.json",mimeType:"application/json",buffer:Buffer.from(unknown)});
      await imported.locator("#coach-dialog-status").filter({hasText:/未知|不存在|无效|无法|失败/}).waitFor();
      check(await imported.locator("#coach-choose option").count() === before &&
        await field(imported,"2026-1","note").inputValue() === secret, "含未知案例的导入改写了已有记录");
      // A large valid class can still be taught and exported as an HTML file.
      const large = JSON.parse(backup.text);
      large.lesson.title = "三十一案例研讨课";
      large.lesson.items = Array.from({length:31}, (_,i) => ({
        caseId:"2026-" + (i+1), question:"练习问题 " + (i+1), scenario:"观察课堂提供的画面。".repeat(55),note:"私人内容"
      }));
      await imported.locator("#coach-import").setInputFiles({name:"大课单.json",mimeType:"application/json",buffer:Buffer.from(JSON.stringify(large))});
      await row(imported,"2026-31").waitFor({state:"attached"});
      check((await order(imported)).length === 31, "可用课单被固定在三十例");
      await panel(imported,"tools");
      await imported.locator("#coach-link").click();
      await imported.locator("#coach-dialog-status").filter({hasText:/过长|太长/}).waitFor();
      const longSheet = await download(imported,"#coach-download");
      check(longSheet.text.includes("练习问题 31") && !longSheet.text.includes("私人内容"), "长课单的离线讲义退路不可用");
    } finally { await restore.close(); }

    await selectLesson(page,first);
    const peer = await context.newPage(); watch(peer); await open(peer);
    await selectLesson(peer,first);
    const drafts = ["教练甲的并行备注","教练乙的并行备注"];
    await Promise.all([page,peer].map((tab,i) => edit(field(tab,"2026-1","note"),drafts[i])));
    await page.reload();
    const choices = await page.locator("#coach-choose option").evaluateAll(options => options.map(o=>o.value).filter(Boolean));
    const notes = [];
    for (const id of choices) {
      await selectLesson(page,id);
      if (await row(page,"2026-1").count()) notes.push(await field(page,"2026-1","note").inputValue());
    }
    check(drafts.every(text=>notes.includes(text)), "两个教师标签并行写同一课单时有草稿被覆盖");
    await peer.close();

    await selectLesson(page,first);
    await page.evaluate(() => {
      const original = Storage.prototype.setItem;
      window.restoreCoachStorage = () => { Storage.prototype.setItem=original; };
      Storage.prototype.setItem = function(k,v) {
        if (k.startsWith("cfa.coach.")) throw new DOMException("quota","QuotaExceededError");
        return original.call(this,k,v);
      };
    });
    const draft = "空间不足时仍要保留的备注";
    await edit(field(page,"2026-1","note"),draft);
    await closePanel(page);
    await page.locator("#coach-retry").waitFor();
    check(await field(page,"2026-1","note").inputValue() === draft &&
      (await download(page,"#coach-backup")).text.includes(draft), "满存储后不能备份当前草稿");
    await closePanel(page);
    await page.evaluate(()=>restoreCoachStorage());
    await page.locator("#coach-retry").click();
    await page.reload();
    check(await field(page,"2026-1","note").inputValue() === draft, "重试未保存草稿");
    const damagedKey = "cfa.coach.lessons.v1.entry." + "0".repeat(32);
    await page.evaluate(key=>localStorage.setItem(key,"{"),damagedKey);
    await page.reload();
    await selectLesson(page,first);
    check(await page.locator("#coach-status").textContent().then(t=>t.includes("1 条本机记录")),
      "课单列表没有提示部分记录不可读");
    const recovery = JSON.parse((await download(page,"#coach-recovery")).text);
    check(recovery.entries.length === 1 && recovery.entries[0].key === damagedKey && recovery.entries[0].value === "{",
      "异常课单的原件导出不完整");
    await closePanel(page);
    await edit(page.locator("#coach-title"),"修复前继续备课");
    await page.reload();
    check(await page.locator("#coach-title").inputValue() === "修复前继续备课" &&
      await page.evaluate(key=>localStorage.getItem(key),damagedKey) === "{", "有效课单未能保存或异常原件被覆盖");
    await page.evaluate(() => navigator.serviceWorker.ready.then(() => true));
    await page.waitForFunction(() => !!navigator.serviceWorker.controller);
    await page.reload();  // Cache this document before disconnecting the browser.
    await context.setOffline(true);
    await page.reload();
    check(await field(page,"2026-1","note").inputValue() === draft, "断网后教练工作区或已保存课单不可恢复");
    check(!errors.length, errors.join("\n"));
    return "PASS 多课编辑/跨赛季选案与排序/中性情境与私人笔记/投屏键盘揭晓/讨论及复盘讲义、分享、离线打印/备份恢复/未知案例/并行和满额";
  } finally { await context.close(); }
}
