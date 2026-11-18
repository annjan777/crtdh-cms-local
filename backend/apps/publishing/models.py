import uuid

from django.conf import settings
from django.db import models


class AuditEntry(models.Model):
    """One row per content write (contract §3 audit). Written only through apps.publishing.audit.record()."""

    CHANNELS = [("admin", "Admin UI"), ("mcp", "Claude (MCP)"), ("api", "API")]
    ACTIONS = [(a, a) for a in ("create", "update", "delete", "reorder", "discard", "restore")]

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    actor_name = models.CharField(max_length=150, blank=True)  # kept if the user is deleted
    channel = models.CharField(max_length=10, choices=CHANNELS)
    connector_session = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    item_id = models.CharField(max_length=200, blank=True, db_index=True)
    resource = models.CharField(max_length=64, db_index=True)
    pk_value = models.CharField("pk", max_length=64, blank=True)
    action = models.CharField(max_length=10, choices=ACTIONS)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-at", "-id"]
        indexes = [models.Index(fields=["resource", "pk_value"])]


class Snapshot(models.Model):
    """An immutable published-state candidate. `published_at` is set when its publish goes live."""

    snapshot_id = models.CharField(max_length=64, unique=True)
    data = models.JSONField()
    sha256 = models.CharField(max_length=64)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @classmethod
    def last_published(cls):
        return cls.objects.filter(published_at__isnull=False).order_by("-published_at", "-id").first()


class Publish(models.Model):
    QUEUED, BUILDING, READY, UPLOADING, LIVE, FAILED, CANCELLED = (
        "queued", "building", "ready_for_upload", "uploading", "live", "failed", "cancelled")
    STATUSES = [(s, s) for s in (QUEUED, BUILDING, READY, UPLOADING, LIVE, FAILED, CANCELLED)]
    ACTIVE = (QUEUED, BUILDING, READY, UPLOADING)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Single-flight: the conditional unique constraint allows one active publish per site, enforced by the DB.
    site = models.CharField(max_length=20, default="crtdh", editable=False)
    status = models.CharField(max_length=20, choices=STATUSES, default=QUEUED)
    step = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    confirm_shrink = models.BooleanField(default=False)
    snapshot = models.ForeignKey(Snapshot, null=True, on_delete=models.PROTECT, related_name="publishes")
    snapshot_path = models.CharField(max_length=500, blank=True)
    tarball_path = models.CharField(max_length=500, blank=True)
    tarball_sha256 = models.CharField(max_length=64, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    live_at = models.DateTimeField(null=True, blank=True)
    # When the publish agent first downloaded the tarball: from then on the upload may happen, so no cancel.
    fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["site"], condition=models.Q(status__in=["queued", "building", "ready_for_upload", "uploading"]),
                                    name="publishing_single_active_publish"),
        ]


class AgentState(models.Model):
    """Singleton (pk=1): when the publish agent last called in."""

    last_seen = models.DateTimeField(null=True, blank=True)

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]


class AgentNonce(models.Model):
    """Seen (timestamp, nonce) pairs for replay protection; rows older than the skew window are purged."""

    nonce = models.CharField(max_length=128, unique=True)
    seen_at = models.DateTimeField(auto_now_add=True, db_index=True)


class ReviewRequest(models.Model):
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class MediaAsset(models.Model):
    """A photo uploaded through a one-time link; its `file` can be assigned to any image field."""

    file = models.ImageField(upload_to="uploads/", width_field="width", height_field="height")
    width = models.PositiveIntegerField(null=True)
    height = models.PositiveIntegerField(null=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)


class UploadLink(models.Model):
    token_hash = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    channel = models.CharField(max_length=10, default="admin")
    connector_session = models.CharField(max_length=64, null=True, blank=True)
    min_width = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    media = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
