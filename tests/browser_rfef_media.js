// Run on the built site. The media error represents an unavailable offline copy.
async (startPage) => {
  const context = await startPage.context().browser().newContext();
  try {
    const page = await context.newPage();
    await page.goto(new URL("rfef.html",startPage.url()).href);
    const figure = page.locator("figure.vitem").filter({has:page.locator("figcaption")}).first();
    const video = figure.locator("video");
    const official = await video.getAttribute("data-rfef-url");
    const caption = await figure.locator("figcaption").allTextContents();
    if (!caption.length || !official.startsWith("https://www.card.rfef.es/wp-content/uploads/") ||
      !(await video.getAttribute("src")).startsWith("videos/rfef/"))
      throw Error("离线视频或官方媒体链接失配");
    await video.evaluate(el=>el.dispatchEvent(new Event("error")));
    const link = figure.getByRole("link",{name:"在线观看（官方直链）"});
    if (await link.getAttribute("href")!==official ||
      JSON.stringify(caption)!==JSON.stringify(await figure.locator("figcaption").allTextContents()))
      throw Error("视频失效后官方跳转或说明丢失");
    return "PASS RFEF offline video fallback and caption";
  } finally {await context.close();}
}
