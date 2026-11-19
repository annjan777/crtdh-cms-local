from django.db import models


class StaleWrite(Exception):
    """The row's version changed between our read and our write (someone else saved it in between)."""

    def __init__(self, model, pk, read_version):
        self.model, self.pk, self.read_version = model, pk, read_version
        super().__init__(f"{model._meta.label} {pk} changed since v{read_version} was read")


class VersionedModel(models.Model):
    """Every editable content row carries `version` (contract §3). Each save of an existing row bumps it, and the
    UPDATE only applies `WHERE version = <the version this instance read>` — atomic on every database. If another
    write got in between, save() raises StaleWrite and nothing is written (apps.publishing turns that into 409)."""

    version = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self._read_version = None
        if not self._state.adding:
            self._read_version = self.version or 0
            self.version = self._read_version + 1
            update_fields = kwargs.get("update_fields")
            if update_fields is not None and "version" not in update_fields:
                kwargs["update_fields"] = list(update_fields) + ["version"]
        try:
            super().save(*args, **kwargs)
        except StaleWrite:
            self.version = self._read_version
            raise

    def _do_update(self, base_qs, using, pk_val, values, update_fields, forced_update):
        read = getattr(self, "_read_version", None)
        if read is None:
            return super()._do_update(base_qs, using, pk_val, values, update_fields, forced_update)
        updated = super()._do_update(base_qs.filter(version=read), using, pk_val, values, update_fields, forced_update)
        if not updated and base_qs.filter(pk=pk_val).exists():
            raise StaleWrite(type(self), pk_val, read)
        return updated
