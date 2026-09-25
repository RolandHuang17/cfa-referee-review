# -*- coding: utf-8 -*-
"""Serve site/ locally with HTTP Range support for video seeking."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "8808"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "range_server.py"), port],
                   cwd=ROOT / "site", check=False)


if __name__ == "__main__":
    main()
