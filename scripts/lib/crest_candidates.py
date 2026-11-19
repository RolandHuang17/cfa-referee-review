"""将待核验队徽和来源放入本机候选目录，供人工复核。"""

import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from lib.atomic_json import write_json
from lib.paths import LOCAL
from lib.safe_http import download


def save_candidate(team, image_url, source_url):
    # 同一队名、图片 URL 复用分片，新赛季目录重新编号不影响候选归属。
    key = hashlib.sha256((team + "\n" + image_url).encode("utf-8")).hexdigest()
    suffix = Path(urlsplit(image_url).path).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}:
        suffix = ".img"
    directory = LOCAL / "crest-candidates" / key
    image = directory / ("candidate" + suffix)
    _, size = download(image_url, image, timeout=20, retries=1)
    if size < 1500:
        image.unlink(missing_ok=True)
        raise ValueError("候选图片过小")
    record = {
        "team": team,
        "file": image.name,
        "image_url": image_url,
        "source_url": source_url,
    }
    write_json(directory / "source.json", record)
    return image


def collect(catalog_path, lookup):
    teams = json.loads(catalog_path.read_text(encoding="utf-8"))["teams"]
    total = 0
    for item in teams.values():
        if item["status"] == "verified":
            continue
        team = item["name"]
        try:
            candidate = lookup(team)
            if candidate:
                image = save_candidate(team, *candidate)
                total += 1
                print(f"待目检 {team}: {image}")
        except (OSError, RuntimeError, ValueError) as exc:
            print(f"跳过 {team}: {exc}")
    print(f"本次保存 {total} 个候选队徽，来源见各自的 source.json")
