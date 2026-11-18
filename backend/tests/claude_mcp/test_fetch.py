"""SSRF matrix for upload_image_from_url's fetcher (mcp_server.fetch) and image processing."""

import socket
import socketserver
import threading
import time

import pytest

from mcp_server.errors import CmsError
from mcp_server.fetch import fetch_image_bytes, host_allowed, is_public_ip
from mcp_server.images import process_image

from .conftest import png_bytes

pytestmark = [pytest.mark.security]

PUBLIC = "93.184.216.34"
ALLOWED = ["photos.example.org", "*.iitkgp.ac.in"]


class FakeServer:
    """Plain-TCP HTTP server whose response is set per test."""

    def __init__(self):
        self.response = b""
        self.delay = 0.0
        self.trickle = None  # (chunk, count, pause)
        self.requests = []
        outer = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                data = b""
                while b"\r\n\r\n" not in data:
                    chunk = self.request.recv(4096)
                    if not chunk:
                        return
                    data += chunk
                outer.requests.append(data.decode("latin-1"))
                time.sleep(outer.delay)
                try:
                    if outer.trickle:
                        head, (chunk, count, pause) = outer.response, outer.trickle
                        self.request.sendall(head)
                        for _ in range(count):
                            self.request.sendall(chunk)
                            time.sleep(pause)
                    else:
                        self.request.sendall(outer.response)
                except OSError:
                    pass

        self.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def server():
    srv = FakeServer()
    yield srv
    srv.close()


def http(body: bytes, status="200 OK", headers=None, length=True) -> bytes:
    lines = [f"HTTP/1.1 {status}", "Content-Type: image/png", "Connection: close"]
    if length:
        lines.append(f"Content-Length: {len(body)}")
    lines += headers or []
    return ("\r\n".join(lines) + "\r\n\r\n").encode() + body


def run(server, url="https://photos.example.org/a.png", addresses=(PUBLIC,), **kw):
    calls = {"resolve": 0, "connect": []}

    def resolver(host, port):
        calls["resolve"] += 1
        return list(addresses)

    def connector(ip, host, port, timeout):
        calls["connect"].append((ip, host, port))
        return socket.create_connection(("127.0.0.1", server.port), timeout=timeout)

    result = fetch_image_bytes(url, resolver=resolver, connector=connector, allowed_hosts=ALLOWED,
                               max_bytes=kw.pop("max_bytes", 1024 * 1024), timeout=kw.pop("timeout", 3.0))
    return result, calls


def blocked(server, **kw):
    with pytest.raises(CmsError) as exc:
        run(server, **kw)
    assert exc.value.code == "CMS_FETCH_BLOCKED", exc.value.message
    assert exc.value.field == "url"
    return exc.value


# ---------------------------------------------------------------- happy path and pinning
def test_fetches_and_pins_the_checked_ip(server):
    body = png_bytes(1800, 1000)
    server.response = http(body)
    (data, source), calls = run(server)
    assert data == body and source == "photos.example.org/a.png"
    assert calls["resolve"] == 1 and calls["connect"] == [(PUBLIC, "photos.example.org", 443)]
    request = server.requests[0]
    assert request.startswith("GET /a.png HTTP/1.1\r\n") and "Host: photos.example.org\r\n" in request


def test_dns_rebinding_cannot_swap_the_address(server):
    """Resolver answers public first, private afterwards: we resolve once and connect to the
    checked address, so the second answer is never used."""
    answers = iter([[PUBLIC], ["127.0.0.1"]])
    server.response = http(png_bytes(10, 10))
    seen = []

    def resolver(host, port):
        return next(answers)

    def connector(ip, host, port, timeout):
        seen.append(ip)
        return socket.create_connection(("127.0.0.1", server.port), timeout=timeout)

    fetch_image_bytes("https://photos.example.org/a.png", resolver=resolver, connector=connector, allowed_hosts=ALLOWED)
    assert seen == [PUBLIC]


# ---------------------------------------------------------------- URL rules
@pytest.mark.parametrize("url", [
    "http://photos.example.org/a.png",
    "ftp://photos.example.org/a.png",
    "file:///etc/passwd",
    "https://user:pw@photos.example.org/a.png",
    "https://photos.example.org:8443/a.png",
    "https://photos.example.org:0/a.png",
    "https://10.0.0.1/a.png",
    "https://[::1]/a.png",
    "https://127.0.0.1/a.png",
    "https://localhost/a.png",
    "https://evil.example.com/a.png",
    "https://photos.example.org.evil.com/a.png",
    "https://iitkgp.ac.in.evil.com/a.png",
    "https://photos.example.org/a b.png",
    "https://photos.example.org/a.png\r\nX: y",
    "",
])
def test_url_rules(server, url):
    blocked(server, url=url)
    assert not server.requests


