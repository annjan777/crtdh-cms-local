"""The only write path for content rows (admin API, MCP, discard, restore).

Each function: validates through the resource's existing serializer, enforces optimistic concurrency
(`expected_version`, contract §3/§4), and writes one audit entry per changed row.
"""
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from . import audit, registry
from .errors import CMSError


def resource_for_model(model):
    for name, res in registry.RESOURCES.items():
        if res.model_class is model:
            return name
    raise KeyError(model)


def get_model(resource):
    return registry.RESOURCES[resource].model_class


def _parse_version(value):
    if value is None or value == "":
        raise CMSError("CMS_VALIDATION", "expected_version is required for updates (send the version you read).",
                       field="expected_version", fix="Send expected_version with the version you last read.")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise CMSError("CMS_VALIDATION", "expected_version must be an integer.", field="expected_version") from None


def stale_error(resource, obj, sent):
    entry = audit.last_entry(resource, obj.pk)
    who = ""
    if entry:
        local = timezone.localtime(entry.at)
        who = f", edited by {entry.actor_name or 'someone'} at {local:%H:%M}"
    iid = registry.item_id(resource, obj.pk, obj)
    return CMSError(
        "CMS_STALE_VERSION",
        f"{iid} changed since you read it (you sent v{sent}, current v{obj.version}{who}).",
        current_version=obj.version,
    )


def _lock(model, pk):
    try:
        return model.objects.select_for_update().get(pk=pk)
    except model.DoesNotExist:
        raise CMSError("CMS_NOT_FOUND", f"{model._meta.verbose_name} {pk} does not exist.") from None


def create_item(resource, data, *, ctx, serializer_class=None, context=None):
    serializer_class = serializer_class or registry.RESOURCES[resource].serializer_class
    with transaction.atomic():
        ser = serializer_class(data=data, context=context or {})
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        audit.record(ctx, "create", resource, obj.pk, None, audit.row_values(obj),
                     registry.item_id(resource, obj.pk, obj))
    return obj


def update_item(resource, pk, data, *, ctx, expected_version, partial=True, serializer_class=None, context=None):
    model = get_model(resource)
    serializer_class = serializer_class or registry.RESOURCES[resource].serializer_class
    sent = _parse_version(expected_version)
    with transaction.atomic():
        if registry.RESOURCES[resource].kind == "singleton":
            model.load()
        obj = _lock(model, pk)
        if obj.version != sent:
            raise stale_error(resource, obj, sent)
        before = audit.row_values(obj)
        ser = serializer_class(obj, data=data, partial=partial, context=context or {})
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        after = audit.row_values(obj)
        changed = [k for k in after if k != "version" and before.get(k) != after.get(k)]
        field = changed[0] if changed else None
        audit.record(ctx, "update", resource, obj.pk, before, after,
                     registry.item_id(resource, obj.pk, obj, field=field))
    return obj


def delete_item(resource, pk, *, ctx, expected_version=None):
    if registry.RESOURCES[resource].kind == "singleton":
        raise CMSError("CMS_VALIDATION", "Page settings cannot be deleted.")
    model = get_model(resource)
    with transaction.atomic():
        obj = _lock(model, pk)
        if expected_version not in (None, "") and obj.version != _parse_version(expected_version):
            raise stale_error(resource, obj, _parse_version(expected_version))
        iid = registry.item_id(resource, obj.pk, obj)
        before = audit.row_values(obj)
        obj.delete()
        audit.record(ctx, "delete", resource, pk, before, None, iid)


def reorder(resource, ids, *, ctx, queryset=None, field="order"):
    """Renumber `field` to the position of each id. Rows whose position changes get a version bump + audit row."""
    model = get_model(resource)
    queryset = queryset if queryset is not None else model.objects.all()
    with transaction.atomic():
        rows = {o.pk: o for o in queryset.select_for_update()}
        for position, pk in enumerate(ids):
            obj = rows[pk]
            old = getattr(obj, field)
            if old == position:
                continue
            before = audit.row_values(obj)
            model.objects.filter(pk=pk).update(**{field: position, "version": F("version") + 1})
            obj.refresh_from_db()
            audit.record(ctx, "reorder", resource, pk, before, audit.row_values(obj), registry.item_id(resource, pk, obj))


def update_by_item_id(item_id, data, *, ctx, expected_version):
    try:
        section_id, resource, pk = registry.parse_item_id(item_id)
    except ValueError as e:
        raise CMSError("CMS_NOT_FOUND", str(e)) from None
    allowed = {fd["name"] for fd in registry.section_index()[section_id][1]["fields"]}
    unknown = sorted(set(data) - allowed - {"expected_version", "order"})
    if unknown:
        raise CMSError("CMS_VALIDATION", f"{section_id} has no field(s) {', '.join(unknown)}.", field=unknown[0])
    return update_item(resource, pk, data, ctx=ctx, expected_version=expected_version)


def attach_media(resource, pk, field, media_id, *, ctx, expected_version):
    """Point an image field at an uploaded MediaAsset (from a one-time upload link)."""
    from .models import MediaAsset

    try:
        asset = MediaAsset.objects.get(pk=media_id)
    except MediaAsset.DoesNotExist:
        raise CMSError("CMS_NOT_FOUND", f"Media {media_id} does not exist.") from None
    min_width = 0
    for _page, s in registry.sections_for_resource(resource):
        for fd in s["fields"]:
            if fd["name"] == field and fd.get("min_width"):
                min_width = max(min_width, fd["min_width"])
    if min_width and (asset.width or 0) < min_width:
        raise CMSError("CMS_IMAGE_TOO_SMALL", f"This photo is {asset.width} px wide; {field} needs at least {min_width} px.",
                       field=field, fix=f"Upload a photo at least {min_width} px wide.")
    model = get_model(resource)
    sent = _parse_version(expected_version)
    with transaction.atomic():
        obj = _lock(model, pk)
        if obj.version != sent:
            raise stale_error(resource, obj, sent)
        before = audit.row_values(obj)
        setattr(obj, field, asset.file.name)
        obj.save()
        audit.record(ctx, "update", resource, obj.pk, before, audit.row_values(obj),
                     registry.item_id(resource, obj.pk, obj, field=field))
    return obj
