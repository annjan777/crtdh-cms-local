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
from apps.publishing.snapshot import avif_supported
from apps.publishing.models import AgentState, Publish, ReviewRequest, Snapshot
from tests.support.errors import assert_contract_error

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
    body = assert_contract_error(second, "CMS_PUBLISH_RUNNING")
    assert first.json()["publish_id"] in body["message"]
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
    body = assert_contract_error(resp, "CMS_BUILD_GUARD")
    assert "equipment shrinks from 3 to 0" in body["message"]
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
