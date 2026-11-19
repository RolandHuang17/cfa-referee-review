# -*- coding: utf-8 -*-
"""生成 PWA 离线层：manifest.webmanifest + icon.svg + sw.js（在线版专用）。

设计约束：
- file:// 双击打开的离线用法完全不受影响——SW 注册在 theme.py 注入的片段里，
  且本身有 http(s) 协议判断，file:// 下静默跳过；
- sw.js 缓存策略：页面导航 network-first（发布后用户第一时间拿到新版，断网回退
  缓存）、静态资源 stale-while-revalidate、videos/ 与外域一律不碰（30GB 视频绝不进缓存）；
- 缓存名带部署路径与内容摘要，激活时只清理本部署旧版本缓存。
"""

import hashlib

from lib.paths import SITE

MANIFEST = """{
  "name": "裁判学习一站式平台",
  "short_name": "裁判学习",
  "description": "中国足协裁判评议 2024–2026 三赛季判例合集：视频复盘、教学分类、各队得失盘点、统一判罚尺度与竞赛规则。",
  "lang": "zh-CN",
  "start_url": "index.html",
  "scope": ".",
  "display": "standalone",
  "background_color": "#f7f2e7",
  "theme_color": "#b3573a",
  "icons": [
    {"src": "icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}
  ]
}
"""

# 与 favicon 同源的盾牌图标（放大画布，供安装横幅/启动屏使用）
ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">
<rect width="96" height="96" rx="20" fill="#f7f2e7"/>
<path fill="#b3573a" stroke="#8a3f27" stroke-width="3" d="M48 10l30 13v22c0 18-12 31-30 37-18-6-30-19-30-37V23z"/>
<path fill="none" stroke="#f7f2e7" stroke-width="6" stroke-linecap="round" d="M38 46l7 7 14-14"/>
</svg>
"""

SW_TEMPLATE = r""""use strict";
const VERSION = "__BUILD_TS__";
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
      // Static HTML reads its filters and search terms in the browser.
      const saved = await cache.match(req, {ignoreSearch: url.pathname.endsWith(".html")});
      return saved || (await cache.match("404.html")) ||
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
"""


def main():
    digest = hashlib.sha256()
    for page in sorted(SITE.glob("*.html")):
        digest.update(page.name.encode("utf-8"))
        digest.update(page.read_bytes())
    ts = digest.hexdigest()[:16]
    (SITE / "manifest.webmanifest").write_text(MANIFEST, encoding="utf-8")
    (SITE / "icon.svg").write_text(ICON_SVG, encoding="utf-8")
    (SITE / "sw.js").write_text(
        SW_TEMPLATE.replace("__BUILD_TS__", ts), encoding="utf-8"
    )
    print(f"PWA 离线层构建完成: manifest + icon.svg + sw.js（缓存版本 {ts}）")


if __name__ == "__main__":
    main()
