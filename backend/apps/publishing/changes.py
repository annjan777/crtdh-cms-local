"""Pending changes (CMS now vs the last published snapshot), discard and restore.

- pending_changes(): the GET /cms/changes/ shape (contract §3).
- discard_item(item_id) / discard_session(session_id): revert rows to their last published values.
- restore_snapshot(snapshot): copy a past snapshot back into the CMS as unpublished changes.
All writes are audited (actions "discard" / "restore").
"""
from django.conf import settings
from django.db import models, transaction

from . import audit, registry
from .content import stale_as_409
from .errors import CMSError
from .models import AuditEntry, Snapshot
from .snapshot import _MediaRewriter, collect, queryset_for, safe_media_path

LABEL_FIELDS = ("title", "name", "heading", "label", "text", "caption", "task", "year")
IGNORED = {"id", "version"}


# ---- helpers ----------------------------------------------------------------------------------------------------
def baseline():
    """(snapshot data, Snapshot) of the last published snapshot, or (None, None)."""
    snap = Snapshot.last_published()
    return (snap.data, snap) if snap else (None, None)


def _model_field_names(resource):
    return {f.name for f in registry.RESOURCES[resource].model_class._meta.concrete_fields} - IGNORED


def _display(value, media_lookup):
    """Hashed snapshot media -> CMS media URL of its source, so the review screen can show the photo."""
    if isinstance(value, str) and value in media_lookup:
        return settings.MEDIA_URL + media_lookup[value]
    return value


def _label(resource, row, section):
    for name in LABEL_FIELDS:
        value = (row or {}).get(name)
        if value:
            value = str(value)
            return value if len(value) <= 80 else value[:77] + "..."
    return f"{section['label']} #{(row or {}).get('id', '')}".strip()


def _section_field_order(section):
    """Field names a singleton section covers, in display order (each image followed by its alt/position)."""
    out = []
    for fd in section["fields"]:
        out.append(fd["name"])
        out.extend(fd[k] for k in ("alt_field", "position_field") if fd.get(k))
    return out


def _rows_by_id(rows):
    return {r["id"]: r for r in rows or []}


def _lookup_factory(*datasets):
    def lookup(resource, pk):
        for data in datasets:
            row = _rows_by_id((data or {}).get("collections", {}).get(resource)).get(pk)
            if row:
                return row
        return None

    return lookup


def _current():
    raw = collect(include_hidden=True)
    rewrite = _MediaRewriter(hashed=True)
    data = {"singletons": rewrite(raw["singletons"]), "collections": rewrite(raw["collections"])}
    return data, {k: v["source"] for k, v in rewrite.media.items()}


# ---- diff -------------------------------------------------------------------------------------------------------
def diff(prev, current, visible_ids=None, media_lookup=None):
    """Pure diff of two snapshot-shaped dicts -> list of change dicts (without author info).

    `visible_ids` {resource: set(ids)} marks which current rows would be published; rows absent from it are hidden.
    Defaults to: every current row is visible.
    """
    prev = prev or {"singletons": {}, "collections": {}}
    media_lookup = media_lookup or {}
    lookup = _lookup_factory(current, prev)
    out = []
    for resource, res in registry.RESOURCES.items():
        fields = _model_field_names(resource)
        if res.kind == "singleton":
            before_row = (prev.get("singletons") or {}).get(resource) or {}
            after_row = (current.get("singletons") or {}).get(resource) or {}
            for _page_id, section in registry.sections_for_resource(resource):
                names = [n for n in _section_field_order(section) if n in fields]
                changed = [
                    {"name": n, "before": _display(before_row.get(n), media_lookup),
                     "after": _display(after_row.get(n), media_lookup)}
                    for n in names if before_row.get(n) != after_row.get(n)
                ]
                if changed:
                    out.append({"item_id": f"{section['id']}.{resource}:{after_row.get('id', 1)}", "resource": resource,
                                "pk": after_row.get("id", 1), "label": section["label"], "kind": "changed",
                                "fields": changed, "_section": section})
            continue
        before = _rows_by_id((prev.get("collections") or {}).get(resource))
        after = _rows_by_id((current.get("collections") or {}).get(resource))
        visible = (visible_ids or {}).get(resource, set(after))
        for pk in sorted(set(before) | set(after)):
            b, a = before.get(pk), after.get(pk)
            row = a or b
            _page, section = registry.section_for(resource, row, lookup)
            if a is None:
                kind = "removed"
            elif pk not in visible:
                if b is None:
                    continue  # hidden and never published: nothing changes on the site
                kind = "hidden"
            else:
                kind = "added" if b is None else "changed"
            changed = []
            for name in sorted(fields):
                bv, av = (b or {}).get(name), (a or {}).get(name)
                if isinstance(bv, list) or isinstance(av, list) or (kind == "removed"):
                    continue
                if name == "is_published":
                    continue
                if bv != av and not (kind == "added" and av in (None, "", False)):
                    changed.append({"name": name, "before": _display(bv, media_lookup), "after": _display(av, media_lookup)})
            if kind == "hidden":
                changed.insert(0, {"name": "is_published", "before": True, "after": False})
            if kind == "changed" and not changed:
                continue
            out.append({"item_id": f"{section['id']}.{resource}:{pk}", "resource": resource, "pk": pk,
                        "label": _label(resource, row, section), "kind": kind, "fields": changed, "_section": section})
    return out


