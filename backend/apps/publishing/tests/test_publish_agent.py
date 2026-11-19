"""Publish orchestration, worker, deterministic tarball, agent endpoints (contract §3, §5)."""
import hashlib
import json
import tarfile
import time
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.carousel.models import HeroSlide
from apps.publishing import publish
from apps.publishing.agent import build_signature, sign
from apps.publishing.models import AgentState, Publish, ReviewRequest, Snapshot
from apps.publishing.snapshot import avif_supported
from tests.support.errors import assert_contract_error

from .a4 import assert_a4_error
from .conftest import SECRET, image_file

pytestmark = pytest.mark.django_db


def agent_call(client, method, path, body=b"", ts=None, secret=SECRET):
    ts = str(int(ts if ts is not None else time.time()))
    headers = {"HTTP_X_AGENT_TIMESTAMP": ts, "HTTP_X_AGENT_SIGNATURE": sign(secret, method, path, ts, body)}
    if method == "GET":
        return client.get(path, **headers)
    return client.generic(method, path, body, content_type="application/json", **headers)


def built(publisher):
    p = publish.start_publish(publisher)
    assert publish.run_once().pk == p.pk
    p.refresh_from_db()
    return p


# ---- start / single flight / guard -------------------------------------------------------------------------------
def test_publish_endpoint_queues_and_reports_status(api_as, content, publish_env):
    client = api_as("publisher")
    resp = client.post("/api/v1/cms/publish/", {}, format="json")
    assert resp.status_code == 202 and resp.json()["status"] == "queued"
    pid = resp.json()["publish_id"]
    status = api_as("editor").get(f"/api/v1/cms/publish/{pid}/").json()
    assert status["status"] == "queued" and set(status) >= {"status", "step", "message", "live_at", "agent_last_seen"}


def test_editor_cannot_publish(api_as, content, publish_env):
    assert_contract_error(api_as("editor").post("/api/v1/cms/publish/", {}, format="json"), "CMS_FORBIDDEN_ROLE")


def test_two_publishers_one_build(api_as, content, publish_env, cms_admin):
    first = api_as("publisher").post("/api/v1/cms/publish/", {}, format="json")
    second = api_as(cms_admin).post("/api/v1/cms/publish/", {}, format="json")
    assert first.status_code == 202
    body = assert_a4_error(second, "CMS_PUBLISH_RUNNING")
    assert first.json()["publish_id"] in body["message"] and body["publish_id"] == first.json()["publish_id"]
    assert Publish.objects.count() == 1


def test_single_flight_is_enforced_by_the_database(content, publish_env, publisher):
    from django.db import IntegrityError, transaction
    p = publish.start_publish(publisher)
    with pytest.raises(IntegrityError), transaction.atomic():
        Publish.objects.create(snapshot=p.snapshot, created_by=publisher)


def test_snapshot_is_taken_at_publish_time(content, publish_env, publisher):
    p = publish.start_publish(publisher)
    HeroSlide.objects.filter(pk=18).update(heading="Typed after pressing publish")
    publish.run_once()
    p.refresh_from_db()
    assert p.status == Publish.READY
    data = json.loads(open(p.snapshot_path).read())
    assert "Typed after pressing publish" not in json.dumps(data)


def test_guard_abort_returns_422_and_nothing_queued(api_as, content, publish_env, publisher):
    p = built(publisher)
    agent_status(p, "live")
    from apps.facilities.models import Equipment
    Equipment.objects.all().update(is_published=False)  # 3 -> 0
    resp = api_as("publisher").post("/api/v1/cms/publish/", {}, format="json")
    body = assert_a4_error(resp, "CMS_BUILD_GUARD")
    assert "equipment shrinks from 3 to 0" in body["message"]
    assert {"resource": "equipment", "before": 3, "after": 0} in body["details"]
    assert Publish.objects.count() == 1
    ok = api_as("publisher").post("/api/v1/cms/publish/", {"confirm_shrink": True}, format="json")
    assert ok.status_code == 202


