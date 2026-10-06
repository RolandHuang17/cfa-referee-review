# -*- coding: utf-8 -*-
"""抓取西班牙裁判委员会《Criterios Arbitrales》手册 → data/rfef.json
（提交进仓库，build_rfef.py 据此生成 site/rfef.html；视频为同域 mp4 直链，
由 download_rfef_videos.py 单独下载到 site/videos/rfef/，不进 git）

用法: python fetch_rfef.py [fetch|parse|all]   (默认 all)
- fetch: 逐专题抓取官方页面，原始 HTML 缓存 data/local/rfef-cache/（断点续抓）
- parse: 纯本地从缓存解析写 data/rfef.json（可反复调参重跑，不联网）

页面为 WordPress + 自定义插件 manual-arbitral-dinamico 的语义化标记：
- 判例行  <div class="manual-criterion-row"> 内 manual-criterion-code/situation/decision
  （表格型判例：编号 | Situación de juego | Decisión esperada）
- 视频卡  <article class="manual-inline-video-card">：lightbox 链接（base64/转义 JSON 内含
  mp4 直链）+ manual-eyebrow（编号）+ manual-card-copy（说明文字）
- 结构：h2 分节（DESCRIPCIÓN / COMPLEJIDAD INTERPRETATIVA / CRITERIOS GENERALES /
  判例组标题），组内 h3 子节（Mano punible…）与 h4 加重/减轻因素列表
- 越位页无判例行，条目由视频文件名前缀合成（OIO.1.1 → OIO.1），描述取视频卡说明
视频文件名前缀即判例编号，是两种形态共同的锚。
"""
import html as htmllib
import json
import random
import re
import sys
import time

from lib.safe_http import fetch_text

from lib.paths import RFEF_CACHE, RFEF_JSON

BASE = "https://www.card.rfef.es"
INDEX = BASE + "/manual/indice/"
DELAY = (3, 8)          # 页间随机间隔（秒）；WordPress 无已知 tarpit，礼貌节流即可
BACKOFFS = [30, 90]     # 失败退避
MIN_BODY = 20000        # 页面 HTML 最小字节数（WP 外壳本身远大于此，低于即判异常页）

# 判罚专题（slug → 中文栏目名）；protestas/encroachment 为纯文字页无判例，
# 与 glosario 等一样只作 rfef.html 页内「延伸栏目」外链
TOPICS = [
    ("penaltis-por-mano", "手球点球"),
    ("penaltis-disputas-piernas", "腿部争抢点球"),
    ("penaltis-acciones-brazos", "手臂动作点球"),
    ("tarjeta-roja-juego-brusco-grave", "严重犯规红牌"),
    ("tarjeta-roja-conducta-violenta", "暴力行为红牌"),
    ("dogso", "DOGSO 破坏明显进球得分机会"),
    ("infracciones-fase-ataque-app", "进攻阶段犯规（APP）"),
    ("fuera-de-juego", "越位"),
]
# 页内延伸栏目（仅外链，不解析）
EXTRA_TOPICS = [
    ("cambios-reglas", "26/27 规则变动"),
    ("manual-var", "VAR 手册"),
    ("protocolos", "协议"),
    ("glosario", "术语表"),
    ("adelantamiento-tiro-penal-encroachment", "点球提前进入（encroachment）"),
    ("protestas", "抗议（protestas）"),
]
TOPIC_CN = dict(TOPICS)

CLEAN_RE = re.compile(r"<[^>]+>")
CARD_RE = re.compile(r'<article class="manual-inline-video-card">[\s\S]*?</article>')
ROW_SPLIT_RE = re.compile(r'class="manual-criterion-row(?![\w-])')
CELL_MARK = re.compile(r'class="manual-criterion-(code|situation|decision)"[^>]*>')
# 判例表之后的结构标记：末行 decision 格以此截断，防止吞进表后解读/视频区
BOUND_RE = re.compile(r"manual-copy-|manual-inline-videos|<section[\s>]|manual-subheading")
H2_RE = re.compile(r"<h2[^>]*>([\s\S]*?)</h2>")
H234_RE = re.compile(r"<h([1-4])[^>]*>([\s\S]*?)</h\1>")
P_RE = re.compile(r"<p[^>]*>([\s\S]*?)</p>", re.I)
LI_RE = re.compile(r"<li[^>]*>([\s\S]*?)</li>", re.I)
MP4_RE = re.compile(r"(https://www\.card\.rfef\.es[^\s\"'<>]+\.mp4)", re.I)
# 结构性标题（不作为判例组名）
STRUCT_H = re.compile(r"(?i)v[ií]deos asociados|[ií]ndice del tema|elementos agravantes|"
                      r"elementos atenuantes|v[ií]deos?")
