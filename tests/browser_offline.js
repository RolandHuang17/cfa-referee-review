// Local-only test server mounts the same site at four scopes and switches worker versions.
async (page) => {
  const base = 'http://127.0.0.1:8876';
  function check(condition, message) {
    if (!condition) throw new Error(message);
  }
  async function controlled(tab, scope) {
    await tab.waitForFunction(url => navigator.serviceWorker.controller?.scriptURL === url, base + scope + "sw.js");
  }
  async function waitForCaches(tab,kept,removed) {
    await tab.evaluate(async ({kept,removed}) => {
      const deadline = Date.now() + 15000;
      do {
        const reg = await navigator.serviceWorker.getRegistration(), names = await caches.keys();
        if (!reg.installing && !reg.waiting && reg.active?.state === "activated" &&
            names.includes(kept) && !names.includes(removed)) return;
        await new Promise(resolve => setTimeout(resolve, 60));
      } while (Date.now() < deadline);
      throw Error("缓存版本未稳定");
    }, {kept,removed});
  }
  const previousName = (scope, version) => "cfa-site-" + encodeURIComponent(scope) + "-" + version;
  const currentName = (scope, version) => "cfa-site:" + encodeURIComponent(scope) + ":" + version;
  // Start with real registrations and populated old-format caches on ordinary sibling paths.
  await page.goto(base + '/icon.svg');
  const previous = await page.evaluate(async () => (await fetch('/__previous', {cache:'no-store'})).text());
  await page.evaluate(async () => {
    const other = await caches.open('cfa-site-%2Fother%2F-v1');
    await other.put('/other/marker', new Response('sibling'));
    const legacy = await caches.open('cfa-site-202610261603');
    await legacy.put('/study/legacy.html', new Response('legacy lesson'));
    await legacy.put('/study/rap.html?q=first', new Response('old lesson'));
    await legacy.put('/study/rap.html?q=second', new Response('updated lesson'));
    await legacy.put('/study/archive.html?lang=en', new Response('English archive'));
    await legacy.put('/study/archive.html?lang=es', new Response('Spanish archive'));
  });
  const root = await page.context().newPage();
  await root.goto(base + '/index.html');
  await controlled(root,'/');
  await page.goto(base + '/study/index.html');
  await controlled(page,'/study/');
  const children = [];
  for (const scope of ['/-club/','/study/-club/']) {
    const tab = await page.context().newPage();
    await tab.goto(base + scope + 'index.html');
    await controlled(tab,scope);
    await tab.goto(base + scope + 'rules.html#law-12');
    check((await tab.title()).includes('竞赛规则'), '子目录首次安装和浏览失败 '+scope);
    children.push({tab,scope});
  }
  for (const term of ['手球','红牌','越位']) {
    await page.goto(base + '/study/search.html?q=' + encodeURIComponent(term));
    check(await page.locator('#q').inputValue() === term, '在线搜索丢失查询参数');
  }
  // Inspect the live cache before upgrade so a migration cannot mask duplicate writes.
  const searchKeys = await page.evaluate(async name => {
    const cache = await caches.open(name);
    return (await cache.keys()).map(r => new URL(r.url)).filter(u => u.pathname === '/study/search.html')
      .map(u => u.search);
  }, previousName('/study/', previous));
  check(searchKeys.length === 1 && searchKeys[0] === '', '不同搜索词重复缓存了静态 HTML');
  await page.goto(base + '/study/season-2026.html#case-229');
  await page.locator('#btnLite').click();
  await page.locator('#noteBox').fill('离线升级测试笔记 [00:05]');
  await page.goto(base + '/study/index.html');
  // Seed the historic shared cache after those installations. Parent migration must
  // not claim a separate app's documents simply because they sit below the parent URL.
  await page.evaluate(async () => {
    const unknown = await caches.open('cfa-site-%2Fstudy%2F-library');
    await unknown.put('/study/library.txt', new Response('independent cache'));
    const shared = await caches.open('cfa-site-202610261603');
    const cover = await fetch('/study/assets/og-card.png');
    if (!cover.ok) throw Error('未找到随包封面');
    await shared.put('/study/assets/og-card.png',cover);
    await shared.put('/study/-club/club-only.html', new Response('club lesson'));
  });
  const quota = await page.context().newCDPSession(page);
  let revision;
  try {
    await quota.send('Storage.overrideQuotaForOrigin', {origin:base,quotaSize:1024});
    revision = await page.evaluate(async () => (await fetch('/__upgrade', {cache:'no-store'})).text());
    await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.getRegistration();
      const failed = new Promise((resolve,reject) => {
        const timer = setTimeout(() => reject(Error("配额不足的升级没有结束")), 15000);
        reg.addEventListener("updatefound", () => {
          const worker = reg.installing;
          function changed() {
            if (worker.state === "redundant" || worker.state === "activated") {
              clearTimeout(timer); resolve(worker.state);
            }
          }
          worker.addEventListener("statechange",changed);
          changed();
        }, {once:true});
      });
      await reg.update().catch(() => {});
      if (await failed !== "redundant") throw Error("测试配额没有中止新安装");
    });
    await waitForCaches(page,previousName('/study/',previous),currentName('/study/',revision));
    await page.context().setOffline(true);
    const stillAvailable = await page.reload();
    check(stillAvailable?.fromServiceWorker() && (await page.title()).includes('裁判'), '安装失败影响了已开的离线首页');
  } finally {
    await page.context().setOffline(false);
    await quota.send('Storage.overrideQuotaForOrigin', {origin:base});
    await quota.detach();
  }
  for (const [tab,scope] of [[root,'/'],[page,'/study/']]) {
    await tab.evaluate(async () => { await (await navigator.serviceWorker.getRegistration()).update(); });
    await waitForCaches(tab,currentName(scope,revision),previousName(scope,previous));
    await controlled(tab,scope);
  }
  const keys = await page.evaluate(() => caches.keys());
  check(keys.includes('cfa-site-%2Fother%2F-v1') && keys.includes('cfa-site-%2Fstudy%2F-library') &&
    keys.includes('cfa-site-202610261603'), '升级误删了其它应用、未知版本或共享缓存');
  for (const {scope} of children)
    check(keys.includes(previousName(scope,previous)), '父目录升级误删子目录缓存 '+scope);
  await page.context().setOffline(true);
  for (const {tab,scope} of children) {
    const response = await tab.reload();
    check(response?.fromServiceWorker() && (await tab.title()).includes('竞赛规则'), '已开子站断网后无法重载 '+scope);
    await controlled(tab,scope);
    await tab.close();
  }
  const rootResponse = await root.reload();
  check(rootResponse?.fromServiceWorker() && (await root.title()).includes('裁判'), '已开的根站点在升级后无法离线使用');
  await root.close();
  await page.goto(base + '/study/season-2026.html#case-229');
  check(await page.locator('#noteBox').inputValue() === '离线升级测试笔记 [00:05]', '升级后笔记丢失');
  check((await page.title()).includes('2026'), '升级后已访问判例无法离线读');
  await page.goto(base + '/study/legacy.html');
  check((await page.locator('body').innerText()).includes('legacy lesson'), '旧版已读内容未迁移');
  await page.goto(base + '/study/rap.html?q=unseen');
  check((await page.locator('body').innerText()).includes('updated lesson'), '旧版仅带参数缓存的静态页未正确迁移');
  await page.goto(base + '/study/archive.html?lang=es');
  check((await page.locator('body').innerText()).includes('Spanish archive'), '非站点生成页的查询变体被错误合并');
  await page.goto(base + '/study/never-visited/nested.html');
  check((await page.locator('body').innerText()).includes('页面不存在'), '未缓存页面缺少离线反馈');
  const home = page.locator('.e-link').first();
  check(await home.evaluate(a => a.href) === base + '/study/index.html', '嵌套错误页的首页链接失去部署前缀');
  await home.click();
  check(page.url() === base + '/study/index.html' && (await page.title()).includes('裁判'), '离线首页不可用');
  await page.goto(base + '/study/never-visited/nested.html');
  await page.locator('#q404').fill('越位');
  await Promise.all([
    page.waitForURL(url => url.pathname === '/study/search.html' && url.searchParams.get('q') === '越位',
      {waitUntil:'domcontentloaded'}),
    page.locator('#go404').click(),
  ]);
  check(await page.locator('#q').inputValue() === '越位', '已缓存的搜索页未能离线打开新关键词');
  check(await page.locator('#sres a').count() > 0, '离线搜索未渲染结果');
  const cached = await page.evaluate(async name => {
    return (await (await caches.open(name)).keys()).map(r => r.url);
  }, currentName('/study/',revision));
  check(cached.includes(base + '/study/assets/og-card.png'), '同一站点共享缓存中的随包资产丢失');
  check(!cached.some(url => url.includes('/-club/')), '共享缓存混入子站独有的课程');
  check(!cached.some(url => url.includes('/videos/')), '视频被缓存');
  check(cached.every(url => new URL(url).origin === base), '缓存混入外域资源');
  for (const html of ['search.html','rap.html']) {
    const copies = cached.map(key => new URL(key)).filter(u => u.pathname === '/study/' + html);
    check(copies.length === 1 && copies[0].search === '', '升级后 ' + html + ' 缓存键未合并');
  }
  await page.context().setOffline(false);

  // Chromium's storage quota affects real Cache.put calls for both fetch strategies.
  const devtools = await page.context().newCDPSession(page);
  try {
    await devtools.send('Storage.overrideQuotaForOrigin', {origin:base,quotaSize:1024});
    const result = await page.goto(base + '/study/cheatsheet.html');
    check(result?.ok() && result.fromServiceWorker() && (await page.title()).includes('考点速查卡'),
      '配额不足时联网导航错误地回退到 404');
    const resource = await page.evaluate(async () => {
      const response = await fetch('icon.svg?quota-check=1');
      return {ok:response.ok, svg:(await response.text()).includes('<svg')};
    });
    check(resource.ok && resource.svg, '配额不足时联网静态资源变成 503');
    const failedWrites = await page.evaluate(async name => {
      const cache = await caches.open(name);
      return !(await cache.match('cheatsheet.html')) && !(await cache.match('icon.svg?quota-check=1'));
    }, currentName('/study/',revision));
    check(failedWrites, '配额测试没有触发真实缓存写入失败');
  } finally {
    await devtools.send('Storage.overrideQuotaForOrigin', {origin:base});
    await devtools.detach();
  }
  return 'PASS 根和子目录真实安装/已打开父子站升级后离线/查询迁移与笔记/404/真实配额下的联网访问';
}
