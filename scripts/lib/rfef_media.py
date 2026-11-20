"""RFEF 手册的官方 MP4 与离线视频文件名，供抓取、下载和展示共用。"""

import re
from urllib.parse import urlsplit

from lib.official_urls import official_url

HOST = "www.card.rfef.es"
UPLOADS = "/wp-content/uploads/"
LOCAL = "videos/rfef/"
MP4 = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.mp4", re.ASCII | re.I)
DEVICE = re.compile(r"(?:con|prn|aux|nul|com[0-9]|lpt[0-9])\.", re.ASCII | re.I)


def safe_filename(name):
    return bool(MP4.fullmatch(name)) and not DEVICE.match(name)


def media_url(value):
    # 早期官方卡片使用 http，沿用旧抓取器的规范化，只返回同官方站的 https。
    if not isinstance(value, str):
        return ""
    if value.startswith("http://"):
        value = "https://" + value[7:]
    parts = official_url(value, {HOST})
    if parts is None or not parts.path.startswith(UPLOADS):
        return ""
    folder, _, filename = parts.path[len(UPLOADS) :].rpartition("/")
    if not safe_filename(filename) or not (
        folder == "manual-videos"
        or re.fullmatch(r"20[0-9]{2}/(?:0[1-9]|1[0-2])", folder)
    ):
        return ""
    return parts._replace(netloc=HOST).geturl()


def local_choices(verified_url):
    """同名视频用其官方上传子目录消歧；两种名称均对应原有下载器。"""
    relative = urlsplit(verified_url).path[len(UPLOADS) :]
    return LOCAL + relative.rsplit("/", 1)[-1], LOCAL + relative.replace("/", "-")


def local_filename(value):
    if not isinstance(value, str) or not value.startswith(LOCAL):
        return ""
    name = value[len(LOCAL) :]
    return name if safe_filename(name) else ""


def assign_local_file(url, used):
    file, alternative = local_choices(url)
    if used.get(alternative.lower()) == url or used.get(file.lower(), url) != url:
        file = alternative
    if used.get(file.lower(), url) != url:
        raise ValueError("RFEF 不同视频对应了同一离线文件名，请核对来源。")
    used[file.lower()] = url
    return file


def destination(directory, relative):
    name = local_filename(relative)
    if not name:
        raise ValueError("RFEF 视频必须使用 videos/rfef 下的单个 MP4 文件名")
    parent = directory.resolve()
    dest = parent / name
    for file in (dest, dest.with_suffix(dest.suffix + ".part")):
        if file.resolve().parent != parent or file.is_symlink():
            raise ValueError("RFEF 视频或下载分片指向了其他文件")
    return dest
