// Run against python scripts/serve.py. The same check supports a lightweight site without videos.
async startPage => {
  const base = new URL("./", startPage.url());
  const ctx = await startPage.context().browser().newContext({serviceWorkers:"block"});
  const check = (ok, message) => { if (!ok) throw Error(message); };
  await ctx.route(/^https?:/, route => new URL(route.request().url()).origin === base.origin
    ? route.continue() : route.abort());
  const page = await ctx.newPage(), played = [], missing = [];
  try {
    for (const [seq, clip] of [[120, "i10c03-1.mp4"], [237, "i25c05-1.mp4"]]) {
      const firstResponse = page.waitForResponse(response =>
        response.request().resourceType() === "media" && new URL(response.url()).pathname.endsWith("/videos/2026/" + clip));
      await page.goto(new URL("season-2026.html?case=" + seq, base).href, {waitUntil:"domcontentloaded"});
      const first = await firstResponse;
      if (first.status() === 404) {
        await page.locator("#vfailGoLite").focus();
        await page.keyboard.press("Enter");
        const toggle = page.locator("#btnLite");
        check(await page.locator("html").getAttribute("data-lite") === "1" &&
          await toggle.getAttribute("aria-pressed") === "true" &&
          await toggle.evaluate(el => el === document.activeElement) &&
          await page.locator("#dHead").isVisible() && await page.locator("#srcActions a").count() >= 2,
          "视频缺失后未能用键盘恢复文字、官方来源和轻量版开关");
        await page.reload();
        check(await toggle.getAttribute("aria-pressed") === "true" &&
          await page.evaluate(() => localStorage.getItem("cfa.lite")) === "1", "刷新丢失轻量模式");
        await toggle.focus();
        await page.keyboard.press("Enter");
        check(await toggle.getAttribute("aria-pressed") === "false" &&
          await page.evaluate(() => localStorage.getItem("cfa.lite")) === "0" &&
          await page.locator("html").getAttribute("data-lite") === null, "无法用同一开关返回完整版");
        missing.push(seq);
        continue;
      }
      check(first.status() === 206 && first.headers()["content-range"], "本地影片未按范围发送");
      await page.waitForFunction(() => {
        const video = document.getElementById("dvid");
        return video.videoWidth > 0 && Number.isFinite(video.duration) && video.duration > 2;
      });
      const result = await page.locator("#dvid").evaluate(async video => {
        function nextEvent(name) {
          return new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(Error("播放器未收到 " + name)), 8000);
            video.addEventListener(name, () => { clearTimeout(timer); resolve(); }, {once:true});
          });
        }
        video.muted = true;
        await video.play();
        const firstTime = video.currentTime;
        await nextEvent("timeupdate");
        video.pause();
        const advanced = video.currentTime > firstTime;
        for (const fraction of [0.85, 0.2]) {
          const seconds = video.duration * fraction;
          const sought = nextEvent("seeked");
          video.currentTime = seconds;
          await sought;
          if (Math.abs(video.currentTime-seconds) > 0.4) throw Error("拖动后的视频时间不符");
        }
        return advanced;
      });
      check(result, "视频时间未前进");
      played.push(seq);
    }
    await page.goto(new URL("index.html", base).href);
    return "PASS 已播放并前后拖动 " + played.length + " 段，本地缺包后转文字阅读 " + missing.length + " 段";
  } finally { await ctx.close(); }
}
