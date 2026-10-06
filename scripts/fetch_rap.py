# -*- coding: utf-8 -*-
"""核对 UEFA RAP（Refereeing Assistance Programme）各期索引 → 辅助维护 data/rap.json

RAP 的实际判例内容在 Nextaur 登录墙后（免费注册）或已失效的下载包里，**不可抓取**；
本脚本只抓 dutchreferee.com 的公开索引页，提取各期链接与说明文本，用于：
1. 首次策展 data/rap.json（人工核对后录入）；
2. UEFA 每年发布新一期 RAP 后，重跑本脚本发现新增期数（merge 子命令把新期并入
   rap.json，已有人工标注的期保持不动）。

用法: python fetch_rap.py [fetch|merge]
- fetch: 抓取索引页缓存 data/local/dutchref-cache/ 并打印期数清单（默认）
- merge: fetch 后把发现的、rap.json 中尚不存在的期数以 status="unreviewed" 并入
"""
import html as htmllib
import json
import re
import sys
import time

from lib.safe_http import fetch_text

from lib.paths import DUTCHREF_CACHE, RAP_JSON

INDEX = "https://www.dutchreferee.com/refereeing-assistance-programme/"
MIN_BODY = 20000
BACKOFFS = [30, 90]

LINK_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)</a>', re.I)
# 期数模式：RAP 2026-1 / RAP 2025:2 / RAP Euro 2024 / RAP Women's Euro 2017 …
EDITION_RE = re.compile(r"(?i)RAP\s+((?:women'?s\s+)?(?:euro\s+)?20\d\d(?:\s*[:\-–]\s*\d)?)")
URL_HOSTS = re.compile(r"(?i)bit\.ly|nextaur\.com|wetransfer|dutchreferee\.com")


def clean(text: str) -> str:
    return htmllib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))).strip()


def fetch_page() -> str:
    DUTCHREF_CACHE.mkdir(parents=True, exist_ok=True)
    cache_f = DUTCHREF_CACHE / "rap-index.html"
    if cache_f.exists() and cache_f.stat().st_size > MIN_BODY:
        print(f"缓存命中: {cache_f.name}", flush=True)
        return cache_f.read_text(encoding="utf-8", errors="replace")
    for i, wait in enumerate([0] + BACKOFFS):
        if wait:
            print(f"  失败，退避 {wait}s 后重试…", flush=True)
            time.sleep(wait)
        try:
            st, txt = fetch_text(INDEX, timeout=45, retries=2)
            if st == 200 and len(txt) > MIN_BODY:
                cache_f.write_text(txt, encoding="utf-8")
                print(f"  已缓存 {len(txt)//1024}KB", flush=True)
                return txt
            print(f"  HTTP {st}, {len(txt)}B", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  请求异常: {e}", flush=True)
    raise SystemExit("索引页抓取失败（重跑可续）")


def discover(page: str) -> list:
    """文档顺序提取 (edition_key, url, link_text)。同链接取首次出现。"""
    out, seen = [], set()
    for m in LINK_RE.finditer(page):
        url, txt = m.group(1), clean(m.group(2))
        if not URL_HOSTS.search(url):
            continue
        em = EDITION_RE.search(txt) or EDITION_RE.search(clean(page[max(0, m.start()-300):m.start()]))
        if not em:
            continue
        key = re.sub(r"\s+", " ", em.group(1)).upper().replace("–", "-").replace(": ", "-")
        key = re.sub(r"\s*-\s*", "-", key)
        if url not in seen:
            seen.add(url)
            out.append({"edition": key, "url": url, "text": txt[:120]})
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    page = fetch_page()
    found = discover(page)
    print(f"\n索引页发现 {len(found)} 个期数链接：")
    for f in found:
        print(f"  {f['edition']:22s} {f['url']}\n    链接文本: {f['text']}")
    if mode == "merge":
        if not RAP_JSON.exists():
            raise SystemExit(f"缺少 {RAP_JSON}，先人工策展创建")
        data = json.loads(RAP_JSON.read_text(encoding="utf-8"))
        have = {e.get("id", "").upper() for e in data.get("editions", [])}
        added = 0
        for f in found:
            if f["edition"] not in have:
                data["editions"].append({
                    "id": f["edition"], "title": f"RAP {f['edition']}",
                    "platform": "nextaur" if "nextaur" in f["url"] else "download",
                    "status": "unreviewed", "url": f["url"], "note": "脚本发现待人工核对"})
                added += 1
        if added:
            data["checked"] = time.strftime("%Y-%m-%d")
            RAP_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                                encoding="utf-8")
        print(f"merge 完成: 新增 {added} 期（status=unreviewed，待人工核对补注）")


if __name__ == "__main__":
    main()
