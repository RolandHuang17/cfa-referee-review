# -*- coding: utf-8 -*-
"""带 Range(断点/快进)支持的本地静态服务器
用法: python range_server.py [端口] [目录]   (默认8808, 服务当前工作目录)
Python内置 http.server 不支持 Range 请求, 导致浏览器视频无法拖动进度条;
本模块补上单区间 Range 处理 (bytes=a-b / bytes=-N), 足够浏览器视频seek使用。
"""

import os
import re
import sys
from datetime import timezone
from email.utils import parsedate_to_datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

RANGE_RE = re.compile(r"bytes=([0-9]*)-([0-9]*)", re.IGNORECASE)
CHUNK_SIZE = 64 * 1024


def byte_range(header, size):
    """Return inclusive bounds. Unknown units and multiple ranges use a full response."""
    match = RANGE_RE.fullmatch(header.strip())
    if not match or not any(match.groups()):
        return None
    first, last = match.groups()
    try:
        if not first:
            return max(0, size - int(last)), size - 1
        return int(first), min(int(last), size - 1) if last else size - 1
    except ValueError:
        return None


class RangeHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            # Seeking or switching cases can cancel an obsolete browser request.
            self.close_connection = True

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def not_modified(self, stat, tag):
        tags = self.headers.get("If-None-Match")
        if tags is not None:
            return tags.strip() == "*" or any(
                value.strip().removeprefix("W/") == tag for value in tags.split(",")
            )
        since = self.headers.get("If-Modified-Since")
        if since:
            try:
                date = parsedate_to_datetime(since)
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                return int(stat.st_mtime) <= date.timestamp()
            except (TypeError, ValueError, OverflowError, OSError):
                pass
        return False

    def send_head(self):
        self.remaining = (
            None  # One handler can serve several requests on the same connection.
        )
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            source = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None
        try:
            stat = os.fstat(source.fileno())
            size = stat.st_size
            tag = f'"{stat.st_dev:x}-{stat.st_ino:x}-{size:x}-{stat.st_mtime_ns:x}-{stat.st_ctime_ns:x}"'
            modified = self.date_time_string(stat.st_mtime)
            if self.not_modified(stat, tag):
                source.close()
                self.send_response(304)
                self.send_header("ETag", tag)
                self.send_header("Last-Modified", modified)
                self.end_headers()
                return None

            # A second-resolution date cannot distinguish two local replacements in the same second.
            validator = self.headers.get("If-Range")
            bounds = (
                byte_range(self.headers.get("Range", ""), size)
                if validator in (None, tag)
                else None
            )
            if bounds is not None:
                start, end = bounds
                if start > end:
                    source.close()
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return None
                source.seek(start)
                self.remaining = end - start + 1
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            else:
                self.remaining = size
                self.send_response(200)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Content-Length", str(self.remaining))
            self.send_header("ETag", tag)
            self.send_header("Last-Modified", modified)
            self.end_headers()
            return source  # do_HEAD and do_GET both close the open file, including on cancellation.
        except BaseException:
            source.close()
            raise

    def copyfile(self, source, outputfile):
        if self.remaining is None:
            return super().copyfile(source, outputfile)
        while self.remaining:
            chunk = source.read(min(CHUNK_SIZE, self.remaining))
            if not chunk:
                # The open file was truncated. A subsequent response must use a new connection.
                self.close_connection = True
                break
            outputfile.write(chunk)
            self.remaining -= len(chunk)

    def log_message(self, fmt, *args):  # 安静模式, 避免窗口刷屏
        if "/videos/" not in (self.path or ""):
            super().log_message(fmt, *args)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8808
    directory = sys.argv[2] if len(sys.argv) > 2 else None
    if directory:
        os.chdir(directory)
    try:
        srv = ThreadingHTTPServer(("0.0.0.0", port), RangeHandler)
    except OSError:
        print(
            f"[提示] 端口{port}被占用, 可能服务已经在运行。若浏览器能打开页面, 无需处理。"
        )
        sys.exit(1)
    print(f"服务已启动: http://127.0.0.1:{port}/index.html  (支持视频快进)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
