# -*- coding: utf-8 -*-
"""Shared, auditable team crest catalog used by all page builders."""
import json

from lib.paths import ROOT, TEAMS_JSON


def load_catalog():
    payload = json.loads(TEAMS_JSON.read_text(encoding="utf-8"))
    return payload["teams"]


def normalize_team(name):
    if not name:
        return ""
    teams = load_catalog()
    aliases = payload_aliases()
    return aliases.get(name, name) if name in teams or name in aliases else name


def payload_aliases():
    payload = json.loads(TEAMS_JSON.read_text(encoding="utf-8"))
    aliases = {}
    for team in payload["teams"].values():
        for alias in team.get("aliases", []):
            aliases[alias] = team["name"]
        aliases[team["name"]] = team["name"]
    return aliases


def load_legacy_map():
    return {name: item["path"] for name, item in load_catalog().items()
            if item.get("status") == "verified" and item.get("path")}


def validate_catalog(catalog):
    """返回人类可读的问题列表；空列表表示目录健全。

    由 scripts/fetch_crests.py（构建步骤，必须 hard-fail）与 tests/test_integrity.py
    （完整性断言，必须一次报告全部问题）共用——两边此前各存一份、措辞还不一致。
    """
    problems = []
    for item in catalog.values():
        name, status, path = item.get("name"), item.get("status"), item.get("path")
        if status not in {"verified", "fallback"}:
            problems.append(f"未知队徽状态: {name} -> {status}")
            continue
        if status == "fallback":
            continue
        if not path or not path.startswith("assets/crests/"):
            problems.append(f"队徽路径无效: {name} -> {path}")
        elif not (ROOT / path).exists():
            problems.append(f"队徽文件不存在: {name} -> {path}")
        if not item.get("source_url") or not item.get("source_type"):
            problems.append(f"缺少来源元数据: {name}")
    return problems
