# -*- coding: utf-8 -*-
"""下载 IFAB 官方 2026-27 竞赛规则繁体中文单页版 PDF
来源: downloads.theifab.com（该URL直接返回PDF文件体）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safe_http as S

S.ALLOWED_HOSTS |= {"downloads.theifab.com", "theifab.com", "www.theifab.com"}

URL = "https://downloads.theifab.com/downloads/laws-of-the-game-202627-traditional-chinese-single-pages?l=en"
OUT = Path(__file__).resolve().parent.parent / "data" / "laws_raw" / "lotg-202627-tc-single.pdf"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists() and OUT.stat().st_size > 5_000_000:
        print(f"已存在: {OUT} ({OUT.stat().st_size/1e6:.1f}MB)")
        return
    print("下载中（约22MB）…")
    _, size = S.download(URL, OUT, timeout=120, retries=3, progress=True)
    if size < 5_000_000:
        raise RuntimeError(f"文件过小，下载可能不完整: {size}")
    print(f"完成: {OUT} ({size/1e6:.1f}MB)")


if __name__ == "__main__":
    main()
