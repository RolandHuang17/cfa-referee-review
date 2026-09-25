# -*- coding: utf-8 -*-
"""检查人工队徽目录，不再自动猜测 Wikipedia 图片。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "teams.json"


def main():
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    verified, fallback = 0, 0
    compat = {}
    for item in payload["teams"].values():
        status = item.get("status")
        path = item.get("path")
        if status == "verified":
            if not path or not path.startswith("assets/crests/"):
                raise SystemExit(f"队徽路径无效: {item['name']}")
            if not (ROOT / path).exists():
                raise SystemExit(f"队徽文件不存在: {item['name']} -> {path}")
            if not item.get("source_url") or not item.get("source_type"):
                raise SystemExit(f"缺少来源元数据: {item['name']}")
            compat[item["name"]] = path
            verified += 1
        elif status == "fallback":
            if path:
                compat[item["name"]] = path
            fallback += 1
        else:
            raise SystemExit(f"未知队徽状态: {item['name']} -> {status}")
    (ROOT / "data" / "crests.json").write_text(
        json.dumps(compat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"队徽目录检查完成: verified={verified}, fallback={fallback}")


if __name__ == "__main__":
    main()
