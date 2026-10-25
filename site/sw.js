"use strict";
// 裁判学习平台 Service Worker：在线版断网可读（file:// 离线用法不经此处）
const VERSION = "202610260214";
const CACHE = "cfa-site-" + VERSION;

self.addEventListener("install", (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(["icon.svg"])).catch(() => {}));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;      // 外域（官方视频/YouTube 等）不碰
  if (url.pathname.includes("/videos/")) return;   // 本地视频目录不进缓存（约 30GB）
  if (url.pathname.endsWith("feed.xml") || url.pathname.endsWith("sitemap.xml")) return;

  if (req.mode === "navigate") {
    // 页面：网络优先（保证发布后更新即时可见），断网回退缓存，再兜底到已存首页
    e.respondWith(
      fetch(req).then((resp) => {
        const copy = resp.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return resp;
      }).catch(() =>
        caches.match(req).then((hit) => hit || caches.match("index.html"))
      )
    );
    return;
  }
  // 静态资源：缓存优先 + 后台更新（队徽等小资源重复访问零请求）
  e.respondWith(
    caches.match(req).then((hit) => {
      const net = fetch(req).then((resp) => {
        if (resp.ok) {
          const copy = resp.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return resp;
      }).catch(() => hit);
      return hit || net;
    })
  );
});
