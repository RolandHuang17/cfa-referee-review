"""UEFA 视频永久链接及已发行的位置书签。"""

import re
from collections import defaultdict

from lib.pagelib import article_anchor


# 2026-10-03 初版已公开的位置链接（382933d）。仅描述该版本，后续采集不改此表。
_PUBLISHED_ORDER = (
    (
        "factual-decisions",
        (
            "02a7-21381fdca64f-3a2d59a205aa-1000",
            "02a7-213688cda827-6312b11a08d7-1000",
            "02a7-213805d7491a-5f1a807b4aa8-1000",
            "02a7-2136896feda3-135f604c50de-1000",
            "02a7-21380631b285-96dc178b8dde-1000",
            "02a7-21368e211b31-517a4c1ff711-1000",
            "02a7-21368e438576-11d4fa29fd02-1000",
            "02a7-2138066c2fc7-7a9c8b989153-1000",
            "02a7-21368e9842c9-d8b450660701-1000",
            "02a7-21368ec750c5-3bb7e14c3a90-1000",
            "02a7-21368ee03a6f-16696003c3b2-1000",
        ),
    ),
    (
        "dogso",
        (
            "02a7-21349a0b3244-24bab522c1a3-1000",
            "02a7-21349a86ebe8-6f7e2294f36a-1000",
            "02a7-2138020d6644-0e87830ba670-1000",
            "02a7-21349b2ceba1-c1a753e4f844-1000",
            "02a7-21381ebb18ab-94cd3d89fd16-1000",
            "02a7-21349c121037-fc840bfac455-1000",
            "02a7-21349c4d7ff8-8c7ae86dda69-1000",
            "02a7-21349c9a5780-84f53f9e061a-1000",
            "02a7-2138027f0186-e473c4d85a04-1000",
        ),
    ),
    (
        "serious-foul-play",
        (
            "02a7-213800174192-9730fd64e1a7-1000",
            "02a7-2139ee549c05-c9136497a54b-1000",
            "02a7-213494fbf281-ae7dbd6dab0f-1000",
            "02a7-21349539ab67-8cd417632f90-1000",
            "02a7-21349571c515-70a7e60db60d-1000",
            "02a7-213800e233f0-12188aeba9f5-1000",
            "02a7-213495e2ed62-cc924b1f9ea5-1000",
        ),
    ),
    (
        "violent-conduct",
        (
            "02a7-213496c23a21-73fed5ebabe2-1000",
            "02a7-213497fdb715-cec56021a982-1000",
            "02a7-213497c4dfba-3f9488ea4279-1000",
            "02a7-21380177f966-95e9b0a6a8fb-1000",
            "02a7-2134987fe962-5e298ca9705c-1000",
        ),
    ),
    (
        "second-yellow",
        (
            "02a7-21349d9eb9f8-c755bc63192b-1000",
            "02a7-21381f5e304d-a30af7eff7cc-1000",
            "02a7-21349e69e7ff-b79dee4c569c-1000",
        ),
    ),
    (
        "handball",
        (
            "02a7-2127f79a9df2-bac5c3f331f3-1000",
            "02a7-212a1f9e502f-b0c5aea37176-1000",
            "02a7-213691191e42-fc94eceefddd-1000",
            "02a7-212a307ac189-f43821a77d23-1000",
            "02a7-212a313a7ce8-389e76b0bbd5-1000",
            "02a7-212a31ebd0a5-7ff3f4bb78ed-1000",
            "02a7-212a324e8355-e72eb590342a-1000",
            "02a7-212a32fd20d4-e8be87df410e-1000",
            "02a7-212a3365767b-91ecfe50dc73-1000",
            "02a7-212a33aeaade-545a4322d2b1-1000",
            "02a7-212a340e624b-bc794713c56e-1000",
            "02a7-212a34d6d5e8-2c4e91ab1c1b-1000",
            "02a7-212a3558343f-975de813b3dd-1000",
            "02a7-212a3592c2cf-54d53eda74fd-1000",
            "02a7-213691771ba3-b3a0855f2eb9-1000",
            "02a7-213691af12ab-ccf226817d5a-1000",
            "02a7-212a36e03f77-51832d26ca8f-1000",
            "02a7-212a37f6a601-3ea1036e48cc-1000",
            "02a7-212a38545690-480b73b65654-1000",
        ),
    ),
    (
        "holding-pushing",
        (
            "02a7-212a39e38caf-872d3e3f9fd3-1000",
            "02a7-212a3a444a6a-023ee8147911-1000",
            "02a7-212a3ad8df21-92b07242e0c1-1000",
            "02a7-212a3b9533e0-c142a22fa1f7-1000",
            "02a7-213692db37be-ec62eb516b73-1000",
            "02a7-212a3c548578-dd83fd87601f-1000",
            "02a7-212a3c96c12d-b04b147859c2-1000",
            "02a7-212a3cdf708e-0bef5786e714-1000",
            "02a7-212a3d576e9b-820074cc3b10-1000",
        ),
    ),
    (
        "tripping",
        (
            "02a7-212a4b7d7cd1-87706bc3a887-1000",
            "02a7-212a4bbc1161-db918b0bd690-1000",
            "02a7-212a4be044e0-0e30721ecf8e-1000",
        ),
    ),
    (
        "step-on-foot",
        (
            "02a7-212a4cc48860-bca7a8ab30e3-1000",
            "02a7-212a4d0a9b0c-9ff322041350-1000",
            "02a7-213694437508-4d6cebcd962f-1000",
            "02a7-212a4da6e0b4-30708ec69f15-1000",
        ),
    ),
    (
        "who-played-the-ball",
        (
            "02a7-213695009523-0fefabd08dc2-1000",
            "02a7-21369549de7c-b46a9b7d1d73-1000",
            "02a7-212a50193a64-b2e3bb528296-1000",
            "02a7-213695b5e3b8-0d4f5e7e3088-1000",
            "02a7-212a50a366a5-d29411d04441-1000",
        ),
    ),
    (
        "goalkeepers",
        (
            "02a7-212a51126c82-11e08a43c5a7-1000",
            "02a7-212a51892974-2029f63e9721-1000",
            "02a7-212a51d2a476-86a0de70255a-1000",
            "02a7-212a52403a8e-ccc80e071299-1000",
            "02a7-212a527f8e6c-da0c96fc2c8c-1000",
        ),
    ),
    (
        "simulation",
        (
            "02a7-2136961dff3b-ee1e7087696e-1000",
            "02a7-212a4e7847bf-c5dd8f42f141-1000",
            "02a7-212a4ec10e1d-510c25da0c92-1000",
        ),
    ),
)


