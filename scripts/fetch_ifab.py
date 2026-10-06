# -*- coding: utf-8 -*-
"""抓取 IFAB《Laws of the Game》VAR 协议页 → data/ifab.json
（提交进仓库，build_ifab.py 据此生成 site/ifab.html；中文全文译制层为 data/ifab-zh.json）

用法: python fetch_ifab.py [fetch|parse|all]   (默认 all)
- fetch: 抓取 VAR protocol 页（SSR 全文，无反爬），缓存 data/local/ifab-cache/
- parse: 纯本地从缓存解析 → data/ifab.json

页面结构（2026-10 实测）：四个 accordion h2 大节（1 Principles / 2 Reviewable
decisions / 3 Practicalities / 4 Procedures），h3 子节，正文 p/li（li 内嵌 p）；
FAQ 为独立 Q&A 容器（问题 h2 + 折叠答案 p，共 ~12 条）。解析按标签顺序提取，
不做语义判断；译文层按 section/block id 平铺匹配（rfef-zh 同构，无块序脆弱性）。
"""
import html as htmllib
import json
import re
import sys
import time

from lib.safe_http import fetch_text

from lib.paths import IFAB_CACHE, IFAB_JSON

URL = "https://www.theifab.com/laws/latest/video-assistant-referee-var-protocol/"
# VAR 协议页之外的官方配套协议/指南页（2026/27 新规与统一尺度材料，人工核对）
EXTRA_PAGES = [
    ("guidelines-introduction", "https://www.theifab.com/laws/latest/guidelines/introduction/"),
    ("temporary-dismissals", "https://www.theifab.com/laws/latest/guidelines-for-temporary-dismissals/"),
    ("return-substitutes", "https://www.theifab.com/laws/latest/guidelines-for-return-substitutes/"),
    ("only-the-captain", "https://www.theifab.com/laws/latest/only-the-captain/"),
    ("throw-in-goal-kick-countdown", "https://www.theifab.com/laws/latest/throw-in-and-goal-kick-countdown-protocol/"),
    ("concussion-substitutions", "https://www.theifab.com/laws/latest/additional-permanent-concussion-substitutions-protocol/"),
    ("off-field-treatment", "https://www.theifab.com/laws/latest/off-field-treatment-and-assessment-protocol/"),
    ("time-limited-substitutions", "https://www.theifab.com/laws/latest/time-limited-substitution-protocol/"),
]
MIN_BODY = 50000
BACKOFFS = [30, 90]

# 页内之外的官方配套入口（人工核对，随数据提交）
LINKS = [
    {"label": "IFAB 官方 PDF 下载门户（Laws / Practical Guidelines / VAR Handbook 等）",
     "url": "https://www.theifab.com/laws-of-the-game-documents/", "internal": False},
    {"label": "Practical Guidelines for Match Officials（引言页，站位/协作/沟通三册入口）",
     "url": "https://www.theifab.com/laws/latest/guidelines/introduction/", "internal": False},
    {"label": "竞赛规则 2026-27 简体全译（本站 rules.html，与本页协议同源 IFAB 原文）",
     "url": "rules.html", "internal": True},
    {"label": "中国足协《统一判罚尺度》官方宣讲（本站 scale.html，场景判例矩阵）",
     "url": "scale.html", "internal": True},
]


def clean(s: str) -> str:
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<[^>]*$", "", s)  # 块尾截断在标签中间的未闭合标签
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s)
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", s).strip()


def fetch_page(url: str = URL) -> str:
    IFAB_CACHE.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9-]", "_", url.split("theifab.com/")[-1]).strip("_")[:80] or "page"
    cache_f = IFAB_CACHE / f"{slug}.html"
    if cache_f.exists() and cache_f.stat().st_size > MIN_BODY:
        return cache_f.read_text(encoding="utf-8", errors="replace")
    for wait in [0] + BACKOFFS:
        if wait:
            time.sleep(wait)
        try:
            st, txt = fetch_text(url, timeout=45, retries=2)
            if st == 200 and len(txt) > MIN_BODY:
                cache_f.write_text(txt, encoding="utf-8")
                return txt
        except Exception:  # noqa: BLE001
            pass
    return ""


