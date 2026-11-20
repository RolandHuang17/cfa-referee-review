// Run with playwright-cli run-code --filename tests/browser_theme_contrast.js on the built site.
async (startPage) => {
  const base = new URL("./", startPage.url());
  const ctx = await startPage.context().browser().newContext({reducedMotion: "reduce", serviceWorkers: "block"});
  const check = (condition, message) => { if (!condition) throw Error(message); };
  const pages = [
    ["index.html", [".hero h1", ".intro", ".case-meta", ".study-button", "#portalSearch"], "#portalSearch"],
    ["season-2026.html?case=229", [".cid", ".txt", ".d-card .badge", "#noteBox", "#fSearch", "#btnLite"], "#fSearch"],
    ["quiz.html", [".page-h", ".page-sub", ".stat span", "#btnStart", ".chip.on", "#btnLite"], "#btnStart"],
    ["rules.html#law-12", [".content h2", ".content p", ".pages", ".hltip", "#fSearch", "#secNote"], "#secNote"],
    ["search.html", [".shead h1", ".shead .sub", "#q"], "#q"]
  ];

  // Every sampled surface is flat. Composite its actual ancestor backgrounds and element
  // opacity. A gradient, image or transparent canvas needs pixel sampling instead.
  function measure(element, mode) {
    const style = getComputedStyle(element);
    const text = mode === "placeholder" ? getComputedStyle(element, "::placeholder") : style;
    function rgba(value) {
      const channels = value.match(/[\d.]+/g)?.map(Number);
      if (!value.startsWith("rgb") || !channels) throw Error("Unsupported computed color " + value);
      const [r, g, b, a = 1] = channels;
      return [r, g, b, a];
    }
    function over(front, back) {
      const a = front[3] + back[3] * (1 - front[3]);
      const rgb = [0,1,2].map(i => a ? (front[i]*front[3] + back[i]*back[3]*(1-front[3])) / a : 0);
      return [...rgb, a];
    }
    function luminance(rgb) {
      const [r,g,b] = rgb.map(v => v/255).map(v => v <= .04045 ? v/12.92 : ((v+.055)/1.055)**2.4);
      return r*.2126 + g*.7152 + b*.0722;
    }
    let ink = rgba(mode === "focus" ? style.outlineColor : text.color);
    let paper = [0,0,0,0];
    if (mode === "placeholder") ink[3] *= Number(text.opacity);
    for (let node = mode === "focus" ? element.parentElement : element; node; node = node.parentElement) {
      const layer = getComputedStyle(node);
      if (paper[3] < 1 && layer.backgroundImage !== "none") throw Error("Sample has a background image");
      const surface = rgba(layer.backgroundColor);
      ink = over(ink, surface);
      paper = over(paper, surface);
      ink[3] *= Number(layer.opacity);
      paper[3] *= Number(layer.opacity);
    }
    if (paper[3] < 1) throw Error("Sample has a transparent canvas");
    const [dark, light] = [luminance(ink), luminance(paper)].sort((a,b) => a-b);
    const size = parseFloat(text.fontSize);
    const large = size >= 24 || (Number(text.fontWeight) >= 700 && size >= 18.667);
    const ring = style.outlineStyle !== "none" && parseFloat(style.outlineWidth) >= 2 && element.matches(":focus-visible");
    return {ratio: (light+.05)/(dark+.05), minimum: mode === "focus" || large ? 3 : 4.5, ring,
      fg: ink.slice(0,3).map(Math.round).join(","), bg: paper.slice(0,3).map(Math.round).join(",")};
  }

  try {
    await ctx.route(/^https?:/, route => new URL(route.request().url()).origin === base.origin ? route.continue() : route.abort());
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", e => errors.push(e.message));
    await ctx.addInitScript(() => { try { localStorage.setItem("cfa.lite", "1"); } catch (_) {} });
    let count = 0;
    for (const [width,height] of [[320,640],[390,844],[768,1024],[1440,900]]) {
      await page.setViewportSize({width,height});
      for (const theme of ["light","dark"]) {
        for (const [href, selectors, focusTarget] of pages) {
          await page.goto(new URL(href,base).href, {waitUntil: "domcontentloaded"});
          if (await page.locator("html").getAttribute("data-theme") !== theme) await page.locator("#btnTheme").click();
          await page.mouse.move(width-1, height-1);
          const where = href + " " + width + " " + theme;
          if (href.startsWith("rules")) await page.locator(".notebox:has(#secNote)>summary").click();

          async function sample(selector, mode) {
            const target = page.locator(selector).first();
            check(await target.isVisible(), where + " hidden sample " + selector);
            const reading = await target.evaluate(measure, mode);
            check(reading.ratio >= reading.minimum, where+" "+selector+" "+mode+" "+reading.fg+"/"+reading.bg+" = "+reading.ratio);
            if (mode === "focus") check(reading.ring, where + " missing keyboard outline on " + selector);
            count++;
          }
          for (const selector of selectors) {
            const isPlaceholder = await page.locator(selector).first().evaluate(e => Boolean(e.placeholder && !e.value));
            await sample(selector, isPlaceholder ? "placeholder" : "text");
          }
          if (href.startsWith("rules")) {
            await page.locator(".notebox:has(#secNote)>summary").focus();
          } else {
            await page.locator(focusTarget).focus();
            await page.keyboard.press("Shift+Tab");
          }
          await page.keyboard.press("Tab");
          check(await page.locator(focusTarget).evaluate(e => e === document.activeElement), where + " unexpected Tab order");
          await sample(focusTarget, "focus");

          if (href.startsWith("season")) {
            const badge = page.locator(".d-card .badge").first();
            check(/错漏判|支持原判|不予认定/.test(await badge.innerText()), where + " verdict needs a text label");
            await page.locator("#btnHideAns").click();
            check(await page.locator("#btnHideAns").getAttribute("aria-pressed") === "true", where + " missing toggle state");
            await sample("#btnHideAns","text");
            await page.locator("#btnHideAns").click();
          }
          if (href === "search.html") {
            await page.locator("#q").fill("手球");
            await page.locator(".sr .t2 mark").first().waitFor();
            for (const s of [".scount",".sr .t1",".sr .t2",".sr .t2 mark"]) await sample(s,"text");
          }
          if (href === "quiz.html") {
            check(await page.locator("#scrStart").evaluate(e => getComputedStyle(e).animationName) === "none", where + " reduced motion");
          }
        }
      }
    }
    check(!errors.length, errors.join("\n"));
    return "PASS " + count + " text, placeholder and keyboard samples across five pages, four widths and two themes";
  } finally { await ctx.close(); }
}