# ---- worker -----------------------------------------------------------------------------------------------------
def test_worker_builds_tarball_per_contract(content, publish_env, publisher, media_root):
    from apps.facilities.models import Equipment
    image_file(media_root / "equipment" / "big.jpg", 1700, 900)
    Equipment.objects.filter(pk=Equipment.objects.first().pk).update(image="equipment/big.jpg")
    p = built(publisher)
    assert p.status == Publish.READY and p.step == "waiting for upload machine"
    assert p.tarball_sha256 == hashlib.sha256(open(p.tarball_path, "rb").read()).hexdigest()
    assert p.tarball_path.endswith(f"crtdh-site-{p.snapshot.snapshot_id}.tar.gz")
    with tarfile.open(p.tarball_path) as tar:
        names = tar.getnames()
        members = tar.getmembers()
        manifest = json.loads(tar.extractfile("manifest.json").read())
    assert "site/index.html" in names and "site/team/index.html" in names and "site/assets/app.js" in names
    assert all(m.isfile() or m.isdir() for m in members)
    assert all(n.split("/")[0] in ("site", "media", "manifest.json") for n in names)
    assert manifest["snapshot_id"] == p.snapshot.snapshot_id and manifest["publish_id"] == str(p.id)
    key = next(iter(p.snapshot.data["media"]))
    h16 = key.rsplit("/", 1)[1].split(".")[0]
    fmts = ["webp", "avif"] if avif_supported() else ["webp"]
    assert set(manifest["media"]) == {f"{h16}.jpg"} | {f"{h16}-{w}.{fmt}" for w in (480, 960, 1600) for fmt in fmts}
    assert manifest["media_included"] == manifest["media"]
    assert {f"media/{n}" for n in manifest["media"]} <= set(names)


def test_only_new_media_after_a_live_publish(content, publish_env, publisher, media_root):
    from apps.facilities.models import Equipment
    image_file(media_root / "equipment" / "a.jpg", 600, 400)
    first, second = Equipment.objects.order_by("id")[:2]
    Equipment.objects.filter(pk=first.pk).update(image="equipment/a.jpg")
    p1 = built(publisher)
    agent_status(p1, "live")
    image_file(media_root / "equipment" / "b.jpg", 600, 400, color=(200, 10, 10))
    Equipment.objects.filter(pk=second.pk).update(image="equipment/b.jpg")
    p2 = built(publisher)
    with tarfile.open(p2.tarball_path) as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())
    per_image = 3 if avif_supported() else 2  # original + 480 px variant(s)
    assert len(manifest["media"]) == 2 * per_image and len(manifest["media_included"]) == per_image


def test_baseline_media_is_still_shipped(content, publish_env, publisher, media_root, baseline):
    from apps.facilities.models import Equipment
    image_file(media_root / "equipment" / "a.jpg", 600, 400)
    Equipment.objects.filter(pk=Equipment.objects.first().pk).update(image="equipment/a.jpg")
    from django.core.management import call_command
    call_command("create_baseline_snapshot", "--force", stdout=open("/dev/null", "w"))  # baseline now has the photo
    p = built(publisher)
    with tarfile.open(p.tarball_path) as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())
    assert manifest["media_included"] == manifest["media"] and manifest["media"]


def test_same_snapshot_builds_byte_identical_tarball(content, publish_env, publisher):
    p = built(publisher)
    first = open(p.tarball_path, "rb").read()
    # rebuild the same publish from scratch (as a retry would)
    Publish.objects.filter(pk=p.pk).update(status=Publish.QUEUED)
    publish.run_once()
    p.refresh_from_db()
    assert open(p.tarball_path, "rb").read() == first and p.attempts == 2


def test_crashed_build_is_retried(content, publish_env, publisher):
    p = publish.start_publish(publisher)
    Publish.objects.filter(pk=p.pk).update(status=Publish.BUILDING, step="frontend")
    assert publish.run_once() is None  # fresh "building" is someone else's
    Publish.objects.filter(pk=p.pk).update(updated_at=timezone.now() - timedelta(hours=1))
    assert publish.run_once().pk == p.pk
    p.refresh_from_db()
    assert p.status == Publish.READY


def test_failed_frontend_build_fails_publish_and_releases_lock(content, publish_env, publisher, monkeypatch):
    monkeypatch.setenv("FAKE_BUILD_FAIL", "1")
    p = built(publisher)
    assert p.status == Publish.FAILED and p.step == "frontend"
    assert "something broke" in p.message and "live site is unchanged" in p.message
    monkeypatch.delenv("FAKE_BUILD_FAIL")
    assert publish.start_publish(publisher).status == Publish.QUEUED


def test_worker_reruns_guard(content, publish_env, publisher):
    p = publish.start_publish(publisher)
    data = p.snapshot.data
    del data["collections"]["equipment"]
    Snapshot.objects.filter(pk=p.snapshot_id).update(data=data)
    publish.run_once()
    p.refresh_from_db()
    assert p.status == Publish.FAILED and p.step == "guard" and "equipment" in p.message


