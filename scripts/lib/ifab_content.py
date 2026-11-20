"""IFAB 原文、译文与定位。详情页和搜索只从这一份配对结果取数。"""

from collections import Counter

from lib.translation_versions import fingerprint


def version_inputs(data):
    """列出可独立复核的英文标题、条款块及问答，供译者更新来源版本。"""
    for section in data.get("sections", []) + data.get("extras", []):
        key = section["id"]
        yield key + "/title", section["h"]
        for block in section.get("blocks", []):
            yield (
                key + "/block/" + (block["h"] or "_head"),
                [[item["k"], item["t"]] for item in block["items"]],
            )
        for q in section.get("faq", []):
            yield key + "/faq/" + q["id"], [q["q"], q["a"]]
    for q in data.get("faq", []):
        yield "faq/" + q["id"], [q["q"], q["a"]]


def _source_anchor(section_id, kind, text):
    # 英文原文决定定位，条款前插或仅修改中文译文不会改变后文书签。
    return f"{section_id}-{kind}-{fingerprint(' '.join(text.split()))[:12]}"


def documents(data, zh, warn=None):
    """返回当前可配对的条款和 FAQ；过期译文只保留在独立标识的旧译区。"""
    pinned = zh.get("source_versions", {})
    inputs = list(version_inputs(data))
    current = {key: fingerprint(value) for key, value in inputs}
    cardinality = Counter(key for key, _ in inputs)

    def matched(key):
        return cardinality[key] == 1 and key in pinned and pinned[key] == current[key]

    def report(key):
        if warn:
            warn(f"ifab-zh {key} 缺译或来源版本不符，显示官方英文")

    def old_questions(source, translated):
        ids = {q["id"] for q in source}
        return [
            line
            for key, pair in translated.items()
            if key not in ids
            for line in (pair.get("q", ""), pair.get("a", ""))
        ]

    def questions(source, translated, section_id):
        result = []
        seen = Counter()
        for q in source:
            key = ("" if section_id == "faq" else section_id + "/") + "faq/" + q["id"]
            zq = translated.get(q["id"], {})
            aligned = matched(key)
            if not aligned or not zq.get("q") or not zq.get("a"):
                report(key)
            anchor = _source_anchor(section_id, "q", q["q"])
            seen[anchor] += 1
            if seen[anchor] > 1:
                anchor += f"-{seen[anchor]}"
            result.append(
                {
                    "id": anchor,
                    "old_id": "faq-" + q["id"] if section_id == "faq" else "",
                    "q": q["q"],
                    "a": q["a"],
                    "zq": zq.get("q", "") if aligned else "",
                    "za": zq.get("a", "") if aligned else "",
                    "previous": [] if aligned else [zq.get("q", ""), zq.get("a", "")],
                    "additional_terms": [],
                }
            )
        return result

    docs = []
    for group in ("sections", "extras"):
        for sec in data.get(group, []):
            key = sec["id"]
            zsec = zh.get(group, {}).get(key, {})
            active_title = matched(key + "/title")
            title = zsec.get("h", "") if active_title else ""
            if not title:
                report(key + "/title")
            faq = questions(sec.get("faq", []), zsec.get("faq", {}), key)
            zblocks = zsec.get("blocks", {})
            used = Counter()
            blocks = []
            for b in sec.get("blocks", []):
                heading = b.get("h", "")
                slot = heading or "_head"
                label = key + "/block/" + slot
                zb = zblocks.get(slot, {})
                zitems = zb if isinstance(zb, list) else zb.get("items", [])
                zheading = "" if isinstance(zb, list) else zb.get("h", "")
                aligned = matched(label) and [i["k"] for i in b["items"]] == [
                    i.get("k") for i in zitems
                ]
                if not aligned or any(not i.get("t") for i in zitems):
                    report(label)
                items = []
                for n, item in enumerate(b["items"]):
                    anchor = _source_anchor(key, "p", item["t"])
                    used[anchor] += 1
                    if used[anchor] > 1:
                        anchor += f"-{used[anchor]}"
                    items.append(
                        {
                            "id": anchor,
                            "k": item["k"],
                            "en": item["t"],
                            "zh": zitems[n].get("t", "") if aligned else "",
                        }
                    )
                # 部分官网配套页还把同一 FAQ 答案拆成一组正文条款。保留正文，
                # 检索指向问答；单独译过的用词一起归入该 FAQ 的检索文字。
                faq_match = None
                if heading.lower() in ("faq", "faqs"):
                    text = " ".join(" ".join(i["en"].split()) for i in items)
                    faq_match = next(
                        (q for q in faq if text == " ".join(q["a"].split())), None
                    )
                    if faq_match:
                        faq_match["additional_terms"].extend(
                            i["zh"]
                            for i in items
                            if i["zh"] and i["zh"] not in faq_match["za"]
                        )
                blocks.append(
                    {
                        "h": heading,
                        "zh": zheading if aligned else "",
                        "items": items,
                        "faq_copy": bool(faq_match),
                        "previous": []
                        if aligned
                        else [zheading, *(i.get("t", "") for i in zitems)],
                    }
                )
            previous = [] if active_title else [zsec.get("h", "")]
            active_slots = {b["h"] or "_head" for b in sec.get("blocks", [])}
            for slot, old in zblocks.items():
                if slot not in active_slots:
                    if isinstance(old, dict):
                        previous.append(old.get("h", ""))
                        old = old.get("items", [])
                    previous.extend(item.get("t", "") for item in old)
            previous.extend(old_questions(sec.get("faq", []), zsec.get("faq", {})))
            docs.append(
                {
                    "id": key,
                    "h": sec["h"],
                    "zh": title,
                    "num": sec.get("num", ""),
                    "url": sec.get("url", ""),
                    "group": group,
                    "blocks": blocks,
                    "faq": faq,
                    "previous": previous,
                }
            )
    docs.append(
        {
            "id": "faq",
            "h": "Official FAQs",
            "zh": "官方 FAQ 判例",
            "num": "",
            "group": "faq",
            "blocks": [],
            "faq": questions(data.get("faq", []), zh.get("faq", {}), "faq"),
            "previous": old_questions(data.get("faq", []), zh.get("faq", {})),
        }
    )
    return docs


def search_rows(data, zh):
    for doc in documents(data, zh):
        title = doc["zh"] or doc["h"]
        paragraph = 0
        for block in doc["blocks"]:
            if block["faq_copy"]:
                continue
            heading = block["zh"] or block["h"]
            scope = " · ".join(dict.fromkeys(x for x in (title, heading) if x))
            for item in block["items"]:
                paragraph += 1
                text = " ".join(
                    dict.fromkeys(
                        x for x in (item["zh"], item["en"], doc["h"], block["h"]) if x
                    )
                )
                yield f"{scope} · 第{paragraph}段", item["id"], text
        for q in doc["faq"]:
            text = " ".join(
                x
                for x in (q["zq"], q["za"], q["q"], q["a"], *q["additional_terms"])
                if x
            )
            yield f"{title} · {(q['zq'] or q['q'])[:54]}", q["id"], text
