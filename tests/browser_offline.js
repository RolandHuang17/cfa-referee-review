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
  });
  await page.goto(base + '/study/index.html');
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) {
      await new Promise(resolve => navigator.serviceWorker.addEventListener('controllerchange', resolve, {once:true}));
    }
  });
  await page.goto(base + '/study/search.html');
  await page.locator('#q').waitFor();
  await page.goto(base + '/study/season-2026.html#case-229');
  await page.locator('#btnLite').click();
  await page.locator('#noteBox').fill('离线升级测试笔记 [00:05]');
  await page.goto(base + '/study/index.html');
  const revision = await page.evaluate(async () => {
    const version = await (await fetch('/__upgrade')).text();
    await (await navigator.serviceWorker.getRegistration()).update();
    return version;
  });
  await page.waitForFunction(async v => (await caches.keys()).some(k => k.endsWith('offline-test-' + v)), revision);
  const keys = await page.evaluate(() => caches.keys());
  check(keys.includes('cfa-site-%2Fother%2F-v1'), '升级误删了同域另一个项目的缓存');
  await page.context().setOffline(true);
  await page.goto(base + '/study/season-2026.html#case-229');
  check(await page.locator('#noteBox').inputValue() === '离线升级测试笔记 [00:05]', '升级后笔记丢失');
  check((await page.title()).includes('2026'), '升级后已访问判例无法离线读');
  await page.goto(base + '/study/legacy.html');
  check((await page.locator('body').innerText()).includes('legacy lesson'), '旧版已读内容未迁移');
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
  await page.context().setOffline(false);
  return 'PASS 升级后离线首页/已读判例/旧缓存迁移/笔记/未访问页面反馈/同域其他项目缓存';
}
