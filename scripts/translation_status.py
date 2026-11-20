# -*- coding: utf-8 -*-
"""译文层覆盖率盘点：各 -zh 层对源数据的翻译完成度。

用法：python scripts/translation_status.py [-v]
      -v 逐条列出缺译及待复核项（默认只打印汇总）。
      --source-version <uefa|ifab> <原文键> 显示单项原文和来源指纹。

供翻译贡献者找活干（缺口清单）与维护者巡检。对齐规则与各层结构见
docs/translation-guide.md；uefa/rfef/conmebol/weekly/ifab/hns 的对齐
另有 test_integrity 硬断言（缺失会拦 CI），本脚本提供更细的粒度。
"""

import argparse
import json
import sys

from lib.conmebol_evidence import event_anchor, event_rows, event_translation
from lib.ifab_content import documents, version_inputs
from lib.translation_versions import fingerprint
from lib.uefa_content import apply_zh, criterion_version

from lib.paths import (
    CONMEBOL_JSON,
    CONMEBOL_ZH_JSON,
    HNS_JSON,
    HNS_ZH_JSON,
    IFAB_JSON,
    IFAB_ZH_JSON,
    RFEF_JSON,
    RFEF_ZH_JSON,
    UEFA_JSON,
    UEFA_ZH_JSON,
    WEEKLY_JSON,
    WEEKLY_ZH_JSON,
)


def source(path):
    return json.loads(path.read_text(encoding="utf-8"))


def translation(path):
    return source(path) if path.exists() else {}


class Coverage:
    def __init__(self):
        kinds = {
            "uefa-zh": ("组名", "组导语", "准则块", "判例标题"),
            "rfef-zh": ("判例情形",),
            "conmebol-zh": ("情境描述",),
            "weekly-zh": ("期目译注",),
            "ifab-zh": tuple(
                scope + kind
                for scope in ("主协议", "配套")
                for kind in ("标题", "小节标题", "条款", " FAQ")
            ),
            "hns-zh": ("判例正文",),
        }
        self.rows = {
            (layer, kind): [] for layer, labels in kinds.items() for kind in labels
        }

    def add(self, layer, kind, key, current, previous=False):
        status = "" if current else ("待复核" if previous else "缺译")
        self.rows[layer, kind].append((key, status))


def uefa_coverage(rows, data, zh):
    apply_zh(data, zh)
    for group in data.get("groups", []):
        key = group["key"]
        old = zh.get("groups", {}).get(key, {})
        for field, source_name, kind, previous in (
            ("name_current_cn", "name_en", "组名", group.get("name_cn")),
            ("intro_cn", "intro", "组导语", old.get("intro")),
        ):
            if group.get(source_name):
                rows.add(
                    "uefa-zh", kind, f"{key}/{source_name}", group[field], previous
                )
        pins = zh.get("source_versions", {}).get("groups", {}).get(key, {})
        old_blocks = old.get("criteria", [])
        versions = pins.get("criteria", [])
        known = dict(zip(versions, old_blocks))
        unmatched = set(known) - {criterion_version(b) for b in group["criteria"]}
        unpaired = bool(unmatched or len(versions) != len(old_blocks))
        for index, (block, current) in enumerate(
            zip(group["criteria"], group["criteria_cn"]), 1
        ):
            version = criterion_version(block)
            # 新块与改写的旧块可能没有可辨认的共同键。若组内还有无法配对的
            # 历史译文，交给译者复核；不要擅自指定旧译属于哪一现行块。
            previous = known.get(version) or unpaired
            rows.add(
                "uefa-zh",
                "准则块",
                f"{key}/criteria/{index} · {block['h']}",
                current,
                previous,
            )
        for item in group["items"]:
            item_id = item["id"]
            old_title = zh.get("items", {}).get(item_id, {}).get("title")
            rows.add(
                "uefa-zh", "判例标题", "items/" + item_id, item["title_cn"], old_title
            )


def ifab_coverage(rows, data, zh):
    # documents() 的次序和官方正文一致。FAQ 的页面锚点由问句生成，
    # 贡献者定位并编辑译文时使用原始 JSON 中的 q1 等 ID。
    docs = documents(data, zh)
    originals = [
        *data.get("sections", []),
        *data.get("extras", []),
        {"faq": data.get("faq", [])},
    ]
    for doc, original in zip(docs, originals):
        section = doc["id"]
        scope = "配套" if doc["group"] == "extras" else "主协议"
        old = zh.get(doc["group"], {}).get(section, {})
        if doc["group"] != "faq":
            rows.add(
                "ifab-zh", scope + "标题", section + "/title", doc["zh"], old.get("h")
            )
        for block in doc["blocks"]:
            slot = section + "/block/" + (block["h"] or "_head")
            previous = any(block["previous"])
            if block["h"]:
                rows.add("ifab-zh", scope + "小节标题", slot, block["zh"], previous)
            for n, item in enumerate(block["items"], 1):
                rows.add(
                    "ifab-zh", scope + "条款", f"{slot} · 第{n}条", item["zh"], previous
                )
        for question, official in zip(doc["faq"], original.get("faq", [])):
            key = ("faq/" if doc["group"] == "faq" else section + "/faq/") + official[
                "id"
            ]
            rows.add(
                "ifab-zh",
                scope + " FAQ",
                key,
                question["zq"] and question["za"],
                any(question["previous"]),
            )


