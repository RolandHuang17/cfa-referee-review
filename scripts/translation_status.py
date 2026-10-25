# -*- coding: utf-8 -*-
"""译文层覆盖率盘点：各 -zh 层对源数据的翻译完成度。

用法：python scripts/translation_status.py [-v]
      -v 逐条列出缺失（默认只打印汇总）。

供翻译贡献者找活干（缺口清单）与维护者巡检。对齐规则与各层结构见
docs/translation-guide.md；uefa/rfef/conmebol/weekly/ifab/hns 的对齐
另有 test_integrity 硬断言（缺失会拦 CI），本脚本提供更细的粒度。
"""

import json
import sys

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


def _read(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def main():
    verbose = "-v" in sys.argv
    rows = []

    uefa, uzh = _read(UEFA_JSON), _read(UEFA_ZH_JSON)
    items = {it["id"] for g in uefa.get("groups", []) for it in g.get("items", [])}
    hit = {k for k in items if (uzh.get("items", {}).get(k) or {}).get("title")}
    rows.append(
        (
            "uefa-zh",
            "判例标题",
            len(items),
            len(hit),
            sorted(items - hit)[:5] if verbose else None,
        )
    )

    rfef, rzh = _read(RFEF_JSON), _read(RFEF_ZH_JSON)
    need, done, miss = [], [], []
    for s in rfef.get("sections", []):
        for g in s.get("groups", []):
            for it in g.get("items", []):
                if not it.get("situation_es"):
                    continue
                need.append(it["id"])
                if (rzh.get("items", {}).get(it["id"]) or {}).get("situation"):
                    done.append(it["id"])
                else:
                    miss.append(it["id"])
    rows.append(
        ("rfef-zh", "判例情形", len(need), len(done), miss[:5] if verbose else None)
    )

    con, czh = _read(CONMEBOL_JSON), _read(CONMEBOL_ZH_JSON)
    need = [c["url"] for c in con.get("cases", []) if c.get("situacion_es")]
    done = [u for u in need if (czh.get("cases", {}).get(u) or {}).get("situation")]
    rows.append(
        (
            "conmebol-zh",
            "情境描述",
            len(need),
            len(done),
            [u.rsplit("/", 1)[-1] for u in set(need) - set(done)][:5]
            if verbose
            else None,
        )
    )

    weekly, wzh = _read(WEEKLY_JSON), _read(WEEKLY_ZH_JSON)
    eps = [e["id"] for e in weekly.get("episodes", [])]
    hit = [i for i in eps if (wzh.get("items", {}).get(i) or {}).get("note")]
    rows.append(
        (
            "weekly-zh",
            "期目译注",
            len(eps),
            len(hit),
            sorted(set(eps) - set(hit))[:5] if verbose else None,
        )
    )

    ifab, izh = _read(IFAB_JSON), _read(IFAB_ZH_JSON)
    faq = [q["id"] for q in ifab.get("faq", [])]
    hit = [q for q in faq if (izh.get("faq", {}).get(q) or {}).get("a")]
    rows.append(
        (
            "ifab-zh",
            "FAQ 问答",
            len(faq),
            len(hit),
            sorted(set(faq) - set(hit))[:5] if verbose else None,
        )
    )

    hns, hzh = _read(HNS_JSON), _read(HNS_ZH_JSON)
    incs = [
        (r["id"], i["no"])
        for r in hns.get("rounds", [])
        for i in r.get("incidents", [])
    ]
    hit = [
        k
        for k in incs
        if (
            hzh.get("rounds", {}).get(str(k[0]), {}).get("incidents", {}).get(str(k[1]))
            or {}
        ).get("paras")
    ]
    rows.append(
        (
            "hns-zh",
            "判例正文",
            len(incs),
            len(hit),
            [f"{r}-{i}" for r, i in set(incs) - set(hit)][:5] if verbose else None,
        )
    )

    print(f"{'层':<14} {'对象':<8} {'覆盖':>10}  完成率")
    all_done = True
    for name, what, total, done, miss in rows:
        pct = f"{done / total * 100:.0f}%" if total else "-"
        flag = "" if done == total else "  ← 有缺口"
        if done != total:
            all_done = False
        print(f"{name:<14} {what:<8} {done}/{total:>6}  {pct}{flag}")
        if verbose and miss:
            for m in miss:
                print(f"    缺失: {m}")
    if all_done:
        print("全部译文层覆盖完整")
    return 0


if __name__ == "__main__":
    sys.exit(main())
