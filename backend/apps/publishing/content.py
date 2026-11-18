"""The only write path for content rows (admin API, MCP, discard, restore).

Each function: validates through the resource's existing serializer, enforces optimistic concurrency
(`expected_version`, contract §3/§4), and writes one audit entry per changed row.
"""
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from . import audit, registry
from .errors import CMSError, with_extra


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
    """409 CMS_STALE_VERSION with addendum-A4 extras edited_by (username) and edited_at (ISO 8601)."""
    entry = audit.last_entry(resource, obj.pk)
    who, edited_by, edited_at = "", None, None
    if entry:
        local = timezone.localtime(entry.at)
        edited_by = entry.actor_name or None
        edited_at = entry.at.isoformat().replace("+00:00", "Z")
        who = f", edited by {edited_by or 'someone'} at {local:%H:%M}"
    iid = registry.item_id(resource, obj.pk, obj)
    return with_extra(CMSError(
        "CMS_STALE_VERSION",
        f"{iid} changed since you read it (you sent v{sent}, current v{obj.version}{who}).",
        current_version=obj.version,
    ), edited_by=edited_by, edited_at=edited_at)


def _lock(model, pk):
    try:
        return model.objects.select_for_update().get(pk=pk)
    except model.DoesNotExist:
        raise CMSError("CMS_NOT_FOUND", f"{model._meta.verbose_name} {pk} does not exist.") from None


def _plain(data):
    """QueryDict (multipart) or dict -> a plain mutable dict (files kept as uploaded objects)."""
    if hasattr(data, "dict") and hasattr(data, "getlist"):
        return {k: data.get(k) for k in data}
    return dict(data or {})


def _truthy(value):
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _next_order(model, data):
    """New rows go to the end of their list (of their parent's list for child rows)."""
    from django.db.models import Max

    qs = model.objects.all()
    for f in model._meta.concrete_fields:
        if f.is_relation and f.name in data and data[f.name] not in (None, ""):
            qs = qs.filter(**{f.attname: data[f.name]})
        elif f.name == "page" and data.get("page"):
            qs = qs.filter(page=data["page"])
    top = qs.aggregate(m=Max("order"))["m"]
    return 0 if top is None else top + 1


def _default_parents(model, validated):
    """A hidden draft without a required group (e.g. a team member's category) joins the first one; the editor
    changes it in the form. No group exists at all -> CMS_VALIDATION."""
    out = {}
    for f in model._meta.concrete_fields:
        if f.is_relation and not f.null and not f.has_default() and f.name not in validated:
            rel = f.related_model
            order = ["order", "id"] if any(x.name == "order" for x in rel._meta.concrete_fields) else ["id"]
            first = rel.objects.order_by(*order).first()
            if first is None:
                raise CMSError("CMS_VALIDATION", f"Add a {rel._meta.verbose_name} first.", field=f.name)
            out[f.name] = first
    return out


def _require_complete(resource, obj):
    """A visible collection row must have every required field of its section (e.g. a hero slide's photo)."""
    _page, view = registry.section_for(resource, obj)
    model = registry.RESOURCES[resource].model_class
    for fd in view["fields"]:
        name = fd["name"]
        try:
            mf = model._meta.get_field(name)
        except Exception:  # noqa: BLE001 - registry-only field
            continue
        required = fd.get("required", not (mf.blank or mf.null or mf.has_default()))
        value = getattr(obj, mf.attname, None)
        if required and (value is None or (hasattr(value, "name") and not value.name) or value == ""):
            label = fd.get("label") or name.replace("_", " ")
            raise CMSError("CMS_VALIDATION", f"Fill in “{label}” before showing this item on the site.", field=name,
                           fix=f"Add the {label.lower()}, or keep the item hidden until it is ready.")


