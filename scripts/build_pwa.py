# -*- coding: utf-8 -*-
"""生成 PWA 离线层：manifest.webmanifest + icon.svg + sw.js（在线版专用）。

设计约束：
- file:// 双击打开的离线用法完全不受影响——SW 注册在 theme.py 注入的片段里，
  且本身有 http(s) 协议判断，file:// 下静默跳过；
- sw.js 缓存策略：页面导航 network-first（发布后用户第一时间拿到新版，断网回退
  缓存）、静态资源 stale-while-revalidate、videos/ 与外域一律不碰（30GB 视频绝不进缓存）；
- 缓存名带构建时间戳，激活时清理旧版本缓存。
"""

from datetime import datetime

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

SW_TEMPLATE = """"use strict";
// 裁判学习平台 Service Worker：在线版断网可读（file:// 离线用法不经此处）
const VERSION = "__BUILD_TS__";
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
"""


def main():
    ts = datetime.now().strftime("%Y%m%d%H%M")
    (SITE / "manifest.webmanifest").write_text(MANIFEST, encoding="utf-8")
    (SITE / "icon.svg").write_text(ICON_SVG, encoding="utf-8")
    (SITE / "sw.js").write_text(
        SW_TEMPLATE.replace("__BUILD_TS__", ts), encoding="utf-8"
    )
    print(f"PWA 离线层构建完成: manifest + icon.svg + sw.js（缓存版本 {ts}）")


if __name__ == "__main__":
    main()
