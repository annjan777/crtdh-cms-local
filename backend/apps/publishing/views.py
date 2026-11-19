"""CMS endpoints (contract §3 "CMS" + addendum 1). Session auth; roles from apps.accounts.roles."""
import os

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.roles import IsEditor, IsPublisher

from . import changes, publish, registry, review, snapshot, uploads
from .audit import context_from_request, serialize_entry
from .errors import CMSError, error_body
from .models import AgentState, AuditEntry, Publish, ReviewRequest, Snapshot


class EditorView(APIView):
    permission_classes = [IsEditor]


class PublisherView(APIView):
    permission_classes = [IsPublisher]


# ---- pages ------------------------------------------------------------------------------------------------------
def _page_summary(page, changed):
    return {"id": page["id"], "path": page["path"], "title": page["title"], "has_changes": page["id"] in changed,
            "sections": [{"id": s["id"], "label": s["label"], "kind": s["kind"], "resource": s["resource"]}
                         for s in page["sections"]]}


class PagesView(EditorView):
    def get(self, request):
        changed = changes.pages_with_changes()
        exported = registry.export_registry()
        return Response({"pages": [_page_summary(p, changed) for p in exported["pages"]],
                         "globals": {"has_changes": "site" in changed,
                                     "sections": [{"id": s["id"], "label": s["label"], "kind": s["kind"],
                                                   "resource": s["resource"]} for s in exported["globals"]]}})


_dims_cache = {}


def _image_info(field_file):
    """{width, height, name} of a stored image (addendum A1 `media`), or None. Header-only read, cached."""
    if not field_file:
        return None
    name = field_file.name
    try:
        path = field_file.path
        st = os.stat(path)
    except (OSError, NotImplementedError, ValueError):
        return None
    key = (path, st.st_size, st.st_mtime_ns)
    if key not in _dims_cache:
        width = height = None
        try:
            from PIL import Image

            with Image.open(path) as im:
                width, height = im.size
        except Exception:  # noqa: BLE001, S110 - not a readable image (e.g. SVG); dims stay unknown
            pass
        _dims_cache[key] = (width, height)
    width, height = _dims_cache[key]
    return {"width": width, "height": height, "name": name.rsplit("/", 1)[-1]}


def _item(section_id, resource, obj, row, view):
    values = {k: v for k, v in row.items() if k != "version"}
    media = {fd["name"]: _image_info(getattr(obj, fd["name"], None))
             for fd in view["fields"] if fd["type"] == "image"}
    return {"item_id": f"{section_id}.{resource}:{obj.pk}", "pk": obj.pk, "version": obj.version,
            "is_published": row.get("is_published", True), "label": changes._label(resource, row, view),
            "values": values, "media": media}


def _section_items(section, request):
    """Addendum A1: [{item_id, pk, version, values, media, children}] (singletons: exactly one item).
    Draft = current DB, hidden rows included (they stay editable)."""
    res = registry.RESOURCES[section["resource"]]
    ctx = {"request": request}
    if res.kind == "singleton":
        obj = res.model_class.load()
        return [_item(section["id"], section["resource"], obj, res.serializer_class(obj, context=ctx).data, section)]
    qs = snapshot.queryset_for(section["resource"], include_hidden=True)
    if section.get("filter"):
        qs = qs.filter(**section["filter"])
    objs = list(qs)
    rows = res.serializer_class(objs, many=True, context=ctx).data
    items = [_item(section["id"], section["resource"], o, r, section) for o, r in zip(objs, rows, strict=True)]
    for child in section.get("children") or []:
        view = registry.section_view(section["id"], child["resource"])
        cres = registry.RESOURCES[child["resource"]]
        parent_ids = [o.pk for o in objs]
        cobjs = list(snapshot.queryset_for(child["resource"], include_hidden=True)
                     .filter(**{f"{child['parent_field']}__in": parent_ids}))
        crows = cres.serializer_class(cobjs, many=True, context=ctx).data
        grouped = {}
        for o, r in zip(cobjs, crows, strict=True):
            grouped.setdefault(getattr(o, f"{child['parent_field']}_id"), []).append(
                _item(section["id"], child["resource"], o, r, view))
        for it in items:
            it.setdefault("children", {})[child["resource"]] = grouped.get(it["pk"], [])
    return items


class PageDetailView(EditorView):
    def get(self, request, page_id):
        if page_id == "site":
            page = {"id": "site", "path": None, "title": "Site settings", "sections": registry.export_registry()["globals"]}
        else:
            page = next((p for p in registry.export_registry()["pages"] if p["id"] == page_id), None)
        if page is None:
            raise CMSError("CMS_NOT_FOUND", f"There is no page {page_id!r}.")
        changed = changes.pages_with_changes()
        sections = [{**s, "items": _section_items(s, request)} for s in page["sections"]]
        return Response({**page, "has_changes": page_id in changed, "sections": sections})


