# -*- coding: utf-8 -*-
"""Serve site/ locally with HTTP Range support for video seeking."""
import os
import subprocess
import sys

from lib.paths import SCRIPTS, SITE


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "8808"
    subprocess.run([sys.executable, str(SCRIPTS / "range_server.py"), port],
                   cwd=SITE, check=False)


if __name__ == "__main__":
    main()
