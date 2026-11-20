"use strict";
const VERSION = "0cbbb5cbf4108b32";
const SCOPE = new URL(self.registration.scope).pathname;
const encodedScope = encodeURIComponent(SCOPE);
const PREFIX = "cfa-site:" + encodedScope + ":";
const OLD_PREFIX = "cfa-site-" + encodedScope + "-";
const CACHE = PREFIX + VERSION;
const STATIC_PAGES = new Set(["index.html", "season-2026.html", "season-2025.html", "season-2024.html", "stats-2026.html", "stats-2025.html", "stats-2024.html", "rules.html", "scale.html", "uefa.html", "rap.html", "rfef.html", "pro.html", "intl.html", "conmebol.html", "weekly.html", "ifab.html", "hns.html", "quiz.html", "compare.html", "cheatsheet.html", "search.html", "404.html"]);
const BUNDLED_ASSETS = new Set(["assets/compare/handball-1-small.webp", "assets/compare/handball-1.webp", "assets/compare/handball-28-small.webp", "assets/compare/handball-28.webp", "assets/compare/referee-large.webp", "assets/compare/referee-mobile.webp", "assets/crests/beijing-guoan.png", "assets/crests/beijing-ligong.png", "assets/crests/changchun-yatai.png", "assets/crests/chengdu-rongcheng.png", "assets/crests/dalian-yingbo.png", "assets/crests/guangxi-hengchen.png", "assets/crests/guangxi-pingguo.png", "assets/crests/hangzhou-linpingwuyue.png", "assets/crests/henan.png", "assets/crests/hubei-qingnianxing.png", "assets/crests/jiangxi-lushan.png", "assets/crests/meizhou-kejia.png", "assets/crests/nantong-zhiyun.png", "assets/crests/qingdao-hainiu.png", "assets/crests/qingdao-xihaian.png", "assets/crests/shaanxi-lianhe.png", "assets/crests/shandong-taishan.png", "assets/crests/shanghai-haigang.png", "assets/crests/shenhua.png", "assets/crests/shenzhen-2028.png", "assets/crests/shenzhen-qingnianren.png", "assets/crests/shenzhen-xinpengcheng.png", "assets/crests/suzhou-dongwu.png", "assets/crests/team-002.png", "assets/crests/team-004.png", "assets/crests/team-007.png", "assets/crests/team-008.png", "assets/crests/team-011.png", "assets/crests/team-012.png", "assets/crests/team-014.png", "assets/crests/team-018.png", "assets/crests/team-020.png", "assets/crests/team-021.png", "assets/crests/team-023.png", "assets/crests/team-024.png", "assets/crests/team-030.png", "assets/crests/team-042.png", "assets/crests/team-043.png", "assets/crests/team-044.png", "assets/crests/team-045.png", "assets/crests/team-049.png", "assets/crests/team-050.png", "assets/crests/team-051.png", "assets/crests/team-056.png", "assets/crests/team-058.png", "assets/crests/team-075.png", "assets/crests/team-080.png", "assets/crests/team-084.png", "assets/crests/team-087.png", "assets/crests/team-088.png", "assets/crests/team-094.png", "assets/crests/team-095.png", "assets/crests/team-098.png", "assets/crests/team-100.png", "assets/crests/team-102.png", "assets/crests/team-111.png", "assets/crests/tianjin-jinmenhu.png", "assets/crests/wuhan-sanzhen.png", "assets/crests/yunnan-yukun.png", "assets/crests/zhejiang-greentown.png", "assets/og-card.png", "assets/portal/case-study.webp", "assets/portal/moments/lib.js", "assets/portal/moments/liquid-hover/moment.css", "assets/portal/moments/liquid-hover/moment.js", "assets/portal/moments/moments.js", "assets/portal/referee-match-small.webp", "assets/portal/referee-match.webp", "assets/rules/p104.png", "assets/rules/p115.png", "assets/rules/p142.png", "assets/rules/p146.png", "assets/rules/p201.png", "assets/rules/p207.png", "assets/rules/p211.png", "assets/rules/p214.png", "assets/rules/p215.png", "assets/rules/p29.png", "assets/rules/p46.png", "assets/rules/p48.png", "assets/rules/p51.png", "assets/rules/p78.png", "assets/rules/p79.png", "assets/rules/p80.png", "assets/rules/p81.png", "assets/rules/p88.png", "assets/rules/p89.png", "assets/rules/p90.png", "assets/rules/p91.png", "assets/scale/2025-fouls-misconduct-highlights-1.png", "assets/scale/2025-fouls-misconduct-highlights-2.png", "assets/scale/2025-fouls-misconduct-highlights-3.png", "assets/scale/2025-fouls-misconduct-highlights-4.png", "assets/scale/2025-fouls-misconduct-highlights-5.png", "assets/scale/2025-fouls-misconduct-highlights-7.png", "assets/scale/2025-fouls-misconduct-highlights-8.png", "assets/scale/2025-fouls-misconduct-highlights-9.png", "assets/scale/2025-fouls-misconduct-reckless-1.png", "assets/scale/2025-fouls-misconduct-reckless-10.png", "assets/scale/2025-fouls-misconduct-reckless-11.png", "assets/scale/2025-fouls-misconduct-reckless-12.png", "assets/scale/2025-fouls-misconduct-reckless-13.png", "assets/scale/2025-fouls-misconduct-reckless-14.png", "assets/scale/2025-fouls-misconduct-reckless-15.png", "assets/scale/2025-fouls-misconduct-reckless-16.png", "assets/scale/2025-fouls-misconduct-reckless-17.png", "assets/scale/2025-fouls-misconduct-reckless-18.png", "assets/scale/2025-fouls-misconduct-reckless-19.png", "assets/scale/2025-fouls-misconduct-reckless-2.png", "assets/scale/2025-fouls-misconduct-reckless-21.png", "assets/scale/2025-fouls-misconduct-reckless-22.png", "assets/scale/2025-fouls-misconduct-reckless-3.png", "assets/scale/2025-fouls-misconduct-reckless-4.png", "assets/scale/2025-fouls-misconduct-reckless-5.png", "assets/scale/2025-fouls-misconduct-reckless-6.png", "assets/scale/2025-fouls-misconduct-reckless-7.png", "assets/scale/2025-fouls-misconduct-reckless-8.png", "assets/scale/2025-fouls-misconduct-reckless-9.png", "assets/scale/2025-fouls-misconduct-var-1.png", "assets/scale/2025-fouls-misconduct-var-2.png", "assets/scale/2026-fouls-misconduct-highlights-A1.png", "assets/scale/2026-fouls-misconduct-highlights-A2.png", "assets/scale/2026-fouls-misconduct-highlights-A3.png", "assets/scale/2026-fouls-misconduct-highlights-A4.png", "assets/scale/2026-fouls-misconduct-highlights-A5.png", "assets/scale/2026-fouls-misconduct-highlights-A6.png", "assets/scale/2026-fouls-misconduct-highlights-A7.png", "assets/scale/2026-fouls-misconduct-highlights-B1.png", "assets/scale/2026-fouls-misconduct-highlights-B2.png", "assets/scale/2026-fouls-misconduct-highlights-B3.png", "assets/scale/2026-fouls-misconduct-highlights-C1.png", "assets/scale/2026-fouls-misconduct-highlights-C2.png", "assets/scale/2026-fouls-misconduct-highlights-C3.png", "assets/scale/2026-fouls-misconduct-highlights-C4.png", "assets/scale/2026-fouls-misconduct-highlights-D1.png", "assets/scale/2026-fouls-misconduct-highlights-D2.png", "assets/scale/2026-fouls-misconduct-highlights-D3.png", "assets/scale/2026-fouls-misconduct-highlights-E1.png", "assets/scale/2026-fouls-misconduct-highlights-E2.png", "assets/scale/2026-fouls-misconduct-highlights-F1.png", "assets/scale/2026-fouls-misconduct-highlights-F2.png", "assets/scale/2026-fouls-misconduct-highlights-F3.png", "assets/scale/2026-fouls-misconduct-highlights-G1.png", "assets/scale/2026-fouls-misconduct-highlights-G2.png", "assets/scale/2026-fouls-misconduct-highlights-H1.png", "assets/scale/2026-fouls-misconduct-highlights-H2.png", "assets/scale/2026-fouls-misconduct-highlights-H3.png"]);
// Released scoped builds end in exactly 16 lowercase hex digits. "-" can also
// start a child's directory name, so a prefix match alone does not establish ownership.
function cacheScope(key){
  const match = /^cfa-site:([^:]+):[0-9a-f]{16}$/.exec(key) ||
    /^cfa-site-(.+)-[0-9a-f]{16}$/.exec(key);
  return match && match[1];
}
function sharedCache(key){ return /^cfa-site-\d{12}$/.test(key); }
const owned = (url) => {
  const parsed = new URL(url);
  return parsed.origin === location.origin && parsed.pathname.startsWith(SCOPE)
    && !parsed.pathname.includes("/videos/");
};
// Only generated HTML interprets its query entirely in the browser.
function cacheKey(req){
  const url = new URL(req.url);
  if (!url.search || !STATIC_PAGES.has(url.pathname.slice(SCOPE.length))) return req;
  url.search = "";
  return new Request(url.href, {headers:req.headers});
}
async function populate(cache, keys){
  // Process old shared caches first, so the scoped version wins if both have a page.
  const mine = keys.filter(k => k !== CACHE && cacheScope(k) === encodedScope);
  const previous = keys.filter(sharedCache).concat(mine.filter(k => k.startsWith(OLD_PREFIX)),
    mine.filter(k => k.startsWith(PREFIX)));
  const children = [...new Set(keys.map(cacheScope).filter(path => path && path !== encodedScope &&
    path.startsWith(encodedScope) && path.endsWith("%2F")))];
  for (const key of previous){
    const old = await caches.open(key);
    for (const req of await old.keys()){
      if (!owned(req.url)) continue;
      // Timestamped caches were shared by every deployment on the origin. A nested
      // path might belong to a separate app. Keep only this site's known nested assets.
      const pathname = new URL(req.url).pathname;
      const encodedPath = encodeURIComponent(pathname);
      if (children.some(child => encodedPath.startsWith(child))) continue;
      const path = pathname.slice(SCOPE.length);
      if (sharedCache(key) && path.includes("/") && !BUNDLED_ASSETS.has(path)) continue;
      const response = await old.match(req);
      if (response && response.ok) await cache.put(cacheKey(req), response);
    }
  }
  await cache.addAll(["index.html", "404.html", "icon.svg"]);
}
self.addEventListener("install", e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    try {
      await populate(await caches.open(CACHE), keys);
    } catch (error) {
      // An incomplete install must leave room for a retry. Keep any pre-existing cache.
      if (!keys.includes(CACHE)) await caches.delete(CACHE).catch(() => {});
      throw error;
    }
    await self.skipWaiting();
  })());
});
self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    for (const key of await caches.keys()){
      if (key !== CACHE && cacheScope(key) === encodedScope) await caches.delete(key);
    }
    await self.clients.claim();
  })());
});
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || !owned(req.url)) return;
  const url = new URL(req.url);
  if (url.pathname.endsWith("feed.xml") || url.pathname.endsWith("sitemap.xml")) return;
  const key = cacheKey(req);
  const store = caches.open(CACHE).catch(() => null);
  async function readCache(key){
    const cache = await store;
    return cache ? cache.match(key).catch(() => undefined) : undefined;
  }
  async function network(){
    const response = await fetch(req);
    const cache = await store;
    if (response.ok && cache){
      // A full or unavailable cache must never discard a usable network response.
      await cache.put(key, response.clone()).catch(() => {});
    }
    return response;
  }
  if (req.mode === "navigate"){
    e.respondWith((async () => {
      try {
        const response = await network();
        if (response.ok || response.status < 500) return response;
      } catch (_) {}
      return (await readCache(key)) || (await readCache("404.html")) ||
        new Response("当前页面尚未离线保存，请联网后重试。", {status:503, headers:{"Content-Type":"text/plain;charset=utf-8"}});
    })());
  } else {
    const update = network().catch(() => undefined);
    e.waitUntil(update);
    e.respondWith((async () => {
      return (await readCache(key)) || (await update) || new Response("", {status:503});
    })());
  }
});
