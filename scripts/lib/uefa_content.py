"""欧足联判例译文与其所针对的官方原文。详情和检索共用配对结果。"""

from collections import Counter

from lib.translation_versions import fingerprint


def criterion_version(block):
    return fingerprint([block["h"], block["items"]])


def apply_zh(data, zh, warn=None):
    """添加当前可配对的展示字段。每次调用重新判断，保留全部官方字段和译文。"""
    zh = zh or {}
    groups = data.get("groups", [])
    zg = zh.get("groups", {})
    zi = zh.get("items", {})
    versions = zh.get("source_versions", {})
    group_ids = Counter(group["key"] for group in groups)
    item_ids = Counter(item["id"] for group in groups for item in group["items"])

    def report(label):
        if warn:
            warn(f"⚠ UEFA {label} 中文待复核，显示官方英文")

    for group in groups:
        key = group["key"]
        translation = zg.get(key, {})
        pins = versions.get("groups", {}).get(key, {}) if group_ids[key] == 1 else {}
        for source, field, chinese in (
            ("name_en", "name_current_cn", group.get("name_cn", "")),
            ("intro", "intro_cn", translation.get("intro", "")),
        ):
            english = group.get(source, "")
            group[field] = chinese if pins.get(source) == fingerprint(english) else ""
            if english and not group[field]:
                report(f"{key}/{source}")

        # 旧译的块序属于译层自身。用标题和整块有序原文重新匹配，
        # 即使官网插入或移动整块，也能保留未改动块的译文。
        old_blocks = translation.get("criteria", [])
        old_versions = pins.get("criteria", [])
        by_version = {}
        if len(old_blocks) == len(old_versions):
            for version, block in zip(old_versions, old_blocks):
                by_version[version] = None if version in by_version else block
        current = [criterion_version(block) for block in group["criteria"]]
        counts = Counter(current)
        group["criteria_cn"] = []
        for block, version in zip(group["criteria"], current):
            merged = by_version.get(version) if counts[version] == 1 else None
            if not (
                merged
                and merged.get("h")
                and len(merged.get("items", [])) == len(block["items"])
                and all(merged["items"])
            ):
                merged = None
                report(f"{key}/criteria/{block['h']}")
            group["criteria_cn"].append(merged)

        for item in group["items"]:
            item_id = item["id"]
            title = zi.get(item_id, {}).get("title", "")
            pin = versions.get("items", {}).get(item_id)
            item["title_cn"] = (
                title
                if item_ids[item_id] == 1 and pin == fingerprint(item["title"])
                else ""
            )
            if not item["title_cn"]:
                report(f"{key}/{item_id}")

    if warn:
        for key in sorted(zg.keys() - group_ids.keys()):
            warn(f"⚠ UEFA 译层保留了现行来源中未匹配的组 {key}")
        for key in sorted(zi.keys() - item_ids.keys()):
            warn(f"⚠ UEFA 译层保留了现行来源中未匹配的判例 {key}")
