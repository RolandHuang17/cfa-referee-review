# -*- coding: utf-8 -*-
"""补充人工目录中缺失的队徽，候选图必须来自明确的 Wikimedia 页面。"""
import json
import re
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safe_http as S

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "teams.json"
OUT = ROOT / "assets" / "crests"
S.ALLOWED_HOSTS |= {"zh.wikipedia.org", "upload.wikimedia.org", "commons.wikimedia.org", "thumb.wikimedia.org"}
PREFER = re.compile(r"logo|crest|队徽|徽标|shield|football.?club|\.fc\b|\.f\.c", re.I)
NOISE = re.compile(r"flag|kit|stadium|map|icon|commons|wikimedia|nike|adidas|ball|sponsor", re.I)


def api(params):
    query = "&".join(f"{k}={S.safe_urlencode(v)}" for k, v in params.items())
    status, text = S.fetch_text(f"https://zh.wikipedia.org/w/api.php?{query}", timeout=8, retries=0)
    if status != 200 or not text.startswith("{"):
        raise RuntimeError(f"Wikipedia API {status}")
    return json.loads(text)


def candidate(team):
    data = api({"action": "query", "format": "json", "prop": "images", "imlimit": "200",
                "generator": "search", "gsrlimit": "5", "gsrsearch": team + " 足球俱乐部"})
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 999))
    choices = []
    for page in pages:
        for image in page.get("images", []):
            title = image.get("title", "")
            if NOISE.search(title) or not PREFER.search(title):
                continue
            score = 4 if re.search(r"logo|crest|队徽", title, re.I) else 2
            if team[:2] in title:
                score += 1
            choices.append((score, title, page.get("title", "")))
    if not choices:
        return None
    return sorted(choices, reverse=True)[0]


def image_url(title):
    data = api({"action": "query", "format": "json", "titles": title,
                "prop": "imageinfo", "iiprop": "url", "iiurlwidth": "240"})
    for page in data.get("query", {}).get("pages", {}).values():
        info = page.get("imageinfo", [{}])[0]
        return info.get("thumburl") or info.get("url")
    return None


def main():
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    updated = 0
    for item in payload["teams"].values():
        if item.get("status") == "verified":
            continue
        existing = OUT / f"{item['slug']}.png"
        if existing.exists() and existing.stat().st_size > 1500:
            item.update({"path": f"assets/crests/{existing.name}", "status": "verified",
                         "source_url": f"https://zh.wikipedia.org/wiki/{S.safe_urlencode(item['name'])}",
                         "source_type": "wikipedia-image"})
            print(f"OK {item['name']} <- existing downloaded image")
            CATALOG.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            continue
        try:
            picked = candidate(item["name"])
            if not picked:
                print(f"SKIP {item['name']}: no explicit crest candidate")
                continue
            url = image_url(picked[1])
            if not url or not url.startswith("https://"):
                continue
            filename = f"{item['slug']}.png"
            dest = OUT / filename
            _, size = S.download(url, dest, timeout=20, retries=1)
            if size < 1500:
                dest.unlink(missing_ok=True)
                continue
            item.update({"path": f"assets/crests/{filename}", "status": "verified",
                         "source_url": f"https://zh.wikipedia.org/wiki/{S.safe_urlencode(picked[2])}",
                         "source_type": "wikipedia-image"})
            updated += 1
            print(f"OK {item['name']} <- {picked[1]}")
        except Exception as exc:  # 网络波动只跳过当前队伍
            print(f"SKIP {item['name']}: {exc}")
        CATALOG.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(.1)
    CATALOG.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"在线补充完成: 新增 {updated} 个队徽")


if __name__ == "__main__":
    main()