def _token(value):
    if re.fullmatch(r"[a-zA-Z0-9_-]+", value):
        return value
    return "~" + value.encode("utf-8").hex()


def group_anchor(key):
    return "group-" + _token(key)


def video_anchor(video_id, url=""):
    if video_id:
        return "video-" + _token(video_id)
    # 官方视频卡可能提供分享链接而没有播放器 ID。
    if url:
        return article_anchor(url)
    raise ValueError("UEFA 视频缺少官方 ID 和分享链接，无法创建书签")


LEGACY_GROUPS = {key: f"u-{i}" for i, (key, _) in enumerate(_PUBLISHED_ORDER)}
LEGACY_VIDEOS = {
    video_anchor(video): (key, f"u-{i}c{j}")
    for i, (key, videos) in enumerate(_PUBLISHED_ORDER)
    for j, video in enumerate(videos, 1)
}


def bookmark_groups(groups):
    """同一视频在多组出现时，永久链接优先定位初版组，其次按组 key 确定。"""
    locations = defaultdict(set)
    for group in groups:
        for item in group["items"]:
            locations[video_anchor(item["id"], item["url"])].add(group["key"])
    result = {}
    for anchor, keys in locations.items():
        published_group = LEGACY_VIDEOS.get(anchor, (None, None))[0]
        result[anchor] = published_group if published_group in keys else min(keys)
    return result
