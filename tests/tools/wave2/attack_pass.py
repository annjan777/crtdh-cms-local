"""Targeted attack pass against a running preprod (report-only; never run against production).

    set -a; . .preprod/env; set +a; python tests/tools/wave2/attack_pass.py > docs/test-evidence/.../attack.txt
Each probe prints PASS (defended) / FAIL (exploitable) / INFO. Exit 1 on any FAIL."""
import io
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "e2e"))
from helpers import totp_now  # noqa: E402

ST = Path(".preprod")
CA = str(ST / "tls" / "cert.pem")
API = "https://localhost:8600"
SITE = os.environ.get("ATTACK_SITE", "https://localhost:3601")
USERS = json.loads((ST / "users.json").read_text())
PW = os.environ["CRTDH_TEST_PASSWORD"]
CTX = ssl.create_default_context(cafile=CA)
RES = []


def out(level, name, detail=""):
    RES.append(level)
    print(f"{level:4} {name}{(': ' + str(detail)[:300]) if detail else ''}", flush=True)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class Client:
    def __init__(self):
        self.jar = CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), _NoRedirect,
                                              urllib.request.HTTPSHandler(context=CTX))
        self.token = ""

    def req(self, method, path, body=None, headers=None, raw=None, csrf=True, base=API):
        h = {"Accept": "application/json", "Referer": API + "/", "Origin": API}
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        if csrf and self.token and method not in ("GET", "HEAD"):
            h["X-CSRFToken"] = self.token
        h.update(headers or {})
        r = urllib.request.Request(base + path, data=data, method=method, headers=h)
        try:
            resp = self.op.open(r, timeout=30)
        except urllib.error.HTTPError as e:
            resp = e
        txt = resp.read()
        try:
            return resp.status if hasattr(resp, "status") else resp.code, json.loads(txt or b"null")
        except ValueError:
            return resp.status if hasattr(resp, "status") else resp.code, txt[:300]

    def csrf(self):
        _, b = self.req("GET", "/api/v1/auth/csrf/")
        self.token = (b or {}).get("csrfToken", "")

    def login(self, user, mfa=True):
        self.csrf()
        s, b = self.req("POST", "/api/v1/auth/login/", {"username": user, "password": PW})
        if mfa and isinstance(b, dict) and b.get("mfa_required"):
            s, b = self.req("POST", "/api/v1/auth/mfa/", {"code": totp_now(USERS[user]["totp_secret"])})
        self.csrf()
        return s, b


