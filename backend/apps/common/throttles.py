from rest_framework.throttling import ScopedRateThrottle

from .middleware import client_ip


class IPScopedThrottle(ScopedRateThrottle):
    """Scoped throttle keyed on the real client IP (CF-Connecting-IP behind the tunnel)."""

    def get_ident(self, request):
        return client_ip(request)
