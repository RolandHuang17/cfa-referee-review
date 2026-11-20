# -*- coding: utf-8 -*-
"""从已构建的 site/ 打包轻量发行清单。

用法：python scripts/package_site.py [版本号]
输出：dist/cfa-referee-site-<版本>.zip（含全部页面/manifest/sw/队徽，排除视频与尺度海报）
用途：GitHub Release 附件——不想 clone 的人多一条获取路径；也是发版前的体积体检。
"""

import re
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path

from build_rules import DIAGRAM_PAGES, PARTIAL_DIAGRAMS
from lib.crest_catalog import load_legacy_map
from lib.pages import PAGE_FILES
from lib.paths import ROOT, SITE

DIST = ROOT / "dist"
SIZE_LIMIT = 60 * 1024 * 1024

# 构建器写出的站点级附件、视觉素材与按需加载的门户模块。
SUPPORT_FILES = (
    "NOTICE.md",
    "feed.xml",
    "icon.svg",
    "manifest.webmanifest",
    "robots.txt",
    "sitemap.xml",
    "sw.js",
    "assets/og-card.png",
    "assets/compare/handball-1.webp",
    "assets/compare/handball-1-small.webp",
    "assets/compare/handball-28.webp",
    "assets/compare/handball-28-small.webp",
    "assets/compare/referee-large.webp",
    "assets/compare/referee-mobile.webp",
    "assets/portal/case-study.webp",
    "assets/portal/referee-match.webp",
    "assets/portal/referee-match-small.webp",
    "assets/portal/moments/lib.js",
    "assets/portal/moments/moments.js",
    "assets/portal/moments/liquid-hover/moment.css",
    "assets/portal/moments/liquid-hover/moment.js",
)


def release_members():
    crests = set(load_legacy_map().values())
    for name in crests:
        if not re.fullmatch(r"assets/crests/[\w-]+\.png", name):
            raise ValueError(f"发行清单中的队徽路径无效：{name}")
    diagrams = {
        f"assets/rules/p{n}.png" for n in DIAGRAM_PAGES | PARTIAL_DIAGRAMS.keys()
    }
    return sorted(set(PAGE_FILES) | set(SUPPORT_FILES) | crests | diagrams)


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else date.today().strftime("%Y.%m.%d")
    if not version.strip() or re.search(r'[<>:"/\\|?*\x00-\x1f]', version):
        raise SystemExit("版本号必须可用作单个文件名")
    site = SITE.parent.resolve() / SITE.name
    members = release_members()
    total = 0
    for name in members:
        path = site / name
        if path.resolve() != path:
            raise SystemExit(f"发行文件经链接指向其他位置：{name}")
        if not path.is_file():
            raise SystemExit(
                f"发行文件缺失：{name}。请先运行 python scripts/build_all.py"
            )
        total += path.stat().st_size
    if total > SIZE_LIMIT:
        raise SystemExit("⚠ 包体超过 60MB——请核查发行文件体积")

    DIST.mkdir(exist_ok=True)
    out = DIST / f"cfa-referee-site-{version}.zip"
    with tempfile.TemporaryDirectory(dir=DIST) as tmp:
        candidate = Path(tmp) / "bundle.zip"
        with zipfile.ZipFile(candidate, "w") as z:
            for name in members:
                # ZipInfo defaults to the ZIP epoch. Rebuilding a page must not
                # change the digest solely through local timestamps or mode bits.
                entry = zipfile.ZipInfo(name)
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                z.writestr(
                    entry,
                    (site / name).read_bytes(),
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )
            total = sum(info.file_size for info in z.infolist())
        if total > SIZE_LIMIT:
            raise SystemExit("⚠ 包体超过 60MB——请核查发行文件体积")
        candidate.replace(out)
    print(
        f"打包完成: {out}（{len(members)} 个文件，{total / 1024 / 1024:.1f} MB → "
        f"{out.stat().st_size / 1024 / 1024:.1f} MB 压缩后）"
    )


if __name__ == "__main__":
    main()