def test_worker_command_once(content, publish_env, publisher):
    from io import StringIO

    from django.core.management import call_command
    publish.start_publish(publisher)
    out = StringIO()
    call_command("run_publish_worker", "--once", stdout=out)
    assert "ready_for_upload" in out.getvalue()


def test_cancel(api_as, content, publish_env, publisher):
    p = publish.start_publish(publisher)
    resp = api_as("publisher").post(f"/api/v1/cms/publish/{p.id}/cancel/", {}, format="json")
    assert resp.status_code == 200 and resp.json()["status"] == "cancelled"
    assert publish.start_publish(publisher)


# ---- agent ------------------------------------------------------------------------------------------------------
def agent_status(p, status, step="switch", message=""):
    from django.test import Client
    body = json.dumps({"publish_id": str(p.id), "status": status, "step": step, "message": message}).encode()
    resp = agent_call(Client(), "POST", "/api/v1/agent/status/", body)
    p.refresh_from_db()
    return resp


def test_agent_auth(client, content, publish_env):
    assert_contract_error(client.get("/api/v1/agent/next/"), "CMS_UNAUTHENTICATED")
    assert agent_call(client, "GET", "/api/v1/agent/next/").status_code == 204
    assert_contract_error(agent_call(client, "GET", "/api/v1/agent/next/", secret="wrong"), "CMS_UNAUTHENTICATED")
    assert_contract_error(agent_call(client, "GET", "/api/v1/agent/next/", ts=time.time() - 301), "CMS_UNAUTHENTICATED")
    ts = str(int(time.time()) - 5)
    body = json.dumps({"publish_id": "00000000-0000-0000-0000-000000000000", "status": "live"}).encode()
    headers = {"HTTP_X_AGENT_TIMESTAMP": ts, "HTTP_X_AGENT_SIGNATURE": sign(SECRET, "POST", "/api/v1/agent/status/", ts, body)}
    first = client.post("/api/v1/agent/status/", body, content_type="application/json", **headers)
    assert_contract_error(first, "CMS_NOT_FOUND")  # authenticated, unknown publish
    assert_contract_error(client.post("/api/v1/agent/status/", body, content_type="application/json", **headers),
                          "CMS_UNAUTHENTICATED")  # replayed POST
    tampered = body.replace(b"live", b"fail")
    assert_contract_error(client.post("/api/v1/agent/status/", tampered, content_type="application/json", **headers),
                          "CMS_UNAUTHENTICATED")
    # a signature for one path does not work on another
    headers["HTTP_X_AGENT_TIMESTAMP"] = str(int(time.time()))
    headers["HTTP_X_AGENT_SIGNATURE"] = sign(SECRET, "GET", "/api/v1/agent/next/", headers["HTTP_X_AGENT_TIMESTAMP"], b"")
    assert client.post("/api/v1/agent/status/", b"", content_type="application/json", **headers).status_code == 401


def test_agent_signature_covers_the_query_string(client, content, publish_env):
    """R-17 / F-15: a signed request cannot have a query string added (or changed) after signing."""
    ts = str(int(time.time()))
    path_only = sign(SECRET, "GET", "/api/v1/agent/next/", ts, b"")
    hdr = {"HTTP_X_AGENT_TIMESTAMP": ts, "HTTP_X_AGENT_SIGNATURE": path_only}
    assert client.get("/api/v1/agent/next/", **hdr).status_code == 204  # today's agent: no query, unchanged
    assert_contract_error(client.get("/api/v1/agent/next/?x=1", **hdr), "CMS_UNAUTHENTICATED")
    with_query = sign(SECRET, "GET", "/api/v1/agent/next/?x=1", ts, b"")
    hdr["HTTP_X_AGENT_SIGNATURE"] = with_query
    assert client.get("/api/v1/agent/next/?x=1", **hdr).status_code == 204
    assert_contract_error(client.get("/api/v1/agent/next/?x=2", **hdr), "CMS_UNAUTHENTICATED")


def test_agent_refuses_everything_without_secret(client, content, publish_env, settings, api_as):
    settings.AGENT_HMAC_SECRET = ""
    assert agent_call(client, "GET", "/api/v1/agent/next/", secret="").status_code == 401
    assert api_as("admin").get("/api/v1/agent/next/").status_code == 401  # a CMS session is not agent auth


