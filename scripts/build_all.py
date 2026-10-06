# -*- coding: utf-8 -*-
"""Build the complete static site into site/."""
import shutil
import subprocess
import sys

from lib.paths import ASSETS, IFAB_PDF, ROOT, SCRIPTS, SITE, SITE_ASSETS


def run(script, *args):
    command = [sys.executable, str(SCRIPTS / script), *args]
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    SITE.mkdir(parents=True, exist_ok=True)
    if IFAB_PDF.exists():
        run("build_rules.py")
    elif not (SITE / "rules.html").exists():
        raise SystemExit("缺少规则 PDF，且 site/rules.html 不存在；请先运行 fetch_laws.py")
    else:
        print("未找到规则 PDF，保留仓库中的 site/rules.html")
    run("fetch_crests.py")
    run("build_portal.py")
    run("build_page.py")
    run("build_stats.py")
    run("build_scale.py")
    run("build_uefa.py")
    run("build_rap.py")
    run("build_rfef.py")
    run("build_pro.py")
    run("build_intl.py")
    run("build_conmebol.py")
    run("build_quiz.py")
    if SITE_ASSETS.exists():
        shutil.rmtree(SITE_ASSETS)
    shutil.copytree(ASSETS, SITE_ASSETS)
    notice = ROOT / "NOTICE.md"
    if notice.exists():
        shutil.copy2(notice, SITE / notice.name)
    print(f"站点构建完成: {SITE}")


if __name__ == "__main__":
    main()
