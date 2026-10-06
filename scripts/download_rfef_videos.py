# -*- coding: utf-8 -*-
"""下载 RFEF 手册判例视频 → site/videos/rfef/（断点续传；不进 git，同 CFA 视频策略）

用法: python download_rfef_videos.py [survey|download|verify]
- survey  (默认): HEAD 普查全部视频的体积与可下载性，打印总量
- download: 4 线程下载（safe_http.download 断点续传，重跑续传）
- verify: 逐个比对本地文件大小 vs 服务器 HEAD
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from lib.safe_http import download, head_size

from lib.paths import RFEF_JSON, SITE_VIDEOS

VID_DIR = SITE_VIDEOS / "rfef"


def load_videos() -> list:
    data = json.loads(RFEF_JSON.read_text(encoding="utf-8"))
    seen, out = set(), []
    for sec in data["sections"]:
        for g in sec["groups"]:
            for it in g["items"]:
                for v in it.get("videos", []):
                    if v["url"] not in seen:
                        seen.add(v["url"])
                        out.append({"url": v["url"], "file": v["file"]})
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "survey"
    vids = load_videos()
    print(f"视频清单: {len(vids)} 个（来自 {RFEF_JSON}）", flush=True)
    if mode == "survey":
        total, ok, miss = 0, 0, []
        for i, v in enumerate(vids):
            n = head_size(v["url"], timeout=30)
            if n:
                ok += 1
                total += n
            else:
                miss.append(v["url"])
            if (i + 1) % 30 == 0:
                print(f"  …{i+1}/{len(vids)}，累计 {total/1e6:.0f}MB", flush=True)
        print(f"survey 完成: 可下载 {ok}/{len(vids)}，合计 {total/1e6:.0f}MB "
              f"({total/1e9:.2f}GB)", flush=True)
        if miss:
            print(f"HEAD 失败 {len(miss)} 个（下载时再试）:", flush=True)
            for u in miss[:10]:
                print(f"  {u}", flush=True)
    elif mode == "download":
        VID_DIR.mkdir(parents=True, exist_ok=True)
        fails = []

        def one(v):
            dest = VID_DIR / v["file"].rsplit("/", 1)[-1]
            st, size = download(v["url"], dest, timeout=90, retries=4)
            return v, st, size

        done = 0
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = [ex.submit(one, v) for v in vids]
            for f in as_completed(futs):
                try:
                    v, st, size = f.result()
                    done += 1
                    print(f"[{done}/{len(vids)}] {size/1e6:6.1f}MB  "
                          f"{v['file'].rsplit('/', 1)[-1]}", flush=True)
                except Exception as e:  # noqa: BLE001
                    fails.append(str(e))
                    print(f"  ✗ {e}", flush=True)
                time.sleep(0.3)  # 礼貌节流
        print(f"download 完成: {len(vids)-len(fails)}/{len(vids)}", flush=True)
        if fails:
            print("失败清单（重跑本脚本续传）:", flush=True)
            for f in fails:
                print(f"  {f}", flush=True)
            sys.exit(1)
    elif mode == "verify":
        bad = []
        for v in vids:
            f = VID_DIR / v["file"].rsplit("/", 1)[-1]
            if not f.exists():
                bad.append((v["file"], "缺失"))
                continue
            n = head_size(v["url"], timeout=30)
            if n and abs(n - f.stat().st_size) > 1024:
                bad.append((v["file"], f"{f.stat().st_size}!={n}"))
        if bad:
            print(f"异常 {len(bad)} 个:")
            for f, why in bad:
                print(f"  {f}: {why}")
            sys.exit(1)
        print(f"verify 通过: {len(vids)} 个视频全部完整", flush=True)


if __name__ == "__main__":
    main()