SEC_INTRO = re.compile(r"(?i)descripci")
SEC_COMPLEX = re.compile(r"(?i)complejidad")
SEC_GENERAL = re.compile(r"(?i)criterios generales")

# 认定归一化（顺序敏感：先长串后短串；未命中回退 other，decision_es 原文保留）
DECISION_RULES = [
    (r"penalti\s+y\s+tarjeta\s+roja", "penalty_red"),
    (r"penalti\s+y\s+tarjeta\s+amarilla", "penalty_yellow"),
    (r"penalti\s+sin\s+tarjeta", "penalty_no_card"),
    (r"^penalti$", "penalty"),
    (r"no\s+penalti", "no_penalty"),
    (r"falta\s+en\s+ataque", "attacking_foul"),
    (r"tiro\s+libre\s+directo", "dfk"),
    (r"tiro\s+libre\s+indirecto", "ifk"),
    (r"tarjeta\s+roja", "red_card"),
    (r"tarjeta\s+amarilla", "yellow_card"),
    (r"sin\s+tarjeta", "no_card"),
    (r"sin\s+sanci[oó]n|no\s+hay\s+sanci[oó]n|no\s+sanci[oó]n", "no_sanction"),
    (r"no\s+infracci[oó]n", "no_infringement"),
    (r"^gol\b", "goal_valid"),
    (r"repetici[oó]n", "retake"),
    (r"fuera\s+de\s+juego", "offside_on"),
    (r"no\s+fuera\s+de\s+juego|permite\s+continuar|se\s+anula", "offside_off"),
    (r"penalti", "penalty"),
]
# 越位页无认定字段：按组码赋认定语义（OIO/OGA=越位犯规，NOIO/NOGA=不越位）
OFFSIDE_ON_CODES = {"OIO", "OGA"}
OFFSIDE_OFF_CODES = {"NOIO", "NOGA"}

# 已知认定短语（长前缀优先）：末行 decision 格偶有吞并表内判读注记，按前缀切开
KNOWN_DECISIONS = [
    "Tiro libre indirecto y tarjeta amarilla", "Penalti y tarjeta roja",
    "Penalti y tarjeta amarilla", "Penalti sin tarjeta", "Tiro libre indirecto",
    "Tiro libre directo", "No penalti", "Tarjeta roja", "Tarjeta amarilla",
    "No infracción", "Sin tarjeta", "Repetición", "Penalti", "Gol",
]


def split_decision(dec: str) -> tuple:
    for k in sorted(KNOWN_DECISIONS, key=len, reverse=True):
        if dec.startswith(k):
            return k, dec[len(k):].strip()
    return dec, ""


def clean(text: str) -> str:
    return htmllib.unescape(re.sub(r"\s+", " ", CLEAN_RE.sub(" ", text))).strip()


def norm_decision(es: str) -> str:
    t = re.sub(r"\s+", " ", es or "").strip().lower()
    if not t:
        return "other"
    for pat, norm in DECISION_RULES:
        if re.search(pat, t):
            return norm
    return "other"


def topic_url(slug: str) -> str:
    return f"{BASE}/manual/{slug}/"