class PreviewView(EditorView):
    def get(self, request, page_id):
        data = snapshot.preview(page_id, request=request)
        if data is None:
            raise CMSError("CMS_NOT_FOUND", f"There is no page {page_id!r}.")
        return Response(data)


# ---- changes ----------------------------------------------------------------------------------------------------
class ChangesView(EditorView):
    def get(self, request):
        return Response(changes.pending_changes(author=request.query_params.get("author") or None,
                                                session_id=request.query_params.get("session_id") or None))


class DiscardView(EditorView):
    def post(self, request):
        ctx = context_from_request(request)
        item_id, session_id = request.data.get("item_id"), request.data.get("session_id")
        if bool(item_id) == bool(session_id):
            raise CMSError("CMS_VALIDATION", "Send either item_id or session_id.", field="item_id")
        if item_id:
            changed = changes.discard_item(str(item_id), ctx=ctx)
            reverted = [item_id] if changed else []
        else:
            reverted = changes.discard_session(str(session_id), ctx=ctx)
        now = changes.pending_changes()
        return Response({"reverted": reverted, "discarded": len(reverted), "pending": now["count"], **now})


class ReviewRequestsView(EditorView):
    def get(self, request):
        open_requests = ReviewRequest.objects.filter(resolved_at__isnull=True).select_related("requested_by")
        return Response({"open": [{"id": r.id, "note": r.note, "created_at": r.created_at,
                                   "requested_by": r.requested_by.get_username() if r.requested_by else None}
                                  for r in open_requests]})

    def post(self, request):
        note = request.data.get("note") or ""
        if not isinstance(note, str):
            raise CMSError("CMS_VALIDATION", "note must be text.", field="note")
        rr = review.request_review(request.user, note, ctx=context_from_request(request))
        return Response({"id": rr.id, "created_at": rr.created_at, "notified": len(review.publisher_emails())}, status=201)


# ---- publish ----------------------------------------------------------------------------------------------------
def publish_payload(p, agent_seen=None):
    now = timezone.now()
    message = p.message
    if p.status == Publish.READY:
        stale = agent_seen is None or (now - agent_seen).total_seconds() > 120
        if stale:
            seen = timezone.localtime(agent_seen).strftime("%d %b %H:%M") if agent_seen else "never"
            message = f"Waiting for upload machine (last seen {seen})."
    return {"id": str(p.id), "publish_id": str(p.id), "status": p.status, "step": p.step, "message": message,
            "live_at": p.live_at, "agent_last_seen": agent_seen, "created_at": p.created_at,
            "created_by": p.created_by.get_username() if p.created_by else None,
            "snapshot_id": p.snapshot.snapshot_id if p.snapshot_id else None, "attempts": p.attempts,
            "cancellable": publish.is_cancellable(p)}


class PublishView(APIView):
    def get_permissions(self):
        return [IsPublisher()] if self.request.method == "POST" else [IsEditor()]

    def get(self, request):
        seen = AgentState.load().last_seen
        qs = Publish.objects.select_related("snapshot", "created_by")[:50]
        return Response({"results": [publish_payload(p, seen) for p in qs]})

    def post(self, request):
        confirm = request.data.get("confirm_shrink", False)
        if not isinstance(confirm, bool):
            confirm = str(confirm).lower() in ("1", "true", "yes")
        p = publish.start_publish(request.user, confirm_shrink=confirm)
        return Response({"publish_id": str(p.id), "status": p.status}, status=202)


class PublishDetailView(EditorView):
    def get(self, request, publish_id):
        p = get_object_or_404(Publish.objects.select_related("snapshot", "created_by"), pk=publish_id)
        return Response(publish_payload(p, AgentState.load().last_seen))


class PublishCancelView(PublisherView):
    def post(self, request, publish_id):
        p = get_object_or_404(Publish, pk=publish_id)
        return Response(publish_payload(publish.cancel_publish(p), AgentState.load().last_seen))


# ---- snapshots --------------------------------------------------------------------------------------------------
class SnapshotsView(EditorView):
    """Addendum A8: {snapshots:[{id, snapshot_id, published_at, published_by, note, is_live}]}, newest first.
    Only snapshots that went live are listed (a failed or cancelled publish never changed the site)."""

    def get(self, request):
        live = publish.last_live_snapshot()
        out = []
        qs = Snapshot.objects.filter(published_at__isnull=False).select_related("created_by").order_by("-published_at", "-id")
        for s in qs[:50]:
            by = s.created_by.get_username() if s.created_by else (s.data or {}).get("published_by")
            out.append({"id": s.id, "snapshot_id": s.snapshot_id, "published_at": s.published_at,
                        "published_by": by, "note": s.note, "is_live": live is not None and s.pk == live.pk,
                        "counts": {k: len(v) for k, v in ((s.data or {}).get("collections") or {}).items()}})
        return Response({"snapshots": out})


