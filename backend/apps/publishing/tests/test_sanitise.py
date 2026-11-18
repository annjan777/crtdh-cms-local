"""Lead review HIGH: rich text cleaned and unsafe links refused on every write path; existing rows cleaned."""
import importlib

import pytest

from apps.common.sanitize import clean_richtext, safe_url
from apps.core.models import AboutPage, NavItem, NewsItem
from apps.publishing import changes
from apps.publishing import content as cms
from apps.publishing.audit import WriteContext
from apps.publishing.errors import CMSError
from tests.support.errors import assert_contract_error

pytestmark = pytest.mark.regression_critical
EVIL = '<p>Hi<img src=x onerror="alert(1)"><script>alert(2)</script><a href="javascript:alert(3)" onclick="x">j</a>' \
       '<a href="//evil.example">e</a><a href="https://iitkgp.ac.in" target="_blank">ok</a><h2>x</h2><h3>t</h3></p>'


def assert_clean(html):
    low = html.lower()
    for bad in ("<img", "onerror", "<script", "javascript:", "onclick", "//evil", "target=", "<h2"):
        assert bad not in low, (bad, html)
    assert '<a href="https://iitkgp.ac.in" rel="noopener">ok</a>' in html and "<h3>t</h3>" in html


def test_clean_richtext_allow_list():
    assert_clean(clean_richtext(EVIL))
    keep = "<p><strong>b</strong> <b>b</b> <em>i</em> <i>i</i><br></p><ul><li>a</li></ul><ol><li>b</li></ol>"
    assert clean_richtext(keep) == keep
    assert clean_richtext("R&D centre, plain text") == "R&D centre, plain text"
    assert clean_richtext('<a href="/about">a</a><a href="mailto:x@y.in">m</a>') == \
        '<a href="/about" rel="noopener">a</a><a href="mailto:x@y.in" rel="noopener">m</a>'


@pytest.mark.parametrize("url", ["https://iitkgp.ac.in", "http://x.in/a?b=1", "/about", "#team", "about",
                                 "mailto:crtdh@iitkgp.ac.in", "tel:+913222", "", None])
def test_safe_urls_allowed(url):
    assert safe_url(url)


@pytest.mark.parametrize("url", ["//evil.example", "/\\evil.example", "javascript:alert(1)", " JavaScript:x",
                                 "java\tscript:x", "java\u200bscript:x", "&#106;avascript:x", "data:text/html,<b>", "vbscript:x",
                                 "ftp://x", "file:///etc/passwd"])
def test_unsafe_urls_refused(url):
    assert not safe_url(url)


@pytest.mark.django_db
def test_api_patch_and_create_clean_richtext(api_as, content):
    client = api_as("editor")
    v = client.get("/api/v1/about-page/").json()["version"]
    resp = client.patch("/api/v1/about-page/", {"intro": EVIL, "dsir_about": EVIL, "expected_version": v},
                        format="json")
    assert resp.status_code == 200, resp.content
    about = AboutPage.load()
    assert_clean(about.intro)
    assert_clean(about.dsir_about)
    created = client.post("/api/v1/innovations/", {"title": "T", "body": EVIL}, format="json")
    assert created.status_code == 201
    assert_clean(created.json()["body"])


@pytest.mark.django_db
def test_mcp_paths_clean_richtext_and_refuse_links(content, editor):
    ctx = WriteContext(user=editor, channel="mcp", connector_session="s1")
    v = AboutPage.load().version
    cms.update_by_item_id("about.intro.about-page:1", {"mission_vision": EVIL}, ctx=ctx, expected_version=v)
    assert_clean(AboutPage.load().mission_vision)
    with pytest.raises(CMSError) as exc:
        cms.create_item("news-items", {"text": "x", "link_url": "javascript:alert(1)"}, ctx=ctx, section_id="home.news")
    assert exc.value.code == "CMS_VALIDATION" and exc.value.body["field"] == "link_url"
    nav = NavItem.objects.first()
    with pytest.raises(CMSError):
        cms.update_by_item_id(f"site.nav.nav-items:{nav.pk}", {"url": "//evil.example"}, ctx=ctx,
                              expected_version=nav.version)
    assert NavItem.objects.get(pk=nav.pk).url == nav.url


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["javascript:alert(1)", "//evil.example", "data:text/html,x"])
def test_api_refuses_unsafe_links(api_as, content, url):
    client = api_as("editor")
    item = NewsItem.objects.first()
    resp = client.patch(f"/api/v1/news-items/{item.pk}/", {"link_url": url, "expected_version": item.version},
                        format="json")
    assert_contract_error(resp, "CMS_VALIDATION", field="link_url")
    v = client.get("/api/v1/site-settings/").json()["version"]
    assert_contract_error(client.patch("/api/v1/site-settings/", {"facebook_url": url, "expected_version": v},
                                       format="json"), "CMS_VALIDATION")


@pytest.mark.django_db
def test_discard_and_restore_clean_dirty_snapshot_values(baseline, editor):
    ctx = WriteContext(user=editor)
    data = baseline.data
    data["singletons"]["about-page"]["intro"] = EVIL  # an old snapshot taken before sanitising existed
    baseline.data = data
    baseline.save(update_fields=["data"])
    cms.update_item("about-page", 1, {"intro": "draft"}, ctx=ctx, expected_version=AboutPage.load().version)
    assert changes.discard_item("about.intro.about-page:1", ctx=ctx)
    assert_clean(AboutPage.load().intro)
    cms.update_item("about-page", 1, {"intro": "draft 2"}, ctx=ctx, expected_version=AboutPage.load().version)
    changes.restore_snapshot(baseline, ctx=ctx)
    assert_clean(AboutPage.load().intro)


@pytest.mark.django_db
def test_restore_refuses_unsafe_link_in_snapshot(baseline, editor):
    data = baseline.data
    data["collections"]["nav-items"][0]["url"] = "javascript:alert(1)"
    baseline.data = data
    baseline.save(update_fields=["data"])
    NavItem.objects.filter(pk=data["collections"]["nav-items"][0]["id"]).update(url="/changed")
    with pytest.raises(CMSError) as exc:
        changes.restore_snapshot(baseline, ctx=WriteContext(user=editor))
    assert exc.value.code == "CMS_VALIDATION"


@pytest.mark.django_db
def test_data_migration_cleans_existing_rows(content):
    from django.apps import apps
    AboutPage.load()
    AboutPage.objects.filter(pk=1).update(intro=EVIL, iitkgp_about="R&D, plain")  # bypasses the hook
    nav = NavItem.objects.first()
    NavItem.objects.filter(pk=nav.pk).update(url="javascript:alert(1)")
    before = AboutPage.objects.get(pk=1).version
    mig = importlib.import_module("apps.publishing.migrations.0003_sanitise_existing_content")
    mig.forwards(apps, None)
    about = AboutPage.objects.get(pk=1)
    assert_clean(about.intro)
    assert about.iitkgp_about == "R&D, plain" and about.version == before + 1
    assert NavItem.objects.get(pk=nav.pk).url == ""
