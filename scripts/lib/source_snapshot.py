"""同既有快照对照来源记录，完成核验后再发布。"""

import json
from datetime import date

from lib.atomic_json import write_json, write_text


def require_coverage(previous, candidate, label):
    previous, candidate = set(previous), set(candidate)
    if not candidate:
        raise ValueError(f"{label} 未解析出记录")
    missing = previous - candidate
    if missing:
        raise ValueError(
            f"{label} 缺少 {len(missing)} 项，示例 {sorted(missing, key=str)[:3]}"
        )


def publish(path, candidate, identities, *, checked):
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    require_coverage(identities(previous), identities(candidate), path.name)
    candidate["fetched"] = (
        date.today().isoformat() if checked else previous.get("fetched", "")
    )
    if candidate != previous:
        write_json(path, candidate)


class SnapshotReads:
    """记录本次用到的来源页，只有全部在线获取时才更新核查日期。"""

    def __init__(self, *, offline=False, refresh=False):
        self.offline = offline
        self.refresh = refresh
        self.requested = set()
        self.verified = set()

    def cached(self, url, path, minimum):
        self.requested.add(url)
        if not self.refresh and path.is_file() and path.stat().st_size > minimum:
            return path.read_text(encoding="utf-8", errors="replace")
        return "" if self.offline else None

    def store(self, url, path, page):
        write_text(path, page)
        self.verified.add(url)

    @property
    def checked(self):
        return bool(self.requested) and self.requested == self.verified
