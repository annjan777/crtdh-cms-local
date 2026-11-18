"""Every MCP tool: happy path, error codes and guardrails, through the real ASGI app."""

import pytest
from asgiref.sync import sync_to_async
from django.core import mail

from mcp_server.models import ConnectorWrite, ToolCall

from .conftest import make_user, mcp_client, stage_image

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio]

WRITE_KEYS = {"id", "version", "preview_url", "status", "message"}


@sync_to_async
def seed():
    from apps.carousel.models import HeroSlide
    from apps.core.models import HomePage, NewsItem
    from apps.media_gallery.models import MediaEvent
    from apps.team.models import TeamCategory, TeamMember

    cat = TeamCategory.objects.create(name="Faculty")
    TeamCategory.objects.create(name="Staff")
    sharma = TeamMember.objects.create(category=cat, name="Prof. Anil Sharma", designation="Associate Professor", order=0)
    TeamMember.objects.create(category=cat, name="Dr. Meera Iyer", designation="Scientist", order=1)
    slides = [HeroSlide.objects.create(image=f"hero_slides/s{i}.jpg", heading=f"Slide {i}", order=i) for i in range(3)]
    NewsItem.objects.create(text="Admissions open", order=0)
    MediaEvent.objects.create(title="Old camp", slug="old-camp", order=0)
    HomePage.load()
    return {"sharma": sharma, "slides": slides}


async def call(client, name, args=None):
    return await client.call_tool(name, args or {})


def ok(res):
    assert not res.is_error, res.content[0].text
    return res.structured_content


def err(res, code):
    assert res.is_error, res.structured_content
    body = res.structured_content
    assert body["code"] == code, body
    assert {"code", "message", "fix", "retryable", "side_effects", "request_id", "field", "current_version"} <= set(body)
    assert body["fix"]
    return body


async def find_one(client, query):
    return ok(await call(client, "find_content", {"query": query}))["matches"][0]


# ---------------------------------------------------------------- tool surface
async def test_tool_surface(asgi_app, token):
    async with mcp_client(asgi_app, token) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    banned = ("publish", "delete", "user", "role", "password", "token")
    assert not [n for n in tools if any(b in n for b in banned)]
    reads = {"find_content", "get_page", "list_pending_changes", "search_media", "get_preview_link"}
    assert reads <= set(tools)
    for name, tool in tools.items():
        if name in reads:
            assert tool.annotations.read_only_hint is True
        else:
            assert tool.annotations.read_only_hint is False and tool.annotations.destructive_hint is False
    for name in ("find_content", "get_page"):
        assert "not instructions" in tools[name].description
    for name in ("update_team_member", "add_media_event", "hide_hero_slide", "update_section", "reorder",
                 "discard_change", "discard_session_changes", "request_upload_link", "upload_image_from_url",
                 "request_review", "add_news_item"):
        assert name in tools, name


# ---------------------------------------------------------------- reads
async def test_find_and_get_page(asgi_app, token):
    await seed()
    async with mcp_client(asgi_app, token) as client:
        match = await find_one(client, "prof. sharma")
        assert match["id"].startswith("team.members.team-members:")
        assert match["page"] == "team" and isinstance(match["version"], int)
        err(await call(client, "find_content", {"query": "   "}), "CMS_VALIDATION")
        page = ok(await call(client, "get_page", {"page": "home"}))
        hero = next(s for s in page["sections"] if s["id"] == "home.hero")
        assert [i["position"] for i in hero["items"]] == [1, 2, 3]
        assert hero["items"][2]["values"]["heading"] == "Slide 2"
        assert next(f for f in hero["fields"] if f["name"] == "image")["min_width"] == 1600
        about = next(s for s in page["sections"] if s["kind"] == "singleton")
        assert about["item"]["id"] == "home.about.home-page:1"
        err(await call(client, "get_page", {"page": "nope"}), "CMS_NOT_FOUND")


async def test_preview_link_is_cms_gated(asgi_app, token):
    await seed()
    async with mcp_client(asgi_app, token) as client:
        data = ok(await call(client, "get_preview_link", {"page": "team"}))
        assert data["preview_url"] == "https://cms.example.org/pages/team"
        assert "token" not in data["preview_url"]
        err(await call(client, "get_preview_link", {"page": "team", "item_id": "team.members.team-members:999"}),
            "CMS_NOT_FOUND")


