"""抓取快照时区分网络核查、历史缓存和纯本地重解析。"""

from lib.atomic_json import write_text

from lib.safe_http import fetch_text


class SourceCache:
    def __init__(self, *, offline=False, refresh=False):
        self.offline = offline
        self.refresh = refresh
        self.verified = set()
        self.failed = set()

    def read(self, url, path, minimum, *, mutable=False, headers=None):
        path.parent.mkdir(parents=True, exist_ok=True)
        cached = (
            path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        )
        if self.offline or (len(cached) > minimum and not mutable and not self.refresh):
            return cached if len(cached) > minimum else ""
        try:
            status, text = fetch_text(url, headers=headers, timeout=45, retries=2)
            if status == 200 and len(text or "") > minimum:
                write_text(path, text)
                self.verified.add(url)
                return text
            if status == 404:
                return ""
        except Exception as exc:
            print(f"来源暂不可用 {url}: {exc}", flush=True)
        self.failed.add(url)
        return cached if len(cached) > minimum else ""