def coverage():
    rows = Coverage()
    uefa_coverage(rows, source(UEFA_JSON), translation(UEFA_ZH_JSON))

    rfef, rzh = source(RFEF_JSON), translation(RFEF_ZH_JSON)
    for section in rfef.get("sections", []):
        for group in section.get("groups", []):
            for item in group.get("items", []):
                if item.get("situation_es"):
                    key = item["id"]
                    rows.add(
                        "rfef-zh",
                        "判例情形",
                        key,
                        rzh.get("items", {}).get(key, {}).get("situation"),
                    )

    con, czh = source(CONMEBOL_JSON), translation(CONMEBOL_ZH_JSON)
    for case in con.get("cases", []):
        url = case["url"]
        for event in event_rows(case):
            if event.get("situacion_es"):
                key = f"{url} · {event_anchor(url, event)} · {event['situacion_es']}"
                rows.add(
                    "conmebol-zh", "情境描述", key, event_translation(url, event, czh)
                )

    weekly, wzh = source(WEEKLY_JSON), translation(WEEKLY_ZH_JSON)
    for ep in weekly.get("episodes", []):
        key = ep["id"]
        rows.add(
            "weekly-zh", "期目译注", key, wzh.get("items", {}).get(key, {}).get("note")
        )

    ifab_coverage(rows, source(IFAB_JSON), translation(IFAB_ZH_JSON))

    hns, hzh = source(HNS_JSON), translation(HNS_ZH_JSON)
    for rd in hns.get("rounds", []):
        translations = hzh.get("rounds", {}).get(str(rd["id"]), {}).get("incidents", {})
        for inc in rd.get("incidents", []):
            rows.add(
                "hns-zh",
                "判例正文",
                f"{rd['id']}/{inc['no']}",
                translations.get(str(inc["no"]), {}).get("paras"),
            )
    return rows


def show_source_version(layer, key):
    if layer == "ifab":
        inputs = version_inputs(source(IFAB_JSON))
    else:
        inputs = uefa_inputs(source(UEFA_JSON))
    matches = [value for name, value in inputs if name == key]
    if len(matches) != 1:
        print(f"无法唯一定位 {layer} {key}（匹配 {len(matches)} 条）", file=sys.stderr)
        return 2
    print(json.dumps(matches[0], ensure_ascii=False, indent=2))
    print(f"当前原文指纹 {fingerprint(matches[0])}")
    return 0


def uefa_inputs(data):
    for group in data.get("groups", []):
        key = group["key"]
        for field in ("name_en", "intro"):
            if group.get(field):
                yield f"{key}/{field}", group[field]
        for n, block in enumerate(group["criteria"], 1):
            yield f"{key}/criteria/{n}", [block["h"], block["items"]]
        for item in group["items"]:
            yield "items/" + item["id"], item["title"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="译文层覆盖与当前原文版本")
    parser.add_argument("-v", action="store_true", help="列出所有缺译或待复核的项目")
    parser.add_argument(
        "--source-version",
        nargs=2,
        metavar=("层", "原文键"),
        help="显示一项 UEFA 或 IFAB 官方原文与指纹",
    )
    args = parser.parse_args(argv)
    if args.source_version:
        layer, key = args.source_version
        if layer not in {"uefa", "ifab"}:
            parser.error("--source-version 的层为 uefa 或 ifab")
        return show_source_version(layer, key)

    print(f"{'层':<14} {'对象':<8} {'覆盖':>10}  完成率")
    complete = True
    rows = coverage().rows
    for (name, what), entries in rows.items():
        missing = [(key, status) for key, status in entries if status]
        total = len(entries)
        done = total - len(missing)
        flag = "  ← 有缺口" if missing else ""
        pct = f"{done / total:.0%}" if total else "—"
        print(f"{name:<14} {what:<8} {done}/{total:>6}  {pct}{flag}")
        if missing:
            complete = False
        if args.v:
            for key, status in missing:
                print(f"    {status}  {key}")
    if not any(rows.values()):
        print("本次没有可盘点的原文")
    elif complete:
        print("全部译文层覆盖完整（按上列盘点对象）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
