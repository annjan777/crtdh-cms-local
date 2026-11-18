from django.db import models


class VersionedModel(models.Model):
    """Every editable content row carries `version` (contract §3). Each save of an existing row bumps it;
    the PATCH views compare it with `expected_version` under a row lock (apps.publishing.concurrency)."""

    version = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.version = (self.version or 0) + 1
            update_fields = kwargs.get("update_fields")
            if update_fields is not None and "version" not in update_fields:
                kwargs["update_fields"] = list(update_fields) + ["version"]
        super().save(*args, **kwargs)
