"""同目录临时写入，验证或写入失败时保留上一份 JSON。"""

import json
import os
import tempfile
from pathlib import Path


def write_json(path, data):
    write_text(path, json.dumps(data, ensure_ascii=False, indent=1))


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
