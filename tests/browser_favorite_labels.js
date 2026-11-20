async (startPage) => {
  const context = await startPage.context().browser().newContext({viewport:{width:1440,height:900}});
  const page = await context.newPage();
  function check(ok,msg) { if (!ok) throw Error(msg); }
  try {
    await page.goto(new URL("season-2026.html", startPage.url()).href);
    const labels = ['赛前 <U19> · A & B 的“争抢” "1"', 'constructor'];
    const backup = {app:"cfa-referee-review-2026", fav:{"1":{tags:labels,ts:1}}, notes:{}};
    page.once("dialog", dialog => dialog.accept());
    await page.locator("#importFile").setInputFiles({name:"课堂收藏.json", mimeType:"application/json", buffer:Buffer.from(JSON.stringify(backup))});
    for (const label of labels) {
      const tag = page.locator("#favList button").filter({hasText:label});
      await tag.waitFor();
      check(await tag.locator(".nm").textContent() === label, "标签显示文字发生变化");
      check(await tag.locator(".nm *").count() === 0 && await tag.getAttribute("data-fav") === "tag:"+label,
        "备份标签未作为普通文字保存");
      check(await tag.locator("b").innerText() === "1","同名内置属性影响收藏数");
      await tag.click();
      const results = page.locator(".prow");
      check(await results.count() === 1 && await results.getAttribute("data-seq") === "1", "导入的标签无法筛选原判例");
    }
    await page.reload();
    check(await page.locator("#favList .nm").filter({hasText:labels[0]}).textContent() === labels[0],"刷新后标签失真");
    return "PASS 收藏标签中的引号、尖括号和同名属性按原文显示、计数、筛选与保存";
  } finally { await context.close(); }
}