def create_item(resource, data, *, ctx, serializer_class=None, context=None, section_id=None):
    """Create a row. Addendum A3: rows start hidden (is_published=false) unless the caller sets is_published.

    With `section_id` (MCP), unknown fields are refused and the section's page filter (e.g. page="covid-19" for
    an image grid) is applied, so the new row lands in that section. A child list (e.g. innovation photos) is
    addressed by its parent section id; pass the parent's pk in the parent field (e.g. "innovation": 4).
    """
    serializer_class = serializer_class or registry.RESOURCES[resource].serializer_class
    data = _plain(data)
    if section_id is not None:
        view = registry.section_view(section_id, resource)
        if view is None:
            raise CMSError("CMS_NOT_FOUND", f"Section {section_id} does not hold {resource}.", field="section")
        if view["kind"] != "collection":
            raise CMSError("CMS_VALIDATION", f"{section_id} is a single block; update it instead of adding items.",
                           field="section")
        unknown = sorted(set(data) - registry.editable_fields(view))
        if unknown:
            raise CMSError("CMS_VALIDATION", f"{section_id} has no field(s) {', '.join(unknown)}.", field=unknown[0])
        for key, value in (view.get("filter") or {}).items():
            if "__" not in key:
                data[key] = value
    res = registry.RESOURCES[resource]
    if res.has_visibility and "is_published" not in data:
        data["is_published"] = False
    hidden = res.has_visibility and not _truthy(data.get("is_published"))
    model = res.model_class
    with transaction.atomic():
        if "order" not in data and any(f.name == "order" for f in model._meta.concrete_fields):
            data["order"] = _next_order(model, data)
        # A hidden draft may start empty (the admin's "Add" creates the row first, then the editor fills it in);
        # required fields are enforced when the row is shown (see _require_complete).
        ser = serializer_class(data=data, partial=hidden, context=context or {})
        ser.is_valid(raise_exception=True)
        extra = _default_parents(model, ser.validated_data) if hidden else {}
        obj = ser.save(**extra)
        if not hidden:
            _require_complete(resource, obj)
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
        if registry.RESOURCES[resource].has_visibility and obj.is_published:
            _require_complete(resource, obj)  # raises -> the transaction rolls back, nothing is saved
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


def _pk_of(value, resource):
    """Accept a pk (int / digit string) or an item id `<section>.<resource>:<pk>`."""
    if isinstance(value, str) and ":" in value:
        try:
            _s, res, pk = registry.parse_item_id(value)
        except ValueError as e:
            raise CMSError("CMS_VALIDATION", str(e), field="order") from None
        if res != resource:
            raise CMSError("CMS_VALIDATION", f"{value} is not a {resource} item.", field="order")
        return pk
    try:
        return int(value)
    except (TypeError, ValueError):
        raise CMSError("CMS_VALIDATION", f"{value!r} is not an item id.", field="order") from None


def reorder(resource, ids, *, ctx, queryset=None, field="order"):
    """Renumber `field` to the position of each id (pks or item ids). Rows whose position changes get a version
    bump + audit row. Unknown ids -> CMS_VALIDATION and nothing changes."""
    ids = [_pk_of(i, resource) for i in ids]
    model = get_model(resource)
    queryset = queryset if queryset is not None else model.objects.all()
    with transaction.atomic():
        rows = {o.pk: o for o in queryset.select_for_update()}
        missing = [pk for pk in ids if pk not in rows]
        if missing:
            raise CMSError("CMS_VALIDATION", f"Unknown {resource} id(s): {', '.join(map(str, missing))}.", field="order")
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
    """PATCH one item by its registry id; only the fields its section (or child list) shows may be written."""
    try:
        _page, view, resource, pk = registry.view_for_item(item_id)
    except ValueError as e:
        raise CMSError("CMS_NOT_FOUND", str(e)) from None
    section_id = view["id"]
    unknown = sorted(set(data) - registry.editable_fields(view) - {"expected_version"})
    if unknown:
        raise CMSError("CMS_VALIDATION", f"{section_id} has no field(s) {', '.join(unknown)}.", field=unknown[0])
    return update_item(resource, pk, data, ctx=ctx, expected_version=expected_version)


def attach_media(resource, pk, field, media_id, *, ctx, expected_version):
    """Point an image field at an uploaded MediaAsset (from a one-time upload link). media_id: int or "media:<id>"."""
    from .models import MediaAsset

    if isinstance(media_id, str) and media_id.startswith("media:"):
        media_id = media_id.split(":", 1)[1]
    try:
        asset = MediaAsset.objects.get(pk=int(media_id))
    except (MediaAsset.DoesNotExist, TypeError, ValueError):
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
    try:
        model_field = model._meta.get_field(field)
    except Exception:  # noqa: BLE001 - FieldDoesNotExist
        model_field = None
    if model_field is None or model_field.get_internal_type() not in ("ImageField", "FileField"):
        raise CMSError("CMS_VALIDATION", f"{resource} has no image field {field!r}.", field=field)
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
