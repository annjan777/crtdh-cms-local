"""Role permissions for content resources (contract §3). Role logic itself lives in apps.accounts.roles."""
from rest_framework.permissions import BasePermission

from apps.accounts.roles import EDITOR, PUBLISHER, has_role


class ContentPermission(BasePermission):
    """Every method needs a signed-in editor; DELETE needs a publisher (admin includes publisher)."""

    message = "Your role does not allow this action."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False  # -> 401 CMS_UNAUTHENTICATED
        role = PUBLISHER if request.method == "DELETE" else EDITOR
        return has_role(request.user, role)
