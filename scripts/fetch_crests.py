# -*- coding: utf-8 -*-
"""检查人工队徽目录，不再自动猜测 Wikipedia 图片。"""
import json

from lib.crest_catalog import validate_catalog
from lib.paths import CRESTS_JSON, TEAMS_JSON


def main():
    teams = json.loads(TEAMS_JSON.read_text(encoding="utf-8"))["teams"]
    problems = validate_catalog(teams)
    if problems:
        raise SystemExit("队徽目录校验失败:\n  " + "\n  ".join(problems))
    compat = {}
    verified, fallback = 0, 0
    for item in teams.values():
        if item.get("status") == "verified":
            compat[item["name"]] = item["path"]
            verified += 1
        else:
            if item.get("path"):
                compat[item["name"]] = item["path"]
            fallback += 1
    CRESTS_JSON.write_text(
        json.dumps(compat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"队徽目录检查完成: verified={verified}, fallback={fallback}")


if __name__ == "__main__":
    main()
