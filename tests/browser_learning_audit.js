// Run against a local site with playwright-cli run-code --filename.
async (page) => {
  const base = new URL("./", page.url());
  const context = await page.context().browser().newContext({
    timezoneId: "Asia/Shanghai", viewport: {width: 390, height: 844}, serviceWorkers: "block",
  });
  function check(ok, description) { if (!ok) throw Error(description); }
  const load = (tab, route) => tab.goto(new URL(route, base).href, {waitUntil: "domcontentloaded"});
  const errors = [];
  context.on("page", tab => tab.on("pageerror", e => errors.push(e.message)));
  const first = await context.newPage(), second = await context.newPage();
  async function openNotes(tab, route, isRule) {
    if (tab.url() === new URL(route, base).href) await tab.reload({waitUntil:"domcontentloaded"});
    else await load(tab, route);
    const recordId = route.split("#")[1].replace(/^case-/, "");
    await tab.waitForFunction(id => typeof noteEditor !== "undefined" && noteEditor.id === id, recordId);
    if (isRule && !(await tab.locator("#noteWrap").evaluate(e => e.open))) await tab.locator("#noteWrap > summary").click();
  }
  async function save(tab, selector, text) {
    await tab.locator(selector).fill(text);
    // Export, visibility changes and switching records also call the normal flush function.
    await tab.evaluate(() => flushNote());
  }
  async function backup(tab, button) {
    return tab.evaluate(async button => {
      let captured;
      const create = URL.createObjectURL;
      URL.createObjectURL = blob => { captured = blob; return create.call(URL, blob); };
      try {
        document.querySelector(button).click();
        return JSON.parse(await captured.text());
      } finally { URL.createObjectURL = create; }
    }, button);
  }
  try {
    await load(first, "index.html");
    await first.evaluate(() => localStorage.setItem("cfa.lite", "1"));
    await load(first, "season-2026.html#case-229");
    const interrupted = await first.evaluate(() => {
      const store = new LearningRecords("test.note-cleanup", true);
      store.put("1", {text:"旧稿",ts:1}, []);
      const old = store.base("1");
      const remove = Storage.prototype.removeItem;
      try {
        Storage.prototype.removeItem = function(key) { if (!old.includes(key)) remove.call(this, key); };
        store.put("1", {text:"第二稿",ts:2}, old);
      } finally { Storage.prototype.removeItem = remove; }
      const second = store.read()["1"];
      store.put("1", {text:"第三稿",ts:3}, store.base("1"));
      const third = store.read()["1"];
      return [second, third, old.some(key => localStorage.getItem(key) !== null)];
    });
    check(interrupted[0].text === "第二稿" && !interrupted[0].conflicts && interrupted[1].text === "第三稿" &&
      !interrupted[1].conflicts && !interrupted[2], "已替换父版本在写入中断后重新出现");
    for (const kind of ["case", "rule"]) {
      const rule = kind === "rule";
      const route = id => rule ? "rules.html#law-" + id : "season-2026.html#case-" + id;
      const [idA, idB] = rule ? [11, 12] : [229, 230];
      const keyA = rule ? "law-" + idA : String(idA);
      const keyB = rule ? "law-" + idB : String(idB);
      const input = rule ? "#secNote" : "#noteBox";
      const button = rule ? "#btnExportN" : "#btnExport";
      await Promise.all([openNotes(first, route(idA), rule), openNotes(second, route(idB), rule)]);
      await Promise.all([save(first, input, "甲的初稿"), save(second, input, "乙的笔记")]);
      if (!rule) await second.locator("#favBtn").click();
      // Chrome may propagate another renderer's localStorage change after both click
      // promises resolve. Require both originals to reach this tab before exporting.
      await first.waitForFunction(([a,b]) => {
        const notes = noteStore.read();
        return notes[a]?.text === "甲的初稿" && notes[b]?.text === "乙的笔记";
      }, [keyA,keyB], {timeout: 5000});
      const distinct = await backup(first, button);
      check(distinct.notes[keyA]?.text === "甲的初稿" && distinct.notes[keyB]?.text === "乙的笔记",
        kind + " 双页独立保存有记录丢失：" + JSON.stringify(distinct.notes));
      if (!rule) check(!!distinct.fav[keyB], "旧页导出遗漏其他标签的收藏");
      await Promise.all([openNotes(first, route(idA), rule), openNotes(second, route(idA), rule)]);
      await Promise.all([save(first, input, "并行版本 A"), save(second, input, "并行版本 B")]);
      await openNotes(first, route(idA), rule);
      await first.waitForFunction(key => {
        const n = noteStore.read()[key];
        const texts = [n?.text, ...(n?.conflicts || []).map(v => v.text)];
        return texts.includes("并行版本 A") && texts.includes("并行版本 B");
      }, keyA, {timeout: 5000});
      const collision = (await backup(first, button)).notes[keyA];
      check([collision.text, ...collision.conflicts.map(v => v.text)].sort().join("/") === "并行版本 A/并行版本 B",
        kind + " 同一记录的并行版本不可导出：" + JSON.stringify(collision));
      await first.locator("#noteCopies summary").click();
      const recovered = await first.locator("#noteCopies p").first().innerText();
      await first.getByRole("button", {name:"恢复此文本"}).first().click();
      check(await first.locator(input).inputValue() === recovered, kind + " 恢复副本未回填");
      await first.locator("#noteCopies summary").click();
      first.once("dialog", dialog => dialog.accept());
      await first.getByRole("button", {name:"保留编辑框文本并移除上述副本"}).click();
      const resolved = (await backup(first, button)).notes[keyA];
      check(resolved.text === recovered && !resolved.conflicts, kind + " 未能归并已查看的版本");
      await first.evaluate(() => {
        const original = Storage.prototype.setItem;
        window.restoreWrites = () => Storage.prototype.setItem = original;
        Storage.prototype.setItem = function(key, value) {
          if (key.includes(".notes")) throw new DOMException("quota", "QuotaExceededError");
          return original.call(this, key, value);
        };
      });
      await save(first, input, "空间不足时的草稿");
      check(await first.locator("#retryWrite").isVisible(), kind + " 失败没有重试入口");
      check((await first.locator("#writeStatus").innerText()).includes("写入失败"), kind + " 失败被显示为已保存");
      check((await backup(first, button)).notes[keyA].text === "空间不足时的草稿", kind + " 草稿未进入导出备份");
      await first.evaluate(() => restoreWrites());
      await first.locator("#retryWrite").click();
      await openNotes(first, route(idA), rule);
      check(await first.locator(input).inputValue() === "空间不足时的草稿", kind + " 草稿重试后刷新未保留");
    }
    await load(first, "quiz.html?cat=handball");
    check(await first.locator("#categoryFilter option").count() === 11, "教学分类菜单应含全部和十个分类");
    check(await first.locator("#categoryFilter").inputValue() === "handball", "专项链接未选中手球");
    for (const id of await first.locator("#categoryFilter option").evaluateAll(items => items.map(x => x.value).filter(Boolean))) {
      await first.locator("#categoryFilter").selectOption(id);
      check(await first.evaluate(id => pool().length > 0 && pool().every(q => q.t === "case" && q.cat === id), id), "分类范围错误 " + id);
    }
    await first.locator("#categoryFilter").selectOption("handball");
    await first.locator("#btnStart").click();
    check(await first.evaluate(() => round.qs.length > 0 && round.qs.every(q => q.t === "case" && q.cat === "handball")), "专项卷混入其他分类");
    await load(first, "quiz.html?range=due");
    check(await first.locator("#btnDue").evaluate(b => b.classList.contains("on")), "到期入口未筛选");
    await load(first, "quiz.html");
    await first.locator('#segMode [data-v="exam"]').click();
    await first.locator('#segSrc [data-v="scale"]').click();
    await first.locator('#segCount [data-v="0"]').click();
    await first.locator("#btnStart").click();
    await first.evaluate(() => {
      for (let i = 0; i < round.qs.length; i++) {
        if (i < 86) {
          const correct = round.qs[i].dec.filter(d => d.active).map(d => d.label);
          for (const option of document.querySelectorAll("#qForm .opt")) if (correct.includes(option.dataset.dec)) option.click();
        }
        document.querySelector("#btnSubmit").click();
      }
    });
    await first.locator("#scrResult").waitFor();
    const result = await first.evaluate(() => {
      return {latest:new QuizRecords().state.history[0], badge:document.querySelector("#rPass").innerText, pct:document.querySelector("#rPct").innerText,
        equality:examPassed(9, 10), over:examPassed(91,100), near:scorePercent(1862,2069)};
    });
    check(result.latest.got === 172 && result.latest.max === 192 && result.pct.includes("89.6") &&
      result.badge.includes("未达") && Number(result.near) < 90 && result.equality && result.over, "模拟考判定没有按原始分值比较");
    await load(first, "quiz.html");
    await first.clock.install();
    await first.clock.setSystemTime(new Date("2026-11-19T01:00:00+08:00"));
    const streak = await first.evaluate(() => {
      localStorage.setItem("cfa.streak", JSON.stringify({last:"2026-11-18", days:3}));
      touchStudyDay(); touchStudyDay();
      return JSON.parse(localStorage.getItem("cfa.streak"));
    });
    check(streak.last === "2026-11-19" && streak.days === 4, "上海午夜后的学习未按本地日期去重累加");
    await first.locator('#segMode [data-v="exam"]').click();
    await first.locator('#segSrc [data-v="theory"]').click();
    await first.locator("#btnStart").click();
    await first.locator("#qForm .opt").first().click();
    await first.evaluate(() => {
      window.beforeTimeout = qhist.length;
      window.alert = () => { window.finishedAtNotice = round.finished &&
        document.getElementById("scrResult").style.display !== "none" && new QuizRecords().state.history.length === window.beforeTimeout+1; };
      startTimer(5);
    });
    await first.clock.fastForward(10000);
    await first.locator("#scrResult").waitFor();
    check(await first.evaluate(() => round.finished && window.finishedAtNotice && qhist.length === window.beforeTimeout + 1 &&
      round.answers[0] != null), "暂停后未按截止时间自动交卷，或遗漏已选答案");
    // Observe Chrome's actual cross-origin media request without contacting the upstream.
    const mediaPage = await context.newPage();
    await load(mediaPage, "index.html");
    await mediaPage.evaluate(() => localStorage.setItem("cfa.lite", "0"));
    await mediaPage.route("**/videos/**", r => r.fulfill({status:404, body:""}));
    const cdn = "https://videooss.thecfa.cn/";
    await mediaPage.route(cdn + "**", r => r.fulfill({status:404, body:""}));
    async function assertFallback(trigger) {
      const [request] = await Promise.all([
        mediaPage.waitForRequest(r => r.url().startsWith(cdn)), trigger(),
      ]);
      const headers = await request.allHeaders();
      check(!headers.referer, "官方视频自动回退仍携带 Referer");
    }
    await assertFallback(() => load(mediaPage, "season-2026.html#case-230"));
    await load(mediaPage, "quiz.html");
    await assertFallback(() => mediaPage.evaluate(() => startRound([DATA.bank.find(q => q.k === "2026-230")])));
    check(!errors.length, errors.join("\n"));
    return "PASS 双标签并发笔记/收藏/冲突恢复/失败重试及草稿导出/专项分类/考试阈值与超时/本地午夜/判例和考试媒体回退";
  } finally {
    await context.close();
  }
}