class SnapshotRestoreView(PublisherView):
    def post(self, request, pk):
        snap = get_object_or_404(Snapshot, pk=pk)
        count = changes.restore_snapshot(snap, ctx=context_from_request(request))
        now = changes.pending_changes()
        return Response({"snapshot_id": snap.snapshot_id, "restored": count, "pending": now["count"], **now})


# ---- audit ------------------------------------------------------------------------------------------------------
class AuditView(EditorView):
    def get(self, request):
        qs = AuditEntry.objects.all()
        fields = None
        item_id = request.query_params.get("item_id")
        if item_id:
            try:
                section_id, resource, pk = registry.parse_item_id(item_id)
            except ValueError as e:
                raise CMSError("CMS_VALIDATION", str(e), field="item_id") from None
            qs = qs.filter(resource=resource, pk_value=str(pk))
            if registry.RESOURCES[resource].kind == "singleton":
                fields = registry.editable_fields(registry.section_view(section_id, resource)) - {"is_published", "order"}
        for param, lookup in (("resource", "resource"), ("session_id", "connector_session"), ("author", "actor_name")):
            if request.query_params.get(param):
                qs = qs.filter(**{lookup: request.query_params[param]})
        out = []
        for e in qs.order_by("-at", "-id")[:500]:
            if fields is not None:
                b, a = e.before or {}, e.after or {}
                if not any(b.get(n) != a.get(n) for n in fields):
                    continue
            out.append(serialize_entry(e, only=fields))
            if len(out) >= 200:
                break
        return Response({"entries": out})


# ---- upload links -----------------------------------------------------------------------------------------------
class UploadLinkSerializer(serializers.Serializer):
    min_width = serializers.IntegerField(required=False, min_value=0, max_value=10000, default=0)


class UploadLinksView(EditorView):
    def post(self, request):
        ser = UploadLinkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(uploads.create_upload_link(request.user, ctx=context_from_request(request),
                                                   min_width=ser.validated_data["min_width"], request=request),
                        status=201)


FORM = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Upload a photo — CRTDH CMS</title><link rel="stylesheet" href="{css}"></head><body><h1>Upload a photo</h1>{body}</body></html>"""


def _page(body, status=200):
    """The one-time upload page. Styles come from a static file: the CSP (style-src 'self') blocks inline CSS."""
    from django.templatetags.static import static

    return HttpResponse(FORM.format(css=escape(static("publishing/upload.css")), body=body), status=status)


def _size_hint():
    from django.conf import settings

    return f"up to {settings.UPLOAD_LIMITS['image'] // (1024 * 1024)} MB"


@csrf_exempt  # the one-time token in the URL is the credential; no session involved
def upload_page(request, token):
    link = uploads.get_link(token)
    wants_json = "application/json" in request.META.get("HTTP_ACCEPT", "")
    if link is None or (link.used_at is not None and request.method == "POST"):
        msg = "This upload link has expired or was already used. Ask for a new one."
        if wants_json:
            return JsonResponse(error_body("CMS_NOT_FOUND", msg, fix="Ask for a new upload link."), status=404)
        return _page(f"<p>{escape(msg)}</p>", status=404)
    if request.method == "GET":
        if link.used_at is not None:
            return _page("<p>Photo received. You can close this page.</p>")
        hint = f"<p class=note>At least {link.min_width} px wide. JPEG, PNG or WebP, {_size_hint()}.</p>" if link.min_width \
            else f"<p class=note>JPEG, PNG or WebP, {_size_hint()}.</p>"
        form = ('<form method="post" enctype="multipart/form-data">'
                '<label for="file">Photo</label><br><input id="file" name="file" type="file" accept="image/jpeg,image/png,image/webp" required>'
                f'{hint}<button type="submit">Upload photo</button></form>')
        return _page(form)
    if request.method != "POST":
        return HttpResponse(status=405)
    file = request.FILES.get("file")
    try:
        if file is None:
            raise CMSError("CMS_VALIDATION", "Choose a photo to upload.", field="file")
        asset = uploads.consume(link, file)
    except CMSError as e:
        if wants_json:
            return JsonResponse(e.body, status=e.status_code)
        return _page(f"<p>{escape(e.body['message'])}</p><p><a href=''>Try again</a></p>", status=e.status_code)
    if wants_json:
        return JsonResponse({"media_id": asset.pk, "width": asset.width, "height": asset.height}, status=201)
    return _page(f"<p>Photo received ({asset.width}×{asset.height}). You can close this page.</p>", status=201)