def test_agent_full_cycle(client, api_as, content, publish_env, publisher, editor):
    rr = ReviewRequest.objects.create(requested_by=editor, note="please")
    p = built(publisher)
    status = api_as("editor").get(f"/api/v1/cms/publish/{p.id}/").json()
    assert status["message"].startswith("Waiting for upload machine (last seen never)")

    nxt = agent_call(client, "GET", "/api/v1/agent/next/")
    assert nxt.status_code == 200
    job = nxt.json()
    assert job == {"publish_id": str(p.id), "snapshot_id": p.snapshot.snapshot_id,
                   "tarball_url": f"/api/v1/agent/builds/{p.id}.tar.gz", "sha256": p.tarball_sha256,
                   "signature": build_signature(SECRET, str(p.id), p.snapshot.snapshot_id, p.tarball_sha256)}
    assert AgentState.load().last_seen is not None
    dl = agent_call(client, "GET", job["tarball_url"])
    assert dl.status_code == 200 and hashlib.sha256(b"".join(dl.streaming_content)).hexdigest() == job["sha256"]

    assert agent_status(p, "uploading", "upload").status_code == 200 and p.status == "uploading"
    again = agent_call(client, "GET", "/api/v1/agent/next/", ts=time.time() - 1)  # distinct request, not a replay
    assert again.json()["publish_id"] == str(p.id)  # keeps being offered until live/failed
    assert agent_status(p, "live", "check_live").status_code == 200
    assert p.status == "live" and p.live_at is not None
    assert Snapshot.last_published().pk == p.snapshot_id
    rr.refresh_from_db()
    assert rr.resolved_at is not None
    assert agent_call(client, "GET", "/api/v1/agent/next/").status_code == 204
    assert agent_status(p, "live").status_code == 200  # idempotent
    assert_contract_error(agent_status(p, "uploading"), "CMS_VALIDATION")
    status = api_as("editor").get(f"/api/v1/cms/publish/{p.id}/").json()
    assert status["status"] == "live" and status["agent_last_seen"]


def test_agent_failure_keeps_previous_live(client, content, publish_env, publisher):
    p1 = built(publisher)
    agent_status(p1, "live")
    HeroSlide.objects.filter(pk=18).update(heading="Second")
    p2 = built(publisher)
    agent_status(p2, "uploading", "upload")
    agent_status(p2, "failed", "upload", "quota exceeded on the server")
    assert p2.status == "failed" and "quota exceeded" in p2.message and "live site is unchanged" in p2.message
    assert Snapshot.last_published().pk == p1.snapshot_id
    assert_contract_error(agent_call(client, "GET", f"/api/v1/agent/builds/{p2.id}.tar.gz"), "CMS_NOT_FOUND")
    assert publish.start_publish(publisher)  # lock released


@pytest.mark.regression_critical
def test_cannot_cancel_after_agent_fetched_the_tarball(api_as, client, content, publish_env, publisher):
    p = built(publisher)
    dl = agent_call(client, "GET", f"/api/v1/agent/builds/{p.id}.tar.gz")
    assert dl.status_code == 200
    b"".join(dl.streaming_content)
    p.refresh_from_db()
    assert p.fetched_at is not None
    resp = api_as("publisher").post(f"/api/v1/cms/publish/{p.id}/cancel/", {}, format="json")
    assert_contract_error(resp, "CMS_VALIDATION")
    assert agent_status(p, "live").status_code == 200
    assert p.status == Publish.LIVE and p.snapshot.__class__.objects.get(pk=p.snapshot_id).published_at


@pytest.mark.regression_critical
def test_agent_report_after_a_racing_cancel_is_recorded(api_as, content, publish_env, publisher):
    from apps.publishing.models import Snapshot
    p = built(publisher)
    Publish.objects.filter(pk=p.pk).update(status=Publish.CANCELLED)  # cancel won the race before the fetch mark
    assert agent_status(p, "live").status_code == 200
    assert p.status == Publish.LIVE and Snapshot.objects.get(pk=p.snapshot_id).published_at is not None
    q = built(publisher)
    Publish.objects.filter(pk=q.pk).update(status=Publish.CANCELLED)
    assert agent_status(q, "failed", step="upload", message="disk full").status_code == 200
    assert q.status == Publish.FAILED


def test_tarball_path_is_per_publish(content, publish_env, publisher):
    first = built(publisher)
    agent_status(first, "failed", step="upload", message="network")
    second = built(publisher)  # same content; same snapshot id when built within the same second
    assert first.tarball_path != second.tarball_path and str(second.id) in second.tarball_path
    assert second.tarball_path.endswith(f"crtdh-site-{second.snapshot.snapshot_id}.tar.gz")


