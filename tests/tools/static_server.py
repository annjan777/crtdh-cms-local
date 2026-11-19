"""Tiny static host for tests: stands in for the CIC web root (public site) and the CMS origin (admin).

  python tests/tools/static_server.py --dir frontend/build/client --port 3601 --mode static
  python tests/tools/static_server.py --dir admin/dist --port 3600 --mode spa --proxy http://localhost:8600

static: /x -> x/index.html | x.html | x ; unknown -> 404.html with HTTP 404 (like Apache on CIC).
spa:    unknown non-file paths -> index.html (admin router).
--cert/--key: serve HTTPS (production settings refuse http origins).
--proxy: /api/, /admin/, /media/, /mcp, /.well-known/, /oauth/, /upload/ are forwarded so the admin
         is same-origin with the CMS API (as in production behind one hostname).
"""
import argparse
import http.server
import os
import socketserver
import urllib.error
import urllib.request
from functools import partial
from pathlib import Path

PROXY_PREFIXES = ("/api/", "/admin/", "/media/", "/mcp", "/.well-known/", "/oauth/", "/o/", "/upload/", "/static/",
                  "/cms/login")  # as deploy/nginx gateway: Django owns /cms/login (OAuth sign-in entry)
HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade", "proxy-authorization", "proxy-authenticate"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _proxy_opener():
    """No redirects; trusts the dev cert in E2E_CA_FILE (self-signed HTTPS backend) when set."""
    ca = os.environ.get("E2E_CA_FILE")
    if not ca:
        return urllib.request.build_opener(_NoRedirect)
    import ssl
    return urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca)))


class Handler(http.server.SimpleHTTPRequestHandler):
    mode = "static"
    proxy = None

    def log_message(self, fmt, *args):
        if os.environ.get("STATIC_SERVER_LOG"):
            super().log_message(fmt, *args)

    def _proxy(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        req = urllib.request.Request(self.proxy + self.path, data=body, method=self.command)
        for k, v in self.headers.items():
            if k.lower() not in HOP:
                req.add_header(k, v)  # Host passes through, as the gateway's `proxy_set_header Host $host`
        req.add_header("X-Forwarded-Proto", "https")
        try:
            resp = _proxy_opener().open(req, timeout=60)
        except urllib.error.HTTPError as e:
            resp = e
        data = resp.read()
        self.send_response(resp.status if hasattr(resp, "status") else resp.code)
        for k, v in resp.headers.items():
            if k.lower() not in HOP and k.lower() != "content-length":
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    static_root = None

    def _route(self):
        if self.static_root and self.path.startswith("/static/"):  # gateway serves collectstatic output itself
            rel = self.path.split("?", 1)[0][len("/static/"):]
            f = (Path(self.static_root) / rel).resolve()
            if Path(self.static_root).resolve() in f.parents and f.is_file():
                self.path = "/" + rel
                self.directory = str(Path(self.static_root))
                return super().do_GET() if self.command == "GET" else super().do_HEAD()
            self.send_error(404)
            return None
        if self.proxy and self.path.startswith(PROXY_PREFIXES):
            return self._proxy()
        root = Path(self.directory)
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        rel = path.lstrip("/")
        cands = [root / rel] if rel else []
        cands += [root / rel / "index.html", root / f"{rel.rstrip('/')}.html"]
        for c in cands:
            if c.is_file():
                self.path = "/" + str(c.relative_to(root))
                return super().do_GET() if self.command == "GET" else super().do_HEAD()
        if self.mode == "spa" and "." not in rel.rsplit("/", 1)[-1]:
            self.path = "/index.html"
            return super().do_GET() if self.command == "GET" else super().do_HEAD()
        page = root / "404.html"
        body = page.read_bytes() if page.is_file() else b"<h1>Not found</h1>"
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command == "GET":
            self.wfile.write(body)

    def do_GET(self):
        self._route()

    def do_HEAD(self):
        self._route()

    def _write(self):
        if self.proxy and self.path.startswith(PROXY_PREFIXES):
            return self._proxy()
        self.send_error(405, "static host: read-only")

    do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _write


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 128
    tls = None

    def finish_request(self, request, client_address):
        # Wrapping the listening socket ran the TLS handshake inside accept() on the main thread: one slow
        # handshake stalled every other connection and Chrome gave up on some CSS (ERR_TOO_MANY_RETRIES ->
        # unstyled pages -> false overflow/font failures in E2E).
        if self.tls is not None:
            try:
                request = self.tls.wrap_socket(request, server_side=True)
            except (OSError, ValueError):
                return
        super().finish_request(request, client_address)


def serve(directory, port, mode="static", proxy=None, host="127.0.0.1", cert=None, key=None, static_root=None):
    handler = type("H", (Handler,), {"mode": mode, "proxy": proxy.rstrip("/") if proxy else None,
                                     "static_root": static_root})
    srv = Server((host, port), partial(handler, directory=str(directory)))
    if cert:
        import ssl
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        srv.tls = ctx  # handshake per connection in the worker thread (see Server.finish_request)
    return srv


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--mode", choices=["static", "spa"], default="static")
    ap.add_argument("--proxy")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--cert")
    ap.add_argument("--key")
    ap.add_argument("--static-root", help="serve this dir at /static/ (the gateway serves collectstatic output)")
    a = ap.parse_args()
    serve(a.dir, a.port, a.mode, a.proxy, a.host, a.cert, a.key, a.static_root).serve_forever()
