# -*- coding: utf-8 -*-
"""打包轻量站点 zip：site/ 剔除 videos/（约 30GB 本地视频不入包）。

用法：python scripts/package_site.py [版本号]
输出：dist/cfa-referee-site-<版本>.zip（含全部页面/manifest/sw/队徽/尺度海报，几 MB）
用途：GitHub Release 附件——不想 clone 的人多一条获取路径；也是发版前的体积体检。
"""

import sys
import zipfile
from datetime import date

from lib.paths import ROOT, SITE

DIST = ROOT / "dist"


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else date.today().strftime("%Y.%m.%d")
    DIST.mkdir(exist_ok=True)
    out = DIST / f"cfa-referee-site-{version}.zip"
    n, total = 0, 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(SITE.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(SITE)
            if rel.parts and rel.parts[0] == "videos":
                continue  # 本地视频目录（gitignored，约 30GB）不入包
            if rel.parts[:2] == ("assets", "scale"):
                continue  # 尺度场景海报帧（约 110MB PNG）不入包：无视频时海报意义有限，
                # 在线版缺海报仅表现为 video 无缩略图，功能不受影响
            z.write(path, rel.as_posix())
            n += 1
            total += path.stat().st_size
    print(
        f"打包完成: {out}（{n} 个文件，{total / 1024 / 1024:.1f} MB → "
        f"{out.stat().st_size / 1024 / 1024:.1f} MB 压缩后）"
    )
    if total > 60 * 1024 * 1024:
        raise SystemExit("⚠ 包体超过 60MB——检查是否有不该入包的大文件")


if __name__ == "__main__":
    main()
