"""HTTP fetch layer built only on the Python standard library."""
from __future__ import annotations

import gzip
import http.client
import socket
import ssl
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlsplit

from .identities import Identity

__all__ = ["FetchResult", "fetch"]


@dataclass
class FetchResult:
    """Everything observed from a single request."""

    identity_key: str
    requested_url: str
    final_url: str = ""
    status: int = 0
    reason: str = ""
    ok: bool = False
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    encoding: str = ""
    elapsed_ms: float = 0.0
    redirect_chain: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def byte_size(self) -> int:
        return len(self.body)


class _RecordingRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, chain: List[str], follow: bool = True):
        self._chain = chain
        self._follow = follow

    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        self._chain.append(newurl)
        if not self._follow:
            return None  # stop redirect processing; raise HTTPError upstream
        return super().redirect_request(req, fp, code, msg, hdrs, newurl)


def _decode_body(body: bytes, encoding: str) -> bytes:
    """Reverse gzip/deflate transport encodings."""
    enc = (encoding or "").lower().strip()
    if enc in ("gzip", "x-gzip"):
        return gzip.decompress(body)
    if enc == "deflate":
        try:
            return zlib.decompress(body)
        except zlib.error:
            return zlib.decompress(body, -zlib.MAX_WBITS)
    return body


def fetch(
    url: str,
    identity: Identity,
    *,
    timeout: float = 15.0,
    follow_redirects: bool = True,
    verify_tls: bool = True,
    method: str = "GET",
) -> FetchResult:
    """Perform a single request using the given identity.

    Network errors never raise: they are captured in ``FetchResult.error`` so
    that an audit of many identities can always complete.
    """
    result = FetchResult(identity_key=identity.key, requested_url=url)
    started = time.perf_counter()
    chain: List[str] = [url]

    if verify_tls:
        ssl_ctx = ssl.create_default_context()
    else:
        ssl_ctx = ssl._create_unverified_context()  # explicit --insecure opt-in

    handlers = [
        urllib.request.HTTPSHandler(context=ssl_ctx),
        _RecordingRedirectHandler(chain, follow=follow_redirects),
    ]
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers=identity.headers(), method=method)

    try:
        try:
            resp = opener.open(req, timeout=timeout)
            status, reason, hdrs = resp.status, resp.reason, resp.headers
            raw = resp.read()
        except urllib.error.HTTPError as e:  # 4xx/5xx still carry a body worth keeping
            status, reason, hdrs = e.code, e.reason, e.headers
            raw = e.read() or b""
            if not follow_redirects and 300 <= e.code < 400:
                pass
        result.status = int(status)
        result.reason = reason or ""
        result.ok = 200 <= result.status < 300
        result.headers = {k: v for k, v in (hdrs.items() if hdrs else [])}
        result.encoding = result.headers.get("Content-Encoding", "") or ""
        try:
            result.body = _decode_body(raw, result.encoding)
        except (gzip.BadGzipFile, zlib.error, EOFError) as exc:
            result.body = raw
            result.error = f"body decode failed: {exc}"
        result.redirect_chain = chain
        result.final_url = chain[-1] if chain else url
    except (urllib.error.URLError, socket.timeout, TimeoutError, http.client.HTTPException, ssl.SSLError, OSError) as exc:
        result.error = f"{type(exc).__name__}: {exc}"
        result.final_url = chain[-1]
        result.redirect_chain = chain
    finally:
        result.elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return result


def same_endpoint(url_a: str, url_b: str) -> bool:
    """Compare host + path (ignoring query order and fragments)."""
    pa, pb = urlsplit(url_a), urlsplit(url_b)
    return (pa.netloc.lower() == pb.netloc.lower()
            and pa.path.rstrip("/") == pb.path.rstrip("/"))