# ---------------------------------------------------------------- updates and versions
async def test_update_team_member_and_stale_version(asgi_app, token):
    await seed()
    async with mcp_client(asgi_app, token) as client:
        m = await find_one(client, "Sharma")
        res = ok(await call(client, "update_team_member", {
            "id": m["id"], "fields": {"designation": "Professor"}, "expected_version": m["version"]}))
        assert WRITE_KEYS <= set(res) and res["status"] == "draft"
        assert res["message"] == "Not live yet — a Publisher must publish it."
        assert res["preview_url"] == f"https://cms.example.org/pages/team?item={m['id'].replace(':', '%3A')}"
        assert res["version"] != m["version"]
        stale = err(await call(client, "update_team_member", {
            "id": m["id"], "fields": {"designation": "Dean"}, "expected_version": m["version"]}), "CMS_STALE_VERSION")
        assert stale["current_version"] == res["version"] and stale["side_effects"] == "none"
        text = (await call(client, "update_team_member", {
            "id": m["id"], "fields": {"designation": "Dean"}, "expected_version": m["version"]})).content[0].text
        assert text.startswith("CMS_STALE_VERSION:")

    from apps.team.models import TeamMember
    assert (await sync_to_async(TeamMember.objects.get)(name="Prof. Anil Sharma")).designation == "Professor"


async def test_validation_errors_name_the_field(asgi_app, token):
    await seed()
    async with mcp_client(asgi_app, token) as client:
        m = await find_one(client, "Sharma")
        v = m["version"]
        assert err(await call(client, "update_team_member", {"id": m["id"], "fields": {"salary": 1},
                                                             "expected_version": v}), "CMS_VALIDATION")["field"] == "salary"
        assert err(await call(client, "update_team_member", {"id": m["id"], "fields": {"designation": "x" * 300},
                                                             "expected_version": v}), "CMS_VALIDATION")["field"] == "designation"
        assert err(await call(client, "update_team_member", {"id": m["id"], "fields": {"category": "Aliens"},
                                                             "expected_version": v}), "CMS_VALIDATION")["field"] == "category"
        err(await call(client, "update_team_member", {"id": m["id"], "fields": {}, "expected_version": v}), "CMS_VALIDATION")
        err(await call(client, "update_team_member", {"id": m["id"], "fields": {"name": "X"}, "expected_version": "abc"}),
            "CMS_VALIDATION")
        err(await call(client, "update_team_member", {"id": "home.hero.hero-slides:1", "fields": {"name": "X"},
                                                      "expected_version": 1}), "CMS_VALIDATION")
        err(await call(client, "update_section", {"id": "team.members.team-members:9999", "fields": {"name": "X"},
                                                  "expected_version": 1}), "CMS_NOT_FOUND")
        err(await call(client, "update_section", {"id": "../../etc", "fields": {"name": "X"},
                                                  "expected_version": 1}), "CMS_NOT_FOUND")


async def test_update_section_singleton_and_richtext(asgi_app, token):
    await seed()

    @sync_to_async
    def innovation():
        from apps.innovations.models import Innovation
        return Innovation.objects.create(title="Eye scanner", body="<p>old</p>", order=0).pk
    pk = await innovation()
    async with mcp_client(asgi_app, token) as client:
        home = ok(await call(client, "get_page", {"page": "home"}))
        item = next(s for s in home["sections"] if s["kind"] == "singleton")["item"]
        ok(await call(client, "update_section", {"id": item["id"], "fields": {"objective_text": "New objective"},
                                                 "expected_version": item["version"]}))
        inno = next(s for s in ok(await call(client, "get_page", {"page": "innovations"}))["sections"])["items"][0]
        assert inno["id"] == f"innovations.list.innovations:{pk}"
        err(await call(client, "update_section", {"id": inno["id"], "fields": {"body": "<script>x</script>"},
                                                  "expected_version": inno["version"]}), "CMS_VALIDATION")
        ok(await call(client, "update_section", {"id": inno["id"], "expected_version": inno["version"], "fields": {
            "body": [{"type": "heading", "text": "What it does"},
                     {"type": "paragraph", "text": [{"text": "Screens <eyes>", "bold": True},
                                                    {"text": " more", "link": "https://example.org"}]},
                     {"type": "bulleted_list", "items": ["fast", [{"text": "cheap", "italic": True}]]}]}}))

    from apps.core.models import HomePage
    from apps.innovations.models import Innovation
    assert (await sync_to_async(HomePage.load)()).objective_text == "New objective"
    body = (await sync_to_async(Innovation.objects.get)(pk=pk)).body
    assert body == ('<h3>What it does</h3><p><strong>Screens &lt;eyes&gt;</strong><a href="https://example.org"> more</a>'
                    '</p><ul><li>fast</li><li><em>cheap</em></li></ul>')


