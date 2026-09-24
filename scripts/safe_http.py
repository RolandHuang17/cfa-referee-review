# -*- coding: utf-8 -*-
"""安全HTTP模块：域名白名单 + HTTPS + DNS解析公网校验 + IP钉扎(防DNS rebinding) + 受限手动重定向"""
import http.client
import ipaddress
import json
import socket
import ssl
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ALLOWED_HOSTS = {
    "www.thecfa.cn",
    "videooss.thecfa.cn",
    "imageoss.thecfa.cn",
    "rest.thecfa.cn",
}
# DoH解析器固定为IP直连（无DNS依赖）；本机若开TUN代理，系统DNS返回fake-ip，
# 因此一律走公共DNS取真实公网IP
DOH_RESOLVERS = ["https://223.5.5.5/resolve", "https://8.8.8.8/resolve"]
for _d in DOH_RESOLVERS:
    assert ipaddress.ip_address(urlsplit(_d).hostname).is_global, _d
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


class SecurityError(Exception):
    pass


_dns_cache = {}


def resolve_host(host: str, timeout=10):
    """通过DoH公共DNS解析域名，校验全部结果为公网地址"""
    if host in _dns_cache:
        return _dns_cache[host]
    last_err = None
    for doh in DOH_RESOLVERS:
        try:
            p = urlsplit(doh)
            if p.hostname not in {urlsplit(d).hostname for d in DOH_RESOLVERS}:
                raise SecurityError(f"DoH解析器不在白名单: {doh}")
            conn = http.client.HTTPSConnection(p.netloc, timeout=timeout)
            conn.request("GET", f"{p.path}?name={host}&type=A",
                         headers={"Accept": "application/dns-json", "User-Agent": UA})
            resp = conn.getresponse()
            data = json.loads(resp.read())
            conn.close()
            ips = [a["data"] for a in data.get("Answer", []) if a.get("type") == 1]
            valid = []
            for s in ips:
                ip = ipaddress.ip_address(s)
                if not ip.is_global:
                    raise SecurityError(f"DoH解析到非公网地址，已阻断: {host} -> {ip}")
                if s not in valid:
                    valid.append(s)
            if valid:
                _dns_cache[host] = valid
                return valid
        except Exception as e:  # noqa: BLE001 - 依次尝试下一个DoH
            last_err = e
    raise SecurityError(f"DoH解析失败: {host}: {last_err}")


def _validate_url(url: str):
    p = urlsplit(url)
    if p.scheme != "https":
        raise SecurityError(f"仅允许https协议: {url}")
    host = p.hostname
    if not host or host not in ALLOWED_HOSTS:
        raise SecurityError(f"主机不在白名单: {host}")
    if p.username or p.password:
        raise SecurityError("URL中不允许携带凭据")
    return p


def _connect(p, timeout: float):
    """解析并校验公网IP后钉扎连接，TLS按真实主机名校验(SNI/证书)"""
    ips = resolve_host(p.hostname)
    ctx = ssl.create_default_context()
    last_err = None
    for ip in ips:
        try:
            sock = socket.create_connection((ip, 443), timeout=timeout)
            ssock = ctx.wrap_socket(sock, server_hostname=p.hostname)
            conn = http.client.HTTPConnection(p.hostname, timeout=timeout)
            conn.sock = ssock  # 钉扎：请求走已校验的IP
            return conn
        except Exception as e:  # noqa: BLE001 - 依次尝试所有解析结果
            last_err = e
    raise SecurityError(f"连接失败: {last_err}")


def safe_urlencode(text: str) -> str:
    """UTF-8 百分号编码（用于查询参数值）"""
    from urllib.parse import quote
    return quote(text, safe="")


