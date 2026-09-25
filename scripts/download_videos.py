# -*- coding: utf-8 -*-
"""下载全部判例视频到 videos/，断点续传+重试，日志写 data/download_log.txt"""
import json
import sys
import time
from pathlib import Path

from safe_http import download, head_size

ROOT = Path(__file__).resolve().parent.parent
VID_DIR = ROOT / "site" / "videos"
LOG = ROOT / "data" / "download_log.txt"


def main():
    season = sys.argv[1] if len(sys.argv) > 1 else "2025"
    data = json.loads((ROOT / "data" / f"cases-{season}.json").read_text(encoding="utf-8"))
    season_vid_dir = VID_DIR / season
    jobs = []
    seen = {}
    for c in data["cases"]:
        for url, fname in zip(c["video_urls"], c["video_files"]):
            if url not in seen:
                seen[url] = fname
                jobs.append((url, fname))
    # 把复用信息写回（同url的第二个名字指向首个文件）
    url2file = dict(seen)
    aliases = {}
    for c in data["cases"]:
        for url, fname in zip(c["video_urls"], c["video_files"]):
            if url2file[url] != fname:
                aliases[fname] = url2file[url]
    if aliases:
        (ROOT / "data" / "video_aliases.json").write_text(
            json.dumps(aliases, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"待下载 {len(jobs)} 个视频（去重后，赛季{season}）")
    # 先统计总大小
    total = 0
    for url, fname in jobs:
        s = head_size(url)
        total += s or 0
        LOG.open("a", encoding="utf-8").write(f"HEAD {fname} {s}\n")
        time.sleep(0.15)
    print(f"总大小: {total/1e9:.2f} GB")
    LOG.open("a", encoding="utf-8").write(f"TOTAL {total}\n")

    fail = []
    done_bytes = 0
    t0 = time.time()
    for i, (url, fname) in enumerate(jobs, 1):
        try:
            status, size = download(url, season_vid_dir / fname, expected_size=None, progress=False)
            done_bytes += size
            eta = ""
            if i > 2:
                rate = done_bytes / max(time.time() - t0, 1) / 1e6
                remain = (total - done_bytes) / 1e6
                if rate > 0.1:
                    eta = f" 速度{rate:.1f}MB/s 预计剩余{remain/rate/60:.0f}分钟"
            print(f"[{i}/{len(jobs)}] {fname} {size/1e6:.1f}MB{eta}", flush=True)
            LOG.open("a", encoding="utf-8").write(f"OK {fname} {size}\n")
        except Exception as e:  # noqa: BLE001
            print(f"[{i}/{len(jobs)}] {fname} 失败: {e}", flush=True)
            LOG.open("a", encoding="utf-8").write(f"FAIL {fname} {e}\n")
            fail.append(fname)
        time.sleep(0.2)
    print(f"\n完成。失败 {len(fail)} 个: {fail}")
    (ROOT / "data" / "download_fail.json").write_text(
        json.dumps(fail, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
