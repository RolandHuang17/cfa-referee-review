# -*- coding: utf-8 -*-
"""并发(5线程)下载全部判例视频到 videos/，断点续传+重试"""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from safe_http import download, head_size

ROOT = Path(__file__).resolve().parent.parent
VID_DIR = ROOT / "videos"
LOG = ROOT / "data" / "download_log.txt"
LOCK = threading.Lock()


def log(msg):
    with LOCK:
        print(msg, flush=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")


def main():
    data = json.loads((ROOT / "data" / "cases.json").read_text(encoding="utf-8"))
    jobs, seen = [], {}
    for c in data["cases"]:
        for url, fname in zip(c["video_urls"], c["video_files"]):
            if url not in seen:
                seen[url] = fname
                jobs.append((url, fname))
    log(f"待下载 {len(jobs)} 个视频（去重后）")

    # 已完成的直接跳过（.part 存在则续传）
    def job(url, fname):
        t0 = time.time()
        status, size = download(url, VID_DIR / fname, timeout=90, retries=5)
        rate = size / max(time.time() - t0, 0.1) / 1e6
        return fname, size, rate

    total_size = 0
    fails = []
    done = 0
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
    log(f"完成。成功{done} 失败{len(fails)} 总计{total_size/1e9:.2f}GB 失败清单:{fails}")
    (ROOT / "data" / "download_fail.json").write_text(
        json.dumps(fails, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
