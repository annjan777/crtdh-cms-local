from django.contrib.sessions.models import Session

from .models import UserSession
from .signals import user_sessions_revoked


def track(request, user):
    from apps.common.middleware import client_ip

    key = request.session.session_key
    if key:
        UserSession.objects.update_or_create(session_key=key, defaults={"user": user, "ip": client_ip(request) or None})


def revoke_all(user, keep=None):
    """Deletes every CMS session of `user` except `keep`; returns how many were deleted."""
    tracked = UserSession.objects.filter(user=user).exclude(session_key=keep or "")
    keys = list(tracked.values_list("session_key", flat=True))
    n, _ = Session.objects.filter(session_key__in=keys).delete()
    tracked.delete()
    user_sessions_revoked.send(sender=type(user), user=user)
    return n