H2_ACC = re.compile(r"<h2[^>]*>\s*<button[^>]*>(.*?)</button>\s*</h2>", re.S)
ITEM_RE = re.compile(r"<li[^>]*>((?:(?!</li>).)*)</li>|<p[^>]*>((?:(?!</p>).)*)</p>", re.S)
QNA_MARK = "QuestionAndAnswer__StyledQuestion"


def extract_items(seg: str) -> list:
    """按文档顺序提取 p/li 文本（li 内嵌 p 时整体吞并，避免重复计数）"""
    items = []
    for m in ITEM_RE.finditer(seg):
        kind = "li" if m.group(1) is not None else "p"
        t = clean(m.group(1) if kind == "li" else m.group(2))
        if t:
            items.append({"k": kind, "t": t})
    return items


def extract_blocks(content: str) -> list:
    """按 h3 切子块 → [{"h": 子节标题(首块空), "items": [{k,t}]}]"""
    h3s = [(m.start(), m.end(), clean(m.group(1)))
           for m in re.finditer(r"<h3[^>]*>(.*?)</h3>", content, re.S)]
    blocks = []
    head = content[:h3s[0][0]] if h3s else content
    if extract_items(head):
        blocks.append({"h": "", "items": extract_items(head)})
    for i, (_, e, t) in enumerate(h3s):
        end = h3s[i + 1][0] if i + 1 < len(h3s) else len(content)
        items = extract_items(content[e:end])
        if items:
            blocks.append({"h": t, "items": items})
    return blocks


def parse_sections(seg: str) -> list:
    """accordion h2 切大节 → [{id,num,h,blocks}]"""
    heads = []
    for m in H2_ACC.finditer(seg):
        texts = [clean(s) for s in re.findall(r"<span[^>]*>(.*?)</span>", m.group(1), re.S)]
        texts = [t for t in texts if t]
        num = next((t.rstrip(".") for t in texts if re.fullmatch(r"\d+\.?", t)), "")
        title = " ".join(t for t in texts if not re.fullmatch(r"\d+\.?", t))
        heads.append({"num": num, "h": title, "pos": m.start(), "end": m.end()})
    out = []
    for i, h in enumerate(heads):
        end = heads[i + 1]["pos"] if i + 1 < len(heads) else len(seg)
        blocks = extract_blocks(seg[h["end"]:end])
        if blocks:
            out.append({"id": f"s{len(out) + 1}", "num": h["num"], "h": h["h"], "blocks": blocks})
    return out


def parse_qna(seg: str) -> list:
    """FAQ：QuestionAndAnswer 容器逐条切分（问题 h2 + 答案区文本）"""
    for anchor in ("The international football association board",
                   "All Rights Reserved", "Download mobile app"):
        p = seg.find(anchor)
        if p != -1:  # 截掉页脚，防最后一题答案吞入页脚文字
            seg = seg[:p]
            break
    out = []
    marks = [m.start() for m in re.finditer(QNA_MARK, seg)]
    for i, s in enumerate(marks):
        chunk = seg[s:marks[i + 1] if i + 1 < len(marks) else len(seg)]
        qm = re.search(r"<h2[^>]*>(.*?)</h2>", chunk, re.S)
        if not qm:
            continue
        q = clean(qm.group(1))
        rest = chunk[qm.end():]
        a = ""
        am = re.search(r"QuestionAndAnswer__StyledAnswer", rest)
        if am:
            gt = rest.find(">", am.end())  # 跳过样式类属性残余，从标签结束后取文本
            a = clean(rest[gt + 1:] if gt != -1 else rest[am.end():])
        if q:
            out.append({"id": f"q{len(out) + 1}", "q": q, "a": a})
    return out


NOISE_RE = re.compile(r"^(en|de|es|fr)$", re.I)
NOISE_TEXT = {"join us!", "key:"}


