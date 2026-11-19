// Run against the built site in a fresh browser profile.
async (startPage) => {
  const base = new URL("./", startPage.url());
  const context = await startPage.context().browser().newContext({viewport:{width:390,height:844}});
  const page = await context.newPage();
  const navigate = name => page.goto(new URL(name, base).href, {waitUntil:"domcontentloaded"});
  function check(value, message) { if (!value) throw new Error(message); }
  try {
    await navigate("index.html");
    await page.keyboard.press("Tab");
    check(await page.locator("a.skip-link").evaluate(el => el === document.activeElement), "首个 Tab 没有到跳过导航");
    await page.keyboard.press("Enter");
    check(await page.locator("main").evaluate(el => el === document.activeElement), "跳过导航未聚焦正文");

    // Prime the installed offline site, including its deferred photograph, then actually disconnect.
    await page.evaluate(() => navigator.serviceWorker.ready.then(() => true));
    await page.waitForFunction(() => !!navigator.serviceWorker.controller);
    await page.reload();
    const photos = page.locator(".case-image img, .library-photo img");
    async function checkPhotos() {
      check(await photos.count() === 2, "判例示例或资料目录的图片缺失");
      for (const [width, height, photoWidth, photoHeight] of [[390,844,576,382], [1440,900,1280,848]]) {
        await page.setViewportSize({width,height});
        for (const img of await photos.all()) await img.scrollIntoViewIfNeeded();
        await page.waitForFunction(([w,h]) => {
          const image = document.querySelector(".library-photo img");
          return image.complete && image.naturalWidth === w && image.naturalHeight === h;
        }, [photoWidth,photoHeight], {timeout:5000});
        for (const img of await photos.all()) {
          check(await img.evaluate(async el => { await el.decode(); return el.naturalWidth > 0; }), "首页图片无法解码");
        }
      }
    }
    await checkPhotos();
    await context.setOffline(true);
    try {
      await page.reload();
      check(await page.evaluate(() => !navigator.onLine), "未切到离线状态");
      await checkPhotos();
    } finally { await context.setOffline(false); }
    await page.setViewportSize({width:390,height:844});

    const review = page.locator("#sampleReview"), sample = page.locator("#sampleText");
    const question = await sample.innerText();
    await review.click();
    check((await sample.innerText()).includes("不予认定"), "示例 183 未显示评议组的不予认定结论");
    await review.click();
    check(await sample.innerText() === question, "示例未恢复原问题");
    await page.locator("#modeLite").click();
    const daily = await page.locator("#todayCase").getAttribute("href");
    await page.locator("#todayCase").click();
    await page.locator("#dcard .concl").waitFor();
    check(/^season-20\d\d\.html#case-\d+$/.test(daily) && page.url() === new URL(daily, base).href, "今日判例未直达");
    await navigate("index.html");
    check((await page.locator("#caseAction").innerText()).includes("继续学习"), "门户未恢复学习入口");
    await page.locator("#todayCase").click();
    check(page.url() === new URL(daily, base).href, "继续学习定位错误");

    await navigate("index.html");
    await page.getByRole("link", {name:/完整判例/}).click();
    check(page.url() === new URL("season-2026.html#case-183", base).href &&
      (await page.locator("#dcard .concl").innerText()).includes("评议组对此判例不予认定"), "首页示例未连到同期同号官方认定");
    await navigate("index.html");
    await page.evaluate(() => {
      localStorage.setItem("cfa2024.last", JSON.stringify({seq:1, ts:Date.now()+1000}));
      localStorage.setItem("cfa2024.seen", JSON.stringify({"1":true, "123":true}));
    });
    await page.reload();
    check(await page.locator("#todayCase").getAttribute("href") === "season-2024.html#case-1" &&
      Number(await page.locator("#msFoot b").innerText()) >= 2, "旧版已读记录未恢复");
    check(await page.locator("#dailyLink").isVisible(), "恢复学习时今日判例入口消失");
    await page.locator("#dailyLink").click();
    check(page.url() === new URL(daily, base).href, "单独的今日判例入口错误");

    await navigate("index.html");
    await page.evaluate(() => localStorage.setItem("cfa2024.last", JSON.stringify({seq:123, ts:Date.now()+2000})));
    await page.setViewportSize({width:320,height:640});
    await page.reload();
    const teams = await page.locator("#homeTeam, #awayTeam").allTextContents();
    check(teams[0].includes("河南万仙山女足") && teams[1].includes("永川茶山竹海澄狮女足"), "长队名未恢复");
    check(await page.evaluate(() => {
      const action = document.querySelector("#todayCase").getBoundingClientRect();
      return document.documentElement.scrollWidth <= innerWidth &&
        [...document.querySelectorAll("#homeTeam,#awayTeam")].every(team => {
          const range = document.createRange(); range.selectNodeContents(team);
          return [...range.getClientRects()].every(r => r.left >= 0 && r.right <= innerWidth + 1 &&
            (r.right <= action.left + 1 || r.left >= action.right - 1 || r.bottom <= action.top + 1 || r.top >= action.bottom - 1));
        });
    }), "320px 长队名超出视口或覆盖学习按钮");

    const picker = page.getByLabel("资料分类");
    const destinations = [
      ["国内赛季评议", "season-2025.html"], ["各队得失盘点", "stats-2024.html"],
      ["规则与练习", "rules.html"], ["欧洲判例与协议", "uefa.html"], ["美洲与全球评议", "pro.html"],
    ];
    check(await picker.locator("option").count() === destinations.length, "资料分类应有五组");
    for (const [label, file] of destinations) {
      await picker.selectOption({label});
      const shelf = page.getByRole("list", {name:label, exact:true});
      await shelf.locator('a[href="' + file + '"]').click();
      await page.waitForURL(url => url.pathname === new URL(file, base).pathname);
      check(!(await page.title()).includes("页面不存在"), "目录入口不可用 " + label);
      await navigate("index.html");
    }

    const search = page.getByRole("searchbox", {name:"全站搜索"});
    await search.fill("掷物"); await search.press("Enter");
    await page.locator('#sres a[href*="rules.html#law-12-p-"]').first().waitFor();
    await page.locator("#btnNav").click();
    check(await page.locator("#btnNav").getAttribute("aria-expanded") === "true" &&
      await page.evaluate(() => document.activeElement.id === "navClose"), "导航焦点或状态错误");
    await page.keyboard.press("Tab");
    check(await page.evaluate(() => !!document.activeElement.closest("#navDrawer")), "焦点脱离导航");
    await page.keyboard.press("Escape");
    await page.waitForFunction(() => !document.getElementById("navDrawer").open &&
      document.getElementById("btnNav").getAttribute("aria-expanded") === "false" &&
      document.activeElement.id === "btnNav", null, {timeout:5000});
    for (const theme of ["dark","light"]) {
      await page.evaluate(t => document.documentElement.dataset.theme = t, theme);
      const size = await page.locator("#btnTheme").boundingBox();
      check(size.width >= 40 && size.height >= 44, "主题按键太小");
      check(await page.locator("#btnTheme svg:visible").count() === 1, "主题图标缺失");
      await page.locator("#btnTheme").click();
      check(await page.evaluate(() => document.documentElement.dataset.theme) !== theme, "主题无法切换");
    }
    await navigate("rfef.html");
    await page.locator("#btnEs").click();
    for (const width of [320,390,768,1080,1440,1920]) {
      await page.setViewportSize({width,height:844});
      check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "RFEF 布局溢出 " + width);
    }
    return "PASS 首页示例认定、五组资料、离线图片、学习进度、320px长队名、键盘跳转、搜索与RFEF";
  } finally { await context.close(); }
}