def _visible_ids():
    return {name: set(queryset_for(name).values_list("id", flat=True)) for name in registry.COLLECTIONS}


def pending_changes(author=None, session_id=None):
    prev, snap = baseline()
    current, media_now = _current()
    media_lookup = {**{k: v["source"] for k, v in ((prev or {}).get("media") or {}).items()}, **media_now}
    items = diff(prev, current, _visible_ids(), media_lookup)
    since = snap.created_at if snap else None

    scope = None
    if author or session_id:
        qs = AuditEntry.objects.all()
        if since:
            qs = qs.filter(at__gt=since)
        if author:
            qs = qs.filter(actor_name=author)
        if session_id:
            qs = qs.filter(connector_session=session_id)
        scope = {(r, p) for r, p in qs.values_list("resource", "pk_value")}

    page_of = {s["id"]: page_id for page_id, s in registry.all_sections()}
    top_label = {s["id"]: s["label"] for _p, s in registry.all_sections()}
    grouped = {}
    for item in items:
        section = item.pop("_section")
        labels = registry.field_labels(section)
        for f in item["fields"]:
            f["label"] = labels.get(f["name"], f["name"].replace("_", " ").capitalize())
        item["section"] = top_label.get(section["id"], section.get("label"))
        if scope is not None and (item["resource"], str(item["pk"])) not in scope:
            continue
        fields = [f["name"] for f in item["fields"]] if registry.RESOURCES[item["resource"]].kind == "singleton" else None
        entry = audit.last_entry(item["resource"], item["pk"], fields=fields, since=since)
        item.update(author=(entry.actor_name or None) if entry else None, channel=entry.channel if entry else None,
                    at=entry.at if entry else None, connector_session=entry.connector_session if entry else None,
                    session_id=entry.connector_session if entry else None)
        grouped.setdefault(page_of[section["id"]], []).append(item)
    order = [p["id"] for p in registry.REGISTRY["pages"]] + ["site"]
    titles = {p["id"]: p["title"] for p in registry.REGISTRY["pages"]} | {"site": "Header and footer"}
    pages = [{"page": p, "title": titles[p], "changes": grouped[p]} for p in order if p in grouped]
    return {"count": sum(len(p["changes"]) for p in pages), "pages": pages, "review_request": open_review_request()}


def open_review_request():
    """Addendum A5: the newest unresolved review request {by, at, note}, or None."""
    from .models import ReviewRequest

    rr = (ReviewRequest.objects.filter(resolved_at__isnull=True).select_related("requested_by")
          .order_by("-created_at", "-id").first())
    if rr is None:
        return None
    by = None
    if rr.requested_by:
        by = rr.requested_by.get_full_name() or rr.requested_by.get_username()
    return {"id": rr.id, "by": by, "at": rr.created_at, "note": rr.note}


def pages_with_changes():
    return {p["page"] for p in pending_changes()["pages"]}


# ---- writing snapshot rows back ---------------------------------------------------------------------------------
def _apply_row(obj, row, media_map, only=None):
    """Copy snapshot values onto a model instance (FKs by id, media back to their source file)."""
    for field in obj._meta.concrete_fields:
        name = field.name
        if name in IGNORED or name not in row or (only is not None and name not in only):
            continue
        value = row[name]
        if isinstance(value, list):
            continue
        if isinstance(field, models.ForeignKey):
            setattr(obj, field.attname, value)
        elif isinstance(field, models.FileField):
            current = getattr(obj, name)
            if not value and current and not current.storage.exists(current.name):
                continue  # missing on disk: published as "no file" already; keep the reference
            source = (media_map.get(value, {}) or {}).get("source", "") if value else ""
            if source and safe_media_path(source) is None:
                raise CMSError("CMS_VALIDATION", "A snapshot media entry points outside the media folder.", field=name)
            setattr(obj, name, source)
        else:
            setattr(obj, name, field.to_python(value) if value is not None else None)
    if hasattr(obj, "is_published") and (only is None or "is_published" in only):
        obj.is_published = True


