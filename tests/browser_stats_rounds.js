// Run with the repository's Playwright CLI against the generated site.
async (startPage) => {
  const base = new URL("./", startPage.url());
  const page = await startPage.context().newPage();
  function check(ok, message) {
    if (!ok) throw Error(message);
  }
  async function matchRows(team, home, away) {
    const card = page.locator('.teamcard[data-name="' + team + '"]');
    if (!(await card.locator(".detail").isVisible())) await card.locator(".thead").click();
    return card.locator(".drow").filter({hasText:home}).filter({hasText:away});
  }
  try {
    await page.goto(new URL("stats-2025.html", base).href);
    for (const view of ["#btnVictim", "#btnBenefit"]) {
      await page.locator(view).click();
      for (const [team, result] of [["南京城市", "本队仍胜"], ["南通支云", "本队仍负"]]) {
        const rows = await matchRows(team, "南通支云", "南京城市");
        check(await rows.count() > 0, "缺少该视角的错漏判事项：" + team);
        for (const row of await rows.all()) {
          check(await row.locator(".corr").innerText() === "整场修正比分 0:2", "两队的整场修正比分不一致");
          check((await row.innerText()).includes(result), "赛果与当前球队不对应：" + team);
        }
      }
    }
    await page.goto(new URL("stats-2024.html", base).href);
    const cup = (await matchRows("成都蓉城", "山东泰山", "成都蓉城")).filter({hasText:"足协杯"});
    check(await cup.count() === 1, "足协杯半决赛的场次不唯一");
    check(await cup.locator(".badge").first().innerText() === "足协杯 · 半决赛", "第 24 期杯赛阶段错误");
    check((await cup.locator(".mt").innerText()).includes("1 : 0"), "足协杯比分关联失效");
    check(await cup.locator("a").getAttribute("href") === "season-2024.html#case-145", "足协杯深链失效");
    return "PASS stats rounds, scores and team perspectives";
  } finally {
    await page.close();
  }
}
