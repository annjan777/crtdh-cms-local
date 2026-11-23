"""The admin SPA (admin/dist) served by Django under /cms/, for hosts without a gateway of our own.

On academicweb (deploy/academicweb) Apache passes /cms/ and /api/ to this app and serves only the public site
itself, so the editor screens come from here, with the same security headers the nginx gateway sends on the CMS
host (CSP read from deploy/nginx/templates/gateway.conf.template, so the two never drift). Off unless
ADMIN_DIST_DIR is set.
"""

import mimetypes
import re
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseNotAllowed
from django.utils._os import safe_join

GATEWAY_TEMPLATE = Path(settings.BASE_DIR).parent / "deploy" / "nginx" / "templates" / "gateway.conf.template"
_FALLBACK_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; "
                 "font-src 'self'; connect-src 'self'; frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
                 "form-action 'self'; object-src 'none'")


@lru_cache(maxsize=1)
def gateway_csp():
    try:
        found = dict(re.findall(r'set \$(csp\w*) "([^"]+)";', GATEWAY_TEMPLATE.read_text()))
    except OSError:
        found = {}
    main = found.get("csp", _FALLBACK_CSP)
    return main, found.get("csp_preview", main.replace("frame-ancestors 'none'", "frame-ancestors 'self'"))


def admin_app(request, path=""):
    root = getattr(settings, "ADMIN_DIST_DIR", "")
    if not root:
        raise Http404
    if request.method not in ("GET", "HEAD"):
        return HttpResponseNotAllowed(["GET", "HEAD"])
    try:
        file = Path(safe_join(root, path or "index.html"))
    except Exception:  # SuspiciousFileOperation: ../ or an absolute path
        raise Http404 from None
    if not file.is_file():
        if path.startswith("assets/") or "." in path.rsplit("/", 1)[-1]:
            raise Http404  # a missing file, not a screen of the app
        file = Path(root) / "index.html"  # client-side routes: /cms/pages/home, /cms/review ...
    resp = FileResponse(file.open("rb"), content_type=mimetypes.guess_type(file.name)[0] or "application/octet-stream")
    main, preview = gateway_csp()
    is_preview = file.name == "preview.html"
    resp["Content-Security-Policy"] = preview if is_preview else main
    resp["X-Frame-Options"] = "SAMEORIGIN" if is_preview else "DENY"
    resp["Cache-Control"] = ("public, max-age=31536000, immutable" if file.parent.name == "assets"
                             else "no-cache")
    return resp
