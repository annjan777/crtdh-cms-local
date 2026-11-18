"""Publish agent endpoints (contract §3; wire format agreed with the publish-agent lane).

Auth: X-Agent-Timestamp (unix s) + X-Agent-Signature = hex HMAC-SHA256(AGENT_HMAC_SECRET,
      METHOD + "\n" + PATH + "\n" + TIMESTAMP + "\n" + hex sha256(body)), |now - ts| <= AGENT_MAX_SKEW,
      each (timestamp, signature) accepted once (replay protection).
"""
import hashlib
import hmac
import json
import time
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import FileResponse, HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .errors import STATUS, error_body
from .models import AgentNonce, AgentState, Publish, ReviewRequest, Snapshot

AGENT_STEPS = {"download", "verify", "upload", "switch", "check_live", "cleanup"}


def _err(code, message, **kw):
    return JsonResponse(error_body(code, message, **kw), status=STATUS[code])


def sign(secret, method, path, timestamp, body):
    msg = f"{method.upper()}\n{path}\n{timestamp}\n{hashlib.sha256(body or b'').hexdigest()}"
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()


def build_signature(secret, publish_id, snapshot_id, sha256):
    msg = f"crtdh-build-v1\n{publish_id}\n{snapshot_id}\n{sha256}"
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()


def _verify(request):
    secret = settings.AGENT_HMAC_SECRET
    ts = request.META.get("HTTP_X_AGENT_TIMESTAMP", "")
    sig = request.META.get("HTTP_X_AGENT_SIGNATURE", "").strip().lower()
    if not secret or not ts or not sig:
        return False
    try:
        ts_int = int(ts)
    except ValueError:
        return False
    if abs(time.time() - ts_int) > settings.AGENT_MAX_SKEW:
        return False
    expected = sign(secret, request.method, request.path, ts, request.body)
    if not hmac.compare_digest(expected, sig):
        return False
    try:
        with transaction.atomic():
            AgentNonce.objects.create(nonce=f"{ts_int}:{sig}")
    except IntegrityError:
        return False  # replayed
    AgentNonce.objects.filter(seen_at__lt=timezone.now() - timedelta(seconds=2 * settings.AGENT_MAX_SKEW + 60)).delete()
    AgentState.objects.update_or_create(pk=1, defaults={"last_seen": timezone.now()})
    return True


def agent_view(fn):
    @csrf_exempt
    def wrapped(request, *args, **kwargs):
        if not _verify(request):
            return _err("CMS_UNAUTHENTICATED", "Agent signature missing, invalid, expired or replayed.",
                        fix="Sign the request with the shared secret and a current timestamp.")
        return fn(request, *args, **kwargs)

    wrapped.__name__ = fn.__name__
    return wrapped


@agent_view
@require_GET
def next_build(request):
    p = (Publish.objects.filter(status__in=[Publish.READY, Publish.UPLOADING]).select_related("snapshot")
         .order_by("created_at").first())
    if p is None:
        return HttpResponse(status=204)
    snapshot_id = p.snapshot.snapshot_id
    return JsonResponse({
        "publish_id": str(p.id),
        "snapshot_id": snapshot_id,
        "tarball_url": f"/api/v1/agent/builds/{p.id}.tar.gz",
        "sha256": p.tarball_sha256,
        "signature": build_signature(settings.AGENT_HMAC_SECRET, str(p.id), snapshot_id, p.tarball_sha256),
    })


@agent_view
@require_GET
def download_build(request, publish_id):
    p = Publish.objects.filter(pk=publish_id, status__in=[Publish.READY, Publish.UPLOADING]).first()
    if p is None or not p.tarball_path:
        return _err("CMS_NOT_FOUND", "No downloadable build with that id.")
    try:
        fh = open(p.tarball_path, "rb")
    except OSError:
        return _err("CMS_NOT_FOUND", "The build file is gone; publish again.")
    return FileResponse(fh, content_type="application/gzip", as_attachment=True,
                        filename=f"crtdh-site-{p.snapshot.snapshot_id}.tar.gz")


ALLOWED = {
    Publish.READY: {Publish.UPLOADING, Publish.LIVE, Publish.FAILED},
    Publish.UPLOADING: {Publish.UPLOADING, Publish.LIVE, Publish.FAILED},
    Publish.LIVE: {Publish.LIVE},
    Publish.FAILED: {Publish.FAILED},
}


@agent_view
@require_POST
def post_status(request):
    try:
        body = json.loads(request.body or b"{}")
        publish_id, new = str(body["publish_id"]), str(body["status"])
    except (ValueError, KeyError, TypeError):
        return _err("CMS_VALIDATION", "Body must be JSON with publish_id and status.")
    step = str(body.get("step") or "")[:100]
    message = str(body.get("message") or "")[:2000]
    with transaction.atomic():
        p = Publish.objects.select_for_update().filter(pk=publish_id).first() if _is_uuid(publish_id) else None
        if p is None:
            return _err("CMS_NOT_FOUND", "Unknown publish id.")
        if new not in ALLOWED.get(p.status, set()):
            return _err("CMS_VALIDATION", f"Cannot move a {p.status} publish to {new}.", field="status")
        now = timezone.now()
        p.status, p.step = new, step or p.step
        if new == Publish.UPLOADING:
            p.message = message or "Uploading to the web server."
        elif new == Publish.FAILED:
            p.message = f"Upload failed at {step or 'upload'}: {message or 'no details'}. The live site is unchanged."
        elif new == Publish.LIVE and not p.live_at:
            p.live_at = now
            p.message = message or "Live."
            Snapshot.objects.filter(pk=p.snapshot_id).update(published_at=now)
            ReviewRequest.objects.filter(resolved_at__isnull=True, created_at__lte=p.created_at).update(resolved_at=now)
        p.save()
    return JsonResponse({"publish_id": str(p.id), "status": p.status})


def _is_uuid(value):
    import uuid

    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False
