"""Roles for the CRTDH CMS (shared contract — see docs/contracts/v3-contracts.md §3).

Roles are Django groups named "editor", "publisher", "admin". A superuser counts as admin.
Higher roles include lower ones: admin ⊃ publisher ⊃ editor.
"""
from rest_framework.permissions import BasePermission

EDITOR, PUBLISHER, ADMIN = "editor", "publisher", "admin"
ORDER = [EDITOR, PUBLISHER, ADMIN]


def user_roles(user):
    if not user or not user.is_authenticated or not user.is_active:
        return []
    if user.is_superuser:
        return list(ORDER)
    names = set(user.groups.values_list("name", flat=True))
    top = max((ORDER.index(n) for n in names if n in ORDER), default=-1)
    return ORDER[: top + 1]


def has_role(user, role):
    return role in user_roles(user)


class _RolePermission(BasePermission):
    role = EDITOR

    def has_permission(self, request, view):
        return has_role(request.user, self.role)


class IsEditor(_RolePermission):
    role = EDITOR


class IsPublisher(_RolePermission):
    role = PUBLISHER


class IsAdminRole(_RolePermission):
    role = ADMIN