# ---------------------------------------------------------------- creates, dedupe, images
async def test_add_team_member_dedupes_in_session(asgi_app, token):
    await seed()
    async with mcp_client(asgi_app, token) as client:
        fields = {"name": "Dr. Rahul Sen", "category": "Staff", "designation": "Engineer"}
        first = ok(await call(client, "add_team_member", {"fields": fields}))
        assert first["deduplicated"] is False and first["change"] == "added"
        again = ok(await call(client, "add_team_member", {"fields": fields}))
        assert again["deduplicated"] is True and again["id"] == first["id"]
        err(await call(client, "add_team_member", {"fields": {"name": "No Category"}}), "CMS_VALIDATION")

    from apps.team.models import TeamMember
    assert await sync_to_async(TeamMember.objects.filter(name="Dr. Rahul Sen").count)() == 1
    assert await sync_to_async(ConnectorWrite.objects.count)() == 1


async def test_add_hero_slide_checks_photo_width(asgi_app, editor, token):
    small = await sync_to_async(stage_image)(editor, 800, 450)
    big = await sync_to_async(stage_image)(editor, 2400, 1350)
    stranger_photo = await sync_to_async(stage_image)(await sync_to_async(make_user)("x"), 2400, 1350)
    async with mcp_client(asgi_app, token) as client:
        tiny = err(await call(client, "add_hero_slide", {"fields": {"image": small, "heading": "Eye camp"}}),
                   "CMS_IMAGE_TOO_SMALL")
        assert "1600" in tiny["message"] and "800" in tiny["message"]
        err(await call(client, "add_hero_slide", {"fields": {"image": stranger_photo, "heading": "x"}}), "CMS_NOT_FOUND")
        err(await call(client, "add_hero_slide", {"fields": {"heading": "no photo"}}), "CMS_VALIDATION")
        res = ok(await call(client, "add_hero_slide", {"fields": {"image": big, "heading": "Free eye camp, 12 Dec"}}))
        assert res["id"].startswith("home.hero.hero-slides:")


async def test_add_media_event_with_photos(asgi_app, editor, token):
    await seed()
    photos = [await sync_to_async(stage_image)(editor, 1600, 1000) for _ in range(2)]
    async with mcp_client(asgi_app, token) as client:
        res = ok(await call(client, "add_media_event", {"fields": {
            "title": "Eye camp, Salua", "event_date": "2026-12-12", "category": "health-camps",
            "photos": [{"media_id": photos[0], "caption": "Screening"}, photos[1]]}}))
        assert res["page"] == "media"
        err(await call(client, "add_media_event", {"fields": {"title": "Bad date", "event_date": "12/12/2026"}}),
            "CMS_VALIDATION")
        err(await call(client, "add_media_event", {"fields": {"title": "Bad cat", "category": "parties"}}), "CMS_VALIDATION")

    from apps.media_gallery.models import MediaEvent
    event = await sync_to_async(MediaEvent.objects.prefetch_related("images").get)(title="Eye camp, Salua")
    assert event.slug == "eye-camp-salua" and str(event.event_date) == "2026-12-12"
    assert [i.caption for i in event.images.all()] == ["Screening", ""]


async def test_add_news_item_and_generic_add_item(asgi_app, token):
    await seed()
    async with mcp_client(asgi_app, token) as client:
        ok(await call(client, "add_news_item", {"fields": {"text": "Eye camp on 12 Dec", "link_url": "/media"}}))
        err(await call(client, "add_news_item", {"fields": {"text": "x", "link_url": "javascript:alert(1)"}}),
            "CMS_VALIDATION")
        res = ok(await call(client, "add_item", {"section": "media.coverage", "fields": {
            "title": "The Telegraph", "url": "https://example.org/article"}}))
        assert res["id"].startswith("media.coverage.media-coverage-links:")
        err(await call(client, "add_item", {"section": "home.about", "fields": {}}), "CMS_VALIDATION")
        err(await call(client, "add_item", {"section": "no.such", "fields": {}}), "CMS_NOT_FOUND")


# ---------------------------------------------------------------- hide, reorder, discard
async def test_hide_reorder_and_discard(asgi_app, token):
    data = await seed()
    async with mcp_client(asgi_app, token) as client:
        hero = next(s for s in ok(await call(client, "get_page", {"page": "home"}))["sections"] if s["id"] == "home.hero")
        third = hero["items"][2]
        ok(await call(client, "hide_hero_slide", {"id": third["id"], "expected_version": third["version"]}))
        news = next(s for s in ok(await call(client, "get_page", {"page": "home"}))["sections"] if s["id"] == "home.news")
        err(await call(client, "hide_item", {"id": news["items"][0]["id"], "expected_version": 0}), "CMS_VALIDATION")
        ids = [i["id"] for i in hero["items"]]
        err(await call(client, "reorder", {"section": "home.hero", "ids": ids[:2]}), "CMS_VALIDATION")
        ok(await call(client, "reorder", {"section": "home.hero", "ids": list(reversed(ids))}))
        pending = ok(await call(client, "list_pending_changes", {}))
        assert pending["count"] == 2 and pending["pages"][0]["page"] == "home"
        assert all(c["this_conversation"] for c in pending["pages"][0]["changes"])
        ok(await call(client, "discard_change", {"id": third["id"]}))
        err(await call(client, "discard_change", {"id": third["id"]}), "CMS_NOT_FOUND")
        ok(await call(client, "discard_session_changes", {}))
        assert ok(await call(client, "list_pending_changes", {}))["count"] == 0

    from apps.carousel.models import HeroSlide
    slides = await sync_to_async(lambda: list(HeroSlide.objects.order_by("order").values_list("pk", "is_published")))()
    assert slides == [(s.pk, True) for s in data["slides"]]


