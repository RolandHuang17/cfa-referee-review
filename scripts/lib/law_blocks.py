"""规则正文段落的稳定定位，供渲染与搜索同源使用。"""

import hashlib
import html
import re


BLOCK = re.compile(r"<(p|li|h3|h4)\b([^>]*)>([\s\S]*?)</\1>")


def text_of(markup):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup))).strip()


def anchored_section(section):
    blocks, seen = [], {}

    def anchor(match):
        tag, attrs, body = match.groups()
        text = text_of(body)
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
        key = f"{section['id']}-p-{digest}"
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            key += f"-{seen[key]}"
        blocks.append((key, text))
        return f'<{tag}{attrs} id="{key}">{body}</{tag}>'

    markup = BLOCK.sub(anchor, section.get("html", ""))
    return markup, blocks
