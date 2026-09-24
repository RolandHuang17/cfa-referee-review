# -*- coding: utf-8 -*-
"""带 Range(断点/快进)支持的本地静态服务器
用法: python range_server.py [端口]   (默认8808, 服务当前工作目录)
Python内置 http.server 不支持 Range 请求, 导致浏览器视频无法拖动进度条;
本模块补上单区间 Range 处理 (bytes=a-b / bytes=-N), 足够浏览器视频seek使用。
"""
import io
import os
import re
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


class RangeHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path) or not os.path.exists(path):
            return super().send_head()  # 目录/404 走默认逻辑
        rng = self.headers.get("Range")
        if not rng:
            return super().send_head()
        m = RANGE_RE.match(rng.strip())
        if not m:
            return super().send_head()
        try:
            f = open(path, "rb")
        except OSError:
            return super().send_head()
        size = os.fstat(f.fileno()).st_size
        s, e = m.group(1), m.group(2)
        if s == "":  # bytes=-N 后缀区间
            length = min(int(e), size)
            start, end = size - length, size - 1
        else:
            start = int(s)
            end = int(e) if e else size - 1
            if end >= size:
                end = size - 1
        if start > end or start >= size:
            f.close()
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Last-Modified", self.date_time_string(os.fstat(f.fileno()).st_mtime))
        self.end_headers()
        if self.command == "HEAD":
            f.close()
            return None
        f.seek(start)
        data = f.read(end - start + 1)
        f.close()
        return io.BytesIO(data)

    def log_message(self, fmt, *args):  # 安静模式, 避免窗口刷屏
        if "/videos/" not in (self.path or ""):
            super().log_message(fmt, *args)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8808
    try:
        srv = ThreadingHTTPServer(("0.0.0.0", port), RangeHandler)
    except OSError:
        print(f"[提示] 端口{port}被占用, 可能服务已经在运行。若浏览器能打开页面, 无需处理。")
        sys.exit(1)
    print(f"服务已启动: http://127.0.0.1:{port}/index.html  (支持视频快进)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
