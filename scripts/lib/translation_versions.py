"""独立翻译层所针对的官方文本版本。"""

import hashlib
import json


def fingerprint(value):
    """原文字段按顺序编码；核对新原文和旧译后再更新对应指纹。"""
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:20]
