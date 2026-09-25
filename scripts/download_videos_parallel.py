# -*- coding: utf-8 -*-
"""并发(5线程)下载判例视频到 videos/{season}/，断点续传+重试
用法: python download_videos_parallel.py 2024|2025
"""
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from safe_http import download

ROOT = Path(__file__).resolve().parent.parent
VID_DIR = ROOT / "site" / "videos"
LOG = ROOT / "data" / "download_log.txt"
LOCK = threading.Lock()


def log(msg):
    with LOCK:
        print(msg, flush=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")


def main():
    season = sys.argv[1] if len(sys.argv) > 1 else "2025"
    data = json.loads((ROOT / "data" / f"cases-{season}.json").read_text(encoding="utf-8"))
    jobs, seen = [], {}
    for c in data["cases"]:
        for url, fname in zip(c["video_urls"], c["video_files"]):
            if url not in seen:
                seen[url] = fname
                jobs.append((url, fname))
    log(f"[{season}] 待下载 {len(jobs)} 个视频（去重后）")

    def job(url, fname):
        t0 = time.time()
        status, size = download(url, VID_DIR / fname, timeout=90, retries=5)
        rate = size / max(time.time() - t0, 0.1) / 1e6
        return fname, size, rate

    total_size, fails, done = 0, [], 0
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(job, u, f): (u, f) for u, f in jobs}
        for fut in as_completed(futs):
            url, fname = futs[fut]
            try:
                _, size, rate = fut.result()
                total_size += size
                done += 1
                log(f"[{done}/{len(jobs)}] {fname} {size/1e6:.1f}MB ({rate:.1f}MB/s)")
            except Exception as e:  # noqa: BLE001
                fails.append(fname)
                log(f"FAIL {fname}: {e}")
            time.sleep(0.1)
    log(f"[{season}] 完成。成功{done} 失败{len(fails)} 总计{total_size/1e9:.2f}GB 失败清单:{fails}")
    (ROOT / "data" / f"download-fail-{season}.json").write_text(
        json.dumps(fails, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
