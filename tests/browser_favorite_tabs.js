// Real independent tabs. Holding the second tab's storage notification also tests a background tab's stale button.
async startPage => {
  const url = new URL("season-2026.html#case-229",startPage.url()).href;
  const ctx = await startPage.context().browser().newContext({serviceWorkers:"block",viewport:{width:1440,height:900}});
  ctx.setDefaultTimeout(10000);
  function check(value, message) { if (!value) throw Error(message); }
  async function saved(page) {
    return page.evaluate(async () => {
      let blob;
      const create = URL.createObjectURL;
      URL.createObjectURL = value => { blob=value; return create.call(URL,value); };
      try {
        document.getElementById("btnExport").click();
        return JSON.parse(await blob.text()).fav["229"] || null;
      } finally { URL.createObjectURL = create; }
    });
  }
  try {
    const first = await ctx.newPage(), second = await ctx.newPage();
    await second.addInitScript(() => {
      window.holdFavorites = true;
      window.addEventListener("storage", e => {
        if (holdFavorites && e.key?.startsWith("cfa2026.fav")) e.stopImmediatePropagation();
      },true);
    });
    await first.goto(url); await second.goto(url);
    await first.locator("#favBtn").click();
    await first.locator("#customTag").fill("课堂一组"); await first.locator("#addTag").click();
    check(await second.locator("#favBtn").getAttribute("aria-pressed") === "false", "第二页未保留旧的按钮状态");
    await second.locator("#favBtn").click();
    check((await saved(second))?.tags.includes("课堂一组"),"陈旧的收藏操作删除了另一页的标签");
    const chip = p => p.locator('#favTags [data-tag="精选"]');
    await chip(first).click();
    check(await chip(second).getAttribute("aria-pressed") === "false", "未能覆盖旧标签状态");
    await chip(second).click();
    check((await saved(second)).tags.sort().join("/") === ["精选","课堂一组"].sort().join("/"),"陈旧的选择标签操作反而移除了标签");

    await second.evaluate(()=>{window.holdFavorites=false;});
    const draft = second.locator("#customTag");
    await draft.fill("下一节课"); await draft.focus();
    await first.locator("#customTag").fill("课堂二组"); await first.locator("#addTag").click();
    await second.locator('#favTags [data-tag="课堂二组"]').waitFor();
    check(await draft.inputValue() === "下一节课" && await draft.evaluate(n=>n === document.activeElement),
      "其它页的标签更新覆盖了输入中的标签或抢走焦点");
    await draft.press("Enter");
    await first.locator('#favTags [data-tag="下一节课"]').waitFor();

    await second.evaluate(()=>{window.holdFavorites=true;});
    await first.locator("#favBtn").click();
    check(await second.locator("#favBtn").getAttribute("aria-pressed") === "true", "没有得到待取消的陈旧收藏按钮");
    await second.locator("#favBtn").click();
    check(await saved(second) === null && await saved(first) === null, "陈旧的取消操作重新创建了已删除的收藏");
    await second.evaluate(()=>{window.holdFavorites=false;});
    await first.locator("#favBtn").click();
    await second.waitForFunction(()=>document.getElementById("favBtn")?.getAttribute("aria-pressed") === "true");
    await second.locator('#favTags [data-tag="精选"]').focus();
    await second.keyboard.press("Space");
    check((await saved(second)).tags.includes("精选"), "键盘无法添加预设标签");
  } finally { await ctx.close(); }
  return "PASS 双页收藏与标签同步、旧按钮幂等添加和取消、输入与键盘焦点保留";
}