# ---------------------------------------------------------------- photos and review
async def test_upload_image_from_url_and_search_media(asgi_app, token, monkeypatch):
    from mcp_server import cms

    from .conftest import png_bytes
    monkeypatch.setattr(cms, "fetch_image_bytes", lambda url, **kw: (png_bytes(2000, 1200), "photos.iitkgp.ac.in/a.png"))
    async with mcp_client(asgi_app, token) as client:
        first = ok(await call(client, "upload_image_from_url", {"url": "https://photos.iitkgp.ac.in/a.png"}))
        assert first["media_id"].startswith("media:") and first["width"] == 2000
        again = ok(await call(client, "upload_image_from_url", {"url": "https://photos.iitkgp.ac.in/a.png"}))
        assert again["media_id"] == first["media_id"] and again["deduplicated"] is True
        found = ok(await call(client, "search_media", {"query": "iitkgp"}))["media"]
        assert [m["media_id"] for m in found] == [first["media_id"]]
        monkeypatch.undo()
        blocked = err(await call(client, "upload_image_from_url", {"url": "http://10.0.0.1/x.png"}), "CMS_FETCH_BLOCKED")
        assert blocked["field"] == "url"


async def test_request_upload_link_unavailable_until_core(asgi_app, token):
    async with mcp_client(asgi_app, token) as client:
        body = err(await call(client, "request_upload_link", {}), "CMS_INTERNAL")
        assert body["retryable"] is False and "upload_image_from_url" in body["fix"]


async def test_request_review_emails_publishers_never_publishes(asgi_app, token):
    await sync_to_async(make_user)("pub", role="publisher", email="pub@example.org")
    await sync_to_async(make_user)("ed2", role="editor", email="ed2@example.org")
    mail.outbox.clear()
    async with mcp_client(asgi_app, token) as client:
        res = ok(await call(client, "request_review", {"note": "Updated Prof. Sharma"}))
    assert res["notified"] == 1 and res["status"] == "waiting_for_review"
    assert mail.outbox[0].to == ["pub@example.org"] and "Updated Prof. Sharma" in mail.outbox[0].body


# ---------------------------------------------------------------- guardrails
async def test_session_cap(asgi_app, token, settings):
    settings.CMS_SESSION_LIMIT = 3
    await seed()
    async with mcp_client(asgi_app, token) as client:
        for i in range(3):
            res = ok(await call(client, "add_news_item", {"fields": {"text": f"news {i}"}}))
        assert res["changes_left_in_session"] == 0
        body = err(await call(client, "add_news_item", {"fields": {"text": "one too many"}}), "CMS_SESSION_LIMIT")
        assert body["retryable"] is False
        ok(await call(client, "find_content", {"query": "news"}))  # reads still work
    # a new conversation (new MCP session) starts a fresh count
    from mcp_server.app import build_app

    async with mcp_client(build_app(), token) as client:
        ok(await call(client, "add_news_item", {"fields": {"text": "new session"}}))


async def test_write_rate_limit(asgi_app, token, settings):
    settings.MCP_WRITE_RATE_LIMIT_PER_MINUTE = 2
    await seed()
    async with mcp_client(asgi_app, token) as client:
        ok(await call(client, "add_news_item", {"fields": {"text": "a"}}))
        ok(await call(client, "add_news_item", {"fields": {"text": "b"}}))
        assert err(await call(client, "add_news_item", {"fields": {"text": "c"}}), "CMS_RATE_LIMITED")["retryable"] is True


async def test_every_call_is_audited(asgi_app, editor, token):
    await seed()
    async with mcp_client(asgi_app, token) as client:
        await call(client, "find_content", {"query": "Sharma"})
        await call(client, "get_page", {"page": "nope"})
    rows = await sync_to_async(lambda: list(ToolCall.objects.order_by("id").values(
        "user_id", "tool", "outcome", "session_key", "arg_names")))()
    assert [(r["tool"], r["outcome"]) for r in rows] == [("find_content", "ok"), ("get_page", "CMS_NOT_FOUND")]
    assert all(r["user_id"] == editor.pk and r["session_key"] for r in rows)
    assert rows[0]["arg_names"] == "query"