def test_reorder_from_a_stale_read_is_409(content, editor, monkeypatch):
    from django.db.models import F

    from apps.core.models import NewsItem
    from apps.publishing import content as cms
    from apps.publishing.audit import WriteContext
    from apps.publishing.errors import CMSError
    ids = list(NewsItem.objects.order_by("order", "id").values_list("id", flat=True))
    real = NewsItem.objects.filter

    class Racing:
        def __init__(self, qs):
            self.qs = qs

        def select_for_update(self, **kw):
            rows = list(self.qs.select_for_update(**kw))
            NewsItem.objects.filter(pk=ids[0]).update(version=F("version") + 1)  # someone else saves meanwhile
            return rows

    with pytest.raises(CMSError) as exc:
        cms.reorder("news-items", list(reversed(ids)), ctx=WriteContext(user=editor), queryset=Racing(real()))
    assert exc.value.code == "CMS_STALE_VERSION"


# ---- QA wave 2 D2: a publish stuck in "uploading" ----------------------------------------------------------------
@pytest.mark.regression_critical
def test_uploading_publish_can_be_cancelled_until_the_tarball_is_fetched(api_as, client, content, publish_env,
                                                                         publisher):
    p = built(publisher)
    assert agent_status(p, "uploading", "download").status_code == 200  # agent reports, then its download fails
    assert p.fetched_at is None
    assert api_as("editor").get(f"/api/v1/cms/publish/{p.id}/").json()["cancellable"] is True
    resp = api_as("publisher").post(f"/api/v1/cms/publish/{p.id}/cancel/", {}, format="json")
    assert resp.status_code == 200 and resp.json()["status"] == "cancelled" and resp.json()["cancellable"] is False
    # the agent's next download is refused and it can't put the publish back into the single-flight slot
    assert_contract_error(agent_call(client, "GET", f"/api/v1/agent/builds/{p.id}.tar.gz"), "CMS_NOT_FOUND")
    assert_contract_error(agent_status(p, "uploading", "download", "retry"), "CMS_VALIDATION")  # distinct body
    assert p.status == Publish.CANCELLED
    assert publish.start_publish(publisher).status == Publish.QUEUED


def test_uploading_publish_cannot_be_cancelled_after_fetch(api_as, client, content, publish_env, publisher):
    p = built(publisher)
    agent_status(p, "uploading", "download")
    b"".join(agent_call(client, "GET", f"/api/v1/agent/builds/{p.id}.tar.gz").streaming_content)
    assert api_as("editor").get(f"/api/v1/cms/publish/{p.id}/").json()["cancellable"] is False
    assert_contract_error(api_as("publisher").post(f"/api/v1/cms/publish/{p.id}/cancel/", {}, format="json"),
                          "CMS_VALIDATION")


@pytest.mark.regression_critical
def test_uploading_without_agent_progress_times_out(content, publish_env, publisher, settings):
    settings.PUBLISH_STALE_UPLOAD_AFTER = 1800
    p = built(publisher)
    agent_status(p, "uploading", "download")
    Publish.objects.filter(pk=p.pk).update(updated_at=timezone.now() - timedelta(minutes=29))
    assert publish.expire_stale_uploads() == 0  # still within the window
    Publish.objects.filter(pk=p.pk).update(updated_at=timezone.now() - timedelta(minutes=31))
    nxt = publish.start_publish(publisher)  # the stale one is failed first, so this is not CMS_PUBLISH_RUNNING
    p.refresh_from_db()
    assert p.status == Publish.FAILED and p.step == publish.STALE_UPLOAD_STEP
    assert "no progress for 30 minutes" in p.message and "live site is unchanged" in p.message
    assert nxt.status == Publish.QUEUED


def test_worker_also_expires_stale_uploads_and_a_late_live_report_is_recorded(content, publish_env, publisher):
    p = built(publisher)
    agent_status(p, "uploading", "upload")
    Publish.objects.filter(pk=p.pk).update(updated_at=timezone.now() - timedelta(hours=2))
    publish.run_once()
    p.refresh_from_db()
    assert p.status == Publish.FAILED and p.step == publish.STALE_UPLOAD_STEP
    assert agent_status(p, "uploading").status_code == 400  # cannot re-take the slot
    assert agent_status(p, "live", "check_live").status_code == 200  # but what happened on the server is recorded
    assert p.status == Publish.LIVE and Snapshot.last_published().pk == p.snapshot_id
