// Run with playwright-cli run-code --filename tests/browser_compare.js against the built site.
async (startPage) => {
  const url = new URL("compare.html", startPage.url());
  const browser = startPage.context().browser();
  const context = await browser.newContext({viewport:{width:390,height:844}});
  const page = await context.newPage();
  const errors = [];
  context.on("page", tab => tab.on("pageerror", e => errors.push(e.message)));
  page.on("pageerror", e => errors.push(e.message));
  function check(ok, message) { if (!ok) throw new Error(message); }
  async function open(tab, fragment) {
    await tab.goto(new URL("#" + fragment, url).href, {waitUntil:"domcontentloaded"});
    await tab.locator("#workspace").waitFor();
  }
  async function notePick(tab, verdict, note) {
    await tab.locator('input[name="verdict"][value="' + verdict + '"]').check();
    await tab.locator("#observation").fill(note);
    await tab.locator("#save-pick").click();
  }
  async function waitSaved(tab, value) {
    await tab.waitForFunction(text => Object.keys(localStorage)
      .filter(key => key.startsWith("cfa.compare."))
      .some(key => (localStorage.getItem(key) || "").includes(text)), value, {timeout:10000});
  }
  async function paired(tab) {
    await tab.locator("#print-review").waitFor();
    check(await tab.locator("#reflection").isVisible(), "答完两例后不能写反思");
  }
  try {
    await page.goto(new URL("index.html",url).href);
    await page.getByLabel("资料分类").selectOption({label:"规则与练习"});
    await page.getByRole("list",{name:"规则与练习"}).getByRole("link",{name:/裁判尺度对照课/}).click();
    check(page.url() === url.href, "首页资料目录未打开对照课");
    const search = new URL("search.html",url);
    search.searchParams.set("q","尺度对照课");
    await page.goto(search.href);
    const searchLessons = page.locator('#sres a[href^="compare.html#lesson-"]');
    await searchLessons.first().waitFor();
    check(await searchLessons.count() === 4 && await page.locator('#sres a[href="compare.html#free"]').count() === 1,
      "统一搜索没有覆盖四个课程与自由配对");
    await page.locator('#sres a[href="compare.html#lesson-offside"]').click();
    await page.locator("#lesson-form").waitFor();
    await page.goto(url.href);
    const oldQuiz = '{"2026-1":{"wrong":1}}';
    await page.evaluate(value => localStorage.setItem("cfa.quiz.wrong",value), oldQuiz);
    const data = await page.locator("#compare-data").evaluate(el => JSON.parse(el.textContent));
    const expected = {
      handball:["2026-1","2026-28"], offside:["2026-14","2026-29"],
      "contact-intensity":["2026-94","2026-47"], "penalty-contact":["2026-13","2026-18"],
    };
    check(data.lessons.length === 4, "精编课数量错误");
    for (const lesson of data.lessons) {
      check(JSON.stringify(lesson.cases.map(c => c.id)) === JSON.stringify(expected[lesson.id]), "策展案例错配 " + lesson.id);
      await page.locator('a[href="#lesson-' + lesson.id + '"]').first().click();
      await page.locator("#lesson-form").waitFor();
      const [a,b] = lesson.cases;
      check(!(await page.locator("#workspace").innerText()).includes(a.quote), "作答前 A 案认定已揭晓");
      await notePick(page, a.answer, "A 的观察 " + lesson.id);
      check(!(await page.locator("#workspace").innerText()).includes(b.quote), "提交 A 后 B 案认定已揭晓");
      await notePick(page, lesson.id === "offside" ? "unsure" : b.answer, "B 的观察 " + lesson.id);
      await paired(page);
      const review = page.locator("#workspace");
      for (const [index, item] of [a,b].entries()) {
        const side = page.locator(index === 0 ? "#side-a" : "#side-b");
        if (await side.isVisible()) await side.click();
        check((await review.innerText()).includes(item.quote), "揭晓缺评议原文 " + item.id);
        const panel = page.locator(index === 0 ? "#panel-a" : "#panel-b");
        const source = new URL(await panel.getByRole("link",{name:/足协原文/}).getAttribute("href"));
        const [season,seq] = item.id.split("-");
        check(source.hostname === "www.thecfa.cn" && source.pathname.endsWith(".html") &&
          await panel.getByRole("link",{name:"完整判例"}).getAttribute("href") === "season-" + season + ".html#case-" + seq,
          "认定缺少可访问的足协原文或完整判例 " + item.id);
      }
      check((await review.innerText()).includes(lesson.difference), "揭晓缺少本组尺度差异 " + lesson.id);
      const reflection = "本次课后反思 " + lesson.id;
      await page.locator("#reflection").fill(reflection);
      await waitSaved(page, reflection);
      await page.reload();
      await paired(page);
      check(await page.locator("#reflection").inputValue() === reflection, "重载丢失反思 " + lesson.id);
      if (lesson.id === "handball") {
        await page.evaluate(() => { window.print = () => { window.comparePrintRequested = true; }; });
        await page.locator("#print-review").click();
        check(await page.evaluate(() => window.comparePrintRequested), "打印按钮未请求浏览器打印");
      }
      if (lesson.id === "handball") {
        await page.evaluate(() => window.addEventListener("beforeprint", () => {
          window.printedBothCases = ["#panel-a","#panel-b"].every(s => document.querySelector(s).getClientRects().length) &&
            document.getElementById("printed-reflection").textContent.includes("本次课后反思");
        }, {once:true}));
        const pdf = await page.pdf({format:"A4"});
        check(pdf.byteLength > 1000 && await page.evaluate(() => window.printedBothCases), "打印复盘单遗漏双案或反思");
      }
      await page.goto(url.href);
    }

    await open(page, "lesson-handball");
    await paired(page);
    const previous = await page.locator("#history-attempt").inputValue();
    await page.locator("#redo").click();
    await page.locator("#lesson-form").waitFor();
    check(await page.locator("#observation").inputValue() === "", "重做带入上一轮草稿");
    await page.locator("#history-attempt").selectOption(previous);
    await paired(page);
    check(await page.locator("#reflection").inputValue() === "本次课后反思 handball", "重做覆盖历史");

    const peer = await context.newPage();
    await open(page,"lesson-offside");
    await page.locator("#redo").click();
    const original = "两张标签同时打开的草稿";
    await page.locator("#observation").fill(original);
    await waitSaved(page, original);
    await Promise.all([page.reload(),open(peer,"lesson-offside")]);
    for (const tab of [page,peer]) check(await tab.locator("#observation").inputValue() === original, "没有打开同一份草稿");
    const concurrent = ["独立并行草稿 A","独立并行草稿 B"];
    await Promise.all([page,peer].map((tab,i) => tab.locator("#observation").fill(concurrent[i])));
    await Promise.all(concurrent.map(value => waitSaved(page,value)));
    await peer.close();
    await page.reload();
    const options = page.locator("#history-attempt option");
    const ids = await options.evaluateAll(x => x.map(o => o.value));
    const recovered = [];
    for (const id of ids) {
      await page.locator("#history-attempt").selectOption(id);
      if (await page.locator("#observation").isVisible()) recovered.push(await page.locator("#observation").inputValue());
    }
    check(concurrent.every(v => recovered.includes(v)), "并行草稿没有从历史恢复");

    await open(page,"lesson-contact-intensity");
    await page.locator("#redo").click();
    await page.evaluate(() => {
      const write = Storage.prototype.setItem;
      window.restoreCompareWrites = () => { Storage.prototype.setItem = write; };
      Storage.prototype.setItem = function(key, value) {
        if (key.startsWith("cfa.compare.")) throw new DOMException("storage full","QuotaExceededError");
        return write.call(this,key,value);
      };
    });
    const draft = "暂存于页面的真实观察";
    await page.locator("#observation").fill(draft);
    await page.locator("#retry-save").waitFor();
    check(await page.locator("#observation").inputValue() === draft &&
      (await page.locator("#save-status").innerText()).trim(), "满额时没有保留草稿和状态");
    await page.evaluate(() => restoreCompareWrites());
    await page.locator("#retry-save").click();
    await waitSaved(page, draft);
    await page.reload();
    check(await page.locator("#observation").inputValue() === draft, "重试后草稿未保存");

    for (const id of ["2024-1","2024-2","2024-3","2024-112"]) {
      const offside = id === "2024-112";
      const peerId = offside ? "2026-14" : "2026-13";
      const official = "https://www.thecfa.cn/zyls1/" + (offside ? "20240807/34876.html" : "20240311/33847.html");
      await open(page,"pair-" + id + "~" + peerId);
      const panel = page.locator("#panel-a");
      check((await panel.innerText()).includes("未单列评议结论") &&
        await panel.getByRole("link",{name:/足协原文/}).getAttribute("href") === official, "未单列结论被误写成正式认定 " + id);
    }
    for (const [id,peerId] of [["2025-183","2026-1"],["2025-188","2026-94"]]) {
      await open(page,"pair-" + id + "~" + peerId);
      const panel = page.locator("#panel-a");
      check(await panel.getByRole("link",{name:/足协原文/}).getAttribute("href") ===
        "https://www.thecfa.cn/cppy/20250917/36917.html", "原期引用错误 " + id);
      check(await panel.getByRole("link",{name:/补充认定/}).getAttribute("href") ===
        "https://www.thecfa.cn/cppy/20250924/36927.html", "补充认定引用错误 " + id);
    }
    for (const invalid of ["pair-2026-1~2026-1", "pair-2026-1~2026-14", "pair-2026-1~2099-1"]) {
      await open(page,invalid);
      await page.locator("#workspace [role=alert]").waitFor();
      check(await page.locator("#pick-category").isVisible(), "错误配对链接未给出重新选择入口");
    }
    await open(page,"free");
    await page.locator("#pick-category").selectOption("handball");
    await page.locator("#season-a").selectOption("2026");
    await page.locator("#filter-a").fill("山东泰山");
    const matches = await page.locator("#pick-a option").evaluateAll(options =>
      options.filter(o => o.value).map(o => [o.value,o.textContent]));
    check(matches.some(([id]) => id === "2026-1") &&
      matches.every(([id,text]) => id.startsWith("2026-") && text.includes("山东泰山")), "分类、赛季和球队组合筛选错误");
    await page.locator("#pick-a").selectOption("2026-1");
    await page.locator("#pick-b").selectOption("2026-1");
    check(await page.locator("#open-pair").isDisabled(), "相同案例不应能开始双案比较");
    await page.locator("#pick-b").selectOption("2026-28");
    await page.locator("#open-pair").click();
    await page.waitForURL(u => u.hash === "#pair-2026-1~2026-28");
    for (const [width,height] of [[320,640],[390,844],[768,1024],[1440,900]]) {
      await page.setViewportSize({width,height});
      check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "自由组合横向溢出 " + width);
      if (width <= 390) {
        for (const side of ["b","a"]) {
          await page.locator("#side-" + side).click();
          check(await page.locator("#panel-" + side).isVisible(), "移动对照页签未选中 " + side);
        }
      }
    }
    await page.setViewportSize({width:390,height:844});
    await page.locator("#side-a").focus();
    await page.keyboard.press("End");
    check(await page.locator("#side-b").getAttribute("aria-selected") === "true" &&
      await page.locator("#panel-b").isVisible(), "页签 End 键未切换到 B 案");
    await page.locator("#swap-pair").click();
    await page.waitForURL(u => u.hash === "#pair-2026-28~2026-1");
    // The URL changes before hashchange renders the two new panels.
    for (const [side, seq, match] of [["a",28,"青岛海牛 对 青岛西海岸"],["b",1,"山东泰山 对 北京国安"]]) {
      const panel = page.locator("#panel-" + side);
      const fullCase = panel.locator('a[href="season-2026.html#case-' + seq + '"]');
      await fullCase.waitFor({state:"attached"});
      await page.locator("#side-" + side).click();
      check(await panel.isVisible() && await panel.getByRole("heading",{level:2}).innerText() === match,
        "交换后 " + side.toUpperCase() + " 面板未显示 " + match);
      check(await fullCase.count() === 1 && await fullCase.innerText() === "完整判例",
        "交换后 " + side.toUpperCase() + " 面板的完整判例链接错误");
    }
    await page.evaluate(() => Object.defineProperty(navigator,"clipboard",{configurable:true,
      value:{writeText:async () => {throw new DOMException("clipboard unavailable","NotAllowedError");}}}));
    await page.locator("#copy-pair").click();
    const fallback = page.getByRole("textbox", {name:"复制此链接"});
    await fallback.waitFor();
    const shared = await fallback.inputValue();
    const canonical = await page.locator('link[rel="canonical"]').getAttribute("href");
    const local = ["localhost","[::1]"].includes(url.hostname) || url.hostname.startsWith("127.") || url.hostname.endsWith(".localhost");
    const expectedShare = new URL("#pair-2026-28~2026-1",local ? canonical : url).href;
    check(shared === expectedShare && !shared.includes(draft), "分享回退未给出外部可用的纯案例链接");
    const fresh = await browser.newContext();
    try {
      const opened = await fresh.newPage();
      const published = new URL(shared);
      const localPage = new URL(published.pathname.split("/").pop(), url);
      localPage.hash = published.hash;
      await opened.goto(localPage.href);
      await opened.locator("#workspace").waitFor();
      check((await opened.locator("#workspace").innerText()).length > 40 &&
        !(await opened.locator("#workspace").innerText()).includes(draft), "新设备不能打开纯案例链接");
    } finally { await fresh.close(); }

    const media = await browser.newContext({serviceWorkers:"block"});
    try {
      const missing = await media.newPage();
      await missing.route("**/videos/**", r => r.fulfill({status:404,body:""}));
      await missing.route("https://videooss.thecfa.cn/**", r => r.fulfill({status:404,body:""}));
      await open(missing,"lesson-handball");
      const [request] = await Promise.all([missing.waitForRequest(r => r.url().startsWith("https://videooss.thecfa.cn/")),
        missing.locator("[data-play]").click()]);
      check(!(await request.allHeaders()).referer, "视频回退发送了 Referer");
      await missing.locator("[data-media-status]").getByText(/无法打开/).waitFor();
      await notePick(missing,"unsure","无片时的观察");
      await missing.goto(new URL("index.html",url).href);
      await missing.locator("#modeLite").click();
      await open(missing,"lesson-handball");
      check(await missing.locator("[data-play], video").count() === 0 &&
        await missing.locator("[data-official-video]").isVisible(), "轻量版应提供官方视频链接");
    } finally { await media.close(); }

    await page.evaluate(() => navigator.serviceWorker.ready.then(() => true));
    await page.waitForFunction(() => !!navigator.serviceWorker.controller);
    await page.reload();
    await context.setOffline(true);
    await page.reload();
    check(await page.evaluate(() => !navigator.onLine) && await page.locator("#workspace").isVisible(), "断网后自由组合不可用");
    await open(page,"lesson-penalty-contact");
    await paired(page);
    check(await page.locator("#reflection").inputValue() === "本次课后反思 penalty-contact", "断网不能恢复已完成学习");
    check(await page.evaluate(() => localStorage.getItem("cfa.quiz.wrong")) === oldQuiz, "对照课改写了原错题本");
    check(!errors.length, errors.join("\n"));
    return "PASS 四组八案/先判后揭晓/备注与反思/历史重做/并行与满额/自由配对/移动打印/纯链接分享/PWA断网";
  } finally { await context.close(); }
}
