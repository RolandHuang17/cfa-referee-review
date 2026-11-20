"""本地浏览器视频拖动使用的单区间请求、缓存校验及连接复用。"""

import functools
import http.client
import io
import os
from contextlib import closing
import subprocess
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from range_server import CHUNK_SIZE, RangeHandler, ThreadingHTTPServer


@pytest.fixture
def preview(tmp_path):
    completed = threading.Event()
    errors = []

    class Handler(RangeHandler):
        def finish(self):
            try:
                super().finish()
            finally:
                completed.set()

        def log_message(self, fmt, *args):
            pass

    (tmp_path / "clip.mp4").write_bytes(b"0123456789")
    (tmp_path / "empty.mp4").touch()
    (tmp_path / "index.html").write_bytes(b"home")
    with ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Handler, directory=tmp_path)
    ) as server:
        server.handle_error = lambda request, address: errors.append(sys.exc_info()[1])
        thread = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.02}
        )
        thread.start()
        try:
            yield server.server_address, completed
        finally:
            server.shutdown()
            thread.join()
    assert errors == []


def request(conn, method="GET", path="/clip.mp4", **headers):
    conn.request(method, path, headers=headers)
    response = conn.getresponse()
    return response.status, response.headers, response.read()


def test_ranges_and_head_on_one_connection(preview):
    address, _ = preview
    entire = b"0123456789"
    with closing(http.client.HTTPConnection(*address, timeout=5)) as conn:
        conn.connect()
        original_socket = conn.sock
        for header, status, span, expected in [
            ("bytes=2-4", 206, "bytes 2-4/10", b"234"),
            ("bytes=4-", 206, "bytes 4-9/10", b"456789"),
            ("bytes=-3", 206, "bytes 7-9/10", b"789"),
            ("bytes=8-25", 206, "bytes 8-9/10", b"89"),
            ("bytes=-15", 206, "bytes 0-9/10", entire),
            ("bytes=10-", 416, "bytes */10", b""),
            ("bytes=-0", 416, "bytes */10", b""),
            ("bytes=2-1", 416, "bytes */10", b""),
            ("bytes=-", 200, None, entire),
            ("bytes=0-1,4-5", 200, None, entire),
        ]:
            for method in ["HEAD", "GET"]:
                code, headers, body = request(conn, method, Range=header)
                assert (code, headers.get("Content-Range")) == (status, span)
                assert headers["Accept-Ranges"] == "bytes"
                assert int(headers["Content-Length"]) == len(expected)
                assert body == (expected if method == "GET" else b"")
                assert conn.sock is original_socket
        assert request(conn, "HEAD")[1]["Content-Length"] == "10"
        assert request(conn, path="/", Range="bytes=0-1")[2] == b"home"
        assert request(conn, path="/empty.mp4", Range="bytes=0-")[0] == 416
        assert request(conn, path="/empty.mp4")[0] == 200
        assert request(conn, path="/missing.mp4", Range="bytes=0-")[0] == 404
        assert request(conn)[2] == entire


def test_cached_seek_after_same_second_replacement(preview, tmp_path):
    address, _ = preview
    with closing(http.client.HTTPConnection(*address, timeout=5)) as conn:
        _, headers, _ = request(conn, "HEAD")
        tag, modified = headers["ETag"], headers["Last-Modified"]
        for validator, status in [(tag, 206), ("W/" + tag, 200), (modified, 200)]:
            code, _, body = request(conn, Range="bytes=5-", **{"If-Range": validator})
            assert (code, body) == (
                status,
                b"56789" if status == 206 else b"0123456789",
            )
        assert (
            request(conn, Range="bytes=2-4", **{"If-None-Match": "W/" + tag})[0] == 304
        )
        assert request(conn, **{"If-Modified-Since": modified})[0] == 304

        old = tmp_path / "clip.mp4"
        stamp = old.stat().st_mtime_ns
        replacement = tmp_path / "replacement.mp4"
        replacement.write_bytes(b"abcdefghij")
        os.utime(replacement, ns=(stamp, stamp))
        os.replace(replacement, old)
        status, fresh, body = request(conn, Range="bytes=5-", **{"If-Range": tag})
        assert (status, body) == (200, b"abcdefghij")
        assert fresh["ETag"] != tag and fresh["Last-Modified"] == modified
        status, _, body = request(conn, Range="bytes=5-", **{"If-Range": fresh["ETag"]})
        assert (status, body) == (206, b"fghij")
        assert (
            request(conn, **{"If-None-Match": tag, "If-Modified-Since": modified})[0]
            == 200
        )


def test_reads_only_the_range_in_bounded_chunks():
    class RecordingFile(io.BytesIO):
        def read(self, size=-1):
            assert 0 < size <= CHUNK_SIZE
            return super().read(size)

    source = RecordingFile(b"x" * (4 * CHUNK_SIZE))
    output = io.BytesIO()
    handler = object.__new__(RangeHandler)
    source.seek(17)
    handler.remaining = 2 * CHUNK_SIZE + 1
    handler.copyfile(source, output)
    assert len(output.getvalue()) == 2 * CHUNK_SIZE + 1
    assert source.tell() == 17 + len(output.getvalue())
    source.seek(-2, io.SEEK_END)
    handler.remaining = 10
    handler.copyfile(source, io.BytesIO())
    assert handler.close_connection


def test_leaving_player_releases_clip(preview, tmp_path):
    address, completed = preview
    video = tmp_path / "clip.mp4"
    with video.open("ab") as f:
        f.truncate(8 * 1024 * 1024)
    with closing(http.client.HTTPConnection(*address, timeout=5)) as conn:
        conn.request("GET", "/clip.mp4", headers={"Range": "bytes=0-"})
        response = conn.getresponse()
        assert response.read(10) == b"0123456789"
        response.close()
    assert completed.wait(5)
    video.rename(tmp_path / "finished.mp4")
    with closing(http.client.HTTPConnection(*address, timeout=5)) as conn:
        assert (
            request(conn, path="/finished.mp4", Range="bytes=0-9")[2] == b"0123456789"
        )


def test_launcher_propagates_child_error():
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    result = subprocess.run(
        [sys.executable, str(scripts / "serve.py"), "invalid-port"],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 1
