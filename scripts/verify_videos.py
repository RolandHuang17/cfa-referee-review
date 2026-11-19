# -*- coding: utf-8 -*-
"""校验本地判例视频大小，区分缺失、不符与远端不可核验。"""

import argparse
import json

from lib.atomic_json import write_json
from lib.paths import DATA, LOCAL_LOGS, SITE_VIDEOS
from lib.safe_http import head_size


def rename_legacy(directory):
    """只迁移 2025 第 27 期拆分遗留文件；保留重名副本供人工核对。"""
    pairs = {"i27c02-2.mp4": "i26c02-2.mp4", "i27c02-3.mp4": "i26c07-2.mp4"}
    for old, new in pairs.items():
        source, target = directory / old, directory / new
        if source.exists():
            if target.exists():
                print(f"保留并存文件 {old} 与 {new}，请人工核对")
            else:
                source.rename(target)
                print(f"改名 {old} -> {new}")


def verify(data, directory):
    files = {}
    for case in data["cases"]:
        if len(case["video_files"]) != len(case["video_urls"]):
            raise ValueError(f"判例 {case['seq']} 的文件与 URL 数量不同")
        for name, url in zip(case["video_files"], case["video_urls"]):
            if files.setdefault(name, url) != url:
                raise ValueError(f"同一视频文件对应多个来源: {name}")
    result = {"ok": 0, "missing": [], "mismatch": [], "unverified": []}
    for name, url in sorted(files.items()):
        path = directory / name
        if not path.is_file():
            result["missing"].append(name)
            continue
        local = path.stat().st_size
        remote = head_size(url)
        if remote is None:
            result["unverified"].append(name)
            print(f"  ? {name}: 无法获取远端大小（本地 {local} 字节）")
        elif remote != local or local == 0:
            result["mismatch"].append((name, local, remote))
        else:
            result["ok"] += 1
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "season", nargs="?", choices=("2024", "2025", "2026"), default="2025"
    )
    parser.add_argument(
        "--migrate-legacy", action="store_true", help="迁移 2025 年的旧视频文件名"
    )
    args = parser.parse_args(argv)
    if args.migrate_legacy:
        if args.season != "2025":
            parser.error("旧文件名迁移仅适用于 2025 赛季")
        rename_legacy(SITE_VIDEOS / args.season)
    data = json.loads((DATA / f"cases-{args.season}.json").read_text(encoding="utf-8"))
    result = verify(data, SITE_VIDEOS)
    result["season"] = args.season
    log = LOCAL_LOGS / "verify_result.json"
    write_json(log, result)
    print(
        f"完整 {result['ok']}，缺失 {len(result['missing'])}，大小不符 {len(result['mismatch'])}，"
        f"未核验 {len(result['unverified'])}。清单见 {log}"
    )
    if result["missing"] or result["mismatch"]:
        return 1
    return 2 if result["unverified"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
