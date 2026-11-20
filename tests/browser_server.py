import http.server
import pathlib
import re
import urllib.parse
import time
import sys

SITE = pathlib.Path(__file__).resolve().parents[1] / "site"


class Server(http.server.SimpleHTTPRequestHandler):
    revision = time.time_ns()
    previous = False
    mounts = ("/study/-club/", "/-club/", "/study/")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def log_message(self, *args):
        pass

    def translate_path(self, path):
        clean = urllib.parse.urlsplit(path).path
        for mount in self.mounts:
            if clean.startswith(mount):
                clean = "/" + clean[len(mount) :]
                break
        return super().translate_path(clean)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path in ("/__previous", "/__upgrade"):
            type(self).previous = path == "/__previous"
            type(self).revision += 1
            self.send_response(200)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(f"{self.revision:016x}".encode("ascii"))
            return
        if path in {mount + "sw.js" for mount in ("/", *self.mounts)}:
            text = (SITE / "sw.js").read_text(encoding="utf8")
            if self.previous or "/-club/" in path:
                # Leave the child installations on the previously released cache naming scheme.
                text = re.sub(
                    r"const CACHE = [^;]+;",
                    'const CACHE = "cfa-site-" + encodeURIComponent(SCOPE) + "-" + VERSION;',
                    text,
                )
            text = re.sub(
                r'const VERSION = "[^"]+";',
                f'const VERSION = "{self.revision:016x}";',
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
