// Run with playwright-cli run-code --filename tests/browser_navigation.js on the built site.
async (startPage) => {
  const base = new URL("./", startPage.url());
  const ctx = await startPage.context().browser().newContext({
    hasTouch: true, reducedMotion: "reduce", serviceWorkers: "block", colorScheme: "light"
  });
  await ctx.route(/^https?:/, route => {
    const url = new URL(route.request().url());
    return url.origin === base.origin ? route.continue() : route.abort();
  });
  await ctx.addInitScript(() => {
    try { localStorage.setItem("cfa.lite", "1"); } catch (_) {}
  });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  const check = (ok, message) => { if (!ok) throw Error(message); };
  const focused = selector => page.evaluate(s => document.activeElement.matches(s), selector);
  const open = href => page.goto(new URL(href, base).href, {waitUntil: "domcontentloaded"});
  const tap = id => page.locator(id).tap();

  async function checkHeader(route, width, height) {
    await page.setViewportSize({width, height});
    await open(route);
    const layout = await page.evaluate(() => {
      const header = document.querySelector(".page-toolbar");
      const workspace = document.querySelector(".workspace, .layout").getBoundingClientRect();
      const rect = header.getBoundingClientRect();
      const controls = Array.from(header.querySelectorAll("a, button, input")).filter(el => el.getClientRects().length);
      const blocked = controls.filter(el => {
        const b = el.getBoundingClientRect();
        return b.left < 0 || b.right > innerWidth || b.top < rect.top || b.bottom > rect.bottom ||
          !el.contains(document.elementFromPoint(b.left + b.width/2, b.top + b.height/2));
      });
      return {
        headerWidth: header.scrollWidth, height: rect.height, start: workspace.top,
        bottom: workspace.bottom, view: innerHeight, blocked: blocked.map(el => el.id || el.className),
        controls: controls.length, searchWidth: document.getElementById("fSearch").clientWidth
      };
    });
    check(layout.headerWidth === width && layout.blocked.length === 0,
      route + " " + width + " 顶栏控件不能直接点击 " + JSON.stringify(layout));
    check(layout.start === layout.height && layout.bottom === layout.view, route + " 顶栏与工作区高度不同步");
    check(layout.height === (width <= 760 ? 96 : 56), "顶栏断点异常");
    check(layout.searchWidth >= 80, "搜索框过窄");

    await page.locator(".skip-link").focus();
    for (let i = 0; i < layout.controls; i++) {
      await page.keyboard.press("Tab");
      check(await focused(".page-toolbar *") && await page.evaluate(() => {
        const b = document.activeElement.getBoundingClientRect();
        return b.left >= 0 && b.right <= innerWidth && document.querySelector(".topbar").scrollLeft === 0;
      }), route + " 第 " + i + " 个顶栏焦点在屏外");
    }
    await page.keyboard.press("Tab");
    if (width <= 768) check(!await focused(".sidebar *"), route + " 关闭的侧栏收到键盘焦点");
    if (width <= 760) {
      for (const id of ["#btnNav", "#btnSb", "#btnTheme", ...(route.includes("season") ? ["#btnHideAns","#btnLite","#btnHelp"] : [])]) {
        const label = page.locator(id + " span").filter({hasText: /[\u3400-\u9fff]/}).last();
        check(await label.isVisible(), id + " 没有可见操作名");
      }
    }
  }

  async function toggleTheme() {
    const before = await page.locator("html").getAttribute("data-theme");
    await tap("#btnTheme");
    check(await page.locator("html").getAttribute("data-theme") !== before, "主题没有切换");
  }

  try {
    for (const [width, height] of [[320,640], [390,844], [768,1024], [1440,900]]) {
      await checkHeader("season-2026.html?case=229", width, height);
      await toggleTheme();
      const hide = page.locator("#btnHideAns"), lite = page.locator("#btnLite");
      const prevHide = await hide.getAttribute("aria-pressed");
      await hide.tap();
      check(await hide.getAttribute("aria-pressed") !== prevHide, "隐藏答案开关没有切换");
      await hide.tap();
      await lite.tap();
      check(await lite.getAttribute("aria-pressed") === "false", "完整版没有切换");
      await lite.tap();
      await tap("#btnHelp");
      check(await page.locator("#modalHelp").isVisible(), "说明无法打开");
      await page.keyboard.press("Escape");
      check(await focused("#btnHelp"), "说明关闭后未回到入口");

      if (width <= 768) {
        await tap("#btnNav");
        check(await focused("#navClose") && await page.locator('#navDrawer a[href="rules.html"]').isVisible(), "站点导航未打开");
        await page.keyboard.press("Escape");
        check(await focused("#btnNav"), "站点导航关闭后未回到入口");
        await tap("#btnSb");
        check(await focused("#sidebar button") && await page.locator("#btnSb").getAttribute("aria-expanded") === "true", "开筛选没有聚焦内部控件");
        await page.locator("#btnStats").focus();
        await page.keyboard.press("Enter");
        await page.keyboard.press("Escape");
        check(await focused("#btnStats") && await page.locator("#sidebar").isVisible(), "关闭模态弹窗时丢失底层筛选焦点");
        await page.keyboard.press("Escape");
        check(await focused("#btnSb") && !await page.locator("#sidebar").isVisible(), "关闭筛选未还原焦点");
        await tap("#mobileBack");
        check(await focused('.prow[data-seq="229"]'), "从详情没有回到原判例");
      } else {
        for (const group of await page.locator(".grp-btn").all()) {
          await group.focus();
          await page.keyboard.press("Enter");
          check(await group.getAttribute("aria-expanded") === "true", "站点分组无法打开");
          await page.keyboard.press("Tab");
          check(await focused(".navpop a"), "键盘无法进入站点分组");
          await page.keyboard.press("Escape");
        }
        await tap("#btnSb");
        check(!await page.locator("#sidebar").isVisible() && (await page.locator(".plist").boundingBox()).width > 250, "桌面收起侧栏后判例列表丢失");
        await tap("#btnSb");
        await page.locator(".prow.sel").focus();
        await page.keyboard.press("Tab");
        check(await focused("#detail *"), "一次 Tab 无法从判例列表进入详情");
        await page.keyboard.press("Shift+Tab");
        check(await focused(".prow.sel"), "从详情返回时丢失判例焦点");
      }
      check(await page.locator('.prow[tabindex="0"]').count() === 1, "全季判例应当共用一个 Tab 停靠点");
      await page.keyboard.press("Home");
      check(await page.locator(".prow").first().evaluate(el => el === document.activeElement), "Home 没有聚焦首例");
      await page.keyboard.press("ArrowDown");
      const target = await page.evaluate(() => document.activeElement.dataset.seq);
      check(!!target, "下箭头没有聚焦下一例");
      await page.keyboard.press("End");
      check(await page.locator(".prow").last().evaluate(el => el === document.activeElement), "End 没有聚焦末例");
      await page.keyboard.press("Home");
      await page.keyboard.press("ArrowDown");
      await page.keyboard.press("Enter");
      check(new URL(page.url()).hash === "#case-" + target, "Enter 没有打开聚焦判例");
      if (width <= 768) {
        check(await focused("#dHead"), "打开详情没有聚焦标题");
        await page.locator(".skip-link").focus();
        await page.keyboard.press("Enter");
        check(await focused(".prow.sel"), "跳至判例列表没有越过顶栏");
        await tap("#btnSb");
        const filter = page.locator("#pathList button").first();
        await filter.focus();
        await page.keyboard.press("Enter");
        check(await focused("#pathList button") && !await page.evaluate(() => document.body.classList.contains("detail-open")),
          "键盘筛选后丢失焦点或离开列表");
        await page.keyboard.press("Escape");
      }
      await page.keyboard.press("/");
      check(await focused("#fSearch"), "原有搜索快捷键失效");

      await checkHeader("rules.html#law-12", width, height);
      await toggleTheme();
      const fs = () => page.locator("html").evaluate(el => parseInt(getComputedStyle(el).getPropertyValue("--fs")));
      const startSize = await fs();
      await tap("#fsPlus");
      check(await fs() === startSize+1, "增大字号无效");
      await tap("#fsMinus");
      check(await fs() === startSize, "减小字号无效");
      await page.locator("#fSearch").fill("越位");
      check(await page.locator("#searchBox .sr").first().isVisible(), "规则搜索未显示结果");
      const results = await page.locator("#searchBox").boundingBox(), header = await page.locator(".topbar").boundingBox();
      check(results.y >= header.height, "规则搜索结果与顶栏重叠");
      await page.keyboard.press("Escape");
      // Exercise the speech controls without depending on an installed voice or playing audio.
      await page.evaluate(() => {
        if (!window.speechSynthesis) return;
        speechSynthesis.speak = utterance => { document.body.dataset.spoken = utterance.lang; };
        speechSynthesis.cancel = () => { delete document.body.dataset.spoken; };
      });
      if (await page.evaluate(() => !!window.speechSynthesis)) {
        await tap("#btnTTS");
        check(await page.locator("body").getAttribute("data-spoken") === "zh-CN", "朗读按钮未开始朗读本章");
        await tap("#btnTTS");
        check(await page.locator("body").getAttribute("data-spoken") === null, "朗读不能停止");
      }
      const expanded = () => page.locator("#btnSb").getAttribute("aria-expanded");
      if (width <= 768) {
        await tap("#btnSb");
        check(await focused('.toc-item[data-id="law-12"]') && await expanded() === "true", "目录没有聚焦当前章");
        await page.keyboard.press("Escape");
        check(await focused("#btnSb") && await expanded() === "false", "目录无法用 Esc 返回");
        await tap("#btnSb");
        await page.locator('.toc-item[data-id="law-11"]').tap();
        check(await focused("#secTitle") && new URL(page.url()).hash === "#law-11" && await expanded() === "false", "点目录没有返回所选章");
      } else {
        check(await expanded() === "true", "桌面目录的初始状态错误");
        await tap("#btnSb");
        check(!await page.locator("#tocSidebar").isVisible() && (await page.locator("#main").boundingBox()).x === 0, "桌面目录收起无效");
        await tap("#btnSb");
        check(await page.locator("#tocSidebar").isVisible(), "桌面目录无法重新打开");
      }
    }
    await page.setViewportSize({width:320,height:640});
    await open("search.html");
    check(await page.locator(".page-toolbar").count() === 0 && (await page.locator(".topbar").boundingBox()).height === 56, "普通页多占了一排");
    check(errors.length === 0, errors.join(" | "));
    return "PASS 320/390/768/1440 顶栏触控与 Tab、双层焦点返回、判例列表导航、规则目录和搜索";
  } finally { await ctx.close(); }
}
