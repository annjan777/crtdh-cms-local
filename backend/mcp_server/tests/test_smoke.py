import pytest

from .conftest import mcp_client

pytestmark = pytest.mark.django_db(transaction=True)


async def test_list_tools_and_find(asgi_app, token):
    from apps.team.models import TeamCategory, TeamMember
    from asgiref.sync import sync_to_async

    @sync_to_async
    def seed():
        cat = TeamCategory.objects.create(name="Faculty")
        TeamMember.objects.create(category=cat, name="Prof. Anil Sharma", designation="Professor")
    await seed()
    async with mcp_client(asgi_app, token) as client:
        tools = await client.list_tools()
        assert "find_content" in {t.name for t in tools.tools}
        res = await client.call_tool("find_content", {"query": "Sharma"})
        assert not res.is_error, res
        assert res.structured_content["matches"][0]["label"] == "Prof. Anil Sharma"
