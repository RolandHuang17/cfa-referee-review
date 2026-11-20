"""Parse public source links against an explicit HTTPS origin before publishing."""

from urllib.parse import urlsplit


def official_url(url, hosts):
    if (
        not isinstance(url, str)
        or not url
        or "\\" in url
        or any(
            character.isspace() or ord(character) < 32 or ord(character) == 127
            for character in url
        )
    ):
        return None
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        return None
    if parts.scheme != "https" or host not in hosts:
        return None
    if parts.netloc.lower() not in (host, host + ":443"):
        return None
    return parts
