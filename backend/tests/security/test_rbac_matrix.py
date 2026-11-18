"""Critical path: RBAC matrix — anonymous / editor / publisher / admin x every CMS API route (contract §3).

Allowed = response is not 401/403 (400/404/409 are fine: the gate let us through).
Denied  = contract §4 error with CMS_UNAUTHENTICATED (anon) or CMS_FORBIDDEN_ROLE (role).
Routes come from the DRF router so new resources are covered automatically.
"""
import pytest

from tests.support.content import resource_models
from tests.support.errors import assert_contract_error

pytestmark = [pytest.mark.needs_integration, pytest.mark.security]

ROLES = ["anon", "editor", "publisher", "admin"]
RANK = {"anon": -1, "editor": 0, "publisher": 1, "admin": 2}
SINGLETONS = ["site-settings", "about-page", "home-page"]
PRIVATE_RESOURCES = {"contact-messages"}  # read/delete by publisher+ (assumption, confirm with lead)


def _collection_routes():
    from config.urls import router
    out = []
    for prefix, _vs, _b in router.registry:
        if prefix in PRIVATE_RESOURCES:
            out += [("GET", f"/api/v1/{prefix}/", "publisher"), ("DELETE", f"/api/v1/{prefix}/{{pk:{prefix}}}/", "publisher")]
            continue
        out += [
            ("GET", f"/api/v1/{prefix}/", "editor"),
            ("POST", f"/api/v1/{prefix}/", "editor"),
            ("GET", f"/api/v1/{prefix}/{{pk:{prefix}}}/", "editor"),
            ("PATCH", f"/api/v1/{prefix}/{{pk:{prefix}}}/", "editor"),
            ("POST", f"/api/v1/{prefix}/reorder/", "editor"),
            ("DELETE", f"/api/v1/{prefix}/{{pk:{prefix}}}/", "publisher"),
        ]
    return out


CMS_ROUTES = [
    ("GET", "/api/v1/auth/me/", "editor"),
    ("GET", "/api/v1/cms/pages/", "editor"),
    ("GET", "/api/v1/cms/pages/home/", "editor"),
    ("GET", "/api/v1/cms/preview/home/", "editor"),
    ("GET", "/api/v1/cms/changes/", "editor"),
    ("POST", "/api/v1/cms/changes/discard/", "editor"),
    ("POST", "/api/v1/cms/review-requests/", "editor"),
    ("POST", "/api/v1/cms/publish/", "publisher"),
    ("GET", "/api/v1/cms/publish/1/", "editor"),
    ("GET", "/api/v1/cms/snapshots/", "editor"),
    ("POST", "/api/v1/cms/snapshots/1/restore/", "publisher"),
    ("GET", "/api/v1/cms/audit/", "editor"),
    ("POST", "/api/v1/cms/upload-links/", "editor"),
] + [(m, f"/api/v1/{s}/", "editor") for s in SINGLETONS for m in ("GET", "PATCH")]


def _routes():
    try:
        return _collection_routes() + CMS_ROUTES
    except Exception:  # router import fails before django setup during collection
        return CMS_ROUTES


ALL = _routes()


def _resolve(path, models):
    if "{pk:" in path:
        prefix = path.split("{pk:")[1].split("}")[0]
        obj = models[prefix].objects.order_by("pk").first()
        path = path.replace(f"{{pk:{prefix}}}", str(obj.pk if obj else 999999))
    return path


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("method,path,min_role", ALL, ids=[f"{m} {p}" for m, p, _ in ALL])
def test_rbac(api_as, sample_content, role, method, path, min_role):
    client = api_as(None if role == "anon" else role)
    url = _resolve(path, resource_models())
    resp = getattr(client, method.lower())(url, {} if method != "GET" else None, format="json")
    allowed = RANK[role] >= RANK[min_role]
    if allowed:
        assert resp.status_code not in (401, 403), f"{role} should reach {method} {url}: {resp.status_code}"
    elif role == "anon":
        assert_contract_error(resp, "CMS_UNAUTHENTICATED")
    else:
        assert_contract_error(resp, "CMS_FORBIDDEN_ROLE")


def test_every_router_resource_is_in_matrix():
    from config.urls import router
    covered = {p.split("/")[3] for _, p, _ in ALL if p.count("/") >= 4}
    assert {prefix for prefix, *_ in router.registry} <= covered


def test_only_public_write_is_contact(api, sample_content):
    """Anonymous: every unsafe method on every route except POST /contact/ is refused."""
    from django.urls import get_resolver
    resp = api.post("/api/v1/contact/", {}, format="json")
    assert resp.status_code in (400, 429), "contact relay must be reachable anonymously"
    for method, path, _ in ALL:
        if method == "GET":
            continue
        r = getattr(api, method.lower())(_resolve(path, resource_models()), {}, format="json")
        assert r.status_code in (401, 403), f"anon {method} {path} -> {r.status_code}"
    assert get_resolver()  # keep import used


def test_deactivated_user_session_stops_working(api_as, editor):
    client = api_as(editor)
    assert client.get("/api/v1/auth/me/").status_code == 200
    editor.is_active = False
    editor.save()
    assert client.get("/api/v1/auth/me/").status_code in (401, 403)