def main():
    # ---------- direct access to app ports bypassing the gateway
    for port, path in ((8600, "/api/v1/auth/csrf/"), (8601, "/.well-known/oauth-protected-resource")):
        code = subprocess.run(["curl", "-s", "--cacert", CA, "--interface", "127.0.0.5", "-o", "/dev/null", "-w",
                               "%{http_code}", f"https://localhost:{port}{path}"], capture_output=True, text=True).stdout
        out("PASS" if code == "403" else "FAIL", f"direct request from non-proxy peer to :{port}", f"HTTP {code}")
    code = subprocess.run(["curl", "-s", "--cacert", CA, "-o", "/dev/null", "-w", "%{http_code}", "-H",
                           "X-Forwarded-For: 160.79.104.1", "-H", "CF-Connecting-IP: 160.79.104.1",
                           "https://localhost:8601/mcp"], capture_output=True, text=True).stdout
    out("PASS" if code == "401" else "FAIL", "spoofed CF-Connecting-IP to MCP still needs OAuth", f"HTTP {code}")

    # ---------- MFA bypass
    c = Client()
    s, b = c.login("erin_editor", mfa=False)
    s2, _ = c.req("GET", "/api/v1/hero-slides/")
    s3, _ = c.req("GET", "/api/v1/auth/me/")
    out("PASS" if s2 in (401, 403) else "FAIL", "password-only session reads content", f"{s2}")
    out("INFO", "password-only session /auth/me", f"{s3}")
    s4, b4 = c.req("PATCH", "/api/v1/hero-slides/1/", {"heading": "x"})
    out("PASS" if s4 in (401, 403) else "FAIL", "password-only session writes content", f"{s4}")
    c6 = Client()
    c6.login("ada_admin")
    step_code = None
    import pyotp
    import time as _t
    step_code = pyotp.TOTP(USERS["ada_admin"]["totp_secret"]).at(int(_t.time()) // 30 * 30)
    c7 = Client()
    c7.csrf()
    c7.req("POST", "/api/v1/auth/login/", {"username": "ada_admin", "password": PW})
    s7, _ = c7.req("POST", "/api/v1/auth/mfa/", {"code": step_code})
    out("PASS" if s7 != 200 else "FAIL", "TOTP code replay in the same 30 s step (second session)", s7)

    # ---------- CSRF
    e = Client()
    e.login("erin_editor")
    _, slides = e.req("GET", "/api/v1/hero-slides/")
    rows = slides.get("results", slides) if isinstance(slides, dict) else slides
    sid, ver = rows[0]["id"], rows[0]["version"]
    s, b = e.req("PATCH", f"/api/v1/hero-slides/{sid}/", {"heading": "csrf probe", "expected_version": ver}, csrf=False)
    out("PASS" if s == 403 else "FAIL", "write without CSRF token", f"{s} {b}")
    s, b = e.req("PATCH", f"/api/v1/hero-slides/{sid}/", {"heading": "csrf probe", "expected_version": ver},
                 headers={"Origin": "https://evil.example", "Referer": "https://evil.example/"})
    out("PASS" if s == 403 else "FAIL", "write with token but foreign Origin", f"{s}")

    # ---------- IDOR / vertical privilege
    for method, path, body in [("GET", "/api/v1/contact-messages/", None), ("GET", "/api/v1/auth/users/", None),
                               ("POST", "/api/v1/auth/users/3/role/", {"role": "admin"}),
                               ("POST", "/api/v1/cms/publish/", {}), ("DELETE", f"/api/v1/hero-slides/{sid}/", None),
                               ("GET", "/api/v1/cms/audit/", None)]:
        s, b = e.req(method, path, body)
        expect_ok = path.endswith("/audit/")
        out("INFO" if expect_ok else ("PASS" if s in (401, 403) else "FAIL"), f"editor {method} {path}", s)
    me = e.req("GET", "/api/v1/auth/me/")[1]
    s, b = e.req("PATCH", "/api/v1/auth/me/", {"roles": ["admin"], "is_superuser": True, "is_staff": True})
    me2 = e.req("GET", "/api/v1/auth/me/")[1]
    out("PASS" if me2.get("roles") == me.get("roles") else "FAIL", "editor self-promotion via PATCH /auth/me/",
        f"{s} roles {me.get('roles')} -> {me2.get('roles')}")
    s, b = e.req("PATCH", f"/api/v1/hero-slides/{sid}/", {"is_published": True, "version": 999, "id": 9999,
                                                          "expected_version": ver})
    out("INFO", "mass-assignment of id/version on update", f"{s} {str(b)[:160]}")

    # ---------- uploads: polyglots, SVG, traversal names
    s, link = e.req("POST", "/api/v1/cms/upload-links/", {"min_width": 0})
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 30, 30)).save(buf, "JPEG")
    poly = buf.getvalue() + b"<html><script>alert(document.domain)</script></html>"
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><script>alert(2)</script></svg>'
    gifar = b"GIF89a" + b"<script>alert(1)</script>" + b"\x00" * 64
    for label, name, data, ctype in [("JPEG+HTML polyglot", "x.jpg", poly, "image/jpeg"),
                                     ("SVG with script", "x.svg", svg, "image/svg+xml"),
                                     ("GIF header + script", "x.gif", gifar, "image/gif"),
                                     ("traversal filename", "../../../../tmp/pwn.jpg", buf.getvalue(), "image/jpeg")]:
        s, link = e.req("POST", "/api/v1/cms/upload-links/", {"min_width": 0})
        if s != 201:
            out("FAIL", f"upload link for {label}", s)
            continue
        boundary = "----crtdhprobe"
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
                f"Content-Type: {ctype}\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
        path = "/" + link["url"].split("/", 3)[3]
        s, b = e.req("POST", path, raw=body, csrf=False,
                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "application/json"})
        if label == "JPEG+HTML polyglot" and s == 201:
            out("INFO", f"upload {label} accepted (expect re-encoded)", b)
        elif label == "traversal filename":
            out("PASS" if not Path("/tmp/pwn.jpg").exists() else "FAIL", "upload traversal filename did not escape", f"{s} {b}")
        else:
            out("PASS" if s >= 400 else "FAIL", f"upload {label} refused", f"{s} {str(b)[:120]}")
        s2, _ = e.req("POST", path, raw=body, csrf=False,
                      headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "application/json"})
        if label == "traversal filename":
            out("PASS" if s2 >= 400 else "FAIL", "upload link is one-time", s2)
    # where did the polyglot land? check its stored bytes have no trailing HTML
    media_root = Path(os.environ.get("MEDIA_ROOT", ".preprod/media"))
    hits = subprocess.run(["grep", "-rl", "alert(document.domain)", str(media_root)], capture_output=True, text=True).stdout.split()
    out("PASS" if not hits else "FAIL", "polyglot HTML tail stripped from stored media (re-encoded)", hits[:3])

    # ---------- path traversal in media
    for p in ["/api/v1/media/../../config/settings.py", "/api/v1/media/..%2f..%2fconfig%2fsettings.py",
              "/api/v1/media/%2e%2e/%2e%2e/etc/passwd", "/api/v1/media//etc/passwd", "/api/v1/media/hero_slides/..%5c..%5cdb"]:
        s, b = e.req("GET", p)
        leak = isinstance(b, bytes) and (b"root:" in b or b"SECRET_KEY" in b or b"import" in b)
        out("FAIL" if leak else "PASS", f"CMS media traversal {p}", s)
    s, b = Client().req("GET", "/api/v1/media/hero_slides/banner06.jpg")
    out("PASS" if s in (401, 403) else "FAIL", "CMS draft media needs a session (anonymous)", s)
    for p in ["/_media/../../../etc/passwd", "/_media/%2e%2e/%2e%2e/etc/passwd", "/..%2f..%2fetc/passwd"]:
        s, b = Client().req("GET", p, base=SITE)
        leak = isinstance(b, bytes) and b"root:" in b
        out("FAIL" if leak else "PASS", f"static host traversal {p}", s)

    # ---------- SSRF via MCP fetch (in-process, production settings, real resolver, no network egress needed)
    code = r"""
import json
from mcp_server import fetch
from mcp_server.errors import CmsError
urls = ["http://127.0.0.1:8600/api/v1/auth/csrf/", "https://127.0.0.1/", "https://localhost/", "https://[::1]/",
        "https://169.254.169.254/latest/meta-data/", "https://10.0.0.1/x.jpg", "https://0x7f000001/", "https://2130706433/",
        "https://localtest.me/x.jpg", "file:///etc/passwd", "gopher://127.0.0.1:25/", "https://user@127.0.0.1/"]
res = {}
for u in urls:
    try:
        fetch.fetch_image_bytes(u)
        res[u] = "FETCHED"
    except CmsError as e:
        res[u] = "blocked: " + str(getattr(e, "code", "")) + " " + str(getattr(e, "message", ""))[:60]
    except Exception as e:
        res[u] = "error: " + type(e).__name__
print(json.dumps(res))
"""
    r = subprocess.run([sys.executable, "manage.py", "shell", "-c", code], cwd="backend", capture_output=True, text=True,
                       env=os.environ)
    try:
        res = json.loads(r.stdout.strip().splitlines()[-1])
        for u, v in res.items():
            out("FAIL" if v == "FETCHED" else "PASS", f"MCP fetch {u}", v)
    except Exception:  # noqa: BLE001
        out("FAIL", "MCP fetch probe could not run", (r.stderr or r.stdout)[-300:])

    # ---------- MFA brute force last (it may lock the account): ada_admin
    c = Client()
    c.login("ada_admin", mfa=False)
    bad = [c.req("POST", "/api/v1/auth/mfa/", {"code": f"{i:06d}"})[0] for i in range(12)]
    out("PASS" if (429 in bad or 423 in bad) else "FAIL", "MFA brute force (12 wrong codes) is throttled/locked", bad)
    s5, b5 = c.req("POST", "/api/v1/auth/mfa/", {"code": totp_now(USERS["ada_admin"]["totp_secret"])})
    out("PASS" if s5 != 200 else "INFO", "correct code accepted right after brute force (should stay locked)", f"{s5} {b5}")

    print(f"\n{RES.count('FAIL')} FAIL, {RES.count('PASS')} PASS, {RES.count('INFO')} INFO")
    return 1 if "FAIL" in RES else 0


if __name__ == "__main__":
    sys.exit(main())