def test_host_patterns():
    assert host_allowed("photos.iitkgp.ac.in", ALLOWED) and host_allowed("PHOTOS.EXAMPLE.ORG.", ALLOWED)
    assert not host_allowed("iitkgp.ac.in", ALLOWED)  # *.x does not include the apex
    assert not host_allowed("xiitkgp.ac.in", ALLOWED)


# ---------------------------------------------------------------- address rules
@pytest.mark.parametrize("address", [
    "10.0.0.1", "172.16.5.4", "192.168.1.10", "127.0.0.1", "0.0.0.0", "169.254.169.254", "100.64.0.1",
    "224.0.0.1", "255.255.255.255", "198.18.0.1", "::1", "::", "fe80::1", "fc00::1", "fd12::1", "ff02::1",
    "::ffff:10.0.0.1", "::ffff:127.0.0.1", "2002:0a00:0001::1", "64:ff9b::10.0.0.1", "not-an-ip",
])
def test_private_addresses_blocked(server, address):
    assert not is_public_ip(address)
    blocked(server, addresses=[address])
    assert not server.requests


def test_any_private_answer_blocks_even_if_one_is_public(server):
    blocked(server, addresses=[PUBLIC, "10.1.2.3"])


def test_public_addresses_allowed():
    assert is_public_ip("93.184.216.34") and is_public_ip("2606:2800:220:1:248:1893:25c8:1946")


def test_unresolvable_host(server):
    blocked(server, addresses=[])


# ---------------------------------------------------------------- response rules
@pytest.mark.parametrize("status", ["301 Moved Permanently", "302 Found", "307 Temporary Redirect", "308 Permanent Redirect"])
def test_redirects_not_followed(server, status):
    server.response = http(b"", status=status, headers=["Location: http://169.254.169.254/latest/meta-data/"])
    err = blocked(server)
    assert "redirect" in err.message
    assert len(server.requests) == 1


def test_non_200_refused(server):
    server.response = http(b"nope", status="404 Not Found")
    blocked(server)


def test_declared_size_over_cap(server):
    server.response = http(b"x" * 10, headers=["Content-Length: 52428800"])[:0] + (
        b"HTTP/1.1 200 OK\r\nContent-Length: 52428800\r\nConnection: close\r\n\r\n")
    assert "larger than" in blocked(server).message


def test_streamed_size_over_cap_without_length(server):
    server.response = b"HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n"
    server.trickle = (b"x" * 65536, 40, 0)  # 2.5 MB against a 1 MB cap
    assert "larger than" in blocked(server).message


def test_slow_first_byte(server):
    server.delay = 2.0
    server.response = http(png_bytes(10, 10))
    start = time.monotonic()
    assert "longer than" in blocked(server, timeout=0.5).message
    assert time.monotonic() - start < 1.8


def test_slowloris_body_hits_overall_deadline(server):
    server.response = b"HTTP/1.1 200 OK\r\nContent-Length: 100000\r\nConnection: close\r\n\r\n"
    server.trickle = (b"x" * 100, 1000, 0.05)  # keeps sending, each chunk within the socket timeout
    start = time.monotonic()
    assert "longer than" in blocked(server, timeout=1.0).message
    assert time.monotonic() - start < 2.5


def test_connection_refused(server):
    def resolver(host, port):
        return [PUBLIC]

    def connector(ip, host, port, timeout):
        raise ConnectionRefusedError()

    with pytest.raises(CmsError) as exc:
        fetch_image_bytes("https://photos.example.org/a.png", resolver=resolver, connector=connector, allowed_hosts=ALLOWED)
    assert exc.value.code == "CMS_FETCH_BLOCKED" and "could not be reached" in exc.value.message


# ---------------------------------------------------------------- content rules (after download)
SVG = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><rect width="10" height="10"/></svg>'


@pytest.mark.parametrize("payload", [SVG, b"<html><script>alert(1)</script></html>", b"GIF89a" + b"\x00" * 50,
                                     b"%PDF-1.4 fake", b""])
def test_non_photos_rejected(payload):
    with pytest.raises(CmsError) as exc:
        process_image(payload)
    assert exc.value.code == "CMS_VALIDATION"


def test_polyglot_is_reencoded_without_payload():
    jpeg = png_bytes(64, 64, fmt="JPEG")
    polyglot = jpeg + b"<html><script>alert(document.cookie)</script></html>"
    out = process_image(polyglot)
    assert out.ext == "jpg" and (out.width, out.height) == (64, 64)
    assert b"<script>" not in out.content and b"<html>" not in out.content


def test_exif_is_stripped():
    from PIL import Image
    import io

    img = Image.new("RGB", (32, 32))
    exif = img.getexif()
    exif[0x013B] = "Secret Photographer"  # Artist
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    out = process_image(buf.getvalue())
    assert b"Secret Photographer" not in out.content


def test_decompression_bomb_rejected():
    from PIL import Image
    import io

    buf = io.BytesIO()
    Image.new("1", (10000, 10000)).save(buf, "PNG")  # 100 MP, tiny file
    with pytest.raises(CmsError):
        process_image(buf.getvalue())
