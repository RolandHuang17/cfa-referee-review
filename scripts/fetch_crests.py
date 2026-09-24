# -*- coding: utf-8 -*-
"""采集男子中超/中甲/中乙球队真实队徽 -> assets/crests/<slug>.png + data/crests.json
来源: zh.wikipedia.org 词条图片列表, 评分挑队徽文件, 经 imageinfo 取240px缩略图
安全: https + 域名白名单 + DoH解析公网IP校验 + IP钉扎 (复用 safe_http)
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safe_http as S

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "crests"
S.ALLOWED_HOSTS |= {"zh.wikipedia.org", "commons.wikimedia.org",
                    "upload.wikimedia.org", "thumb.wikimedia.org"}

TEAMS = {
    # 中超
    "上海申花": ("shenhua", "上海申花足球俱乐部"),
    "长春亚泰": ("changchun-yatai", "长春亚泰足球俱乐部"),
    "成都蓉城": ("chengdu-rongcheng", "成都蓉城足球俱乐部"),
    "天津津门虎": ("tianjin-jinmenhu", "天津津门虎足球俱乐部"),
    "深圳新鹏城": ("shenzhen-xinpengcheng", "深圳新鹏城足球俱乐部"),
    "武汉三镇": ("wuhan-sanzhen", "武汉三镇足球俱乐部"),
    "青岛西海岸": ("qingdao-xihaian", "青岛西海岸足球俱乐部"),
    "上海海港": ("shanghai-haigang", "上海海港足球俱乐部"),
    "大连英博": ("dalian-yingbo", "大连英博足球俱乐部"),
    "山东泰山": ("shandong-taishan", "山东泰山足球俱乐部"),
    "云南玉昆": ("yunnan-yukun", "云南玉昆足球俱乐部"),
    "河南俱乐部": ("henan", "河南足球俱乐部"),
    "北京国安": ("beijing-guoan", "北京国安足球俱乐部"),
    "青岛海牛": ("qingdao-hainiu", "青岛海牛足球俱乐部"),
    "梅州客家": ("meizhou-kejia", "梅州客家足球俱乐部"),
    "浙江俱乐部绿城": ("zhejiang-greentown", "浙江职业足球俱乐部"),
    # 中甲
    "南通支云": ("nantong-zhiyun", "南通支云足球俱乐部"),
    "南京城市": ("nanjing-chengshi", "南京城市足球俱乐部"),
    "广西平果": ("guangxi-pingguo", "广西平果足球俱乐部"),
    "上海嘉定汇龙": ("jiading-huilong", "上海嘉定汇龙足球俱乐部"),
    "定南赣联": ("dingnan-ganlian", "定南赣联足球俱乐部"),
    "石家庄功夫": ("shijiazhuang-gongfu", "石家庄功夫足球俱乐部"),
    "苏州东吴": ("suzhou-dongwu", "苏州东吴足球俱乐部"),
    "广东广州豹": ("guangzhou-bao", "广东广州豹足球俱乐部"),
    "深圳青年人": ("shenzhen-qingnianren", "深圳青年人足球俱乐部"),
    "佛山南狮": ("foshan-nanshi", "佛山南狮足球俱乐部"),
    "大连鲲城": ("dalian-kuncheng", "大连鲲城足球俱乐部"),
    "重庆铜梁龙": ("chongqing-tonglianglong", "重庆铜梁龙足球俱乐部"),
    "辽宁铁人": ("liaoning-tieren", "辽宁铁人足球俱乐部"),
    "陕西联合": ("shaanxi-lianhe", "陕西联合足球俱乐部"),
    "延边龙鼎": ("yanbian-longding", "延边龙鼎足球俱乐部"),
    # 中乙
    "广东铭途": ("guangdong-mingtu", "广东铭途足球俱乐部"),
    "广西恒宸": ("guangxi-hengchen", "广西恒宸足球俱乐部"),
    "赣州瑞狮": ("ganzhou-ruishi", "赣州瑞狮足球俱乐部"),
    "无锡吴钩": ("wuxi-wugou", "无锡吴钩足球俱乐部"),
    "杭州临平吴越": ("hangzhou-linpingwuyue", "杭州临平吴越足球俱乐部"),
    "湖北青年星": ("hubei-qingnianxing", "湖北青年星足球俱乐部"),
    "山西崇德荣海": ("shanxi-chongde", "山西崇德荣海足球俱乐部"),
    "昆明城星": ("kunming-chengxing", "昆明城星足球俱乐部"),
    "温州俱乐部": ("wenzhou", "温州俱乐部中胤"),
    "兰州陇原竞技": ("lanzhou-longyuan", "兰州陇原竞技足球俱乐部"),
    "贵州筑城竞技": ("guizhou-zhucheng", "贵州筑城竞技足球俱乐部"),
    "江西庐山": ("jiangxi-lushan", "江西庐山足球俱乐部"),
    "长春喜都": ("changchun-xidu", "长春喜都足球俱乐部"),
    "广州蒲公英": ("guangzhou-pugongying", "广州蒲公英足球俱乐部"),
    "泰安天贶": ("taian-tiankuang", "泰安天贶足球俱乐部"),
    "海门珂缔缘": ("haimen-kedi", "海门珂缔缘足球俱乐部"),
    "深圳二零二八": ("shenzhen-2028", "深圳二零二八足球俱乐部"),
    "北京理工": ("beijing-ligong", "北京理工足球俱乐部"),
    "广西蓝航": ("guangxi-lanhang", "广西蓝航足球俱乐部"),
    "泉州亚新": ("quanzhou-yaxin", "泉州亚新足球俱乐部"),
}

# 人工兜底: 维基无队徽的队 -> 直接图片URL（逐队人工核实后填写）
MANUAL_URL = {}

# 人工指定: 词条内挑错的队 -> 正确的维基文件标题（键=采集关键词）
MANUAL_FILE = {
    "大连英博足球俱乐部": "File:Dalian Yingbo F.C.svg",
    "长春亚泰足球俱乐部": "File:ChangchunYataiFC03.png",
}

# 已知页面上会误采到的他队/无关文件（评分时直接排除）
BLOCK_FILES = re.compile(r"Wikinews-logo|Adidas Logo|Heilongjiang Lava Spring|"
                         r"Guangzhou City FC logo|Question book-new|Yingbo", re.I)

# 维基上确认无法取到正确队徽的队（跳过采集，页面用首字占位）
NO_WIKI_CREST = {"大连鲲城", "广东广州豹"}

B_TEAM_MAP = {
    "山东泰山B队": "山东泰山",
    "成都蓉城B队": "成都蓉城",
    "武汉三镇B队": "武汉三镇",
    "上海海港富盛经开": "上海海港",
}

NAME_VARIANTS = {
    "河南俱乐部酒祖杜康": "河南俱乐部",
    "河南酒祖杜康": "河南俱乐部",
    "浙江俱乐部": "浙江俱乐部绿城",
    "陕西联合月亮泊": "陕西联合",
    "广西平果国晶": "广西平果",
    "大连英博海发": "大连英博",
    "温州俱乐部中胤": "温州俱乐部",
}

NOISE = re.compile(r"flag|kit[ _-]|conversion|icon|portal|soccer.?ball|cruz roja"
                   r"|commons|wikimedia|wiki |arrow|\.jpg$|\.jpeg$|hengchen"
                   r"|wikivoyage|nike|yunnan yukun|r&f|guangzhou city fc", re.I)
PREFER = re.compile(r"logo|队徽|徽|crest|shield|俱乐部|\.fc\.|fc\.|f\.c\.|football club", re.I)


def api(params):
    qs = "&".join(f"{k}={S.safe_urlencode(v)}" for k, v in params.items())
    status, text = S.fetch_text(f"https://zh.wikipedia.org/w/api.php?{qs}",
                                timeout=25, retries=2)
    if status != 200 or not text.strip().startswith("{"):
        raise RuntimeError(f"API响应异常 status={status} head={text[:60]!r}")
    return json.loads(text)


def pick_crest_file(images):
    titles = [im.get("title") if isinstance(im, dict) else im for im in images or []]
    best, best_score = None, -1
    for im in titles:
        low = im.lower()
        if NOISE.search(low) or BLOCK_FILES.search(low):
            continue
        score = 0
        if PREFER.search(im):
            score = 2
            if re.search(r"logo|队徽|crest", low):
                score = 3
        # 分数<2的弱候选(纯扩展名匹配, 常是地图钉/模板图)不接受
        if score > best_score and score >= 2:
            best, best_score = im, score
    return best


def crest_thumb_url(file_title):
    d = api({"action": "query", "format": "json", "titles": file_title,
             "prop": "imageinfo", "iiprop": "url", "iiurlwidth": "240"})
    for pp in d.get("query", {}).get("pages", {}).values():
        if "missing" in pp:
            return None
        ii = pp.get("imageinfo", [{}])[0]
        return ii.get("thumburl") or ii.get("url")
    return None


def fetch_crest(slug, keyword):
    d = api({"action": "query", "format": "json", "prop": "images", "imlimit": "500",
             "redirects": "1", "generator": "search", "gsrlimit": "3",
             "gsrsearch": keyword})
    pages = d.get("query", {}).get("pages", {})
    if not pages:
        return False, "词条未找到"
    # 搜索排序会波动，取前3个词条中第一个能挑出队徽的
    pages_sorted = sorted(pages.values(), key=lambda x: x.get("index", 99))
    file_title, last_msg = None, "词条无队徽候选图"
    if name_override := MANUAL_FILE.get(keyword) or MANUAL_FILE.get(
            next(iter(pages_sorted), {}).get("title", "")):
        file_title = name_override
    else:
        for p in pages_sorted:
            file_title = pick_crest_file(p.get("images"))
            if file_title:
                break
            last_msg = f"词条[{p.get('title')}]无队徽候选图"
    if not file_title:
        return False, last_msg
    thumb = crest_thumb_url(file_title)
    if not thumb:
        return False, f"缩略图解析失败: {file_title}"
    if not thumb.lower().startswith("https://"):
        return False, f"非https缩略图: {thumb[:60]}"
    dest = OUT_DIR / f"{slug}.png"
    _, size = S.download(thumb, dest, timeout=60, retries=3)
    if size < 1000:
        dest.unlink(missing_ok=True)
        return False, "下载内容过小"
    return True, f"{file_title}"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manual_url = json.loads((ROOT / "data" / "crest_manual.json").read_text(encoding="utf-8")) \
        if (ROOT / "data" / "crest_manual.json").exists() else {}
    crests, fail = {}, []
    for name, (slug, kw) in TEAMS.items():
        dest = OUT_DIR / f"{slug}.png"
        if name in NO_WIKI_CREST:
            dest.unlink(missing_ok=True)
            print(f"  跳过 {name}（维基无正确队徽，用首字占位）")
            continue
        if dest.exists() and dest.stat().st_size > 1000:
            crests[name] = f"assets/crests/{slug}.png"
            print(f"  已有 {name}")
            continue
        ok, msg = False, ""
        for attempt in range(3):
            try:
                ok, msg = fetch_crest(slug, kw)
                break
            except Exception as e:  # noqa: BLE001 - 限流/网络错误退避重试
                msg = f"异常: {e}"
                time.sleep(8 * (attempt + 1))
        if not ok and name in manual_url:
            try:
                _, size = S.download(manual_url[name], dest, timeout=60, retries=3)
                ok, msg = size > 1000, "manual url"
            except Exception as e:  # noqa: BLE001
                msg = f"manual异常: {e}"
        if ok:
            crests[name] = f"assets/crests/{slug}.png"
            print(f"  OK {name} ({msg})")
        else:
            fail.append(name)
            print(f"  FAIL {name}: {msg}")
        time.sleep(1.0)
    for bt, parent in B_TEAM_MAP.items():
        if parent in crests:
            crests[bt] = crests[parent]
    (ROOT / "data" / "crests.json").write_text(
        json.dumps(crests, ensure_ascii=False, indent=1), encoding="utf-8")
    # 清理孤儿: 删除不在映射中的历史文件
    used = {Path(f).name for f in crests.values()}
    for p in OUT_DIR.glob("*.png"):
        if p.name not in used:
            p.unlink()
            print(f"  清理孤儿文件 {p.name}")
    print(f"\n完成: {len(crests)}队有队徽, 失败{len(fail)}: {fail}")


if __name__ == "__main__":
    main()