def safe_request(url: str, headers=None, method="GET", timeout=30, max_redirects=3):
    """返回 (status, headers, HTTPResponse, conn)。调用方负责 read/close。"""
    hops = 0
    while True:
        p = _validate_url(url)
        conn = _connect(p, timeout)
        path = p.path or "/"
        if p.query:
            path += "?" + p.query
        h = {"User-Agent": UA, "Accept-Encoding": "identity"}
        if headers:
            h.update(headers)
        conn.request(method, path, headers=h)
        resp = conn.getresponse()
        if resp.status in (301, 302, 303, 307, 308):
            loc = resp.getheader("Location") or ""
            resp.read()
            resp.close()
            conn.close()
            hops += 1
            if hops > max_redirects:
                raise SecurityError("重定向次数过多")
            url = urljoin(url, loc)
            continue
        return resp.status, {k.lower(): v for k, v in resp.getheaders()}, resp, conn


def fetch_text(url: str, headers=None, timeout=30, retries=3):
    """GET并返回 (status, text)。自动重试。"""
    last = None
    for i in range(retries):
        try:
            status, hdrs, resp, conn = safe_request(url, headers=headers, timeout=timeout)
            data = resp.read()
            resp.close()
            conn.close()
            charset = "utf-8"
            ctype = hdrs.get("content-type", "")
            if "charset=" in ctype:
                charset = ctype.split("charset=")[-1].strip()
            return status, data.decode(charset, errors="replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"请求失败 {url}: {last}")


def head_size(url: str, timeout=30):
    """HEAD获取Content-Length，失败返回None"""
    try:
        status, hdrs, resp, conn = safe_request(url, method="HEAD", timeout=timeout)
        resp.read()
        resp.close()
        conn.close()
        if status == 200:
            n = hdrs.get("content-length")
            return int(n) if n else None
    except Exception:  # noqa: BLE001
        pass
    return None


def download(url: str, dest: Path, headers=None, expected_size=None, timeout=60,
             retries=5, progress=False):
    """断点续传下载。返回 (status, final_size)。已完整则跳过。"""
    import os
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    if dest.exists() and not tmp.exists():
        return 200, dest.stat().st_size  # 之前已完整下载
    have = tmp.stat().st_size if tmp.exists() else 0
    if expected_size and have and have == expected_size and dest.exists():
        return 200, dest.stat().st_size
    for attempt in range(1, retries + 1):
        try:
            have = tmp.stat().st_size if tmp.exists() else 0
            h = dict(headers or {})
            if have:
                h["Range"] = f"bytes={have}-"
            status, hdrs, resp, conn = safe_request(url, headers=h, timeout=timeout)
            if status == 416:  # 已下载完整但未改名
                resp.close(); conn.close()
                os.replace(tmp, dest)
                return 200, tmp.stat().st_size
            if status not in (200, 206):
                resp.close(); conn.close()
                raise RuntimeError(f"HTTP {status}")
            if status == 200 and have:  # 服务器不支持Range，重下
                have = 0
                tmp.unlink(missing_ok=True)
            total = None
            cr = hdrs.get("content-range")
            cl = hdrs.get("content-length")
            if cr and "/" in cr:
                total = int(cr.rsplit("/", 1)[-1]) if cr.rsplit("/", 1)[-1].isdigit() else None
            elif cl:
                total = int(cl) + (have if status == 206 else 0)
            mode = "ab" if status == 206 and have else "wb"
            done = 0 if mode == "wb" else have
            with open(tmp, mode) as f:
                while True:
                    chunk = resp.read(1 << 17)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if progress and total:
                        print(f"\r    {done/1e6:.1f}/{total/1e6:.1f}MB", end="", flush=True)
            resp.close()
            conn.close()
            if total and done != total:
                raise RuntimeError(f"大小不符 {done}!={total}")
            os.replace(tmp, dest)
            if progress:
                print()
            return 200, done
        except Exception as e:  # noqa: BLE001
            if progress:
                print(f"\n    重试{attempt}: {e}")
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"下载失败(重试{retries}次): {url}")
