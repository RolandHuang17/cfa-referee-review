# -*- coding: utf-8 -*-
"""Inline the shared visual system into generated offline pages."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME = (ROOT / "src" / "theme.css").read_text(encoding="utf-8")


def inject_theme(html):
    return html.replace("</head>", f"<style data-cfa-theme>\n{THEME}\n</style></head>", 1)
