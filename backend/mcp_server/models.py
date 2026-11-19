"""Bookkeeping for the Claude connector. Content itself lives in the CMS apps."""

from django.conf import settings
from django.db import models


class ConnectorSession(models.Model):
    """One MCP connection (the Mcp-Session-Id Claude keeps for a conversation).

    Holds the change counter behind CMS_SESSION_LIMIT and groups that session's drafts."""

    key = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    change_count = models.PositiveIntegerField(default=0)
    review_requested_at = models.DateTimeField(null=True, blank=True)  # request_review: once per session
    review_notified = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)


class ConnectorWrite(models.Model):
    """Each change Claude made, with the values before it (used for create de-duplication
    and, until backend-core's publishing module lands, for discard and pending changes)."""

    KINDS = [("added", "added"), ("changed", "changed"), ("hidden", "hidden"), ("reordered", "reordered")]
    session = models.ForeignKey(ConnectorSession, on_delete=models.CASCADE, related_name="writes")
    item_id = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=KINDS)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    dedupe_key = models.CharField(max_length=64, null=True, blank=True)
    discarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "dedupe_key"],
                condition=models.Q(dedupe_key__isnull=False),
                name="mcp_write_dedupe_per_session",
            )
        ]


class ToolCall(models.Model):
    """Audit row for every MCP tool call (channel = mcp). Arguments are not stored, only
    their names, so no content or URLs with tokens end up here."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    session_key = models.CharField(max_length=64, blank=True)
    tool = models.CharField(max_length=64)
    arg_names = models.CharField(max_length=300, blank=True)
    outcome = models.CharField(max_length=32)  # "ok" or an error code
    item_id = models.CharField(max_length=200, blank=True)
    request_id = models.CharField(max_length=32)
    duration_ms = models.PositiveIntegerField(default=0)
    at = models.DateTimeField(auto_now_add=True, db_index=True)
