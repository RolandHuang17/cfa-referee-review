# -*- coding: utf-8 -*-
"""下载完成后的最终校验：
1. 改名第27期文章遗留的两个视频文件（i27c02-2/3 -> i26c02-2/i26c07-2）
2. 核对每个视频文件大小与服务器Content-Length一致
3. 报告缺失/损坏文件（可重跑 download_videos_parallel.py 补齐）
"""
import json
import sys
from pathlib import Path

from safe_http import head_size

ROOT = Path(__file__).resolve().parent.parent
SEASON = sys.argv[1] if len(sys.argv) > 1 else "2025"
VID = ROOT / "site" / "videos" / SEASON


def rename_legacy():
    pairs = {"i27c02-2.mp4": "i26c02-2.mp4", "i27c02-3.mp4": "i26c07-2.mp4"}
    for old, new in pairs.items():
        o, n = VID / old, VID / new
        if o.exists() and not n.exists():
            o.rename(n)
            print(f"改名 {old} -> {new}")
        elif o.exists() and n.exists():
            if o.stat().st_size == n.stat().st_size:
                o.unlink()
                print(f"删除重复 {old}")
            else:
                print(f"警告: {old} 与 {new} 并存且大小不同，请人工检查")


def main():
    rename_legacy()
    data = json.loads((ROOT / "data" / f"cases-{SEASON}.json").read_text(encoding="utf-8"))
    need = {}
    for c in data["cases"]:
        for f in c["video_files"]:
            need.setdefault(f, c["seq"])
    missing, size_mismatch, ok = [], [], 0
    for f in sorted(need):
        p = VID / f
        if not p.exists():
            missing.append(f)
            continue
        remote = head_size("https://videooss.thecfa.cn/upload/video/" + _remote_path(data, f))
        local = p.stat().st_size
        if remote and remote != local:
            size_mismatch.append((f, local, remote))
        elif remote is None:
            print(f"  ? {f}: 无法获取远端大小(本地{local/1e6:.1f}MB)")
            ok += 1
        else:
            ok += 1
        print(f"  √ {f} {local/1e6:.1f}MB")
    print(f"\n校验完成: 完整{ok} 缺失{len(missing)} 大小不符{len(size_mismatch)}")
    if missing:
        print("缺失:", missing)
        print("-> 重跑 scripts/download_videos_parallel.py 可补齐")
    if size_mismatch:
        print("大小不符:", size_mismatch)
        print("-> 删除对应 .mp4 后重跑下载脚本修复")
    (ROOT / "data" / "verify_result.json").write_text(
        json.dumps({"missing": missing, "mismatch": size_mismatch, "ok": ok},
                   ensure_ascii=False, indent=1), encoding="utf-8")


def _remote_path(data, fname):
    """从当前赛季数据反查视频URL路径"""
    for c in data["cases"]:
        if fname in c["video_files"]:
            i = c["video_files"].index(fname)
            return c["video_urls"][i].replace("https://videooss.thecfa.cn/upload/video/", "")
    raise KeyError(fname)


if __name__ == "__main__":
    main()
