from django.conf import settings
from django.db import models


class GrantFamily(models.Model):
    """One Claude connection: the consent that started a chain of rotated refresh tokens.

    django-oauth-toolkit gives every rotated refresh token the same `token_family`; this row
    remembers when that family began so a connection can never outlive
    MCP_OAUTH_MAX_GRANT_DAYS, however often it refreshes (rotation alone would slide the
    expiry forever).
    """

    token_family = models.UUIDField(unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_id} since {self.created_at:%Y-%m-%d}"
