import http.server
import pathlib
import re
import urllib.parse
import time
import sys

SITE = pathlib.Path(__file__).resolve().parents[1] / "site"


class Server(http.server.SimpleHTTPRequestHandler):
    revision = time.time_ns()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def log_message(self, *args):
        pass

    def translate_path(self, path):
        clean = urllib.parse.urlsplit(path).path
        if clean.startswith("/study/"):
            clean = clean[len("/study") :]
        return super().translate_path(clean)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/__upgrade":
            type(self).revision += 1
            self.send_response(200)
            self.end_headers()
            self.wfile.write(str(self.revision).encode("ascii"))
            return
        if path == "/study/sw.js":
            text = (SITE / "sw.js").read_text(encoding="utf8")
            text = re.sub(
                r'const VERSION = "[^"]+";',
                f'const VERSION = "offline-test-{self.revision}";',
                text,
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(text.encode("utf8"))
            return
        return super().do_GET()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8876
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Server).serve_forever()
