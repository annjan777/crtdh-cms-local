"""SSRF-hardened HTTPS fetch for upload_image_from_url.

Rules (PLAN WS4.4, threat model): https only, default port only, no credentials in the URL,
host on MCP_FETCH_ALLOWED_HOSTS; resolve once and refuse if ANY address is not a public
unicast address (v4 and v6, including v4-mapped/6to4/Teredo forms); connect to that pinned
IP with SNI and certificate checks against the original hostname (so DNS rebinding between
check and connect is impossible); never follow redirects; at most MCP_FETCH_MAX_BYTES within
MCP_FETCH_TIMEOUT_SECONDS overall. Tests inject `resolver` and `connector`.
"""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
import time
from collections.abc import Callable
from urllib.parse import urlsplit

from django.conf import settings

from .errors import CmsError

Resolver = Callable[[str, int], list[str]]
Connector = Callable[[str, str, int, float], socket.socket]

USER_AGENT = "CRTDH-CMS-image-fetch/1.0"


def _blocked(message: str, *, fix: str | None = None) -> CmsError:
    return CmsError("CMS_FETCH_BLOCKED", f"{message} Nothing was downloaded.", fix=fix, field="url")


def host_allowed(host: str, patterns: list[str]) -> bool:
    host = host.lower().rstrip(".")
    for pattern in patterns:
        pattern = pattern.lower().strip()
        if pattern.startswith("*."):
            if host.endswith(pattern[1:]) and host != pattern[2:]:
                return True
        elif host == pattern:
            return True
    return False


def is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        embedded = ip.ipv4_mapped or ip.sixtofour or (ip.teredo[1] if ip.teredo else None)
        if embedded is not None and not is_public_ip(str(embedded)):
            return False
        if ip.ipv4_mapped is not None:
            return is_public_ip(str(ip.ipv4_mapped))
    return bool(
        ip.is_global
        and not ip.is_multicast
        and not ip.is_private
        and not ip.is_loopback
        and not ip.is_link_local
        and not ip.is_reserved
        and not ip.is_unspecified
    )


def system_resolver(host: str, port: int) -> list[str]:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return sorted({info[4][0] for info in infos})


def tls_connector(ip: str, host: str, port: int, timeout: float) -> socket.socket:
    raw = socket.create_connection((ip, port), timeout=timeout)
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        return context.wrap_socket(raw, server_hostname=host)
    except Exception:
        raw.close()
        raise


class _SocketResponse(http.client.HTTPResponse):
    pass


def fetch_image_bytes(
    url: str,
    *,
    resolver: Resolver | None = None,
    connector: Connector | None = None,
    allowed_hosts: list[str] | None = None,
    max_bytes: int | None = None,
    timeout: float | None = None,
) -> tuple[bytes, str]:
    """Return (body, "host/path") or raise CmsError(CMS_FETCH_BLOCKED / CMS_VALIDATION)."""
    resolver = resolver or system_resolver
    connector = connector or tls_connector
    allowed_hosts = settings.MCP_FETCH_ALLOWED_HOSTS if allowed_hosts is None else allowed_hosts
    max_bytes = settings.MCP_FETCH_MAX_BYTES if max_bytes is None else max_bytes
    timeout = settings.MCP_FETCH_TIMEOUT_SECONDS if timeout is None else timeout

    if not isinstance(url, str) or len(url) > 2000 or any(c in url for c in "\r\n\t "):
        raise _blocked("That URL is not valid.")
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise _blocked("Only https:// links can be fetched.")
    if parts.username or parts.password or "@" in parts.netloc:
        raise _blocked("Links with a user name or password in them are not fetched.")
    host = (parts.hostname or "").lower()
    try:
        port = parts.port if parts.port is not None else 443
    except ValueError:
        raise _blocked("That URL has an invalid port.") from None
    if not host or port != 443:
        raise _blocked("Only the standard https port is allowed.")
    try:
        ipaddress.ip_address(host.strip("[]"))
        raise _blocked("Links to a bare IP address are not fetched.")
    except ValueError:
        pass
    if not host_allowed(host, allowed_hosts):
        raise _blocked(
            f"{host} is not on this site's list of trusted photo sources.",
            fix="Use request_upload_link so the user can upload the photo directly.",
        )

    deadline = time.monotonic() + timeout
    try:
        addresses = resolver(host, port)
    except OSError:
        raise _blocked(f"{host} could not be found.") from None
    if not addresses:
        raise _blocked(f"{host} could not be found.")
    if not all(is_public_ip(a) for a in addresses):
        raise _blocked(f"{host} points to a private or internal network address.")
    pinned = addresses[0]

    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    sock = None
    try:
        sock = connector(pinned, host, port, max(0.1, deadline - time.monotonic()))
        sock.settimeout(max(0.1, deadline - time.monotonic()))
        request = (
            f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {USER_AGENT}\r\n"
            "Accept: image/jpeg, image/png, image/webp\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = _SocketResponse(sock, method="GET")
        response.begin()
        if 300 <= response.status < 400:
            raise _blocked("The link redirects somewhere else; redirects are not followed.",
                           fix="Ask the user for the direct link to the image, or use request_upload_link.")
        if response.status != 200:
            raise _blocked(f"The server answered HTTP {response.status}.")
        length = response.getheader("Content-Length")
        if length is not None and length.isdigit() and int(length) > max_bytes:
            raise _blocked(f"The file is larger than {max_bytes // (1024 * 1024)} MB.")
        chunks, total = [], 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise _blocked(f"The download took longer than {timeout:g} seconds.")
            sock.settimeout(remaining)
            chunk = response.read1(65536) if hasattr(response, "read1") else response.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise _blocked(f"The file is larger than {max_bytes // (1024 * 1024)} MB.")
            chunks.append(chunk)
        return b"".join(chunks), f"{host}{parts.path}"[:300]
    except CmsError:
        raise
    except (TimeoutError, socket.timeout):
        raise _blocked(f"The download took longer than {timeout:g} seconds.") from None
    except ssl.SSLError:
        raise _blocked(f"{host} did not present a valid HTTPS certificate.") from None
    except (OSError, http.client.HTTPException):
        raise _blocked(f"{host} could not be reached.") from None
    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