def fetch_page(url: str) -> str:
    """带退避的抓取；缓存命中直接返回。失败返回 ''（重跑续传）。"""
    slug = url.rstrip("/").rsplit("/", 1)[-1] or "indice"
    cache_f = RFEF_CACHE / f"{slug}.html"
    RFEF_CACHE.mkdir(parents=True, exist_ok=True)
    if cache_f.exists() and cache_f.stat().st_size > MIN_BODY:
        print(f"缓存命中: {cache_f.name}", flush=True)
        return cache_f.read_text(encoding="utf-8", errors="replace")
    for i, wait in enumerate([0] + BACKOFFS):
        if wait:
            print(f"  失败，退避 {wait}s 后第 {i} 次重试…", flush=True)
            time.sleep(wait)
        try:
            st, txt = fetch_text(url, timeout=45, retries=2)
            if st == 200 and len(txt) > MIN_BODY:
                cache_f.write_text(txt, encoding="utf-8")
                print(f"  已缓存 {len(txt)//1024}KB → {cache_f.name}", flush=True)
                return txt
            print(f"  HTTP {st}, {len(txt)}B", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  请求异常: {e}", flush=True)
    print(f"  抓取失败（重跑本脚本可续）: {url}", flush=True)
    return ""


def fetch_all():
    ok = 0
    for i, (slug, _cn) in enumerate(TOPICS):
        url = topic_url(slug)
        print(f"[{i+1}/{len(TOPICS)}] {url}", flush=True)
        if fetch_page(url):
            ok += 1
        if i < len(TOPICS) - 1:
            time.sleep(random.uniform(*DELAY))
    print(f"fetch 完成: {ok}/{len(TOPICS)} 专题已缓存", flush=True)


# ---------------- 解析 ----------------

def _norm_url(raw: str) -> str:
    url = htmllib.unescape(raw).replace("\\/", "/")
    url = re.sub(r"^http://", "https://", url).strip()
    return url if url.lower().startswith("https://www.card.rfef.es/") else ""


def parse_video_cards(page: str) -> list:
    """视频卡 → [{pos, id, url, caption_es}]（按文档序，URL 去重）。"""
    out = []
    for m in CARD_RE.finditer(page):
        card = m.group(0)
        vid = ""
        am = re.search(r'aria-label="Reproducir ([^"]+)"', card)
        if am:
            vid = clean(am.group(1))
        url = ""
        um = re.search(r'url(&quot;|")\s*:\s*(&quot;|")\s*([^"&]+)', card)
        if um:
            url = _norm_url(um.group(3))
        if not url:
            bm = re.search(r'(https?://[^"\s<>]+\.mp4)', htmllib.unescape(card))
            url = _norm_url(bm.group(1)) if bm else ""
        if not url:
            continue
        cap = ""
        cm = re.search(r'manual-card-copy">\s*<p[^>]*>([\s\S]*?)</p>', card)
        if cm:
            cap = clean(cm.group(1))
        if not vid:  # 兜底：从 URL 文件名取
            vid = url.rsplit("/", 1)[-1][:-4]
        out.append({"_pos": m.start(), "id": vid, "url": url, "caption_es": cap})
    # 去重（同 URL 保留首现）
    seen, uniq = set(), []
    for v in out:
        if v["url"].lower() not in seen:
            seen.add(v["url"].lower())
            uniq.append(v)
    return uniq


def parse_rows(page: str) -> list:
    """判例行 → [{pos, id, situation_es, decision_es}]。

    行内三格以 manual-criterion-* 标记切分：格文本 = 本标记结束 → 下一标记开始，
    clean() 会剥掉中间的闭合/开启标签。表头行（code 空 / Situación 占位）跳过。
    """
    positions = [m.start() for m in ROW_SPLIT_RE.finditer(page)]
    rows = []
    for i, pos in enumerate(positions):
        seg = page[pos: positions[i + 1] if i + 1 < len(positions) else pos + 9000]
        marks = [(m.group(1), m.end()) for m in CELL_MARK.finditer(seg)]
        if len(marks) < 3:
            continue
        cells = {}
        for j, (cls, start) in enumerate(marks):
            end = marks[j + 1][1] if j + 1 < len(marks) else len(seg)
            b = BOUND_RE.search(seg, start, end)
            if b:
                end = b.start()
            # 从下一标记的 class 属性头回退到其所属开标签起点，避免把标签残留算进文本
            back = seg.rfind("<div", start, end)
            cells[cls] = clean(seg[start: back if back > start else end])
        code, sit = cells.get("code", ""), cells.get("situation", "")
        if not code or not sit or sit.startswith("Situación"):
            continue
        rows.append({"_pos": pos, "id": code, "situation_es": sit,
                     "decision_es": cells.get("decision", "")})
    return rows


def parse_sections(page: str) -> dict:
    """h2 分节文本：intro_es / complexity_es / general_es（各截 2000 字，含列表项）。"""
    hs = [(m.start(), clean(m.group(1))) for m in H2_RE.finditer(page)]
    out = {}
    for i, (pos, name) in enumerate(hs):
        end = hs[i + 1][0] if i + 1 < len(hs) else len(page)
        chunk = page[pos:end]
        paras = [clean(p) for p in P_RE.findall(chunk)] + \
                [clean(p) for p in LI_RE.findall(chunk)]
        paras = [p for p in paras if len(p) > 40]
        key = None
        if SEC_INTRO.search(name):
            key = "intro_es"
        elif SEC_COMPLEX.search(name):
            key = "complexity_es"
        elif SEC_GENERAL.search(name):
            key = "general_es"
        if key and not out.get(key):
            out[key] = " ".join(paras)[:2000]
    return out


def parse_page(page: str, slug: str) -> dict:
    hs = list(H2_RE.finditer(page))
    h2s = [(m.start(), clean(m.group(1))) for m in hs
           if clean(m.group(1)) and not STRUCT_H.search(clean(m.group(1)))]
    h234 = [(m.start(), m.group(1), clean(m.group(2))) for m in H234_RE.finditer(page)]
    rows = parse_rows(page)
    vids = parse_video_cards(page)

    def nearest_h2(pos: int):
        name, h2pos = "", -1
        for hpos, hname in h2s:
            if hpos < pos:
                name, h2pos = hname, hpos
            else:
                break
        return name, h2pos

    def item_extras(pos: int) -> dict:
        """条目所在 h3 子节名与 h4 加重/减轻因素列表（若有）；h1/h2 重置。"""
        sub, note = "", ""
        for hpos, lvl, hname in h234:
            if hpos >= pos:
                break
            if lvl in ("1", "2"):
                sub, note = "", ""
            elif lvl == "3" and not STRUCT_H.search(hname):
                sub, note = hname, ""
            elif lvl == "4" and sub:
                end = next((p for p, l, n in h234 if p > hpos), pos)
                if end > pos:
                    end = pos
                chunk = page[hpos:end]
                bullets = [clean(x) for x in LI_RE.findall(chunk)] + \
                          [clean(x) for x in P_RE.findall(chunk)]
                bullets = [b for b in bullets if len(b) > 8]
                if bullets:
                    note = "；".join(bullets)[:1200]
        return {"sub_es": sub, "note_es": note}

    # 判例行装配
    items, by_id = [], {}
    for r in rows:
        it = {"id": r["id"], "situation_es": r["situation_es"],
              "decision_es": r["decision_es"], "_pos": r["_pos"],
              **item_extras(r["_pos"])}
        items.append(it)
        by_id[r["id"]] = it
    # 视频装配：前缀锚定到判例；无判例行的（越位型）由卡片合成条目
    for v in vids:
        base = re.sub(r"\.\d+$", "", v["id"]) if re.match(
            r"^[A-ZÑÁÉÍÓÚÜ]{1,8}\.\d+\.\d+$", v["id"]) else v["id"]
        it = by_id.get(base)
        if it is None:
            desc = re.sub(r"^[A-ZÑÁÉÍÓÚÜ]{1,8}\.\d+(\.\d+)?\s*[:：]\s*", "",
                          v["caption_es"]).strip()
            it = {"id": base, "situation_es": desc, "decision_es": "",
                  "_pos": v["_pos"], **item_extras(v["_pos"])}
            items.append(it)
            by_id[base] = it
        it.setdefault("videos", []).append(
            {"url": v["url"], "id": v["id"], "caption_es": v["caption_es"]})
    # 文件名冲突兜底（同 stem 异路径）→ 加父目录名前缀
    used = {}
    for it in items:
        for v in it.get("videos", []):
            stem = v["url"].rsplit("/", 1)[-1][:-4]
            if stem in used and used[stem] != v["url"]:
                stem = v["url"].split("/uploads/")[-1].replace("/", "-")[:-4]
            used[stem] = v["url"]
            v["file"] = f"videos/rfef/{stem}.mp4"
            v["decision_norm"] = ""
    for it in items:
        head, rest = split_decision(it.get("decision_es", ""))
        if rest:
            it["decision_es"] = head
            it["decision_extra_es"] = rest
        it["decision_norm"] = norm_decision(it.get("decision_es", ""))
    items.sort(key=lambda x: x["_pos"])
    for it in items:
        (it.get("videos") or []).sort(key=lambda v: v["id"])
    # 分组：code = 编号首段，组名取条目前最近的非结构 h2
    groups, order = [], {}
    for it in items:
        code = it["id"].split(".")[0]
        if code not in order:
            gname, gh2pos = nearest_h2(it["_pos"])
            order[code] = len(groups)
            groups.append({"code": code, "name_es": gname or code,
                           "_h2pos": gh2pos, "items": []})
        groups[order[code]]["items"].append(it)
    # 组级判读注记：组 h2 与下一 h2 之间的 h3/h4 分节
    # （如 Mano punible / no punible 与 Elementos agravantes / atenuantes 列表），
    # 以及表后的判读总结段落（manual-copy-text conclusion）
    h2_all = [(m.start(), clean(m.group(1))) for m in H2_RE.finditer(page)]
    for g in groups:
        lo = g.pop("_h2pos")
        hi = next((p for p, _ in h2_all if p > lo), len(page))
        notes, cur = [], None
        conclusions = []
        for m in re.finditer(r'class="manual-copy-text[^"]*"[^>]*>', page[lo:hi]):
            start = lo + m.end()
            nxt = re.search(r'manual-copy-|manual-inline-videos|<section[\s>]|'
                            r'manual-subheading|<h[1-6][\s>]', page[start:hi])
            chunk = page[start: hi if not nxt else start + nxt.start()]
            paras = [clean(x) for x in P_RE.findall(chunk)] + \
                    [clean(x) for x in LI_RE.findall(chunk)]
            paras = [p for p in paras if len(p) > 40]
            if paras:
                conclusions.append(" ".join(paras)[:3000])
        for hpos, lvl, hname in h234:
            if not (lo < hpos < hi):
                continue
            nxt = next((p for p, l, n in h234 if p > hpos), hi)
            chunk = page[hpos: min(nxt, hi)]
            bullets = [clean(x) for x in LI_RE.findall(chunk)] + \
                      [clean(x) for x in P_RE.findall(chunk)]
            bullets = [b for b in bullets if len(b) > 8]
            if lvl == "3":
                cur = None
                if not STRUCT_H.search(hname):
                    cur = {"h": hname, "items": bullets[:10]}
                    notes.append(cur)
            elif lvl == "4" and cur is not None:
                tail = ("：" + "；".join(bullets)[:900]) if bullets else ""
                cur["items"].append((hname + tail)[:1000])
        if notes:
            g["notes_es"] = notes
        if conclusions:
            g["conclusion_es"] = " ".join(conclusions)[:3500]
    for it in items:
        code = it["id"].split(".")[0]
        if not it.get("decision_es"):
            if code in OFFSIDE_ON_CODES:
                it["decision_norm"] = "offside_on"
            elif code in OFFSIDE_OFF_CODES:
                it["decision_norm"] = "offside_off"
    for it in items:
        it.pop("_pos", None)
    sec = parse_sections(page)
    h1 = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", page, re.I)
    return {"key": slug, "name_es": clean(h1.group(1)) if h1 else slug.replace("-", " "),
            "name_cn": TOPIC_CN.get(slug, slug), "url": topic_url(slug),
            "intro_es": sec.get("intro_es", ""),
            "complexity_es": sec.get("complexity_es", ""),
            "general_es": sec.get("general_es", ""),
            "groups": groups}


def parse_all():
    sections = []
    for slug, _cn in TOPICS:
        cache_f = RFEF_CACHE / f"{slug}.html"
        if not cache_f.exists():
            print(f"⚠ 缓存缺失，跳过: {slug}", flush=True)
            continue
        page = cache_f.read_text(encoding="utf-8", errors="replace")
        sec = parse_page(page, slug)
        n_it = sum(len(g["items"]) for g in sec["groups"])
        n_vid = sum(len(it.get("videos", [])) for g in sec["groups"] for it in g["items"])
        print(f"{slug}: {len(sec['groups'])} 组 / {n_it} 例 / {n_vid} 视频", flush=True)
        if n_it:
            sections.append(sec)
        else:
            print(f"⚠ 无判例，检查解析: {slug}", flush=True)
    data = {"source": INDEX, "source_name": "RFEF/CTA《Criterios Arbitrales》判罚标准手册",
            "season": "2026/27", "fetched": time.strftime("%Y-%m-%d"),
            "extra_topics": [{"key": k, "name_cn": cn, "url": topic_url(k)}
                             for k, cn in EXTRA_TOPICS],
            "sections": sections}
    RFEF_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(len(g["items"]) for s in sections for g in s["groups"])
    v = sum(len(it.get("videos", [])) for s in sections
            for g in s["groups"] for it in g["items"])
    print(f"parse 完成: {len(sections)} 栏目 / {n} 例 / {v} 视频 → {RFEF_JSON}", flush=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("fetch", "all"):
        fetch_all()
    if mode in ("parse", "all"):
        parse_all()


if __name__ == "__main__":
    main()
