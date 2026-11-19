# -*- coding: utf-8 -*-
"""Build the complete static site into site/."""

import shutil
import subprocess
import sys

from lib.paths import ASSETS, ROOT, SCRIPTS, SITE, SITE_ASSETS


def run(script, *args):
    command = [sys.executable, str(SCRIPTS / script), *args]
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    SITE.mkdir(parents=True, exist_ok=True)
    run("build_rules.py", "--from-json")
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
    run("build_weekly.py")
    run("build_ifab.py")
    run("build_hns.py")
    run("build_quiz.py")
    run("build_cheatsheet.py")
    run("build_search.py")
    run("build_pwa.py")
    run("build_seo.py")
    run("build_feed.py")
    if SITE_ASSETS.exists():
        shutil.rmtree(SITE_ASSETS)
    shutil.copytree(ASSETS, SITE_ASSETS)
    notice = ROOT / "NOTICE.md"
    if notice.exists():
        shutil.copy2(notice, SITE / notice.name)
    print(f"站点构建完成: {SITE}")


if __name__ == "__main__":
    main()
