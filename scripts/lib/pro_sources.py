"""Verified PRO article permalinks, embedded YouTube videos and USSF entry points."""

import re
from urllib.parse import parse_qs

from lib.official_urls import official_url

HOST = "proreferees.com"
BASE = "https://" + HOST
SOURCE = BASE + "/category/inside-video-review/"
USSF = {
    "videos": "https://www.ussoccer.com/refereeing/videos",
    "learning": "https://learning.ussoccer.com/referee",
    "refereeing": "https://www.ussoccer.com/refereeing",
}
YT_HOSTS = {"youtube.com", "www.youtube.com"}
EMBED_HOSTS = YT_HOSTS | {"youtube-nocookie.com", "www.youtube-nocookie.com"}
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
SLUG = r"[A-Za-z0-9][A-Za-z0-9_-]*"
DATED = re.compile(
    r"/20[0-9]{2}/(?:0[1-9]|1[0-2])/(?:0[1-9]|[12][0-9]|3[01])/" + SLUG + r"/?"
)


def article_url(value, *, dated=False):
    if not isinstance(value, str):
        return ""
    if value.startswith("/") and not value.startswith("//"):
        value = BASE + value
    parts = official_url(value, {HOST})
    if parts is None:
        return ""
    # Published older backups can contain undated, single-slug WP permalinks.
    if not DATED.fullmatch(parts.path) and (
        dated or not re.fullmatch("/" + SLUG + "/?", parts.path)
    ):
        return ""
    return BASE + parts.path.rstrip("/") + "/"


def video_url(value, *, embed=False):
    parts = official_url(value, EMBED_HOSTS if embed else YT_HOSTS)
    if parts is None:
        return ""
    if embed:
        prefix = "/embed/"
        if not parts.path.startswith(prefix):
            return ""
        code = parts.path[len(prefix) :]
    else:
        ids = parse_qs(parts.query).get("v", [])
        if parts.path != "/watch" or len(ids) != 1:
            return ""
        code = ids[0]
    return "https://www.youtube.com/watch?v=" + code if VIDEO_ID.fullmatch(code) else ""
