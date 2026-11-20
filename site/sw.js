"use strict";
const VERSION = "02669f1b90099645";
const SCOPE = new URL(self.registration.scope).pathname;
const PREFIX = "cfa-site-" + encodeURIComponent(SCOPE) + "-";
const CACHE = PREFIX + VERSION;
const STATIC_PAGES = new Set(["index.html", "season-2026.html", "season-2025.html", "season-2024.html", "stats-2026.html", "stats-2025.html", "stats-2024.html", "rules.html", "scale.html", "uefa.html", "rap.html", "rfef.html", "pro.html", "intl.html", "conmebol.html", "weekly.html", "ifab.html", "hns.html", "quiz.html", "compare.html", "cheatsheet.html", "search.html", "404.html"]);
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
self.addEventListener("install", e => {
  e.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    const keys = await caches.keys();
    // Process old shared caches first, so the scoped version wins if both have a page.
    const previous = keys.filter(k => /^cfa-site-\d+$/.test(k))
      .concat(keys.filter(k => k !== CACHE && k.startsWith(PREFIX)));
    for (const key of previous){
      const old = await caches.open(key);
      for (const req of await old.keys()){
        if (owned(req.url)){
          const response = await old.match(req);
          if (response && response.ok) await cache.put(cacheKey(req), response);
        }
      }
    }
    await cache.addAll(["index.html", "404.html", "icon.svg"]);
    await self.skipWaiting();
  })());
});
self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    for (const key of await caches.keys()){
      if (key.startsWith(PREFIX) && key !== CACHE) await caches.delete(key);
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
