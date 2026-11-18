"""Serializer fields that push every upload through apps.common.images.

CommonConfig.ready() maps models.ImageField -> SafeImageField and
models.FileField -> SafeFileField for every ModelSerializer, so no serializer
can accept an unchecked file. Stored names are content hashes, never the
uploader's filename.
"""
import os

from django.core.files.base import ContentFile
from rest_framework import serializers

from .errors import CMSError
from .images import process_upload as _process


def process_upload(field, data, **kw):
    try:
        return _process(data, **kw)
    except CMSError as e:
        e.body["field"] = e.body["field"] or field.field_name
        raise

# Minimum source width per "<app_label>.<model>.<field>" (PLAN WS2.6). The
# publishing registry's `min_width` should feed this once it lands.
MIN_WIDTHS = {
    "carousel.heroslide.image": 1600,
}


def _field_key(field):
    model = getattr(getattr(field.parent, "Meta", None), "model", None)
    if model is None:
        return None
    return f"{model._meta.app_label}.{model._meta.model_name}.{field.source}"


def _to_content_file(processed):
    with open(processed.path, "rb") as fh:
        data = fh.read()
    os.unlink(processed.path)
    return ContentFile(data, name=f"{processed.sha256[:16]}.{processed.ext}")


class SafeImageField(serializers.ImageField):
    def to_internal_value(self, data):
        serializers.FileField.to_internal_value(self, data)  # name/empty checks only
        key = _field_key(self)
        processed = process_upload(self, data, min_width=MIN_WIDTHS.get(key), kind="image")
        return _to_content_file(processed)


class SafeFileField(serializers.FileField):
    def to_internal_value(self, data):
        super().to_internal_value(data)
        kind = "video" if "video" in (self.source or "") else "document"
        return _to_content_file(process_upload(self, data, kind=kind))
