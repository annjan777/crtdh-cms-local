"""Route walk (plan WS5.1): every /api/v1 route x anonymous / no role / editor / publisher / admin."""

import pytest
from django.urls import URLPattern, URLResolver, get_resolver, reverse

from apps.publishing import registry
from apps.publishing.models import Publish

pytestmark = [pytest.mark.django_db, pytest.mark.security]

LEVEL = {None: -1, "none": 0, "editor": 1, "publisher": 2, "admin": 3}
OWNED_ELSEWHERE = {"token-obtain-pair", "token-refresh", "auth-me"}  # backend-security's auth endpoints


def api_routes():
    names = set()

    def walk(patterns, prefix=""):
        for p in patterns:
            if isinstance(p, URLResolver):
                walk(p.url_patterns, prefix + str(p.pattern))
            elif isinstance(p, URLPattern) and p.name and (prefix + str(p.pattern)).startswith("api/v1/"):
                if "(?P<format>" not in str(p.pattern):
                    names.add(p.name)

    walk(get_resolver().url_patterns)
    return names


def check(resp, need, role, what):
    level = LEVEL[role]
    if need is None:
        expected = "agent"
        ok = resp.status_code == 401
    elif level < 0:
        expected, ok = 401, resp.status_code == 401
    elif level < need:
        expected, ok = 403, resp.status_code == 403
    else:
        expected, ok = "allowed", resp.status_code not in (401, 403) and resp.status_code < 500
    assert ok, f"{what} as {role}: got {resp.status_code}, expected {expected}: {resp.content[:200]!r}"
    return resp


@pytest.mark.parametrize("role", list(LEVEL))
def test_every_route_enforces_roles(role, api_as, baseline, publish_env, publisher):
    client = api_as(role)
    routes = api_routes()
    covered = set()
    running = Publish.objects.create(snapshot=baseline, created_by=publisher)

    def go(method, name, need, data=None, **kwargs):
        covered.add(name)
        url = reverse(name, kwargs=kwargs or None)
        resp = getattr(client, method)(url, data if data is not None else {}, format="json") if method != "get" \
            else client.get(url)
        return check(resp, need, role, f"{method.upper()} {url}")

    # content resources
    for resource in registry.COLLECTIONS:
        model = registry.RESOURCES[resource].model_class
        basename = next(b for prefix, _vs, b in __import__("config.urls", fromlist=["router"]).router.registry
                        if prefix == resource)
        obj = model.objects.order_by("id").first()
        go("get", f"{basename}-list", 1)
        go("post", f"{basename}-list", 1, {})
        go("get", f"{basename}-detail", 1, pk=obj.pk)
        go("patch", f"{basename}-detail", 1, {"expected_version": obj.version}, pk=obj.pk)
        go("put", f"{basename}-detail", 1, {"expected_version": obj.version}, pk=obj.pk)
        if f"{basename}-reorder" in routes:
            go("post", f"{basename}-reorder", 1, {"order": []})
        go("delete", f"{basename}-detail", 2, pk=obj.pk)
    for name in ("site-settings", "about-page", "home-page"):
        go("get", name, 1)
        go("patch", name, 1, {"expected_version": 999})
    go("get", "api-root", 1)

    # contact: public create, publisher-only inbox
    from apps.contact.models import ContactMessage
    msg = ContactMessage.objects.create(name="A", email="a@example.test", message="hi")
    covered.add("contact-create")
    resp = client.post(reverse("contact-create"), {}, format="json")
    assert resp.status_code not in (401, 403), resp.status_code
    go("get", "contact-message-list", 2)
    go("get", "contact-message-detail", 2, pk=msg.pk)
    go("delete", "contact-message-detail", 2, pk=msg.pk)

    # CMS
    go("get", "cms-pages", 1)
    go("get", "cms-page", 1, page_id="home")
    go("get", "cms-preview", 1, page_id="home")
    go("get", "cms-changes", 1)
    go("post", "cms-discard", 1, {})
    go("get", "cms-review-requests", 1)
    go("post", "cms-review-requests", 1, {"note": "x"})
    go("get", "cms-publish", 1)
    go("post", "cms-publish", 2, {})
    go("get", "cms-publish-detail", 1, publish_id=running.id)
    go("post", "cms-publish-cancel", 2, publish_id=running.id)
    go("get", "cms-snapshots", 1)
    go("post", "cms-snapshot-restore", 2, pk=baseline.pk)
    go("get", "cms-audit", 1)
    go("post", "cms-upload-links", 1, {})
    covered.add("cms-upload")  # token-authenticated: a bad token is 404 for everyone
    assert client.get(reverse("cms-upload", kwargs={"token": "bad"})).status_code == 404

    # publish agent: HMAC only, never a CMS session
    go("get", "agent-next", None)
    go("get", "agent-build", None, publish_id=running.id)
    go("post", "agent-status", None, {"publish_id": str(running.id), "status": "live"})

    missing = routes - covered - OWNED_ELSEWHERE
    assert not missing, f"routes without an RBAC expectation: {sorted(missing)}"


def test_django_admin_is_read_only_by_default_in_production(client, superuser, settings, content):
    assert settings.DEBUG is False and settings.DJANGO_ADMIN_READONLY is True
    client.force_login(superuser)
    assert client.get("/admin/carousel/heroslide/").status_code == 200  # can look
    assert client.get("/admin/carousel/heroslide/add/").status_code == 403
    resp = client.post("/admin/carousel/heroslide/18/change/", {"heading": "hacked"})
    assert resp.status_code in (403, 200)
    from apps.carousel.models import HeroSlide
    assert HeroSlide.objects.get(pk=18).heading != "hacked"
    assert client.post("/admin/carousel/heroslide/18/delete/", {"post": "yes"}).status_code == 403
    assert HeroSlide.objects.filter(pk=18).exists()


def test_django_admin_writable_when_setting_off(client, superuser, settings):
    settings.DJANGO_ADMIN_READONLY = False
    client.force_login(superuser)
    assert client.get("/admin/carousel/heroslide/add/").status_code == 200
