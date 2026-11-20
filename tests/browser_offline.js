// 本地验收服务器在 /study/ 提供站点，/__upgrade 更换 SW 版本。
async (page) => {
  const base = 'http://127.0.0.1:8876';
  function check(condition, message) {
    if (!condition) throw new Error(message);
  }
  await page.goto(base + '/index.html');
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
  await page.goto(base + '/study/index.html');
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) {
      await new Promise(resolve => navigator.serviceWorker.addEventListener('controllerchange', resolve, {once:true}));
    }
  });
  for (const term of ['手球','红牌','越位']) {
    await page.goto(base + '/study/search.html?q=' + encodeURIComponent(term));
    check(await page.locator('#q').inputValue() === term, '在线搜索丢失查询参数');
  }
  // Inspect the live cache before upgrade so a migration cannot mask duplicate writes.
  const searchKeys = await page.evaluate(async () => {
    const name = (await caches.keys()).find(k => k.startsWith('cfa-site-%2Fstudy%2F-'));
    const cache = await caches.open(name);
    return (await cache.keys()).map(r => new URL(r.url)).filter(u => u.pathname === '/study/search.html')
      .map(u => u.search);
  });
  check(searchKeys.length === 1 && searchKeys[0] === '', '不同搜索词重复缓存了静态 HTML');
  await page.goto(base + '/study/season-2026.html#case-229');
  await page.locator('#btnLite').click();
  await page.locator('#noteBox').fill('离线升级测试笔记 [00:05]');
  await page.goto(base + '/study/index.html');
  const revision = await page.evaluate(async () => {
    const version = await (await fetch('/__upgrade')).text();
    await (await navigator.serviceWorker.getRegistration()).update();
    return version;
  });
  await page.waitForFunction(async v => {
    const scoped = (await caches.keys()).filter(k => k.startsWith('cfa-site-%2Fstudy%2F-'));
    return scoped.length === 1 && scoped[0].endsWith('offline-test-' + v);
  }, revision);
  const keys = await page.evaluate(() => caches.keys());
  check(keys.includes('cfa-site-%2Fother%2F-v1'), '升级误删了同域另一个项目的缓存');
  await page.context().setOffline(true);
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
  await page.locator('#go404').click();
  check(new URL(page.url()).pathname === '/study/search.html', '嵌套错误页的搜索地址错误');
  check(await page.locator('#q').count() === 1 && await page.locator('#q').inputValue() === '越位',
    '已缓存的搜索页未能离线打开新关键词');
  check(await page.locator('#sres a').count() > 0, '离线搜索未渲染结果');
  const cached = await page.evaluate(async v => {
    const name = (await caches.keys()).find(k => k.endsWith('offline-test-' + v));
    return (await (await caches.open(name)).keys()).map(r => r.url);
  }, revision);
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
    const failedWrites = await page.evaluate(async v => {
      const name = (await caches.keys()).find(k => k.endsWith('offline-test-' + v));
      const cache = await caches.open(name);
      return !(await cache.match('cheatsheet.html')) && !(await cache.match('icon.svg?quota-check=1'));
    }, revision);
    check(failedWrites, '配额测试没有触发真实缓存写入失败');
  } finally {
    await devtools.send('Storage.overrideQuotaForOrigin', {origin:base});
    await devtools.detach();
  }
  return 'PASS 离线升级/查询缓存合并与迁移/笔记/404与同域隔离/配额不足时联网导航与静态资源';
}
