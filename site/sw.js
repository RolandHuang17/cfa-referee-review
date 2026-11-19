"use strict";
const VERSION = "d5e91bac94eae656";
const SCOPE = new URL(self.registration.scope).pathname;
const PREFIX = "cfa-site-" + encodeURIComponent(SCOPE) + "-";
const CACHE = PREFIX + VERSION;
const owned = (url) => {
  const parsed = new URL(url);
  return parsed.origin === location.origin && parsed.pathname.startsWith(SCOPE)
    && !parsed.pathname.includes("/videos/");
};
self.addEventListener("install", e => {
  e.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    const keys = await caches.keys();
    for (const key of keys.filter(k => k !== CACHE && (k.startsWith(PREFIX) || /^cfa-site-\d+$/.test(k)))){
      const old = await caches.open(key);
      for (const req of await old.keys()){
        if (owned(req.url)){
          const response = await old.match(req);
          if (response && response.ok) await cache.put(req, response);
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
  async function network(cache){
    const response = await fetch(req);
    if (response.ok) await cache.put(req, response.clone());
    return response;
  }
  if (req.mode === "navigate"){
    e.respondWith((async () => {
      const cache = await caches.open(CACHE);
      try {
        const response = await network(cache);
        if (response.ok || response.status < 500) return response;
      } catch (_) {}
      return (await cache.match(req)) || (await cache.match("404.html")) ||
        new Response("当前页面尚未离线保存，请联网后重试。", {status:503, headers:{"Content-Type":"text/plain;charset=utf-8"}});
    })());
  } else {
    const update = caches.open(CACHE).then(cache => network(cache)).catch(() => undefined);
    e.waitUntil(update);
    e.respondWith((async () => {
      const cache = await caches.open(CACHE);
      return (await cache.match(req)) || (await update) ||
        new Response("", {status:503});
    })());
  }
});