def _strip_noise(blocks: list, faq: list):
    """配套页尾部噪声：语言码列表 / Join us! / 页脚署名。"""
    for b in blocks:
        b["items"] = [it for it in b["items"]
                      if not NOISE_RE.fullmatch(it["t"]) and it["t"].lower() not in NOISE_TEXT
                      and not it["t"].startswith("The international football association board")]
    for q in faq:
        q["a"] = re.sub(r"\s+(?:en|de|es|fr)(\s+(?:en|de|es|fr))+\s*$", "", q["a"], flags=re.I)
        q["a"] = re.sub(r"\s*Join us!.*$", "", q["a"], flags=re.I)


def parse_extra(page_id: str, url: str, html: str) -> dict:
    """配套协议页：h1 大标题 + h2 页名 + h3 子块（无 accordion），FAQ 容器若在有则解析。"""
    seg = html
    h2m = re.search(r"<h2[^>]*>(.*?)</h2>", seg, re.S)
    h = clean(h2m.group(1)) if h2m else page_id
    start = seg.find("</h2>")
    if start != -1:
        seg = seg[start + 4:]
    for anchor in ("The international football association board",
                   "All Rights Reserved", "Download mobile app"):
        p = seg.find(anchor)
        if p != -1:  # 截掉页脚与侧栏尾部
            seg = seg[:p]
            break
    blocks = extract_blocks(seg)
    faq = parse_qna(seg) if "QuestionAndAnswer__StyledQuestion" in seg else []
    blocks = [b for b in blocks if b["items"]]
    _strip_noise(blocks, faq)
    return {"id": page_id, "url": url, "h": h, "blocks": blocks, "faq": faq}


def parse_all():
    html = fetch_page()
    if not html:
        raise SystemExit("IFAB VAR protocol 页抓取失败（缓存与网络均无结果）")
    h1 = html.find("Video Assistant Referee (VAR) protocol")
    if h1 == -1:
        raise SystemExit("页面结构变化：找不到主标题（解析锚点失效）")
    seg = html[h1:]
    qa_start = seg.find("QuestionAndAnswer__StyledQnAContainer")
    main_seg = seg[:qa_start] if qa_start != -1 else seg
    sections = parse_sections(main_seg)
    faq = parse_qna(seg)
    if not sections or not faq:
        raise SystemExit(f"解析异常：sections={len(sections)} faq={len(faq)}（页面结构可能变化）")
    extras = []
    for page_id, url in EXTRA_PAGES:
        ehtml = fetch_page(url)
        if not ehtml:
            print(f"⚠ 配套页抓取失败，跳过: {page_id}")
            continue
        ex = parse_extra(page_id, url, ehtml)
        if not ex["blocks"]:
            print(f"⚠ 配套页解析为空，跳过: {page_id}")
            continue
        n_it = sum(len(b["items"]) for b in ex["blocks"])
        print(f"  extra {page_id}: 「{ex['h'][:44]}」 {len(ex['blocks'])} 子块 / {n_it} 条 / FAQ {len(ex['faq'])}", flush=True)
        extras.append(ex)
        time.sleep(2.0)
    data = {"source": URL,
            "source_name": "IFAB《Laws of the Game》— Video Assistant Referee (VAR) protocol & FAQs",
            "fetched": time.strftime("%Y-%m-%d"),
            "sections": sections, "faq": faq, "links": LINKS, "extras": extras}
    IFAB_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    n_items = sum(len(b["items"]) for s in sections for b in s["blocks"])
    print(f"parse 完成: {len(sections)} 节 / {sum(len(s['blocks']) for s in sections)} 子节 / "
          f"{n_items} 段条目 / FAQ {len(faq)} 条 → {IFAB_JSON}", flush=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("fetch", "parse", "all"):
        parse_all()
    else:
        raise SystemExit("用法: fetch_ifab.py [fetch|parse|all]")


if __name__ == "__main__":
    main()
