# -*- coding: utf-8 -*-
"""Shared, auditable team crest catalog used by all page builders."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "teams.json"


def load_catalog():
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return payload["teams"]


def normalize_team(name):
    if not name:
        return ""
    teams = load_catalog()
    aliases = payload_aliases()
    return aliases.get(name, name) if name in teams or name in aliases else name


def payload_aliases():
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    aliases = {}
    for team in payload["teams"].values():
        for alias in team.get("aliases", []):
            aliases[alias] = team["name"]
        aliases[team["name"]] = team["name"]
    return aliases


def load_legacy_map():
    return {name: item["path"] for name, item in load_catalog().items()
            if item.get("status") == "verified" and item.get("path")}
