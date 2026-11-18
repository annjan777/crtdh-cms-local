import uuid

from django.conf import settings


class RequestIdMiddleware:
    """Gives every request an id (echoed as X-Request-ID and in error bodies)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = uuid.uuid4().hex
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response


class SecurityHeadersMiddleware:
    """CSP and Permissions-Policy (SecurityMiddleware covers HSTS, nosniff, Referrer-Policy)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", settings.CONTENT_SECURITY_POLICY)
        response.setdefault("Permissions-Policy", settings.PERMISSIONS_POLICY)
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if request.path.startswith("/api/"):
            response.setdefault("Cache-Control", "no-store")
        return response


def client_ip(request):
    """The caller's IP. CF-Connecting-IP is trusted only behind the Cloudflare tunnel."""
    if settings.TRUST_CF_CONNECTING_IP:
        ip = request.META.get("HTTP_CF_CONNECTING_IP", "").strip()
        if ip:
            return ip
    return request.META.get("REMOTE_ADDR", "")
