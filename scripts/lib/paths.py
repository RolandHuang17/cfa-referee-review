# -*- coding: utf-8 -*-
"""仓库路径常量的唯一权威源。

任何脚本需要定位仓库内的目录或共享数据文件时，从这里 import，不要再自己拼
`Path(__file__).resolve().parent.parent`——那正是本模块要消灭的 25 份拷贝。

调用方式无关：CPython 把**脚本自身所在目录**（不是 cwd）放进 sys.path[0]，
所以 `python scripts/foo.py`（cwd=仓库根）与 `cd scripts && python foo.py`
都会得到 sys.path[0] = <repo>/scripts，`from lib.paths import ...` 两式皆通。
唯一例外是 `python -m scripts.foo`（sys.path[0] 变成仓库根，lib 解析不到），
但仓库内无人这样调用，CI 用的是 `python scripts/build_all.py`。

命名禁令：本模块**不得**出现叫 OUT 或 BASE 的常量。OUT 在四个脚本里指四个
不同的东西（laws.json / IFAB PDF / assets/crests ×2），BASE 在三个脚本里永远
是 URL 而非路径。把这类名字收拢进来等于把要消灭的歧义重新造一遍。
单脚本私有的输出路径（各自的 OUT_JSON、LOG、VID_DIR 等）同理不收拢。
"""
from pathlib import Path

# scripts/lib/paths.py -> parents[0]=scripts/lib, [1]=scripts, [2]=仓库根
ROOT = Path(__file__).resolve().parents[2]

SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
THEME_CSS = SRC / "theme.css"

# GitHub Pages 发布根（.github/workflows/pages.yml 的 path: site）。
# 必须自包含：CSS/JS/数据全部内联，页面运行时零外部依赖。
SITE = ROOT / "site"
SITE_ASSETS = SITE / "assets"
SITE_VIDEOS = SITE / "videos"

# "assets/crests/" 这个前缀被写死在 data/teams.json 与完整性断言里，改不得。
ASSETS = ROOT / "assets"
CRESTS_DIR = ASSETS / "crests"
# build_all 每次整目录重建 site/assets，尺度海报必须落在根 assets/ 才不会被冲掉。
SCALE_POSTERS = ASSETS / "scale"
RULES_IMG_DIR = ASSETS / "rules"

DATA = ROOT / "data"
TEAMS_JSON = DATA / "teams.json"
CRESTS_JSON = DATA / "crests.json"
CREST_OVERRIDES_JSON = DATA / "crest_overrides.json"
LAWS_JSON = DATA / "laws.json"
SCALE_JSON = DATA / "scale.json"
UEFA_JSON = DATA / "uefa.json"
RAP_JSON = DATA / "rap.json"            # UEFA RAP 各期索引（人工策展+脚本核对）
RFEF_JSON = DATA / "rfef.json"          # RFEF《Criterios Arbitrales》（fetch_rfef.py 产物）
RFEF_ZH_JSON = DATA / "rfef-zh.json"    # RFEF 中文译文层（与 RFEF_JSON 并存，勿互相覆写）
PRO_JSON = DATA / "pro.json"            # 美国 PRO 评议周报索引（fetch_pro.py 产物）
INTL_JSON = DATA / "intl.json"          # 全球评议资源导航（人工策展）
CONMEBOL_JSON = DATA / "conmebol.json"  # 南美足联 VAR 逐案判例（fetch_conmebol.py 产物）
WEEKLY_JSON = DATA / "weekly.json"      # 全球周更评议节目判例索引（fetch_weekly.py 产物）
WEEKLY_ZH_JSON = DATA / "weekly-zh.json"  # weekly 中文译注层（与 WEEKLY_JSON 并存，勿互相覆写）
IFAB_JSON = DATA / "ifab.json"          # IFAB VAR 协议/统一尺度材料（fetch_ifab.py 产物）
IFAB_ZH_JSON = DATA / "ifab-zh.json"    # IFAB 中文译文层（与 IFAB_JSON 并存，勿互相覆写）
ISSUES = DATA / "issues"

# 本机专用：原始材料、抓取缓存、截图、日志。整个 data/local/ 被 git 忽略，
# clone 下来是空的——凡往这里写文件的脚本都必须自己 mkdir(parents=True)。
LOCAL = DATA / "local"
LOCAL_LOGS = LOCAL / "logs"
SHOTS = LOCAL / "shots"
IFAB_PDF = LOCAL / "laws" / "lotg-202627-tc-single.pdf"
UEFA_CACHE = LOCAL / "uefa-cache"
RFEF_CACHE = LOCAL / "rfef-cache"
DUTCHREF_CACHE = LOCAL / "dutchref-cache"
PRO_CACHE = LOCAL / "pro-cache"
CONMEBOL_CACHE = LOCAL / "conmebol-cache"
WEEKLY_CACHE = LOCAL / "weekly-cache"
IFAB_CACHE = LOCAL / "ifab-cache"
# 2024 官方统一尺度材料包（3.3GB，第三代 EXE+XML）。2025/2026 两包在仓库外
# 的 ROOT.parent，见 build_scale.PACKAGES。
SCALE_PACK_2024 = LOCAL / "scale-2024"
