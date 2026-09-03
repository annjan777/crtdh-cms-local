from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """SAFE_METHODS (GET/HEAD/OPTIONS) are open to anyone.
    Every other method (POST/PUT/PATCH/DELETE, including the custom
    `reorder` action) requires an authenticated staff user.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