def _restore_row(resource, row, data, ctx, action, item_id_value, done=None):
    """Upsert one collection row from snapshot `data` (re-creating missing FK parents first)."""
    done = done if done is not None else set()
    model = registry.RESOURCES[resource].model_class
    for field in model._meta.concrete_fields:
        if isinstance(field, models.ForeignKey) and row.get(field.name) is not None:
            parent_res = registry.FK_RESOURCES.get((resource, field.name))
            if parent_res and not field.related_model.objects.filter(pk=row[field.name]).exists():
                parent_row = _rows_by_id(data["collections"].get(parent_res)).get(row[field.name])
                if parent_row is None:
                    raise CMSError("CMS_VALIDATION", f"Cannot restore {item_id_value}: its {field.name} no longer exists.")
                _restore_row(parent_res, parent_row, data, ctx, action,
                             registry.item_id(parent_res, parent_row["id"], parent_row, _lookup_factory(data)), done)
    obj = model.objects.select_for_update().filter(pk=row["id"]).first()  # caller holds the transaction
    before = audit.row_values(obj)
    if obj is None:
        obj = model(pk=row["id"])
    _apply_row(obj, row, data.get("media") or {})
    after_preview = audit.row_values(obj)
    if before is not None and {k: v for k, v in before.items() if k != "version"} == \
            {k: v for k, v in after_preview.items() if k != "version"}:
        return False
    obj.save()
    audit.record(ctx, action, resource, obj.pk, before, audit.row_values(obj), item_id_value)
    done.add((resource, obj.pk))
    return True


def discard_item(item_id_value, *, ctx):
    """Revert one item to its last published values. Returns True if anything changed."""
    try:
        section_id, resource, pk = registry.parse_item_id(item_id_value)
    except ValueError as e:
        raise CMSError("CMS_NOT_FOUND", str(e)) from None
    prev, _snap = baseline()
    if prev is None:
        raise CMSError("CMS_VALIDATION", "Nothing has been published yet, so there is nothing to revert to.",
                       fix="Publish once (or run manage.py create_baseline_snapshot) before discarding changes.")
    res = registry.RESOURCES[resource]
    model = res.model_class
    section = registry.section_view(section_id, resource)
    with stale_as_409(resource), transaction.atomic():
        if res.kind == "singleton":
            prev_row = (prev.get("singletons") or {}).get(resource) or {}
            model.load()
            obj = model.objects.select_for_update().get(pk=1)
            before = audit.row_values(obj)
            _apply_row(obj, prev_row, prev.get("media") or {}, only=set(_section_field_order(section)))
            if audit.row_values(obj) == before:
                return False
            obj.save()
            audit.record(ctx, "discard", resource, obj.pk, before, audit.row_values(obj), item_id_value)
            return True
        prev_row = _rows_by_id((prev.get("collections") or {}).get(resource)).get(pk)
        if prev_row is None:
            obj = model.objects.select_for_update().filter(pk=pk).first()
            if obj is None:
                raise CMSError("CMS_NOT_FOUND", f"{item_id_value} does not exist.")
            before = audit.row_values(obj)
            obj.delete()  # added since the last publish: discarding removes it
            audit.record(ctx, "discard", resource, pk, before, None, item_id_value)
            return True
        return _restore_row(resource, prev_row, prev, ctx, "discard", item_id_value)


def discard_session(session_id, *, ctx):
    """Revert every item a connector session touched since the last publish. Returns the reverted item ids."""
    _prev, snap = baseline()
    qs = AuditEntry.objects.filter(connector_session=session_id).exclude(action__in=["discard", "restore"])
    if snap:
        qs = qs.filter(at__gt=snap.created_at)
    reverted, seen = [], set()
    for iid in qs.order_by("-at", "-id").values_list("item_id", flat=True):
        if not iid or iid in seen:
            continue
        seen.add(iid)
        try:
            if discard_item(iid, ctx=ctx):
                reverted.append(iid)
        except CMSError as e:
            if e.code != "CMS_NOT_FOUND":
                raise
    return reverted


def restore_snapshot(snapshot, *, ctx):
    """Make the CMS match a past snapshot (as unpublished changes). Rows not in it are hidden, never deleted."""
    data = snapshot.data
    count = 0
    lookup = _lookup_factory(data)
    with stale_as_409(), transaction.atomic():
        for resource, res in registry.RESOURCES.items():
            model = res.model_class
            if res.kind == "singleton":
                row = (data.get("singletons") or {}).get(resource)
                if not row:
                    continue
                model.load()
                obj = model.objects.select_for_update().get(pk=1)
                before = audit.row_values(obj)
                _apply_row(obj, row, data.get("media") or {})
                if audit.row_values(obj) != before:
                    obj.save()
                    audit.record(ctx, "restore", resource, obj.pk, before, audit.row_values(obj),
                                 registry.item_id(resource, obj.pk))
                    count += 1
                continue
            rows = (data.get("collections") or {}).get(resource) or []
            for row in rows:
                if _restore_row(resource, row, data, ctx, "restore", registry.item_id(resource, row["id"], row, lookup)):
                    count += 1
            keep = {r["id"] for r in rows}
            if res.has_visibility:
                for obj in model.objects.select_for_update().filter(is_published=True).exclude(pk__in=keep):
                    before = audit.row_values(obj)
                    obj.is_published = False
                    obj.save()
                    audit.record(ctx, "restore", resource, obj.pk, before, audit.row_values(obj),
                                 registry.item_id(resource, obj.pk, obj))
                    count += 1
    return count
