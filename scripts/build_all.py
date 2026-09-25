# -*- coding: utf-8 -*-
"""Build the complete static site into site/."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"


def run(script, *args):
    command = [sys.executable, str(ROOT / "scripts" / script), *args]
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    SITE.mkdir(parents=True, exist_ok=True)
    law_pdf = ROOT / "data" / "laws_raw" / "lotg-202627-tc-single.pdf"
    if law_pdf.exists():
        run("build_rules.py")
    elif not (SITE / "rules.html").exists():
        raise SystemExit("缺少规则 PDF，且 site/rules.html 不存在；请先运行 fetch_laws.py")
    else:
        print("未找到规则 PDF，保留仓库中的 site/rules.html")
    run("build_portal.py")
    run("build_page.py")
    run("build_stats.py")
    site_assets = SITE / "assets"
    if site_assets.exists():
        shutil.rmtree(site_assets)
    shutil.copytree(ROOT / "assets", site_assets)
    notice = ROOT / "NOTICE.md"
    if notice.exists():
        shutil.copy2(notice, SITE / notice.name)
    print(f"站点构建完成: {SITE}")


if __name__ == "__main__":
    main()
